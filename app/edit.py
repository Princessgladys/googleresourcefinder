# Copyright 2009-2010 by Ka-Ping Yee
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

from google.appengine.api.labs import taskqueue
from google.appengine.api.labs.taskqueue import Task

import cache
import datetime
import logging
import model
import pickle
import re
import StringIO
import urlparse
import utils
import wsgiref

from access import check_action_permitted
from feed_provider import schedule_add_record
from feeds.crypto import sign, verify
from rendering import clean_json, json_encode
from utils import DateTime, ErrorMessage, HIDDEN_ATTRIBUTE_NAMES, Redirect
from utils import db, can_edit, get_message, html_escape, simplejson
from utils import to_unicode, users, _

XSRF_KEY_NAME = 'resource-finder-edit'
DAY_SECS = 24 * 60 * 60

class ChangeMetadata:
    """Simple struct to hold metadata for a change and reduce the number of
    arguments passed around to various functions."""
    def __init__(self, observed, author, author_nickname, author_affiliation):
        self.observed = observed
        self.author = author
        self.author_nickname = author_nickname
        self.author_affiliation = author_affiliation

# ==== Form-field generators and parsers for each attribute type =============

class AttributeType:
    input_size = 10

    def text_input(self, name, value):
        """Generates a text input field."""
        value = to_unicode(value)
        return u'<input name="%s" value="%s" size=%d>' % (
            html_escape(name), html_escape(value), self.input_size)

    def make_input(self, name, value, attribute=None):
        """Generates the HTML for an input field for the given attribute."""
        return self.text_input(name, value)

    def to_stored_value(self, name, value, request, attribute):
        """Converts args into the storage value for this attribute type."""
        if isinstance(value, basestring):
            value = value.strip()
        if value or value == 0:
            return value
        return None

    def apply_change(self, subject, minimal_subject, report, subject_type,
                     request, attribute, change_metadata):
        """Adds an attribute to the given Subject, MinimalSubject, and
        Report based on a query parameter. Also adds the required change
        history fields according to the invariants in model.py."""
        name = attribute.key().name()
        value = self.to_stored_value(name, request.get(name, None),
                                     request, attribute)
        comment = request.get('%s__comment' % name, None)

        report.set_attribute(name, value, comment)
        subject.set_attribute(name, value,
                               change_metadata.observed,
                               change_metadata.author,
                               change_metadata.author_nickname,
                               change_metadata.author_affiliation,
                               comment)
        if name in subject_type.minimal_attribute_names:
            minimal_subject.set_attribute(name, value)

class StrAttributeType(AttributeType):
    input_size = 40

class TextAttributeType(AttributeType):
    def make_input(self, name, value, attribute):
        return '<textarea name="%s" rows=5 cols=34>%s</textarea>' % (
            html_escape(name), html_escape(value or ''))

    def to_stored_value(self, name, value, request, attribute):
        if value:
            return db.Text(value)
        return None

class ContactAttributeType(AttributeType):
    input_size = 30

    def make_input(self, name, value, attribute):
        contact_name, contact_phone, contact_email = (
            (value or '').split('|') + ['', '', ''])[:3]
        return '''<table>
                    <tr><td class="label">%s</td><td>%s</td></tr>
                    <tr><td class="label">%s</td><td>%s</td></tr>
                    <tr><td class="label">%s</td><td>%s</td></tr>
                  </table>''' % (
            #i18n: a person's name
            _('Name'), self.text_input(name + '.name', contact_name),
            #i18n: telephone number
            _('Phone'), self.text_input(name + '.phone', contact_phone),
            #i18n: E-mail address
            _('E-mail'), self.text_input(name + '.email', contact_email),
        )

    def parse_input(self, report, name, value, request, attribute):
        contact = (request.get(name + '.name', '') + '|' +
                   request.get(name + '.phone', '') + '|' +
                   request.get(name + '.email', ''))
        # make sure we put None if all three are empty
        return contact != '||' and contact or None

class DateAttributeType(AttributeType):
    input_size = 10

    def to_stored_value(self, name, value, request, attribute):
        if not value or not value.strip():
            return None
        try:
            year, month, day = map(int, value.split('-'))
            return DateTime(year, month, day)
        except (TypeError, ValueError):
            raise ErrorMessage(
                #i18n: Error message for invalid date entry
                400, _('Invalid date: %(date)r (need YYYY-MM-DD format)')
                % value)

class IntAttributeType(AttributeType):
    input_size = 10

    def to_stored_value(self, name, value, request, attribute):
        if value or value == 0:
            return int(float(value))
        return None

