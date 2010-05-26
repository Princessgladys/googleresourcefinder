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

import datetime
import logging
import model
from utils import db, get_message, run, to_local_isotime
from utils import Handler, HIDDEN_ATTRIBUTE_NAMES

def format(value):
    """Formats values in a way that is suitable to display in the bubble."""
    if isinstance(value, unicode):
        return value.encode('utf-8')
    if isinstance(value, str):
        return value.replace('\n', ' ')
    if isinstance(value, list):
        return ', '.join(get_message('attribute_value', v) for v in value)
    if isinstance(value, datetime.datetime):
        return to_local_isotime(value.replace(microsecond=0))
    if isinstance(value, db.GeoPt):
        return '(%f, %f)' % (value.lat, value.lon);
    if isinstance (value, bool):
        return value and format(_('Yes')) or format(_('No'))
    if value is not None and value != 0:
        return value
    return u'\u2013'.encode('utf-8')

class ValueInfo:
    """Simple struct used by the django template to extract values"""
    def __init__(self, label, value, author=None, affiliation=None,
                 comment=None, date=None):
        self.label = format(label)
        self.raw = value
        self.value = format(value)
        self.author = format(author)
        self.affiliation = format(affiliation)
        self.comment = format(comment)
        self.date = format(date)

class ValueInfoExtractor:
    """Base class to determine attributes to display in the bubble"""
    def __init__(self, special_attribute_names):
        """Initializes the ValueInfo Extractor.

        Args:
          special_attribute_names: attribute names that are rendered
          specially in the bubble, not in the general list of attributes"""
        self.special_attribute_names = special_attribute_names

    def extract(self, facility, attribute_names):
        """Extracts attributes from the given facility.

        Args:
          facility: facility from which to extract attributes
          attribute_names: key_name of attributes to display for the facility

        Returns:
          A 3-tuple of specially-handled ValueInfos, non-special ValueInfos,
          and ValueInfos to be displayed in change details"""
        special = dict(
            (a, ValueInfo(get_message('attribute_name', a), None))
            for a in self.special_attribute_names)
        general = []
        details = []

        for name in attribute_names:
            value = facility.get_value(name)
            if not value:
                continue
            value_info = ValueInfo(
                get_message('attribute_name', name),
                value,
                facility.get_author_nickname(name),
                facility.get_author_affiliation(name),
                facility.get_comment(name),
                facility.get_observed(name))
            if name in special:
                special[name] = value_info
            else:
                general.append(value_info)
            details.append(value_info)
        return (special, general, details)

class HospitalValueInfoExtractor(ValueInfoExtractor):
    template_name = 'templates/hospital_bubble.html'

    def __init__(self):
        ValueInfoExtractor.__init__(
            self, ['title', 'location', 'available_beds', 'total_beds',
                   'healthc_id', 'address', 'services'])

    def extract(self, facility, attribute_names):
        return ValueInfoExtractor.extract(
            self, facility, filter(lambda n: n not in HIDDEN_ATTRIBUTE_NAMES,
                                   attribute_names))

    def format_services(self, services):
        if services == '&ndash;':
            return services
        service_titles = []
        for name in services.split(', '):
            service_titles.append(get_message('attribute_value', name))
        return ', '.join(service_titles)

VALUE_INFO_EXTRACTORS = {
    'hospital': HospitalValueInfoExtractor(),
}

class Bubble(Handler):
    def get(self):
        facility = model.Facility.get_by_key_name(self.params.facility_name)
        if not facility:
            #i18n: Error message for request missing facility name.
            raise ErrorMessage(404, _('Invalid or missing facility name.'))
        facility_type = model.FacilityType.get_by_key_name(facility.type)

        value_info_extractor = VALUE_INFO_EXTRACTORS[facility.type]
        (special, general, details) = value_info_extractor.extract(
            facility, facility_type.attribute_names)
        edit_link = '/edit?facility_name=%s' % self.params.facility_name

        self.render(value_info_extractor.template_name,
                    edit_link=edit_link,
                    facility_name=self.params.facility_name,
                    last_updated=max(detail.date for detail in details),
                    special=special,
                    general=general,
                    details=details)

if __name__ == '__main__':
    run([('/bubble', Bubble)], debug=True)
