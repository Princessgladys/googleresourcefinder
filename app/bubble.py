# Copyright 2010 by Steve Hakusa
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

"""Handler for dynamically loading a bubble with attributes from a facility."""

import cache
import datetime
import logging
import model
from utils import db, get_message, run, to_local_isotime
from utils import ErrorMessage, Handler, HIDDEN_ATTRIBUTE_NAMES

def format(value, localize=False):
    """Formats values in a way that is suitable to display in the bubble.
    If 'localize' is true, the value is treated as a localizable message key or
    list of message keys to be looked up in the 'attribute_value' namespace."""
    if localize:
        if isinstance(value, list):
            value = [get_message('attribute_value', item) for item in value]
        else:
            value = get_message('attribute_value', value)
    if isinstance(value, unicode):
        return value.encode('utf-8')
    if isinstance(value, str) and value != '':
        return value.replace('\n', ' ')
    if isinstance(value, list) and value != []:
        return ', '.join(value).encode('utf-8')
    if isinstance(value, datetime.datetime):
        return to_local_isotime(value.replace(microsecond=0))
    if isinstance(value, db.GeoPt):
        latitude = u'%.4f\u00b0 %s' % (
            abs(value.lat), value.lat >= 0 and 'N' or 'S')
        longitude = u'%.4f\u00b0 %s' % (
            abs(value.lon), value.lon >= 0 and 'E' or 'W')
        return (latitude + ', ' + longitude).encode('utf-8')
    if isinstance (value, bool):
        return value and format(_('Yes')) or format(_('No'))
    if value or value == 0:
        return value
    return u'\u2013'.encode('utf-8')

class ValueInfo:
    """Simple struct used by the django template to extract values"""
    def __init__(self, name, value, localize, author=None, affiliation=None,
                 comment=None, date=None):
        self.label = get_message('attribute_name', name)
        self.raw = value
        self.value = format(value, localize)
        self.author = format(author)
        self.affiliation = format(affiliation)
        self.comment = format(comment)
        self.date = format(date)

class ValueInfoExtractor:
    """Base class to determine attributes to display in the bubble"""

    # TODO(kpy): The localized_attribute_names could be determined by looking
    # for attributes with type 'choice' or 'multi'.  Specifying them here is
    # redundant but saves us having to load Attribute entities from the
    # datastore.  If the cost of loading them turns out to be small, get rid
    # of this redundancy.
    def __init__(self, special_attribute_names, localized_attribute_names):
        """Initializes the ValueInfo Extractor.

        Args:
          special_attribute_names: names of attributes that are rendered
              specially in the bubble, not in the general list of attributes
          localized_attribute_names: names of attributes whose values should
              be localized (i.e. choice or multi attributes)"""
        self.special_attribute_names = special_attribute_names
        self.localized_attribute_names = localized_attribute_names

    def extract(self, facility, attribute_names):
        """Extracts attributes from the given facility.

        Args:
          facility: facility from which to extract attributes
          attribute_names: key_name of attributes to display for the facility

        Returns:
          A 3-tuple of specially-handled ValueInfos, non-special ValueInfos,
          and ValueInfos to be displayed in change details"""
        special = dict(
            (a, ValueInfo(get_message('attribute_name', a), None, False))
            for a in self.special_attribute_names)
        general = []
        details = []

        for name in attribute_names:
            value_info = self.get_value_info(facility, name)
            if not value_info:
                continue
            if name in special:
                special[name] = value_info
            else:
                general.append(value_info)
            details.append(value_info)
        return (special, general, details)

    def get_value_info(self, facility, attribute_name):
        value = facility.get_value(attribute_name)
        if value:
            return ValueInfo(
                attribute_name,
                value,
                attribute_name in self.localized_attribute_names,
                facility.get_author_nickname(attribute_name),
                facility.get_author_affiliation(attribute_name),
                facility.get_comment(attribute_name),
                facility.get_observed(attribute_name))

class HospitalValueInfoExtractor(ValueInfoExtractor):
    template_name = 'templates/hospital_bubble.html'

    def __init__(self):
        ValueInfoExtractor.__init__(
            self,
            ['title', 'location', 'available_beds', 'total_beds',
             'healthc_id', 'pcode', 'address', 'services', 'operational_status'],
            # TODO(kpy): This list is redundant; see the comment above
            # in ValueInfoExtractor.
            ['services', 'organization_type', 'category', 'construction',
             'operational_status']
        )

    def extract(self, facility, attribute_names):
        (special, general, details) = ValueInfoExtractor.extract(
            self, facility, filter(lambda n: n not in HIDDEN_ATTRIBUTE_NAMES,
                                   attribute_names))
        value_info = ValueInfoExtractor.get_value_info(self, facility,
            'operational_status')
        if value_info:
            general.append(value_info)
        return (special, general, details)

VALUE_INFO_EXTRACTORS = {
    'hospital': HospitalValueInfoExtractor(),
}

class Bubble(Handler):
    def get(self):
        facility = model.Facility.get_by_key_name(self.params.facility_name)
        if not facility:
            #i18n: Error message for request missing facility name.
            raise ErrorMessage(404, _('Invalid or missing facility name.'))
        facility_type = cache.FACILITY_TYPES[facility.type]

        value_info_extractor = VALUE_INFO_EXTRACTORS[facility.type]
        (special, general, details) = value_info_extractor.extract(
            facility, facility_type.attribute_names)
        edit_link = '/edit?facility_name=%s&embed=yes' % self.params.facility_name

        self.render(value_info_extractor.template_name,
                    edit_link=edit_link,
                    facility_name=self.params.facility_name,
                    last_updated=max(detail.date for detail in details),
                    special=special,
                    general=general,
                    details=details)

if __name__ == '__main__':
    run([('/bubble', Bubble)], debug=True)