class FloatAttributeType(IntAttributeType):
    def make_input(self, name, value, attribute):
        return AttributeType.make_input(self, name, '%g' % value, attribute)

    def to_stored_value(self, name, value, request, attribute):
        if value or value == 0:
            return float(value)
        return None

class BoolAttributeType(AttributeType):
    def make_input(self, name, value, attribute):
        options = []
        if value == True:
            value = 'TRUE'
        elif value == False:
            value = 'FALSE'
        else:
            value = ''
        for choice, title in [
            #i18n: Form option to indicate that a value is not specified
            ('', to_unicode(_('(unspecified)'))),
            #i18n: Form option for a true Boolean value
            ('TRUE', to_unicode(_('Yes'))),
            #i18n: Form option for a false Boolean value
            ('FALSE', to_unicode(_('No')))]:
            selected = (value == choice) and 'selected' or ''
            options.append('<option value="%s" %s>%s</option>' %
                           (choice, selected, title))
        return '<select name="%s">%s</select>' % (
            html_escape(name), ''.join(options))

    def to_stored_value(self, name, value, request, attribute):
        # Note: There are 3 states here to account for, 'True', 'False',
        # or 'None' (aka no answer)
        if value:
            return (value == 'TRUE')
        return None

class ChoiceAttributeType(AttributeType):
    def make_input(self, name, value, attribute):
        options = []
        if value is None:
            value = ''
        for choice in [''] + attribute.values:
            message = get_message('attribute_value', choice)
            #i18n: Form option to indicate that a value is not specified
            title = html_escape(message or to_unicode(_('(unspecified)')))
            selected = (value == choice) and 'selected' or ''
            options.append('<option value="%s" %s>%s</option>' %
                           (choice, selected, title))
        return '<select name="%s">%s</select>' % (
            html_escape(name), ''.join(options))

class MultiAttributeType(AttributeType):
    def make_input(self, name, value, attribute):
        if value is None:
            value = []
        checkboxes = []
        for choice in attribute.values:
            message = get_message('attribute_value', choice)
            #i18n: Form option to indicate that a value is not specified
            title = html_escape(message or to_unicode(_('(unspecified)')))
            checked = (choice in value) and 'checked' or ''
            id = name + '.' + choice
            checkboxes.append(
                ('<input type=checkbox name="%s" id="%s" %s>' +
                 '<label for="%s">%s</label>') % (id, id, checked, id, title))
        return '<br>\n'.join(checkboxes)
    
    def to_stored_value(self, name, value, request, attribute):
        value = []
        for choice in attribute.values:
            if request.get(name + '.' + choice):
                value.append(choice)
        return value or None

class GeoPtAttributeType(AttributeType):
    def make_input(self, name, value, attribute):
        lat = value and value.lat or ''
        lon = value and value.lon or ''

        #i18n: Label for text input
        return (to_unicode(_('Latitude')) + ' '
                + self.text_input('%s.lat' % name, lat) +
                '&nbsp;' +
                #i18n: Label for text input
                to_unicode(_('Longitude')) + ' '
                + self.text_input('%s.lon' % name, lon))

    def to_stored_value(self, name, value, request, attribute):
        lat = request.get('%s.lat' % name, None)
        lon = request.get('%s.lon' % name, None)
        if lat and long:
            return db.GeoPt(float(lat), float(lon))
        return None

ATTRIBUTE_TYPES = {
    'str': StrAttributeType(),
    'text': TextAttributeType(),
    'contact': ContactAttributeType(),
    'date': DateAttributeType(),
    'int': IntAttributeType(),
    'float': FloatAttributeType(),
    'bool': BoolAttributeType(),
    'choice': ChoiceAttributeType(),
    'multi': MultiAttributeType(),
    'geopt': GeoPtAttributeType(),
}

def make_input(subject, attribute):
    """Generates the HTML for an input field for the given attribute."""
    name = attribute.key().name()
    return ATTRIBUTE_TYPES[attribute.type].make_input(
        name, subject.get_value(name), attribute)

def render_json(value):
    """Renders the given value as json"""
    return clean_json(simplejson.dumps(value, indent=None, default=json_encode))

def render_attribute_as_json(subject, attribute):
    """Returns the value of this attribute as a JSON string"""
    name = attribute.key().name()
    return render_json(subject.get_value(name))

def apply_change(subject, minimal_subject, report, subject_type,
                 request, attribute, change_metadata):
    """Adds an attribute to the given Subject, MinimalSubject and Report
    based on a query parameter."""
    attribute_type = ATTRIBUTE_TYPES[attribute.type]
    attribute_type.apply_change(subject, minimal_subject, report,
                                subject_type, request, attribute,
                                change_metadata)

