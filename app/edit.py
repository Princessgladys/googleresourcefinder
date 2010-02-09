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

import model
import utils
from utils import ErrorMessage, Redirect, db, html_escape, users


# ==== Form-field generators and parsers for each attribute type =============

class AttributeType:
    input_size = 10
    def make_input(self, name, value, attribute):
        """Generates the HTML for an input field for the given attribute."""
        return '<input name="%s" value="%s" size=%d>' % (
            html_escape(name),
            html_escape(value is not None and str(value) or ''),
            self.input_size)

    def parse_input(self, report, name, value, request, attribute):
        """Adds an attribute to the given Report based on a query parameter."""
        setattr(report, name, value)

class StrAttributeType(AttributeType):
    input_size = 40

class TextAttributeType(AttributeType):
    def make_input(self, name, value, attribute):
        return '<textarea name="%s" rows=5 cols=40>%s</textarea>' % (
            html_escape(name), html_escape(value or ''))

    def parse_input(self, report, name, value, request, attribute):
        setattr(report, name, db.Text(value))

class IntAttributeType(AttributeType):
    input_size = 10

    def parse_input(self, report, name, value, request, attribute):
        setattr(report, name, value and int(float(value)) or None)

class FloatAttributeType(IntAttributeType):
    def make_input(self, name, value, attribute):
        IntAttribute.make_input(self, name, '%g' % value, attribute)

    def parse_input(self, report, name, value, request, attribute):
        setattr(report, name, value and float(value) or None)

class ChoiceAttributeType(AttributeType):
    def make_input(self, name, value, attribute):
        options = []
        if value is None:
            value = ''
        for choice in [''] + attribute.values:
            escaped_choice = html_escape(choice or '(unspecified)')
            selected = (value == choice) and 'selected' or ''
            options.append('<option value="%s" %s>%s</option>' % (
                escaped_choice, selected, escaped_choice))
        return '<select name="%s">%s</select>' % (
            html_escape(name), ''.join(options))

class MultiAttributeType(AttributeType):
    def make_input(self, name, value, attribute):
        if value is None:
            value = []
        checkboxes = []
        for choice in attribute.values:
            escaped_choice = html_escape(choice or '(unspecified)')
            checked = (choice in value) and 'checked' or ''
            id = name + '.' + choice
            checkboxes.append(
                ('<input type=checkbox name="%s" id="%s" %s>' +
                 '<label for="%s">%s</label>') % (
                id, id, checked, id, escaped_choice))
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
    'int': IntAttributeType(),
    'float': FloatAttributeType(),
    'choice': ChoiceAttributeType(),
    'multi': MultiAttributeType(),
}

def make_input(report, attribute):
    """Generates the HTML for an input field for the given attribute."""
    name = attribute.key().name()
    return ATTRIBUTE_TYPES[attribute.type].make_input(
        name, getattr(report, name, None), attribute)

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
        if not self.auth:
            raise Redirect(users.create_login_url('/'))
        try:
            self.version = utils.get_latest_version(self.params.cc)
        except:
            raise ErrorMessage(404, 'Invalid or missing country code.')
        self.facility = model.Facility.all().ancestor(self.version).filter(
            'id =', self.params.id).get()
        if not self.facility:
            raise ErrorMessage(404, 'Invalid or missing facility id.')
        self.facility_type = model.FacilityType.get_by_key_name(
            self.facility.type, self.version)
        self.attributes = dict(
            (a.key().name(), a)
            for a in model.Attribute.all().ancestor(self.version))

    def get(self):
        self.init()
        fields = []
        report = model.Report.all().ancestor(self.version).filter(
            'facility_id =', self.params.id).order('-timestamp').get()
        for attribute_name in self.facility_type.attributes:
            attribute = self.attributes[attribute_name]
            fields.append({
                'name': attribute.name,
                'type': attribute.type,
                'input': make_input(report, attribute)
            })

        self.render('templates/edit.html',
            facility=self.facility, fields=fields, params=self.params,
            authorization=self.auth and self.auth.description or 'anonymous',
            logout_url=users.create_logout_url('/'))

    def post(self):
        self.init()
        report = model.Report(
            self.version,
            facility_id=self.facility.id,
            date=utils.Date.today()
        )
        for attribute_name in self.facility_type.attributes:
            attribute = self.attributes[attribute_name]
            parse_input(report, self.request, attribute)
        report.put()

        raise Redirect('/')

if __name__ == '__main__':
    utils.run([('/edit', Edit)], debug=True)
