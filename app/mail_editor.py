# Copyright 2010 by Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Accepts and processes email messages containing subject updates."""

__author__ = 'pfritzsche@google.com (Phil Fritzsche)'

import email
import logging
import re
import string
from datetime import datetime

from google.appengine.api.labs import taskqueue
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler

import cache
import model
import utils
from utils import db, split_key_name

# TODO(pfritzsche): taken from Ping's new CL (with minor changes);
# when it has been submitted, remove this function from this file
# and make call to feeds_delta.py instead.
def update_subject(subject, observed, account, source_url, values, comments={},
                   arrived=None):
    """Applies a set of changes to a single subject with a single author,
    producing one new Report and updating one Subject and one MinimalSubject.
    'account' can be any object with 'user', 'nickname', and 'affiliation'
    attributes.  'values' and 'comments' should both be dictionaries with
    attribute names as their keys."""

    # SubjectType and Attribute entities are in separate entity groups from
    # the Subject, so we have to obtain them outside of the transaction.
    subdomain, subject_name = split_key_name(subject)
    subject_type = cache.SUBJECT_TYPES[subdomain][subject.type]
    minimal_attribute_names = subject_type.minimal_attribute_names
    editable_attributes = []
    for name in subject_type.attribute_names:
        attribute = cache.ATTRIBUTES[name]
        if utils.can_edit(account, subdomain, attribute):
            editable_attributes.append(name)

    # We'll use these to fill in the metadata on the subject.
    user_id = account.user_id
    nickname = account.nickname
    affiliation = account.affiliation

    # The real work happens here.
    def work(transactional=True):
        # We want to transactionally update the Report, Subject, and
        # MinimalSubject, so reload the Subject inside the transaction.
        subject = model.Subject.get(subdomain, subject_name)
        minimal_subject = model.MinimalSubject.get_by_subject(subject)

        # Create an empty Report.
        report = model.Report(
            subject,
            observed=observed,
            author=account.user_id,
            source=source_url,
            arrived=arrived or DateTime.utcnow())

        # Fill in the new values on the Report and update the Subject.
        change_information = []
        unchanged_values = {}
        subject_changed = False
        for name in values:
            if name in editable_attributes:
                report.set_attribute(name, values[name], comments.get(name))
                last_observed = subject.get_observed(name)
                # Only update the Subject if the incoming value is newer.
                if last_observed is None or last_observed < observed:
                    subject_changed = True
                    change_information.append({
                        'attribute': name,
                        'old_value': subject.get_value(name),
                        'new_value': values[name],
                        'author': nickname
                    })
                    subject.set_attribute(
                        name, values[name], observed, user_id, nickname,
                        affiliation, comments.get(name))
                    if name in minimal_attribute_names:
                        minimal_subject.set_attribute(name, values[name])
                else:
                    unchanged_values[name] = values[name]
            else:
                unchanged_values[name] = values[name]

        # Store the new Report.
        db.put(report)

        # If the Subject has been modified, store it and flush the cache.
        if subject_changed:
            db.put([subject, minimal_subject])
            cache.MINIMAL_SUBJECTS[subdomain].flush()
            cache.JSON[subdomain].flush()

            params = {
                'action': 'subject_changed',
                'user_email': account.email,
                'subject_name': subject.key().name(),
                'observed': utils.url_pickle(observed),
                'changed_data': utils.url_pickle(change_information),
                'unchanged_data': utils.url_pickle(unchanged_values)
            }

            # Schedule a task to e-mail users who have subscribed to this
            # subject.
            taskqueue.add(method='POST', url='/mail_alerts',
                          params=params, transactional=transactional)

    db.run_in_transaction(work)


class HospitalMailParser:
    def __init__(self):
        self.unsupported = ['services', 'organization_type', 'category',
                            'construction', 'operational_status']

    def parse_updates(self, update_lines, subject, subject_type, quoted):
        updates = []
        errors = []
        for update in update_lines:
            update = update.split()
            if not update:
                continue

            if quoted:
                update = [word for word in update if
                          re.match('\w+', word, flags=re.UNICODE)]
            for i in range(4):
                # Automate the generation of potential atribute names from the
                # line; hospital attribute names are between 1 and 4 words long.
                # This checks each line for any potential attribute name
                # that fits this length description.
                index = 4 - i
                if len(update) <= index:
                    continue
                attribute_name = '_'.join(update[:index]).lower()
                if attribute_name in subject_type.attribute_names:
                    if self.supported(attribute_name):
                        try:
                            value = self.parse(attribute_name, update, index)
                            updates.append((attribute_name, value))
                        except:
                            errors.append(('Bad value', update))
                    else:
                        errors.append(
                            ('Unsupported attribute or value', update))
                    # Break to remove the situation where substrings of an
                    # attribute name may also be counted [i.e. commune and
                    # commune_code]; users who really want to set the "commune"
                    # attribute to the value "code" must escape code with "'s.
                    break
        return updates, errors

    def parse(self, attribute_name, update, index):
        """Parses a list of Unicode strings into an attribute value."""
        type = cache.ATTRIBUTES[attribute_name].type
        if type in ['str', 'text']:
            return ' '.join(update[index:])
        if type == 'int':
            return int(update[index])
        if type == 'float':
            return float(update[index])
        if type == 'bool':
            return bool(update[index].lower() in ['y', 'yes', 'true'])
        if type == 'geopt':
            return db.GeoPt(*map(float, string.split(',')))

    def supported(self, attribute_name):
        return attribute_name not in self.unsupported


