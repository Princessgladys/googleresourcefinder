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

"""Handler for dynamically loading a bubble with attributes from a subject."""

import cache
import datetime
import logging
import model
from utils import db, get_message, run, to_local_isotime, value_or_dash
from utils import ErrorMessage, Handler, HIDDEN_ATTRIBUTE_NAMES

from google.appengine.api import users

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
    return value_or_dash(value)

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

    def extract(self, subject, attribute_names):
        """Extracts attributes from the given subject.

        Args:
          subject: subject from which to extract attributes
          attribute_names: key_name of attributes to display for the subject

        Returns:
          A 3-tuple of specially-handled ValueInfos, non-special ValueInfos,
          and ValueInfos to be displayed in change details"""
        special = dict(
            (a, ValueInfo(get_message('attribute_name', a), None, False))
            for a in self.special_attribute_names)
        general = []
        details = []

        for name in attribute_names:
            value_info = self.get_value_info(subject, name)
            if not value_info:
                continue
            if name in special:
                special[name] = value_info
            else:
                general.append(value_info)
            details.append(value_info)
        return (special, general, details)

    def get_value_info(self, subject, attribute_name):
        observed = subject.get_observed(attribute_name)
        if observed:
            return ValueInfo(
                attribute_name,
                subject.get_value(attribute_name),
                attribute_name in self.localized_attribute_names,
                subject.get_author_nickname(attribute_name),
                subject.get_author_affiliation(attribute_name),
                subject.get_comment(attribute_name),
                observed)

class HospitalValueInfoExtractor(ValueInfoExtractor):
    template_name = 'templates/hospital_bubble.html'

    def __init__(self):
        ValueInfoExtractor.__init__(
            self,
            ['title', 'location', 'available_beds', 'total_beds', 'healthc_id',
             'pcode', 'address', 'services', 'operational_status'],
            # TODO(kpy): This list is redundant; see the comment above
            # in ValueInfoExtractor.
            ['services', 'organization_type', 'category', 'construction',
             'operational_status']
        )

    def extract(self, subject, attribute_names):
        (special, general, details) = ValueInfoExtractor.extract(
            self, subject, filter(lambda n: n not in HIDDEN_ATTRIBUTE_NAMES,
                                   attribute_names))
        value_info = ValueInfoExtractor.get_value_info(self, subject,
            'operational_status')
        if value_info:
            general.append(value_info)
        return (special, general, details)

VALUE_INFO_EXTRACTORS = {
    'haiti': {
        'hospital': HospitalValueInfoExtractor(),
    }
}

class Bubble(Handler):
    def get(self):
        # Need 'view' permission to see a bubble.
        self.require_action_permitted('view')

        subject = model.Subject.get(self.subdomain, self.params.subject_name)
        if not subject:
            #i18n: Error message for request missing subject name.
            raise ErrorMessage(404, _('Invalid or missing subject name.'))

        subscribed = ''
        if self.user:
            subject_name = '%s:%s' % (self.subdomain, self.params.subject_name)
            subscribed = True if model.Subscription.get(
                subject_name, self.user.email()) else ''

        subject_type = cache.SUBJECT_TYPES[self.subdomain][subject.type]

        value_info_extractor = VALUE_INFO_EXTRACTORS[
            self.subdomain][subject.type]
        (special, general, details) = value_info_extractor.extract(
            subject, subject_type.attribute_names)
        edit_url = self.get_url('/edit', subject_name=self.params.subject_name,
                                embed='yes')
        login_url = users.create_login_url(
            self.get_url('/', subject_name=self.params.subject_name,
                         embed='yes'))
        frequency = self.account and self.account.default_frequency or 'instant'

        self.render(value_info_extractor.template_name,
                    user=self.user,
                    login_url=login_url,
                    edit_url=edit_url,
                    subdomain=self.subdomain,
                    subscribed=subscribed,
                    frequency=frequency,
                    subject_name=self.params.subject_name,
                    last_updated=max(detail.date for detail in details),
                    special=special,
                    general=general,
                    details=details)

if __name__ == '__main__':
    run([('/bubble', Bubble)], debug=True)
