# Copyright 2010 by Google Inc.

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

import cache
import utils

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


def generate_bad_value_error_msg(text, attribute):
    """Generates an error message for an incorrect value for the specified
    attribute's type."""
    name = utils.get_message('attribute_name', attribute.key().name(), 'en')
    line = '%s: %s' % (name, text)
    return {
        'error_message': ERRORS_BY_TYPE[attribute.type] % {'attribute': name},
        'original_line': line
    }


class AmbiguousUpdateNotice:
    def __init__(self, matches=None):
        self.matches = matches

    def format(self):
        """Generates an error message for an ambiguous attribute name."""
        #i18n: Error message for an ambiguous attribute name
        msg = _('Attribute name is ambiguous. Please specify one of the ' +
                'following:')
        for match in self.matches:
            change = utils.format_changes(match)
            msg += '\n-- %s: %s' % (change['attribute'], change['value'])
        return msg


class BadValueNotice:
    def __init__(self, update_text=''):
        self.update_text = update_text

    def format(self, attribute):
        return generate_bad_value_error_msg(self.update_text, attribute)


class ValueNotAllowedNotice:
    def __init__(self, update_text=''):
        self.update_text = update_text

    def format(self, attribute):
        """Generates an error message. Includes a list of accepted values
        for the given attribute."""
        values = generate_bad_value_error_msg(self.update_text, attribute)
        error = values['error_message'] + '\n'
        #i18n: Accepted values error message
        options = '-- ' + _('Accepted values are: ')
        attribute_choices = [cache.MAIL_UPDATE_TEXTS[
                                 'attribute_value'][val].en[0]
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

