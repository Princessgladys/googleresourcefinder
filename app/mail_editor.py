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

"""Accepts and processes email messages containing subject updates.

Receives any email addressed to 'updates@resource-finder.appspotmail.com'.
Parses through the email in the form described at /help/email. Confirms any
changes to the user as well as any errors that were discovered in the
received update.

    get_updates(): given an update section of a received email, finds any
        updates and errors present
    parse(): parses a list of unicode strings into datastore-friendly objects
    MailEditor: incoming mail handler-- responds to incoming emails addressed to
        updates@resource-finder@appspotmail.com
    format_changes(): helper function to format attribute value tuples
"""

__author__ = 'pfritzsche@google.com (Phil Fritzsche)'

import email
import logging
import os
import re
import string
from datetime import datetime

from google.appengine.api import mail
from google.appengine.api.labs import taskqueue
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler

import cache
import model
import utils
from utils import db, format, order_and_format_updates, split_key_name

STOP_DELIMITER = '--- --- --- ---'

# TODO(pfritzsche): taken from Ping's new CL (with some changes);
# when it has been submitted, remove this function from this file
# and make merge it with the one from feeds_delta.py.
def update_subject(subject, observed, account, source_url, values, comments={},
                   arrived=None):
    """Applies a set of changes to a single subject with a single author,
    producing one new Report and updating one Subject and one MinimalSubject.
    'account' can be any object with 'user', 'nickname', and 'affiliation'
    attributes. 'values' and 'comments' should both be dictionaries with
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
                # Only update the Subject if the incoming value is newer and the
                # new value does not equal the old value.
                if (last_observed is None or last_observed < observed and
                    subject.get_value(name) != values[name]):
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


def get_updates(update_lines, subject, subject_type, quoted, unsupported):
    """Given a set of text for a specific subject, this will locate all
    attribute / value pair updates as well as detect any errors present in
    the update text of the email.

    Args:
        update_lines: a list of lines from the email to be analyzed
        subject: the subject these lines pertain to
        subject_type: the type of the subject in question
        quoted: (bool) whether or not these lines are from a quote
            section of email or a non-quoted section of email
        unsupported: a list of unsupported attribute names

    Returns:
        updates: a list of update tuples (attribute, value)
        errors: a list of error tuples (error_message, error_line)
        stop: if the stop delimeter was found, returns True to let the outer
            loop know to stop; returns False if it is ok to keep processing
    """
    stop = False
    updates = []
    errors = []
    for update in update_lines:
        if STOP_DELIMITER in update:
            stop = True
            break
        update_split = update.split()
        if not update:
            continue

        if quoted:
            update_split = [word for word in update_split if
                            re.match('\w+', word, flags=re.UNICODE)]
        for i in range(5, 0, -1):
            # Automate the generation of potential atribute names from the
            # line; hospital attribute names are between 1 and 4 words long.
            # This checks each line for any potential attribute name
            # that fits this length description.
            if len(update) <= i:
                continue
            attribute_name = '_'.join(update_split[:i]).lower()
            if attribute_name in subject_type.attribute_names:
                if attribute_name not in unsupported:
                    try:
                        value = parse(attribute_name, update_split, i)
                        updates.append((attribute_name, value))
                    except ValueError, error:
                        msg = ('"%s" is not a valid value for %s' %
                               (' '.join(update_split[i:]), attribute_name))
                        errors.append((msg, update))
                else:
                    errors.append(
                        ('Unsupported attribute', update))
                # Break to remove the situation where substrings of an
                # attribute name may also be counted [i.e. commune and
                # commune_code]; users who really want to set the "commune"
                # attribute to the value "code" must escape code with "'s.
                break
    return updates, errors, stop


def parse(attribute_name, update, index):
    """Parses a list of Unicode strings into an attribute value."""
    type = cache.ATTRIBUTES[attribute_name].type
    if type in ['str', 'text']:
        value = ' '.join(update[index:])
        # Users wishing to escape string values so as not to be counted as
        # an attribute name by mistake may do so by surrounding the value
        # in quotes. Remove them here for the actual value if they exist.
        if value[0] == '"' and value[-1] == '"':
            value = value[1:-1]
        return value
    if type == 'int':
        return int(update[index])
    if type == 'bool':
        return bool(update[index].lower() in ['y', 'yes', 'true'])


UNSUPPORTED_ATTRIBUTES = {
    'haiti': {
        'hospital': ['services', 'organization_type', 'category',
                     'construction', 'operational_status']
    }
}


class MailEditor(InboundMailHandler):
    """Primary handler for inbound emails targeting
    updates@resource-finder.appspotmail.com.

    Args:
        account: the account of the user the email is from

    Methods:
        authenticate: checks to see if the email is from a valid account
        is_authentication: checks to see if the email includes
            authenticating text
        receive: override function- triggered when an email is received
        process_email: searches the text of an email for updates and errors
        update_subjects: updates the datastore with all valid updates
        send_email: sends a response/confirmation email to the user
    """

    def authenticate(self, message):
        """Checks to see if the email is from a user with an existing account.
        Account must have both a nickname and affiliation to be considered valid
        for submission to the datastore. Returns True if the account exists."""
        self.account = model.Account.all().filter(
            'email =', message.sender).get()
        return (self.account and self.account.nickname and
                self.account.affiliation)

    def is_authentication(self, message):
        """Checks to see if the email contains a nickname and affiliation for
        entry into the database. If both are found, creates a new account for
        the user and inserts it into the datastore then returns True. Returns
        False if no such information is found."""
        def regex(s, text):
            exp = '^%s\s+(?P<%s>.+)' % (s, s)
            return re.search(exp, text, flags=re.UNICODE | re.I | re.MULTILINE)
        if self.account:
            return
        for content_type, body in message.bodies('text/html'):
            body = body.decode()
            nickname_match = regex('nickname', body)
            affiliation_match = regex('affiliation', body)
            if nickname_match and affiliation_match:
                nickname = nickname_match.group('nickname')
                affiliation = affiliation_match.group('affiliation')
                self.account = model.Account(
                    key_name=message.sender, email=message.sender,
                    description=message.sender, nickname=nickname,
                    affiliation=affiliation, locale='en',
                    default_frequency='instant', email_format='plain')
                db.put(self.account)
                return self.account

    def receive(self, message):
        """Overrides InboundMailHandler. Runs when a new message is received.

        Authenticates the email, then locates any updates and/or errors in the
        body of the email. If any updates are found, they are inserted into the
        datastore. If any updates or errors are found, or the email is not yet
        authorized to submit, then a response email is sent detailing any
        new information and/or problems.
        """
        self.need_authentication = False
        if not (self.authenticate(message) or self.is_authentication(message)):
            self.need_authentication = True
        for content_type, body in message.bodies():
            updates, errors = self.process_email(body.decode())
            if updates:
                date_format = '%a, %d %b %Y %H:%M:%S'
                observed = datetime.strptime(message.date[:-6], date_format)
                if not self.need_authentication:
                    self.update_subjects(updates, observed)
                logging.info('mail_editor.py: update received from %s' %
                             message.sender)
                self.send_email(message, updates, errors)
                break

    def process_email(self, body):
        """Given the body of an email, locates updates from the user.

        Searches for unquoted regions first. If no valid updates are found in
        an unquoted section of the email, it then looks for updates in the
        quoted sections of the email.
        """
        updates_all = []
        errors_all = []
        stop = False
        grep_base = 'UPDATE )(?P<title>\w+(?:\s+\w+)*)*\s*\(' + \
                    '(?P<subdomain>\w+)\s(?P<healthc_id>\w+)\)'
        unquoted_grep = '(?<=^%s' % grep_base
        quoted_grep = '.+(?<=%s' % grep_base
        flags = re.UNICODE | re.MULTILINE
        match = re.finditer(unquoted_grep, body, flags=flags)
        quoted_match = re.finditer(quoted_grep, body, flags=flags)

        # work happens here
        def process(subject_match, quoted=False):
            start = subject_match.end()
            end = body.find('UPDATE', start + 1)
            if end == -1:
                update_lines = body[start:].split('\n')
            else:
                update_lines = body[start:end].split('\n')
            subdomain = subject_match.group('subdomain')
            healthc_id = subject_match.group('healthc_id')
            subject = model.Subject.all_in_subdomain(subdomain).filter(
                'healthc_id__ =', healthc_id).get()
            subject_type = cache.SUBJECT_TYPES[subdomain][subject.type]
            unsupported = UNSUPPORTED_ATTRIBUTES[subdomain][subject.type]
            updates, errors, stop = get_updates(
                update_lines, subject, subject_type, quoted, unsupported)
            if updates:
                updates_all.append((subject, updates))
            if errors:
                errors_all.append((subject, errors))
            return stop

        for subject_match in match:
            if stop:
                break
            stop = process(subject_match)
        if not updates_all and not errors_all:
            for subject_match in quoted_match:
                if stop:
                    break
                stop = process(subject_match, True)
        return updates_all, errors_all

    def update_subjects(self, updates, observed, comment=''):
        """Goes through the supplied list of updates. Adds to the datastore."""
        for update in updates:
            subject, update_info = update
            source = 'email: %s' % self.account.email
            values = dict(update_info)
            update_subject(subject, observed, self.account, source, values,
                           arrived=observed)

    def send_email(self, original_message, updates, errors):
        """Sends a response email to the user if necessary.

        If the user is not yet authorized to post, includes information on how
        to authorize themself. Also includes a list of all accepted updates and
        a list of any errors found in the update text that was submitted.
        """
        if self.account:
            locale = self.account.locale or 'en'
            nickname = self.account.nickname or self.account.email
        else:
            locale = 'en'
            nickname = original_message.sender

        formatted_updates = []
        for update in updates:
            subject, update_data = update
            subdomain, subject_name = split_key_name(subject)
            subject_type = cache.SUBJECT_TYPES[subdomain][subject.type]
            formatted_updates.append({
                'subject_title': subject.get_value('title'),
                'subdomain': subdomain,
                'healthc_id': subject.get_value('healthc_id'),
                'changed_attributes': order_and_format_updates(
                    update_data, subject_type, locale, format_changes, 0)
            })

        formatted_errors = []
        for error in errors:
            subject, error_data = error
            subdomain, subject_name = split_key_name(subject)
            formatted_errors.append({
                'subject_title': subject.get_value('title'),
                'subdomain': subdomain,
                'healthc_id': subject.get_value('healthc_id'),
                'data': error_data
            })

        template_values = {
            'nickname': nickname,
            'updates': formatted_updates,
            'errors': formatted_errors,
            'authenticate': self.need_authentication
        }
        path = os.path.join(os.path.dirname(__file__),
                            'locale/%s/update_response_email.txt' % locale)
        body = template.render(path, template_values)
        subject_base = 'Resource Finder Updates'
        subject = 'ERROR - %s' % subject_base if errors else subject_base
        message = mail.EmailMessage(
            sender='updates@resource-finder.appspotmail.com',
            to=original_message.sender,
            subject=subject,
            body=body)
        message.send()


def format_changes(update, locale):
    """Helper function; used to format an attribute, value pair for email."""
    attribute, value = update
    return {
        'attribute': attribute.replace('_', ' ').capitalize(),
        'value': format(value)
    }

if __name__ == '__main__':
    utils.run([MailEditor.mapping()], debug=True)
