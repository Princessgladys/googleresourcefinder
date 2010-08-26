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
        <subdomain>-updates@resource-finder@appspotmail.com
    match_email(): given a string, uses re to locate email addresses
    generate_ambiguous_update_error_msg(): helper function; given a list of
        potential matches for an ambiguous update, creates an error message
    format_changes(): helper function to format attribute value tuples
    parse_utc_offset(): turns a UTC offset in string form into a timedelta
"""

__author__ = 'pfritzsche@google.com (Phil Fritzsche)'

import email
import logging
import os
import re
import string
from datetime import datetime, timedelta

from google.appengine.api import mail
from google.appengine.api.datastore_errors import BadValueError
from google.appengine.api.labs import taskqueue
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler

import cache
import model
import utils
from feeds.xmlutils import Struct
from utils import db, format, get_message, order_and_format_updates

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


def parse(attribute_name, update):
    """Parses a list of Unicode strings into an attribute value."""
    if update.strip() == '*none':
        return

    attribute = cache.ATTRIBUTES[attribute_name]
    if attribute.type in ['str', 'text']:
        return update
    if attribute.type == 'int':
        return int(update)
    if attribute.type == 'bool':
        return bool(update.lower() in ['y', 'yes', 'true'])
    if attribute.type == 'geopt':
        location = update.split(',')
        if len(location) != 2:
            raise ValueError
        return db.GeoPt(float(location[0]), float(location[1]))
    if attribute.type == 'choice':
        formatted = update.upper().replace(' ', '_')
        if formatted not in attribute.values:
            raise ValueError
        return formatted
    if attribute.type == 'multi':
        values = [x.strip() for x in update.split(',')]
        to_add = []
        to_subtract = []
        errors = []
        for value in values:
            formatted = value.upper().replace(' ', '_')
            if formatted[0] == '-' and formatted[1:] in attribute.values:
                to_subtract.append(formatted[1:])
            elif formatted in attribute.values:
                to_add.append(formatted)
            else:
                errors.append(formatted)
        return (attribute, to_subtract, to_add, errors)


def get_list_update(subject, attribute, subtract, add):
    """Returns an updated version of the subject's current value for the
    attribute to include the changs sent by the user."""
    current_value = set(subject.get_value(attribute.key().name()))
    current_value -= set(subtract)
    current_value |= set(add)
    return list(current_value)


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


DEFAULT_SUBJECT_TYPES = {
    'haiti': 'hospital',
    'pakistan': 'hospital'
}


def match_email(text):
    """Given a string, tries to find a regex match for an email."""
    email_regex = r'(.+\s+)*(<)*\s*(?P<email>\w+(?:.+\w+)*@\w+(?:.+\w+)' + \
                  r'(?:\.\w+)+)(>)*'
    match = re.match(email_regex, text)
    if match:
        return match.group('email')


def generate_ambiguous_update_error_msg(matches):
    #i18n: Error message for an ambiguous attribute name
    msg = _('Attribute name is ambiguous. Please specify one of the following:')
    for match in matches:
        change = format_changes(match)
        msg += '\n-- %s: %s' % (change['attribute'], change['value'])
    return msg


def generate_bad_value_error_msg(value, line, attribute_name):
    values = {'value': value, 'attribute': simple_format(attribute_name)}
    return {
        'error_message':
            #i18n: Error message for an invalid value
            _('"%(value)s" is not a valid value for "%(attribute)s"') %  values,
        'original_line': line
    }


class MailEditor(InboundMailHandler):
    """Primary handler for inbound emails targeting
    <subdomain>-updates@resource-finder.appspotmail.com.

    Args:
        account: the account of the user the email is from

    Methods:
        init: handles various initialization tasks for the class
        validate_subdomain: confirms that the given subdomain is valid
        have_profile_info: checks to see if the current account exists and has a
            valid nickname and affiliation
        check_and_store_profile_info: checks to see if the email includes
            profile information for the user and adds to the datastore if found
        receive: override function- triggered when an email is received
        match_nickname_affiliation: locates the nickname and affiliation in a
            body of text, if present
        extract_subject_from_update_line: given an update header, locates the
            subject title (and key name if present)
        extract_update_lines: given a body of text and an update header, returns
            a list of the non-empty lines up through the next update
        process_email: searches the text of an email for updates and errors
        get_attribute_matches: gets a list of potential attribute name matches
            from a given update line
        update_subjects: updates the datastore with all valid updates
        send_email: sends a response/confirmation email to the user
    """
    def init(self, message):
        self.domain = 'http://%s' % self.request.headers['Host']
        # Pulls out the email address from any string
        self.email = match_email(message.sender)
        self.account = model.Account.all().filter('email =', self.email).get()
        # "To" field of email messages should be in the form
        # "<subdomain>-updates@resouce-finder.appspotmail.com".
        self.subdomain = message.to.split('-')[0]

        regex_base = r'update\s+(?P<subject>.*)'
        self.update_line_flags = re.UNICODE | re.MULTILINE | re.I
        self.update_line_regexes = {
            'unquoted': '^%s' % regex_base,
            'quoted': '^(?P<quotes>\W+)%s' % regex_base,
            'key': '.*\((?P<subject_name>.+/.+)\)\s*$'
        }

    def validate_subdomain(self):
        """Checks to make sure the user-supplied subdomain is legitimate."""
        return model.Subdomain.get_by_key_name(self.subdomain)

    def have_profile_info(self):
        """Checks to see if there is an account for the user's email and if it
        has a nickname and affiliation associated with it."""
        return self.account and self.account.nickname and \
            self.account.affiliation

    def check_and_store_profile_info(self, message):
        """Checks to see if the email contains a nickname and affiliation for
        entry into the database. If both are found, creates a new account for
        the user and inserts it into the datastore then returns True. Returns
        False if no such information is found."""
        if self.have_profile_info():
            return True
        # TODO(pfritzsche): Add HTML support.
        for content_type, body in message.bodies('text/plain'):
            body = body.decode()
            nickname, affiliation = self.match_nickname_affiliation(
                body.split('update')[0])
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
        self.need_profile_info = not (self.have_profile_info() or
            self.check_and_store_profile_info(message))
        if not self.validate_subdomain():
            # TODO(pfritzsche): Add better handling of invalid subdomain
            self.send_email(message, {}, no_subdomain=True)
            return
        # TODO(pfritzsche): Add HTML support.
        for content_type, body in message.bodies('text/plain'):
            data = self.process_email(body.decode())
            if (data.unrecognized_subject_stanzas or data.ambiguous_stanzas or
                data.update_stanzas or data.error_stanzas):
                # Email date arrives in the same form as the following example:
                # Thu, 19 Aug 2010 17:29:23 -0400.
                date_format = '%a, %d %b %Y %H:%M:%S'
                # Chop off the last 6 characters because %z UTC offset parsing
                # is not supported on all systems. Then manually parse it
                # because Python is silly [@http://bugs.python.org/issue6641]
                observed = (datetime.strptime(message.date[:-6], date_format) -
                            parse_utc_offset(message.date[-5:]))
                if data.update_stanzas and not self.need_profile_info:
                    self.update_subjects(data.update_stanzas, observed)
                logging.info('mail_editor.py: update received from %s' %
                             self.email)
                self.send_email(message, data)
            else:
                self.send_template_email(message)
            break # to only pay attention to the first body found

    def match_nickname_affiliation(self, text):
        """For the supplied string s, try to find a match in text containing
        the string s, followed by whitespace and then extra text. The extra text
        will be accessible by the group name s.
        """
        def check_for_example(s, example):
            exp = r'%s\s+(?P<%s>.+)' % (s, s)
            matches = re.finditer(exp, text, flags=self.update_line_flags)
            for match in matches:
                if match.group(s) == example:
                    continue
                return match.group(s).strip()
        nickname = check_for_example('nickname', 'John Smith')
        affiliation = check_for_example('affiliation', 'Smith Inc.')
        return (nickname, affiliation)

    def extract_subject_from_update_line(self, match):
        """Given a re.match for an update line, returns the corresponding
        subject if one exists."""
        subject_line = match.group('subject')
        key_match = re.match(self.update_line_regexes['key'], subject_line,
                             flags=self.update_line_flags)
        if key_match:
            subject_name = key_match.group('subject_name')
            subject = model.Subject.get(self.subdomain, subject_name)
            return subject
        else:
            subjects = model.Subject.all_in_subdomain(self.subdomain).filter(
                'title__ =', subject_line.strip()).fetch(3)
            if len(subjects) == 1:
                return subjects[0]
            return subjects

    def extract_update_lines(self, match, body):
        """Given a re.match, the body of the email, and whether or not we are
        concerned with the quoted section of the body, returns the section
        corresponding to the match's updates."""
        start = match.end()
        quotes = 'quotes' in match.groupdict() and match.group('quotes') or ''
        end = body.lower().find('%supdate'.lower() % quotes, start + 1)
        update_block = body[start:] if end == -1 else body[start:end]
        return [line for line in update_block.split('\n') if
                line.startswith(quotes)]

    def process_email(self, body):
        """Given the body of an email, locates updates from the user.

        Searches for unquoted regions first. If no valid updates are found in
        an unquoted section of the email, it then looks for updates in the
        quoted sections of the email.
        """
        data = Struct(
            # list of tuples (subject, updates for the subject)
            update_stanzas=[],
            # list of tuples (subject, error'd lines)
            error_stanzas=[],
            # list of tuples (potential subjects, updates)
            ambiguous_stanzas=[],
            # list of tuples (subject title, updates)
            unrecognized_subject_stanzas=[]
        )
        stop = False

        # Handles the work of the function. For each potential subject match
        # found, locates any updates or errors, and picks out unrecognized data.
        def process(matches):
            for subject_match in matches:
                errors = []
                updates = []
                stop = False
                is_ambiguous = False
                subject = None
                subject_s = self.extract_subject_from_update_line(subject_match)
                update_lines = self.extract_update_lines(subject_match, body)
                if subject_s:
                    if isinstance(subject_s, list):
                        data.ambiguous_stanzas.append((subject_s, update_lines))
                    else:
                        subject = subject_s
                else:
                    data.unrecognized_subject_stanzas.append(
                        (subject_match.group('subject'), update_lines))
                if not subject:
                    continue
                subject_type = cache.SUBJECT_TYPES[self.subdomain][subject.type]
                unsupported = \
                    UNSUPPORTED_ATTRIBUTES[self.subdomain][subject.type]
                for update in update_lines:
                    if STOP_DELIMITER in update:
                        stop = True
                        break
                    match_es = self.get_attribute_matches(subject_type, update)
                    if match_es and isinstance(match_es, list):
                        errors.append({
                            'error_message':
                                generate_ambiguous_update_error_msg(match_es),
                            'original_line': update
                        })
                        continue
                    elif not match_es:
                        continue
                    name, update_text = match_es
                    pretty_name = simple_format(name)
                    try:
                        value = parse(name, update_text)
                        if isinstance(value, tuple): # multi
                            attr, subtract, add, error = value
                            if error: # error
                                error_text = ', '.join(error)
                                line = '%s: %s' % (pretty_name, error_text)
                                errors.append(generate_bad_value_error_msg(
                                    error_text, line, pretty_name))
                            value = get_list_update(subject, attr, subtract, add)
                        updates.append((name, value))
                    except (ValueError, BadValueError):
                        errors.append(generate_bad_value_error_msg(
                            update_text, update, pretty_name))
                if updates:
                    data.update_stanzas.append((subject, updates))
                if errors:
                    data.error_stanzas.append((subject, errors))
                if stop:
                    return

        for key in ['unquoted', 'quoted']:
            matches = re.finditer(self.update_line_regexes[key], body,
                                  flags=self.update_line_flags)
            process(matches)
            if (data.ambiguous_stanzas or data.unrecognized_subject_stanzas or
                data.update_stanzas or data.error_stanzas or stop):
                break
        return data

    def get_attribute_matches(self, st, update):
        """Given an update line and subject type, locates any attribute name
        matches that exist in the line. Returns a list of tuples
        (attribute name, unparsed value) for all located matches or if only one
        match is found, simply returns that match."""
        matches = []
        update_split = [word for word in update.lower().split() if
                        re.match('.*\w+.*', word, flags=re.UNICODE)]
        for i in range(len(update_split), 0, -1):
            colon_found = False
            if len(update_split[:i]) < i:
                continue
            pre_name = '_'.join(update_split[:i]).lower()
            if pre_name[-1] == ':':
                name = pre_name[:-1]
                colon_found = True
            else:
                name = pre_name
            if name in st.attribute_names:
                matches.append((name, ' '.join(update_split[i:])))
                if colon_found:
                    break
        return matches[0] if len(matches) == 1 else matches

    def update_subjects(self, updates, observed, comment=''):
        """Goes through the supplied list of updates. Adds to the datastore."""
        for update in updates:
            subject, update_info = update
            source = 'email: %s' % self.account.email
            values = dict(update_info)
            update_subject(subject, observed, self.account, source, values,
                           arrived=observed)

    def send_email(self, original_message, data, no_subdomain=False):
        """Sends a response email to the user if necessary.

        If the user has not yet provided a nickname and affiliation to the
        system, the email includes information on how to do so. It also
        includes a list of all accepted updates and a list of any errors found
        in the update text that was submitted.
        """
        locale, nickname = get_locale_and_nickname(
            self.account, original_message)
        if self.account:
            locale = self.account.locale or 'en'
            nickname = self.account.nickname or self.account.email
        else:
            locale = 'en'
            nickname = original_message.sender

        formatted_updates = []
        formatted_errors = []
        formatted_ambiguities = []
        formatted_unrecognized_subjects = []
        if data:
            for update in data.update_stanzas:
                subject, update_data = update
                subject_type = cache.SUBJECT_TYPES[self.subdomain][subject.type]
                formatted_updates.append({
                    'subject_title': subject.get_value('title'),
                    'subject_name': subject.get_name(),
                    'changed_attributes': order_and_format_updates(
                        update_data, subject_type, locale, format_changes, 0)
                })

            for error in data.error_stanzas:
                subject, error_data = error
                formatted_errors.append({
                    'subject_title': subject.get_value('title'),
                    'subject_name': subject.get_name(),
                    'data': error_data
                })

            for ambiguity in data.ambiguous_stanzas:
                subjects, update_data = ambiguity
                subjects_formatted = []
                for i in range(len(subjects)):
                    subjects_formatted.append({
                        'title': subjects[i].get_value('title'),
                        'name': subjects[i].get_name()
                    })
                formatted_ambiguities.append({
                    'subject_title': subjects_formatted[0]['title'],
                    'subjects': subjects_formatted,
                    'updates': update_data
                })

            for stanza in data.unrecognized_subject_stanzas:
                subject_title, update_data = stanza
                formatted_unrecognized_subjects.append({
                    'subject_title': subject_title,
                    'updates': update_data
                })

        template_values = {
            'nickname': nickname,
            'updates': formatted_updates,
            'errors': formatted_errors,
            'ambiguities': formatted_ambiguities,
            'unrecognized': formatted_unrecognized_subjects,
            'need_profile_info': self.need_profile_info,
            'url': self.domain,
            'help_file': no_subdomain and 'subdomain_email_update_help.txt' or \
                '%s_email_update_help.txt' % self.subdomain
        }
        path = os.path.join(os.path.dirname(__file__),
            'locale/%s/update_response_email.txt' % locale)
        body = template.render(path, template_values)
        if (formatted_errors or formatted_ambiguities or
            formatted_unrecognized_subjects):
            subject = 'ERROR - %s' % original_message.subject
        else:
            subject = original_message.subject
        message = mail.EmailMessage(
            sender=self.subdomain + '-updates@resource-finder.appspotmail.com',
            to=self.email, subject=subject, body=body)
        message.send()

    def send_template_email(self, original_message):
        """Sends a response email to the user containing a blank template for
        the specified subject (in the subject line) if one exists at all."""
        locale, nickname = get_locale_and_nickname(
            self.account, original_message)
        s = model.Subject.get(self.subdomain, original_message.subject)
        subject_title = s and s.get_value('title')
        subject_name = s and s.get_name()
        s_type = s and s.type or DEFAULT_SUBJECT_TYPES[self.subdomain]
        subject_type = cache.SUBJECT_TYPES[self.subdomain][s_type]
        attributes = [simple_format(a) for a in subject_type.attribute_names if
                      utils.can_edit(self.account, self.subdomain,
                                     cache.ATTRIBUTES[a])]

        template_values = {
            'nickname': nickname,
            'subject_title': subject_title,
            'subject_name': subject_name,
            'attributes': attributes,
            'help_file': '%s_email_update_help.txt' % self.subdomain
        }

        path = os.path.join(os.path.dirname(__file__),
            'locale/%s/template_response_email.txt' % locale)
        body = template.render(path, template_values)
        message = mail.EmailMessage(
            sender=self.subdomain + '-updates@resource-finder.appspotmail.com',
            to=self.email, subject=original_message.subject, body=body)
        message.send()


def get_locale_and_nickname(account, message):
    if account:
        locale = account.locale or 'en'
        nickname = account.nickname or account.email
    else:
        locale = 'en'
        nickname = message.sender
    return (locale, nickname)


def format_changes(update, locale='en'):
    """Helper function; used to format an attribute, value pair for email."""
    attribute, value = update
    formatted_value = ', '.join([simple_format(x) for x in value]) if \
        cache.ATTRIBUTES[attribute].type == 'multi' else format(value)
    return {
        'attribute': simple_format(attribute),
        'value': formatted_value
    }


def simple_format(text):
    return text.capitalize().replace('_', ' ')


def parse_utc_offset(text):
    """Returns a timedelta representation of a UTC offset string."""
    if not re.match('^[+-][0-2][0-9][0-6][0-9]$', text):
        return timedelta()
    offset = timedelta(hours=int(text[1:3]), minutes=int(text[3:]))
    if text[0] == '+':
        return offset
    else:
        return -offset


if __name__ == '__main__':
    utils.run([MailEditor.mapping()], debug=True)
