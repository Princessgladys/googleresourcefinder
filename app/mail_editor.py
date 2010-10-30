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

    find_attribute_value(): tries to match a given value with a translation
    check_messages_for_attr_info(): finds the name of the message that matches
        the given parameters
    parse(): parses a list of unicode strings into datastore-friendly objects
    get_list_update(): for multi attr's, combines two sets (to add and subtract)
        with the current value for a specified subject
    match_email(): given a string, uses reg. exp. to locate email addresses
    generate_ambiguous_update_error_msg(): given a list of potential matches
        for an ambiguous update, creates an error message
    generate_bad_value_error_msg(): generates an error message for type errors
    generate_error_with_correction(): generates an error message, including
        a list of accepted values for the given attribute
    get_min_subjects_by_lowercase_title(): searches minimal subjects by title
    MailEditor: incoming mail handler-- responds to incoming emails addressed to
        <subdomain>-updates@resource-finder@appspotmail.com
    get_locale_and_nickname(): returns a locale and nickname for the given
        account and email message
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
from feedlib.xml_utils import Struct
from utils import db, format, get_message, order_and_format_updates
from utils import NoValueFoundError, ValueNotAllowedError

# Constant to represent the list of strings that denotes a value of None. We
# use this instead of None so as not to confuse setting a value to None with
# simply not setting a value to anything.
none_texts = cache.MAIL_UPDATE_TEXTS['attribute_value'].get('none')
# The following check is performed to allow mail_editor to be imported
# from its test file, even before the datastore has been populated
if none_texts:
    NONE_VALS = none_texts.en
else:
    NONE_VALS = ['*none']

# Mapping of attribute types to error messages.
ERRORS_BY_TYPE = {
    #i18n: Error message for an invalid value to a boolean attribute
    'bool': _('"%(attribute)s" requires a boolean value: "yes" or "no".'),
    #i18n: Error message for an invalid value to an int attribute
    'int': _('"%(attribute)s" requires a numerical value.'),
    #i18n: Error message for an invalid value to a geopt attribute
    'geopt': _('"%(attribute)s" requires two numbers separated by a comma.'),
    #i18n: Error message for an invalid value to a choice attribute
    'choice': _('"%(attribute)s" requires one of a specific set of values.'),
    #i18n: Error message for an invalid value to a multi attribute
    'multi': _('"%(attribute)s" requires all values to be from a specific set.')
}


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
                'subdomain': subdomain,
                'action': 'subject_changed',
                'user_email': account.email,
                'subject_name': subject.name,
                'observed': utils.url_pickle(observed),
                'changed_data': utils.url_pickle(change_information),
                'unchanged_data': utils.url_pickle(unchanged_values)
            }

            # Schedule a task to e-mail users who have subscribed to this
            # subject.
            taskqueue.add(method='POST', url='/mail_alerts',
                          params=params, transactional=transactional)

    db.run_in_transaction(work)


def find_attribute_value(attribute, update_text):
    """Checks to see if the given value matches any value in the given
    attribute's values. If no match is found, checks to see if it matches
    any item in the MailUpdateText table, within the 'attribute_value'
    namespace. Case insensitive. Returns None if not found.
    
    Note: currently defaulting to the 'en' values until multi-language
    support is added."""
    update_upper = update_text.upper().replace(' ', '_')
    if update_upper in attribute.values:
        return update_upper
    attr_val = check_messages_for_attr_info(
        'attribute_value', update_text)
    if attr_val:
        return attr_val
    maps = cache.MAIL_UPDATE_TEXTS['attribute_value']
    update_lower = update_text.lower()
    for key, map in maps.iteritems():
        if (update_lower in [text.lower() for text in map.en] and
            map.name in attribute.values):
            return map.name # name is an attribute value


def check_messages_for_attr_info(ns, alt_name, locale='en'):
    """Iterates through the Message table trying to find the name that
    matches the given alternate name in the supplied namespace for the
    given locale."""
    for key, msg in cache.MESSAGES.iteritems():
        if key[0] == ns:
            text = getattr(msg, locale)
            if text and text.lower() == alt_name.lower():
                return msg.name


