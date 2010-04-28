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
from access import check_user_role

# ==== Form-field generators and parsers for each attribute type =============

class AttributeType:
    input_size = 10

    def text_input(self, name, value):
        """Generates a text input field."""
        if isinstance(value, unicode):
            pass
        elif isinstance(value, str):
            value = value.decode('utf-8')
        elif value is not None:
            value = str(value)
        else:
            value = ''
        return u'<input name="%s" value="%s" size=%d>' % (
            html_escape(name), html_escape(value), self.input_size)

    def make_input(self, version, name, value, attribute=None):
        """Generates the HTML for an input field for the given attribute."""
        return self.text_input(name, value)

    def parse_input(self, report, name, value, request, attribute):
        """Adds an attribute to the given Report based on a query parameter."""
        setattr(report, name, value)

class StrAttributeType(AttributeType):
    input_size = 40

class TextAttributeType(AttributeType):
    def make_input(self, version, name, value, attribute):
        return '<textarea name="%s" rows=5 cols=40>%s</textarea>' % (
            html_escape(name), html_escape(value or ''))

    def parse_input(self, report, name, value, request, attribute):
        setattr(report, name, db.Text(value))

class ContactAttributeType(AttributeType):
    input_size = 30

    def make_input(self, version, name, value, attribute):
        contact_name, contact_phone, contact_email = (
            (value or '').split('|') + ['', '', ''])[:3]
        return '''<table>
                    <tr><td class="label">%s</td><td>%s</td></tr>
                    <tr><td class="label">%s</td><td>%s</td></tr>
                    <tr><td class="label">%s</td><td>%s</td></tr>
                  </table>''' % (
            _('Name'), self.text_input(name + '.name', contact_name),
            _('Phone'), self.text_input(name + '.phone', contact_phone),
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
                    400, _('Invalid date: %r (need YYYY-MM-DD format)') % value)
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
    def make_input(self, version, name, value, attribute):
        Attribute.make_input(self, version, name, '%g' % value, attribute)

    def parse_input(self, report, name, value, request, attribute):
        if value:
            value = float(value)
        else:
            value = None
        setattr(report, name, value)

class BoolAttributeType(AttributeType):
    def make_input(self, version, name, value, attribute):
        options = []
        if value == True:
            value = 'TRUE'
        elif value == False:
            value = 'FALSE'
        else:
            value = ''
        for choice, title in [
            ('', _('(unspecified)')), ('TRUE', _('yes')), ('FALSE', _('no'))]:
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
    def make_input(self, version, name, value, attribute):
        options = []
        if value is None:
            value = ''
        for choice in [''] + attribute.values:
            message = get_message(version, 'attribute_value', choice)
            title = html_escape(message or _('(unspecified)'))
            selected = (value == choice) and 'selected' or ''
            options.append('<option value="%s" %s>%s</option>' %
                           (choice, selected, title))
        return '<select name="%s">%s</select>' % (
            html_escape(name), ''.join(options))

class MultiAttributeType(AttributeType):
    def make_input(self, version, name, value, attribute):
        if value is None:
            value = []
        checkboxes = []
        for choice in attribute.values:
            message = get_message(version, 'attribute_value', choice)
            title = html_escape(message or _('(unspecified)'))
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

def make_input(version, report, attribute):
    """Generates the HTML for an input field for the given attribute."""
    name = attribute.key().name()
    return ATTRIBUTE_TYPES[attribute.type].make_input(
        version, name, getattr(report, name, None), attribute)

def parse_input(report, request, attribute):
    """Adds an attribute to the given Report based on a query parameter."""
    name = attribute.key().name()
    return ATTRIBUTE_TYPES[attribute.type].parse_input(
        report, name, request.get(name, None), request, attribute)


# ==== Handler for the edit page =============================================

class Edit(utils.Handler):
    def init(self):
        """Checks for authentication and sets up self.version, self.facility,
        self.facility_type, and self.attributes based on the query params."""

        self.require_user_role('user', self.params.cc)

        try:
            self.version = utils.get_latest_version(self.params.cc)
        except:
            raise ErrorMessage(404, _('Invalid or missing country code.'))
        self.facility = model.Facility.get_by_key_name(
            self.params.facility_name, self.version)
        if not self.facility:
            raise ErrorMessage(404, _('Invalid or missing facility name.'))
        self.facility_type = model.FacilityType.get_by_key_name(
            self.facility.type, self.version)
        self.attributes = dict(
            (a.key().name(), a)
            for a in model.Attribute.all().ancestor(self.version))
        self.readonly_attribute_names = ['healthc_id',]

    def get(self):
        self.init()
        fields = []
        readonly_fields = [{
            'name': 'ID',
            'value': self.params.facility_name
        }]

        report = (model.Report.all()
            .ancestor(self.version)
            .filter('facility_name =', self.params.facility_name)
            .order('-timestamp')).get()
        for name in self.facility_type.attribute_names:
            attribute = self.attributes[name]
            if name in self.readonly_attribute_names:
                readonly_fields.append({
                    'name': get_message(self.version, 'attribute_name', name),
                    'value': getattr(report, name, None)
                })
            else:
                fields.append({
                    'name': get_message(self.version, 'attribute_name', name),
                    'type': attribute.type,
                    'input': make_input(self.version, report, attribute)
                })

        self.render('templates/edit.html',
            facility=self.facility, fields=fields,
            readonly_fields=readonly_fields, params=self.params,
            authorization=self.auth and self.auth.description or 'anonymous',
            logout_url=users.create_logout_url('/'))

    def post(self):
        self.init()
        logging.info("record by user: %s"%users.get_current_user())
        last_report = (model.Report.all()
            .ancestor(self.version)
            .filter('facility_name =', self.params.facility_name)
            .order('-timestamp')).get()
        report = model.Report(
            self.version,
            facility_name=self.facility.key().name(),
            date=utils.Date.today(),
            user=users.get_current_user(),
        )
        for name in self.facility_type.attribute_names:
            if name in self.readonly_attribute_names:
                setattr(report, name, getattr(last_report, name, None))
            else:
                attribute = self.attributes[name]
                parse_input(report, self.request, attribute)
        report.put()
        if self.params.embed:
            self.write(_('Record updated.'))
        else:
            raise Redirect('/')

if __name__ == '__main__':
    utils.run([('/edit', Edit)], debug=True)
