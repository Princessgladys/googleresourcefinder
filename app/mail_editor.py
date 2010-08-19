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
from utils import db, format, order_and_format_updates

# If this is found in a line of the email, the system will immediately stop
# parsing and ignore the remainder of the email.
STOP_DELIMITER = '--- --- --- ---'

# TODO(pfritzsche): taken from Ping's new CL (with some changes);
# when it has been submitted, remove this function from this file
# and merge it with the one from feeds_delta.py.
def update_subject(subject, observed, account, source_url, values, comments={},
                   arrived=None):
    """Applies a set of changes to a single subject with a single author,
    producing one new Report and updating one Subject and one MinimalSubject.
    'account' can be any object with 'user', 'nickname', and 'affiliation'
    attributes. 'values' and 'comments' should both be dictionaries with
    attribute names as their keys."""

    # SubjectType and Attribute entities are in separate entity groups from
    # the Subject, so we have to obtain them outside of the transaction.
    subdomain = subject.get_subdomain()
    subject_name = subject.get_name()
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


# TODO(pfritzsche): Add support for all attributes.
UNSUPPORTED_ATTRIBUTES = {
    'haiti': {
        'hospital': ['services', 'organization_type', 'category',
                     'construction', 'operational_status']
    },
    'pakistan': {
        'hospital': ['services', 'organization_type', 'category',
                     'construction', 'operational_status']
    }
}


def match_nickname_affiliation(s, text):
    """For the supplied string s, try to find a match in text containing
    the string s, followed by whitespace and then extra text. The extra text
    will be accessible by the group name s.
    """
    if not s:
        return
    exp = r'^%s\s+(?P<%s>.+)' % (s, s)
    match = re.search(exp, text, flags=re.UNICODE | re.I | re.MULTILINE)
    return match and match.group(s) or None


