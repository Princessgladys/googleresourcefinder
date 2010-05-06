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

import logging
import model
import utils
from utils import DateTime, ErrorMessage, Redirect
from utils import db, get_message, html_escape, users
from feeds.crypto import sign, verify

XSRF_KEY_NAME = 'resource-finder-edit'
DAY_SECS = 24 * 60 * 60

# ==== Form-field generators and parsers for each attribute type =============

class AttributeType:
    input_size = 10

    def text_input(self, name, value):
        """Generates a text input field."""
        value = decode(value)
        return u'<input name="%s" value="%s" size=%d>' % (
            html_escape(name), html_escape(value), self.input_size)

    def make_input(self, version, name, value, lang, attribute=None):
        """Generates the HTML for an input field for the given attribute."""
        return self.text_input(name, value)

    def parse_input(self, report, name, value, request, attribute):
        """Adds an attribute to the given Report based on a query parameter."""
        setattr(report, name, value)

class StrAttributeType(AttributeType):
    input_size = 40

class TextAttributeType(AttributeType):
    def make_input(self, version, name, value, lang, attribute):
        return '<textarea name="%s" rows=5 cols=40>%s</textarea>' % (
            html_escape(name), html_escape(value or ''))

    def parse_input(self, report, name, value, request, attribute):
        setattr(report, name, db.Text(value))

class ContactAttributeType(AttributeType):
    input_size = 30

    def make_input(self, version, name, value, lang, attribute):
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
        # make sure we put empty string of all three are empty
        contact = contact != '||' and contact or ''
        setattr(report, name, contact)

class DateAttributeType(AttributeType):
    input_size = 10

    def parse_input(self, report, name, value, request, attribute):
        if value.strip():
            try:
                year, month, day = map(int, value.split('-'))
                setattr(report, name, DateTime(year, month, day))
            except (TypeError, ValueError):
                raise ErrorMessage(
                    #i18n: Error message for invalid date entry
                    400, _('Invalid date: %(date)r (need YYYY-MM-DD format)')
                    % value)
        else:
            setattr(report, name, None)

class IntAttributeType(AttributeType):
    input_size = 10

    def parse_input(self, report, name, value, request, attribute):
        if value:
            value = int(float(value))
        else:
            value = None
        setattr(report, name, value)

class FloatAttributeType(IntAttributeType):
    def make_input(self, version, name, value, lang, attribute):
        Attribute.make_input(self, version, name, '%g' % value, lang, attribute)

    def parse_input(self, report, name, value, request, attribute):
        if value:
            value = float(value)
        else:
            value = None
        setattr(report, name, value)

class BoolAttributeType(AttributeType):
    def make_input(self, version, name, value, lang, attribute):
        options = []
        if value == True:
            value = 'TRUE'
        elif value == False:
            value = 'FALSE'
        else:
            value = ''
        for choice, title in [
            #i18n: Form option not specified
            ('', decode(_('(unspecified)'))),
            #i18n: Form option for agreement
            ('TRUE', decode(_('Yes'))),
            #i18n: Form option for disagreement
            ('FALSE', decode(_('No')))]:
            selected = (value == choice) and 'selected' or ''
            options.append('<option value="%s" %s>%s</option>' %
                           (choice, selected, title))
        return '<select name="%s">%s</select>' % (
            html_escape(name), ''.join(options))

    def parse_input(self, report, name, value, request, attribute):
        if value:
            value = (value == 'TRUE')
        else:
            value = None
        setattr(report, name, value)

class ChoiceAttributeType(AttributeType):
    def make_input(self, version, name, value, lang, attribute):
        options = []
        if value is None:
            value = ''
        for choice in [''] + attribute.values:
            message = get_message(version, 'attribute_value', choice, lang)
            #i18n: Form option not specified
            title = html_escape(message or decode(_('(unspecified)')))
            selected = (value == choice) and 'selected' or ''
            options.append('<option value="%s" %s>%s</option>' %
                           (choice, selected, title))
        return '<select name="%s">%s</select>' % (
            html_escape(name), ''.join(options))