def parse(attribute, update):
    """Parses a list of Unicode strings into an attribute value. Note:
    this currently assumes we are working with English values only.
    Multiple languages are not yet supported."""
    update = update.strip()
    if not update:
        raise NoValueFoundError
    if update in NONE_VALS:
        return

    if attribute.type in ['str', 'text']:
        return update
    if attribute.type == 'int':
        return int(update)
    if attribute.type == 'bool':
        ns = 'attribute_value'
        yes_vals = cache.MAIL_UPDATE_TEXTS[ns]['true'].en
        no_vals = cache.MAIL_UPDATE_TEXTS[ns]['false'].en
        if update.lower() not in yes_vals + no_vals:
            raise ValueError
        return bool(update.lower() in yes_vals)
    if attribute.type == 'geopt':
        location = update.split(',')
        if len(location) != 2:
            raise ValueError
        return db.GeoPt(float(location[0]), float(location[1]))
    if attribute.type == 'choice':
        value = find_attribute_value(attribute, update)
        if not value:
            raise ValueNotAllowedError
        return value 
    if attribute.type == 'multi':
        values = [x.strip() for x in update.split(',') if x]
        plus_minus = ['-', '+']
        has_plus_minus = [x for x in values if x[0] in plus_minus]
        if has_plus_minus:
            to_subtract = []
            to_add = []
            errors = []
            for value in values:
                subtract = value[0] == '-'
                add = value[0] == '+'
                new_value = (subtract or add) and value[1:] or value
                formatted = find_attribute_value(attribute, new_value)
                if subtract and formatted:
                    to_subtract.append(formatted)
                elif formatted:
                    to_add.append(formatted)
                else:
                    errors.append(value)
            return (to_subtract, to_add, errors)
        else:
            new_value = []
            errors = []
            for value in values:
                formatted = find_attribute_value(attribute, value)
                if formatted:
                    new_value.append(formatted)
                else:
                    errors.append(value)
            return (new_value, errors)


def get_list_update(subject, attribute, subtract, add):
    """Returns an updated version of the subject's current value for the
    attribute to include the changes sent by the user."""
    current_value = set(subject.get_value(attribute.key().name()) or [])
    current_value -= set(subtract)
    current_value |= set(add)
    return list(current_value)


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
    """Generates an error message for an ambiguous attribute name."""
    #i18n: Error message for an ambiguous attribute name
    msg = _('Attribute name is ambiguous. Please specify one of the following:')
    for match in matches:
        change = format_changes(match)
        msg += '\n-- %s: %s' % (change['attribute'], change['value'])
    return msg


def generate_bad_value_error_msg(update_text, attribute):
    """Generates an error message for an incorrect value for the specified
    attribute's type."""
    name = get_message('attribute_name', attribute.key().name(), 'en')
    line = '%s: %s' % (name, update_text)
    return {
        'error_message': ERRORS_BY_TYPE[attribute.type] % {'attribute': name},
        'original_line': line
    }


def generate_error_with_correction(line, attribute):
    """Generates an error message. Includes a list of accepted values for the
    given attribute."""
    values = generate_bad_value_error_msg(line, attribute)
    error = values['error_message'] + '\n'
    #i18n: Accepted values error message
    options = '-- ' + _('Accepted values are: ')
    attribute_choices = [cache.MAIL_UPDATE_TEXTS['attribute_value'][val].en[0]
                         for val in attribute.values]
    for i, value in enumerate(attribute_choices):
        if len(options) + len(value) >= 80:
            error += options + '\n'
            options = '---- '
        maybe_comma = i != len(attribute_choices) - 1 and ', ' or ''
        options += value + maybe_comma 
    error += options
    values['error_message'] = error
    return values