def match_email(text):
    """Given a string, tries to find a regex match for an email."""
    email_regex = r'(.+\s+)*(<)*\s*(?P<email>\w+(?:.+\w+)*@\w+(?:\.\w+)+)(>)*'
    match = re.match(email_regex, text)
    if match:
        return match.group('email')


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
    def init(self, message):
        self.domain = self.request.headers['Host']
        # Pulls out the email address from any string
        self.email = match_email(message.sender)

        # Initialize regexes for finding subjects to update from the email
        unquoted_base = '^' # beginning of a regex for an unquoted line
        quoted_base = '^(?P<quotes>\W+)' # beginning for a quoted line
        regex_wo_key = r'update\s+(?P<title>.*)' # match a line with no key
        regex_w_key = r'%s\s*\((?P<subject_name>.+/.+)\)' % regex_wo_key
        # ^ match a line that contains a key and possibly the subject's title
        self.update_line_flags = re.UNICODE | re.MULTILINE | re.I
        self.update_line_regexes = []
        for base in [unquoted_base, quoted_base]:
            self.update_line_regexes.append([
                base + regex_w_key,
                base + regex_wo_key
            ])

        self.subdomain = message.to[:message.to.find('-')]

    def validate_subdomain(self):
        """Checks to make sure the user-supplied subdomain is legitimate."""
        return model.Subdomain.get_by_key_name(self.subdomain)

    def authenticate(self, message):
        """Checks to see if the email is from a user with an existing account.
        Account must have both a nickname and affiliation to be considered valid
        for submission to the datastore. Returns True if the account exists."""
        self.account = model.Account.all().filter(
            'email =', self.email).get()
        return (self.account and self.account.nickname and
                self.account.affiliation)

    def is_authentication(self, message):
        """Checks to see if the email contains a nickname and affiliation for
        entry into the database. If both are found, creates a new account for
        the user and inserts it into the datastore then returns True. Returns
        False if no such information is found."""
        if self.account and self.account.nickname and self.account.affiliation:
            return
        # TODO(pfritzsche): Add HTML support.
        for content_type, body in message.bodies('text/plain'):
            body = body.decode()
            nickname = match_nickname_affiliation('nickname', body)
            affiliation = match_nickname_affiliation('affiliation', body)
            if nickname and affiliation:
                self.account = self.account or model.Account(
                    email=self.email, description=message.sender,
                    locale='en', default_frequency='instant',
                    email_format='plain')
                self.account.nickname = nickname
                self.account.affiliation = affiliation
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
        self.init(message)
        self.need_authentication = not (self.authenticate(message) or
                                        self.is_authentication(message))
        if not self.validate_subdomain():
            # TODO(pfritzsche): Add better handling of invalid subdomain
            self.send_email(message, [], [], [], no_subdomain=True)
            return
        # TODO(pfritzsche): Add HTML support.
        for content_type, body in message.bodies('text/plain'):
            updates, errors, ambiguities = self.process_email(body.decode())
            if updates or errors or ambiguities:
                date_format = '%a, %d %b %Y %H:%M:%S'
                observed = datetime.strptime(message.date[:-6], date_format)
                if updates and not self.need_authentication:
                    self.update_subjects(updates, observed)
                logging.info('mail_editor.py: update received from %s' %
                             self.email)
                self.send_email(message, updates, errors, ambiguities)
            else:
                self.send_email(message, [], [], [])
            break # to only pay attention to the first body found

    def process_email(self, body):
        """Given the body of an email, locates updates from the user.

        Searches for unquoted regions first. If no valid updates are found in
        an unquoted section of the email, it then looks for updates in the
        quoted sections of the email.
        """
        updates_all = [] # list of tuples (subject, updates for the subject)
        errors_all = [] # list of tuples (error message, line in question)
        ambiguous_all = [] # list of tuples (potential subjects, given updates)
        stop = False

        # work happens here
        def process(match, quoted=False):
            for subject_match in match:
                errors = []
                updates = []
                ambiguity = False
                if 'subject_name' in subject_match.groupdict():
                    subject_name = subject_match.group('subject_name')
                    subject = model.Subject.get(self.subdomain, subject_name)
                    if not subject:
                        continue
                else:
                    subjects = model.Subject.all().filter('title__ =',
                        subject_match.group('title').strip()).fetch(3)
                    if subjects:
                        subject = subjects[0]
                        # If there is more than one match for this title, it is
                        # marked ambiguous. We don't know which the user wanted.
                        ambiguity = len(subjects) != 1
                    else:
                        continue
                start = subject_match.end()
                quotes = quoted and subject_match.group('quotes') or ''
                end = body.lower().find(
                    '%supdate'.lower() % quotes, start + 1)
                update_block = body[start:] if end == -1 else body[start:end]
                update_lines = [
                    line for line in update_block.split('\n') if line]
                if ambiguity:
                    ambiguous_all.append((subjects, update_lines))
                    continue
                subject_type = cache.SUBJECT_TYPES[self.subdomain][subject.type]
                unsupported = \
                    UNSUPPORTED_ATTRIBUTES[self.subdomain][subject.type]
                stop = False
                for update in update_lines:
                    if STOP_DELIMITER in update:
                        stop = True
                        break
                    update_split = [word for word in update.split() if
                                    re.match('.*\w+.*', word, flags=re.UNICODE)]
                    for i in range(len(update_split), 0, -1):
                        # Automate the generation of potential atribute names
                        # from the line; hospital attribute names are between 1
                        # and 4 words long. This checks each line for any
                        # potential attribute name that fits this description.
                        if len(update_split) <= i: # update must have >=1 words
                            continue         # present after the attribute name
                        name_match = re.match(
                            '\w+', '_'.join(update_split[:i]).lower())
                        if name_match:
                            name = name_match.group(0)
                        if name in subject_type.attribute_names:
                            if name not in unsupported:
                                try:
                                    value = parse(name, update_split, i)
                                    updates.append((name, value))
                                except ValueError, error:
                                    data = {
                                        'value': ' '.join(update_split[i:]),
                                        'attribute': name
                                    }
                                    #i18n: Error message for an invalid value
                                    msg = _('"%(value)s" is not a valid value' +
                                            ' for %(attribute)s') % data
                                    errors.append({
                                        'error_message': msg,
                                        'original_line': update
                                    })
                            else:
                                errors.append(
                                    #i18n: Error message for an unsupported
                                    #i18n: attribute
                                    (_('Unsupported attribute'), update))
                            # Break to remove the situation where substrings of
                            # a name may also be counted; i.e. users who really
                            # want to set the "commune" attribute to the value
                            # "code" must escape code with "'s.
                            break
                if updates and not ambiguity:
                    updates_all.append((subject, updates))
                if errors:
                    errors_all.append((subject, errors))
                if stop:
                    return

        for base in self.update_line_regexes:
            for regex in base:
                match = re.finditer(regex, body, flags=self.update_line_flags)
                process(match)
            if (updates_all or errors_all or ambiguous_all or stop):
                break
        return updates_all, errors_all, ambiguous_all

    def update_subjects(self, updates, observed, comment=''):
        """Goes through the supplied list of updates. Adds to the datastore."""
        for update in updates:
            subject, update_info = update
            source = 'email: %s' % self.account.email
            values = dict(update_info)
            update_subject(subject, observed, self.account, source, values,
                           arrived=observed)

    def send_email(self, original_message, updates, errors, ambiguities,
                   no_subdomain=False):
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
            subject_type = cache.SUBJECT_TYPES[self.subdomain][subject.type]
            formatted_updates.append({
                'subject_title': subject.get_value('title'),
                'subject_name': subject.get_name(),
                'changed_attributes': order_and_format_updates(
                    update_data, subject_type, locale, format_changes, 0)
            })

        formatted_errors = []
        for error in errors:
            subject, error_data = error
            formatted_errors.append({
                'subject_title': subject.get_value('title'),
                'subject_name': subject.get_name(),
                'data': error_data
            })

        formatted_ambiguities = []
        for ambiguity in ambiguities:
            subjects, update_data = ambiguity
            for i in range(len(subjects)):
                subject_data = {
                    'title': subjects[i].get_value('title'),
                    'name': subjects[i].get_name()
                }
                subjects[i] = subject_data
            formatted_ambiguities.append({
                'subject_title': subjects[0]['title'],
                'subjects': subjects,
                'updates': update_data
            })

        template_values = {
            'nickname': nickname,
            'updates': formatted_updates,
            'errors': formatted_errors,
            'ambiguities': formatted_ambiguities,
            'authenticate': self.need_authentication,
            'url': self.domain,
            'help_file': no_subdomain and 'subdomain_email_update_help.txt' or \
                '%s_email_update_help.txt' % self.subdomain
        }
        path = os.path.join(os.path.dirname(__file__),
            'locale/%s/update_response_email.txt' % locale)
        body = template.render(path, template_values)
        subject = 'ERROR - %s' % original_message.subject \
            if errors or ambiguities else original_message.subject
        message = mail.EmailMessage(
            sender=self.subdomain + '-updates@resource-finder.appspotmail.com',
            to=self.email, subject=subject, body=body)
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