class MultiAttributeType(AttributeType):
    def make_input(self, version, name, value, lang, attribute):
        if value is None:
            value = []
        checkboxes = []
        for choice in attribute.values:
            message = get_message(version, 'attribute_value', choice, lang)
            #i18n: Form option not specified
            title = html_escape(message or decode(_('(unspecified)')))
            checked = (choice in value) and 'checked' or ''
            id = name + '.' + choice
            checkboxes.append(
                ('<input type=checkbox name="%s" id="%s" %s>' +
                 '<label for="%s">%s</label>') % (id, id, checked, id, title))
        return '<br>\n'.join(checkboxes)

    def parse_input(self, report, name, value, request, attribute):
        value = []
        for choice in attribute.values:
            if request.get(name + '.' + choice):
                value.append(choice)
        setattr(report, name, value or None)

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
}

def decode(value):
    if isinstance(value, unicode):
        return value
    elif isinstance(value, str):
        return value.decode('utf-8')
    elif value is not None:
        return str(value)
    else:
        return ''

def make_input(version, report, lang, attribute):
    """Generates the HTML for an input field for the given attribute."""
    name = attribute.key().name()
    return ATTRIBUTE_TYPES[attribute.type].make_input(
        version, name, getattr(report, name, None), lang, attribute)

def parse_input(report, request, attribute):
    """Adds an attribute to the given Report based on a query parameter."""
    name = attribute.key().name()
    return ATTRIBUTE_TYPES[attribute.type].parse_input(
        report, name, request.get(name, None), request, attribute)

def get_last_report(version, facility_name):
    return (model.Report.all()
            .ancestor(version)
            .filter('facility_name =', facility_name)
            .order('-timestamp')).get()


# ==== Handler for the edit page =============================================

class Edit(utils.Handler):
    def init(self):
        """Checks for logged-in user and sets up self.version, self.facility,
        self.facility_type, and self.attributes based on the query params."""

        self.require_logged_in_user()

        try:
            self.version = utils.get_latest_version(self.params.cc)
        except:
            #i18n: Error message for request missing country code.
            raise ErrorMessage(404, _('Invalid or missing country code.'))
        self.facility = model.Facility.get_by_key_name(
            self.params.facility_name, self.version)
        if not self.facility:
            #i18n: Error message for request missing facility name.
            raise ErrorMessage(404, _('Invalid or missing facility name.'))
        self.facility_type = model.FacilityType.get_by_key_name(
            self.facility.type, self.version)
        self.attributes = dict(
            (a.key().name(), a)
            for a in model.Attribute.all().ancestor(self.version))

    def get(self):
        self.init()
        fields = []
        readonly_fields = [{
            'name': 'ID',
            'value': self.params.facility_name
        }]

        lang = self.params.lang
        report = get_last_report(self.version, self.params.facility_name)
        for name in self.facility_type.attribute_names:
            attribute = self.attributes[name]
            if attribute.editable:
                fields.append({
                    'name': get_message(self.version, 'attribute_name',
                                        name, lang),
                    'type': attribute.type,
                    'input': make_input(self.version, report, lang, attribute)
                })
            else:
                readonly_fields.append({
                    'name': get_message(self.version, 'attribute_name',
                                        name, lang),
                    'value': getattr(report, name, None)
                })

        token = sign(XSRF_KEY_NAME, self.user.user_id(), DAY_SECS)

        self.render('templates/edit.html',
            token=token, facility=self.facility, fields=fields,
            readonly_fields=readonly_fields, params=self.params,
            logout_url=users.create_logout_url('/'))

    def post(self):
        self.init()

        if self.request.get('cancel'):
            raise Redirect('/')

        if not verify(XSRF_KEY_NAME, self.user.user_id(),
            self.request.get('token')):
            raise ErrorMessage(403, 'Unable to submit data for %s'
                               % self.user.email())

        logging.info("record by user: %s" % self.user)
        last_report = get_last_report(self.version, self.params.facility_name)
        report = model.Report(
            self.version,
            facility_name=self.facility.key().name(),
            date=utils.Date.today(),
            user=self.user,
        )
        for name in self.facility_type.attribute_names:
            attribute = self.attributes[name]
            if attribute.editable:
                parse_input(report, self.request, attribute)
            else:
                setattr(report, name, getattr(last_report, name, None))
        report.put()
        if self.params.embed:
            #i18n: Record updated successfully.
            self.write(_('Record updated.'))
        else:
            raise Redirect('/')

if __name__ == '__main__':
    utils.run([('/edit', Edit)], debug=True)