UPDATE_PARSER = {
    'haiti': {
        'hospital': HospitalMailParser
    }
}


class MailEditor(InboundMailHandler):
    def authenticate(self, message):
        self.account = model.Account.all().filter(
            'email =', message.sender).get()
        return self.account.nickname and self.account.affiliation

    def is_authentication(self, message):
        if self.account:
            return
        for content_type, body in message.bodies('text/html'):
            body = body.decode()
            grep_base = string.Template('\n$name\s+(?P<$name>\w+(?:\s+\w+)*)\n')
            nickname_match = re.match(
                grep_base.substitute({'name': 'nickname'}),
                body, flags=re.UNICODE | re.I)
            affiliation_match = re.match(
                grep_base.substitute({'name': 'affiliation'}),
                body, flags=re.UNICODE | re.I)
            if nickname_match and affiliation_match:
                nickname = nickname_match.group('nickname')
                affiliation = affiliation_match.group('affiliation')
                self.account = Account(
                    key_name=message.sender,
                    email=message.sender,
                    description=email,
                    nickname=nickname,
                    affiliation=affiliation,
                    locale='en',
                    default_frequency='instant',
                    email_format='plain')
                db.put(self.account)

    def receive(self, message):
        if not self.authenticate(message) or self.is_authentication(message):
            self.send_authentication_email()
        else:
            for content_type, body in message.bodies('text/html'):
                updates, errors = self.parse_email(body.decode())
                if updates:
                    date_format = '%a, %d %b %Y %H:%M:%S'
                    observed = datetime.strptime(message.date[:-6], date_format)
                    self.update_subjects(updates, observed)
                    logging.info('mail_editor.py: update received from %s' %
                                 message.sender)
                    self.send_confirmation_email(message, updates, errors)

    def parse_email(self, body):
        updates_all = []
        errors_all = []
        grep_base = 'UPDATE )(?P<title>\w+(?:\s+\w+)*)*\s*\(' + \
                    '(?P<subdomain>\w+)\s(?P<healthc_id>\w+)\)'
        unquoted_grep = '(?<=\n%s' % grep_base
        quoted_grep = '.+(?<=%s' % grep_base
        match = re.finditer(unquoted_grep, body, flags=re.UNICODE)
        quoted_match = re.finditer(quoted_grep, body, flags=re.UNICODE)

        def process(subject_match, quoted=False):
            start = subject_match.end()
            end = body.find('UPDATE', start + 1)
            update_lines = body[start:end].split('\n')
            subdomain = subject_match.group('subdomain')
            subject = model.Subject.all_in_subdomain(subdomain).filter(
                'healthc_id__ =', subject_match.group('healthc_id')).get()
            subject_type = cache.SUBJECT_TYPES[subdomain][subject.type]
            processor = UPDATE_PARSER[subdomain][subject.type]()
            updates, errors = processor.parse_updates(update_lines, subject,
                                                      subject_type, quoted)
            if updates:
                updates_all.append((subject, updates))
            if errors:
                errors_all.append((subject, errors))

        for subject_match in match:
            process(subject_match)
        if not updates_all and not errors_all:
            for subject_match in quoted_match:
                process(subject_match, True)
        return updates_all, errors_all

    def update_subjects(self, updates, observed, comment=''):
        for update in updates:
            subject, update_info = update
            source = 'email: %s' % self.account.email
            values = dict(update_info)
            update_subject(subject, observed, self.account, source, values,
                           arrived=observed)

    def send_confirmation_email(self, original_message, updates, errors):
        """        locale = self.account.get('locale', 'en')
        path = os.path.join(os.path.dirname(__file__),
                            'locale/%s/update_confirmation_email.txt' % locale)
        body = template.render(path, updates=updates, received=message.date)
        message = mail.EmailMessage(
            sender='updates@resource-finder.appspot.com',
            to=original_message.sender,
            subject=original_message.subject,
            body=body)
        message.send()"""
        logging.info('confirmation sent!')

if __name__ == '__main__':
    utils.run([MailEditor.mapping()], debug=True)