def get_min_subjects_by_lowercase_title(subdomain, title_lower, max=3):
    """Returns a list of minimal subjects by title, case insensitive."""
    minimal_subjects = []
    for key in cache.MINIMAL_SUBJECTS[subdomain]:
        ms = cache.MINIMAL_SUBJECTS[subdomain][key]
        if ms.get_value('title', '').lower() == title_lower:
            minimal_subjects.append(ms)
        if len(minimal_subjects) >= max:
            break
    return minimal_subjects


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
        check_and_return_attr_names: searches the MailUpdateMessage table in
            the datastore for an attribute mapped to the given string
        update_subjects: updates the datastore with all valid updates
        send_email: sends a response/confirmation email to the user
        send_template_email: sends an email to the user containing a blank
            template on how to update subjects
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
            'quoted': '^(?P<quotes>[^a-zA-Z0-9_\n]+)%s' % regex_base,
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
            return model.Subject.get(self.subdomain, subject_name)
        else:
            title_lower = subject_line.strip().lower()
            minimal_subjects = get_min_subjects_by_lowercase_title(
                self.subdomain, title_lower)
            if len(minimal_subjects) == 1:
                return minimal_subjects[0].parent()
            return [ms.parent() for ms in minimal_subjects]

    def extract_update_lines(self, match, body):
        """Given a re.match, the body of the email, and whether or not we are
        concerned with the quoted section of the body, returns the section
        corresponding to the match's updates."""
        start = match.end()
        quotes = 'quotes' in match.groupdict() and match.group('quotes') or ''
        end = body.lower().find('%supdate'.lower() % quotes, start + 1)
        update_block = body[start:] if end == -1 else body[start:end]
        return [line.replace(quotes, '', 1) for line in update_block.split('\n')
                if line.startswith(quotes)]

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
                    attribute = cache.ATTRIBUTES[name]
                    try:
                        value = parse(attribute, update_text)
                        if value and attribute.type == 'multi':
                            has_update = True
                            if len(value) == 3: # user used plus/minus syntax
                                subtract, add, error = value
                                if not subtract and not add:
                                    has_update = False
                                value = get_list_update(
                                    subject, attribute, subtract, add)
                            else:
                                value, error = value
                                
                            if error:
                                error_text = ', '.join(error)
                                errors.append(generate_error_with_correction(
                                    error_text, attribute))
                            if not has_update:
                                continue
                        updates.append((name, value))
                    except ValueError, BadValueError:
                        errors.append(generate_bad_value_error_msg(
                            update_text, attribute))
                    except ValueNotAllowedError:
                        errors.append(generate_error_with_correction(
                            update_text, attribute))
                    except NoValueFoundError:
                        continue
                if updates:
                    data.update_stanzas.append((subject, updates))
                if errors:
                    data.error_stanzas.append((subject, errors))
                if stop:
                    return

        for key in ['unquoted', 'quoted']:
            matches = re.finditer(self.update_line_regexes[key],
                                  body.split(STOP_DELIMITER)[0],
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

        # try to match on colon first
        update_split = update.split(':', 1)
        if len(update_split) > 1:
            attribute, update_text = update_split
            attribute_lower = attribute.lower()

            # use _'s as the subject type attribute_names lists do, too
            attribute_formatted = attribute_lower.replace(' ', '_')
            
            # check for actual attribute names
            if attribute_formatted in st.attribute_names:
                return (attribute_formatted, update_text.strip())

            # check for alternate mapping matches
            # when checking the map, use spaces as the mapped values do
            attribute_name = self.check_and_return_attr_name(
                st, attribute_lower.replace('_', ' '))
            if attribute_name:
                return (attribute_name, update_text.strip())

        # if no valid match is found with the colon, guess and check
        update_split = update.split()
        for i in range(len(update_split), 0, -1):
            if len(update_split[:i]) < i:
                continue
            name_formatted = '_'.join(update_split[:i]).lower()
            if name_formatted in st.attribute_names:
                matches.append((name_formatted, ' '.join(update_split[i:])))
            name = ' '.join(update_split[:i]).lower().replace('_', ' ')
            name_match = self.check_and_return_attr_name(st, name)
            if name_match and name_match != name:
                update = ' '.join(update_split)
                is_already_found = False
                for match in matches:
                    if name_match == match[0]:
                        is_already_found = True
                if not is_already_found:
                    value_start = update.find(
                        ' ', update.find(name) + len(name)) + 1
                    matches.append((name_match, update[value_start:])) 
        return matches[0] if len(matches) == 1 else matches

    def check_and_return_attr_name(self, st, *names):
        """Given an attribute name or names, searches the MailUpdateMessage
        table's attribute_name namespace in the datastore for an attribute name,
        mapped to any of the given strings."""
        ns = 'attribute_name'
        for name in names:
            attr_name = check_messages_for_attr_info(ns, name)
            if attr_name:
                return attr_name
            mail_texts = cache.MAIL_UPDATE_TEXTS[ns]
            for key, message in mail_texts.iteritems():
                for val in getattr(message, 'en'):
                    if name == val.lower():
                        return key # key is an attribute name

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
        title_lower = original_message.subject.strip().lower()
        minimal_subjects = get_min_subjects_by_lowercase_title(
            self.subdomain, title_lower)
        ms = len(minimal_subjects) == 1 and minimal_subjects[0] or None
        subject_title = ms and ms.get_value('title')
        subject_name = ms and ms.get_name()
        s_type = ms and ms.type or DEFAULT_SUBJECT_TYPES[self.subdomain]
        subject_type = cache.SUBJECT_TYPES[self.subdomain][s_type]
        attributes = [get_message('attribute_name', a, 'en') for a in
                      subject_type.attribute_names if
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
    """Returns a locale and nickname for the given account and email message."""
    if account:
        locale = account.locale or 'en'
        nickname = account.nickname or account.email
    else:
        locale = 'en'
        nickname = message.sender
    return (locale, nickname)


def format_changes(update, locale='en'):
    """Helper function; used to format an attribute, value pair for email."""
    attribute_name, value = update
    attribute = cache.ATTRIBUTES[attribute_name]
    if attribute.type == 'multi':
        formatted_value = ', '.join([get_message(
            'attribute_value', e, locale) or e for e in value])
    elif attribute.type == 'choice':
        formatted_value = get_message(
            'attribute_value', value, locale) or value
    else:
        formatted_value = format(value)
    return {
        'attribute': get_message(
            'attribute_name', attribute_name, locale),
        'value': formatted_value
    }


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