def has_changed(subject, request, attribute):
    """Returns True if the request has an input for the given attribute
    and that attribute has changed from the previous value in the subject."""
    name = attribute.key().name()
    value = ATTRIBUTE_TYPES[attribute.type].to_stored_value(
        name, request.get(name, None), request, attribute)
    current = render_json(value)
    previous = request.get('editable.%s' % name, None)
    return previous != current

def has_comment_changed(subject, request, attribute):
    """Returns True if the request has a comment for the given attribute
    and that comment has changed from the previous value in subject."""
    name = attribute.key().name()
    old_comment = subject.get_comment(name)
    new_comment = request.get('%s__comment' % name)
    return new_comment and (old_comment != new_comment)

def is_editable(request, attribute):
    """Returns true if the special hidden 'editable.name' field is set in
    the request, indicating that the given field was editable by the user
    at the time the edit page was rendered."""
    return 'editable.%s' % attribute.key().name() in request.arguments()

def get_suggested_nickname(user):
    """Returns the suggested Account.nickname based on a user.nickname"""
    return re.sub('@.*', '', user and user.nickname() or '')

def get_source_url(request):
    source_url = wsgiref.util.request_uri(request.environ)
    parsed_url = urlparse.urlparse(source_url)
    return len(parsed_url) > 1 and '://'.join(parsed_url[:2]) or None

def update(key, subject_type, request, user, account, attributes, subdomain,
           transactional=True):
    """Given a subject, subject type, and request information from the
    edit page, this performs required updates to the subject's stored
    information if changes have been made. Also triggers a taskqueue event to
    run the mail alerts system for any new changes.

    Args:
        key: key_name of the potentially changed subject
        subject_type: type of the subject
        request: http request information
        user: current user
        account: current user's account
        attributes: a list of attributes for this subject
        subdomain: the current subdomain
        transactional: (optional) True if this function is being run in
            transaction
    """
    subject = db.get(key)
    minimal_subject = model.MinimalSubject.get_by_subject(subject)
    utcnow = datetime.datetime.utcnow().replace(microsecond=0)
    report = model.Report(
        subject,
        arrived=utcnow,
        source=get_source_url(request),
        author=user,
        observed=utcnow)
    change_metadata = ChangeMetadata(
        utcnow, user, account.nickname, account.affiliation)
    has_changes = False
    changed_attributes_dict = {}
    changed_attribute_information = []
    unchanged_attribute_values = {}

    for name in subject_type.attribute_names:
        attribute = attributes[name]
        # To change an attribute, it has to have been marked editable
        # at the time the page was rendered, the new value has to be
        # different than the one in the subject at the time the page
        # rendered, and the user has to have permission to edit it now.
        value_changed = has_changed(subject, request, attribute)
        comment_changed = has_comment_changed(
            subject, request, attribute)
        if (is_editable(request, attribute) and
            (value_changed or comment_changed)):
            if not can_edit(account, subdomain, attribute):
                raise ErrorMessage(
                    403, _(
                    #i18n: Error message for lacking edit permissions
                    '%(user)s does not have permission to edit %(a)s')
                    % {'user': user.email(),
                       'a': get_message('attribute_name',
                                        attribute.key().name())})
            has_changes = True
            change_info = {'attribute': name,
                           'old_value': subject.get_value(name)}
            apply_change(subject, minimal_subject, report,
                         subject_type, request, attribute,
                         change_metadata)
            change_info['new_value'] = subject.get_value(name)
            change_info['author'] = subject.get_author_nickname(name)
            changed_attribute_information.append(change_info)
            changed_attributes_dict[name] = attribute
        else:
            unchanged_attribute_values[name] = subject.get_value(name)
    
    if has_changes:
        # Schedule a task to add a feed record.
        # We can't really do this inside this transaction, since
        # feed records are not part of the entity group.
        # Transactional tasks is the closest we can get.
        # TODO(kpy): This is disabled for now because it causes
        # intermittent exceptions.  Re-enable it when we have it
        # tested and working.
        # schedule_add_record(self.request, user,
        #     subject, changed_attributes_dict, utcnow)
        db.put([report, subject, minimal_subject])
        cache.MINIMAL_SUBJECTS[subdomain].flush()
        cache.JSON[subdomain].flush()
        
        # On edit, create a task to e-mail users who have subscribed
        # to that subject. Values are converted to unicode due to
        # an issue where simplejson will not convert from pickle's
        # 8-bit output to unicode; initial values must also be unicode.
        json_attrs_changed = simplejson.dumps(unicode(
            pickle.dumps(changed_attribute_information), 'latin-1'))
        json_attrs_unchanged = simplejson.dumps(unicode(
            pickle.dumps(unchanged_attribute_values), 'latin-1'))
        
        params = {
            'subject_name': subject.key().name(),
            'action': 'subject_changed',
            'changed_data': json_attrs_changed,
            'unchanged_data': json_attrs_unchanged
        }

        taskqueue.add(url='/mail_alerts', method='POST',
                      params=params, transactional=transactional)


