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

import datetime
import logging
import model
import re
import utils
from access import check_user_role
from main import USE_WHITELISTS
from utils import DateTime, ErrorMessage, HIDDEN_ATTRIBUTE_NAMES, Redirect
from utils import db, get_message, html_escape, to_unicode, users, _
from feeds.crypto import sign, verify

# TODO(shakusa) Add per-attribute comment fields

XSRF_KEY_NAME = 'resource-finder-edit'
DAY_SECS = 24 * 60 * 60

class ChangeMetadata:
    """Simple struct to hold metadata for a change and reduce the number of
    arguments passed around to various functions."""
    def __init__(self, user, source, affiliation, observed):
        self.user = user
        self.source = source
        self.affiliation = affiliation
        self.observed = observed

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
        if value or value == 0:
            return value
        return None

    def has_changed(self, facility, name, value, request, attribute):
        """Returns True if the request has an input for the given attribute
        and that attribute has changed from the previous value in facility."""
        value = self.to_stored_value(name, value, request, attribute)
        old_value = get_value(facility, name)
        return value != old_value

    def apply_change(self, facility, report, name, value, request, attribute,
                     change_metadata):
        """Adds an attribute to the given Facility and Report based on a query
        parameter. Also adds the required change history fields."""
        value = self.to_stored_value(name, value, request, attribute)
        setattr(facility, '%s__' % name, value)
        setattr(report, '%s__' % name, value)

        comment_key = '%s__comment' % name
        comment_value = request.get(comment_key, None)
        if comment_value:
            setattr(report, comment_key, comment_value)
            setattr(facility, comment_key, comment_value)
        if change_metadata.user:
            setattr(facility, '%s__user' % name, change_metadata.user)
        if change_metadata.source:
            setattr(facility, '%s__source' % name, change_metadata.source)
        if change_metadata.affiliation:
            setattr(facility, '%s__affiliation' % name,
                    change_metadata.affiliation)
        if change_metadata.observed:
            setattr(facility, '%s__observed' % name, change_metadata.observed)

class StrAttributeType(AttributeType):
    input_size = 40

class TextAttributeType(AttributeType):
    def make_input(self, name, value, attribute):
        return '<textarea name="%s" rows=5 cols=40>%s</textarea>' % (
            html_escape(name), html_escape(value or ''))

    def to_stored_value(self, name, value, request, attribute):
        if value or value == 0:
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

    def to_stored_value(self, name, value, request, attribute):
        contact = (request.get(name + '.name', '') + '|' +
                   request.get(name + '.phone', '') + '|' +
                   request.get(name + '.email', ''))
        # make sure we put empty string of all three are empty
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
        Attribute.make_input(self, name, '%g' % value, attribute)

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
            #i18n: Form option not specified
            ('', to_unicode(_('(unspecified)'))),
            #i18n: Form option for agreement
            ('TRUE', to_unicode(_('Yes'))),
            #i18n: Form option for disagreement
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
            #i18n: Form option not specified
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
            #i18n: Form option not specified
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
                #i18n: Label for text input
                to_unicode(_('Longitude')) + ' '
                + self.text_input('%s.lon' % name, lon))

    def to_stored_value(self, name, value, request, attribute):
        lat = float(request.get('%s.lat' % name, None))
        lon = float(request.get('%s.lon' % name, None))
        return db.GeoPt(lat, lon)

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

def get_value(facility, name, default=None):
    """Returns a dynamic property of the given name from the facility."""
    return getattr(facility, '%s__' % name, default)

def make_input(facility, attribute):
    """Generates the HTML for an input field for the given attribute."""
    name = attribute.key().name()
    return ATTRIBUTE_TYPES[attribute.type].make_input(
        name, get_value(facility, name), attribute)

def apply_change(facility, report, request, attribute, change_metadata):
    """Adds an attribute to the given Facility and Report based on
    a query parameter."""
    name = attribute.key().name()
    value = request.get(name, None)
    attribute_type = ATTRIBUTE_TYPES[attribute.type]
    attribute_type.apply_change(facility, report, name, value, request,
                                attribute, change_metadata)

def has_changed(facility, request, attribute):
    """Returns True if the request has an input for the given attribute
    and that attribute has changed from the previous value in facility."""
    name = attribute.key().name()
    value = request.get(name, None)
    attribute_type = ATTRIBUTE_TYPES[attribute.type]
    return attribute_type.has_changed(facility, name, value, request, attribute)

