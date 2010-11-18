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

# ========================================================= Notice Classes
# The *Notice classes serve as containers for information pertaining to
# erroneous updates received by the mail_editor module. Each class is set
# to store a specific type of information (i.e. a list of regex matches in
# AmbiguousUpdateNotice) and should be able to produce a formatted string
# containing text suitable for display to a user describing the issue with
# the information, via the format() function."""

class Notice:
    """Base class."""
    def format(self):
        """Should be overriden with a function capable of producing a
        formatted error string for the user describing the reason why
        the Notice was created."""
        raise NotImplementedError


class AmbiguousUpdateNotice(Notice):
    """Notice for ambiguous updates. Used to store a list of regex matches
    for attribute names that are not exact. i.e. If a user submits the line
    "organization type foo", it is unclear if they are trying to set the
    attribute "organization" to the value "type foo" or if they are trying
    to set the attribute "organization type" to the value "foo"."""

    def __init__(self, matches):
        self.matches = matches

    def format(self):
        """Produces an error message containing a list of all possible
        attribute matches based on the user's query."""
        #i18n: Error message for an ambiguous attribute name
        msg = _('Attribute name is ambiguous. Please specify one of the ' +
                'following:')
        for match in self.matches:
            change = utils.format_attr_value(match)
            msg += '\n-- %s: %s' % (change['attribute'], change['value'])
        return msg


class BadValueNotice(Notice):
    """Used when the given value is invalid for the attribute in question.
    For example, this might be used when the user gives a non-numeric string
    to update an integer-only attribute, or when a user tries to enter an
    invalid selection to a multiple choice attribute."""

    def __init__(self, update_text, attribute):
        self.update_text = update_text
        self.attribute = attribute

    def format(self):
        """Produces an error message detailing the issue with the update
        text received. If the attribute has specific choices the user must
        select from, they will be included for reference."""
        # Produce error message
        name = utils.get_message(
            'attribute_name', self.attribute.key().name(), 'en')
        error_msg = ERRORS_BY_TYPE[self.attribute.type] % \
            {'attribute': name}

        # If the attribute does not have specific values the user may
        # choose from, return the error as is. Otherwise, produce a
        # list of the available choices.
        if not self.attribute.values:
            return error_msg

        error_msg += '\n'
        #i18n: Accepted values error message
        options = '-- ' + _('Accepted values are: ')
        self.attribute_choices = [cache.MAIL_UPDATE_TEXTS[
                                  'attribute_value'][val].en[0]
                                  for val in self.attribute.values]
        for i, value in enumerate(self.attribute_choices):
            if len(options) + len(value) >= 80:
                error_msg += options + '\n'
                options = '---- '
            maybe_comma = i != len(self.attribute_choices) - 1 and ', ' or ''
            options += value + maybe_comma 
        return error_msg + options