# ==== Handler for the edit page =============================================

class Edit(utils.Handler):
    def init(self):
        """Checks for logged-in user and sets up self.subject
        and self.subject_type based on the query params."""
        # Need 'edit' permission to see or submit the edit form.
        self.require_action_permitted('edit')

        # Regardless of permissions, the user has to be logged in so we
        # can record the author information with the edit.
        self.require_logged_in_user()

        self.subject = model.Subject.get(
            self.subdomain, self.params.subject_name)
        if not self.subject:
            #i18n: Error message for request missing subject name.
            raise ErrorMessage(404, _('Invalid or missing subject name.'))
        self.subject_type = \
            cache.SUBJECT_TYPES[self.subdomain][self.subject.type]

    def get(self):
        self.init()
        fields = []
        readonly_fields = []

        for name in self.subject_type.attribute_names:
            if name in HIDDEN_ATTRIBUTE_NAMES:
                continue
            attribute = cache.ATTRIBUTES[name]
            comment = self.subject.get_comment(attribute.key().name())
            if not comment:
                comment = ''
            if can_edit(self.account, self.subdomain, attribute):
                fields.append({
                    'name': name,
                    'title': get_message('attribute_name', name),
                    'type': attribute.type,
                    'input': make_input(self.subject, attribute),
                    'json': render_attribute_as_json(self.subject, attribute),
                    'comment': '',
                })
            else:
                readonly_fields.append({
                    'title': get_message('attribute_name', name),
                    'value': self.subject.get_value(name)
                })

        token = sign(XSRF_KEY_NAME, self.user.user_id(), DAY_SECS)

        self.render('templates/edit.html',
            token=token, subject_title=self.subject.get_value('title'),
            fields=fields, readonly_fields=readonly_fields,
            account=self.account,
            suggested_nickname=get_suggested_nickname(self.user),
            params=self.params, edit_url=self.get_url('/edit'),
            logout_url=users.create_logout_url('/'),
            subdomain=self.subdomain)

    def post(self):
        self.init()

        if self.request.get('cancel'):
            raise Redirect(self.get_url('/'))

        if not verify(XSRF_KEY_NAME, self.user.user_id(),
            self.request.get('token')):
            raise ErrorMessage(403, 'Unable to submit data for %s'
                               % self.user.email())

        if not self.account.nickname:
            nickname = self.request.get('account_nickname', None)
            if not nickname:
                logging.error("Missing editor nickname")
                #i18n: Error message for request missing nickname
                raise ErrorMessage(400, 'Missing editor nickname.')
            self.account.nickname = nickname.strip()

            affiliation = self.request.get('account_affiliation', None)
            if not affiliation:
                logging.error("Missing editor affiliation")
                #i18n: Error message for request missing affiliation
                raise ErrorMessage(400, 'Missing editor affiliation.')
            self.account.affiliation = affiliation.strip()
            self.account.actions.append('edit')
            self.account.put()
            logging.info('Assigning nickname "%s" and affiliation "%s" to %s'
                         % (nickname, affiliation, self.account.email))

        logging.info("record by user: %s" % self.user)

        # Cannot run datastore queries in a transaction outside the entity group
        # being modified, so fetch the attributes and default account here
        attributes = cache.ATTRIBUTES.load()
        cache.DEFAULT_ACCOUNT.load()
        db.run_in_transaction(update, self.subject.key(), self.subject_type,
                              self.request, self.user, self.account,
                              attributes, self.subdomain)
        if self.params.embed:
            #i18n: Record updated successfully.
            self.write(_('Record updated.'))
            # Fire off a task to asynchronously refresh the JSON cache
            # and reduce the latency of the next page load.
            taskqueue.add(url='/refresh_json_cache?lang=%s&subdomain=%s'
                          % (self.params.lang, self.subdomain), method='GET')
        else:
            raise Redirect(self.get_url('/'))

if __name__ == '__main__':
    utils.run([('/edit', Edit)], debug=True)