def can_edit(auth, attribute):
    """Returns True if the user can edit the given attribute."""
    return not attribute.edit_role or check_user_role(
        auth, attribute.edit_role)

def get_suggested_nickname(user):
    """Returns the suggested Authorization.nickname based on a user.nickname"""
    return re.sub('@.*', '', user and user.nickname() or '')

# ==== Handler for the edit page =============================================

class Edit(utils.Handler):
    def init(self):
        """Checks for logged-in user and sets up self.facility,
        self.facility_type, and self.attributes based on the query params."""

        self.require_logged_in_user()

        # TODO(shakusa) Can remove after launch when we no longer want to
        # restrict editing to editors
        if USE_WHITELISTS:
            self.require_user_role('editor')

        self.facility = model.Facility.get_by_key_name(
            self.params.facility_name)
        if not self.facility:
            #i18n: Error message for request missing facility name.
            raise ErrorMessage(404, _('Invalid or missing facility name.'))
        self.facility_type = model.FacilityType.get_by_key_name(
            self.facility.type)
        self.attributes = dict(
            (a.key().name(), a) for a in model.Attribute.all())

    def get(self):
        self.init()
        fields = []
        readonly_fields = [{
            #i18n: Identifier for a facility
            'title': to_unicode(_('Facility ID')),
            'value': self.params.facility_name
        }]

        for name in self.facility_type.attribute_names:
            if name in HIDDEN_ATTRIBUTE_NAMES:
                continue
            attribute = self.attributes[name]
            if can_edit(self.auth, attribute):
                fields.append({
                    'name': name,
                    'title': get_message('attribute_name', name),
                    'type': attribute.type,
                    'input': make_input(self.facility, attribute)
                })
            else:
                readonly_fields.append({
                    'title': get_message('attribute_name', name),
                    'value': get_value(self.facility, name)
                })

        token = sign(XSRF_KEY_NAME, self.user.user_id(), DAY_SECS)

        self.render('templates/edit.html',
            token=token, facility=self.facility, fields=fields,
            readonly_fields=readonly_fields, auth=self.auth,
            suggested_nickname=get_suggested_nickname(self.user),
            params=self.params, logout_url=users.create_logout_url('/'),
            instance=self.request.host.split('.')[0])

    def post(self):
        self.init()

        if self.request.get('cancel'):
            raise Redirect('/')

        if not verify(XSRF_KEY_NAME, self.user.user_id(),
            self.request.get('token')):
            raise ErrorMessage(403, 'Unable to submit data for %s'
                               % self.user.email())

        if not self.auth.nickname:
            nickname = self.request.get('auth_nickname', None)
            if not nickname:
                logging.error("Missing editor nickname")
                #i18n: Error message for request missing nickname
                raise ErrorMessage(403, 'Missing editor nickname.')
            self.auth.nickname = nickname

            affiliation = self.request.get('auth_affiliation', None)
            if not affiliation:
                logging.error("Missing editor affiliation")
                #i18n: Error message for request missing affiliation
                raise ErrorMessage(403, 'Missing editor affiliation.')
            self.auth.affiliation = affiliation
            self.auth.user_roles.append('editor')
            self.auth.put()
            logging.info('Assigning nickname "%s" and affiliation "%s" to %s'
                         % (nickname, affiliation, self.auth.email))

        logging.info("record by user: %s" % self.user)
        utcnow = datetime.datetime.utcnow().replace(microsecond=0)
        change_metadata = ChangeMetadata(
            self.user, self.auth.nickname, self.auth.affiliation, utcnow)
        report = model.Report(
            self.facility,
            arrived=utcnow,
            observed=utcnow,
            user=self.user)

        has_changes = False
        for name in self.facility_type.attribute_names:
            attribute = self.attributes[name]
            if (can_edit(self.auth, attribute) and
                has_changed(self.facility, self.request, attribute)):
                has_changes = True
                apply_change(self.facility, report, self.request, attribute,
                             change_metadata)

        if has_changes:
            db.put([report, self.facility])
        if self.params.embed:
            #i18n: Record updated successfully.
            self.write(_('Record updated.'))
        else:
            raise Redirect('/')

if __name__ == '__main__':
    utils.run([('/edit', Edit)], debug=True)
