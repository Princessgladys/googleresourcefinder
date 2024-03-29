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

import access
import cache
import datetime
import logging
import model
from rendering import to_json, to_minimal_subject_jobject
from utils import db, get_message, format, run, to_local_isotime, value_or_dash
from utils import ErrorMessage, Handler, HIDDEN_ATTRIBUTE_NAMES

from google.appengine.api import users

class ValueInfo:
    """Simple struct used by the django template to extract values"""
    def __init__(self, name, value, localize, author=None, affiliation=None,
                 comment=None, date=None):
        self.label = get_message('attribute_name', name)
        self.specified = value is not None
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

class HaitiHospitalValueInfoExtractor(ValueInfoExtractor):
    template_name = 'templates/haiti_hospital_bubble.html'

    def __init__(self):
        ValueInfoExtractor.__init__(
            self,
            ['title', 'location', 'available_beds', 'total_beds', 'healthc_id',
             'pcode', 'address', 'services', 'operational_status',
             'alert_status'],
            # TODO(kpy): This list is redundant; see the comment above
            # in ValueInfoExtractor.
            ['services', 'organization_type', 'category', 'construction',
             'operational_status']
        )

    def extract(self, subject, attribute_names):
        (special, general, details) = ValueInfoExtractor.extract(
            self, subject, filter(lambda n: n not in HIDDEN_ATTRIBUTE_NAMES,
                                   attribute_names))
        op_status_info = ValueInfoExtractor.get_value_info(self, subject,
            'operational_status')
        alert_status_info = ValueInfoExtractor.get_value_info(self, subject,
            'alert_status')
        if op_status_info:
            general.append(op_status_info)
        if alert_status_info:
            general.append(alert_status_info)
        return (special, general, details)

class HospitalValueInfoExtractor(ValueInfoExtractor):
    template_name = 'templates/hospital_bubble.html'

    def __init__(self):
        ValueInfoExtractor.__init__(
            self,
            ['title', 'location', 'available_beds', 'total_beds', 'id',
             'alt_id', 'address', 'maps_link', 'services', 'operational_status',
             'alert_status'],
            # TODO(kpy): This list is redundant; see the comment above
            # in ValueInfoExtractor.
            ['services', 'organization_type', 'category', 'construction',
             'operational_status']
        )

    def extract(self, subject, attribute_names):
        (special, general, details) = ValueInfoExtractor.extract(
            self, subject, filter(lambda n: n not in HIDDEN_ATTRIBUTE_NAMES,
                                   attribute_names))
        op_status_info = ValueInfoExtractor.get_value_info(self, subject,
            'operational_status')
        alert_status_info = ValueInfoExtractor.get_value_info(self, subject,
            'alert_status')
        if op_status_info:
            general.append(op_status_info)
        if alert_status_info:
            general.append(alert_status_info)
        return (special, general, details)

VALUE_INFO_EXTRACTORS = {
    'haiti': {
        'hospital': HaitiHospitalValueInfoExtractor(),
    },
    'pakistan': {
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
            subscribed = bool(model.Subscription.get(subject_name,
                                                     self.user.email()))

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
        settings_url = self.get_url('/settings')
        # Email updates are currently available only in English.
        show_edit_by_email = self.params.lang == 'en'
        edit_by_email_url = self.get_url('/mail_editor_start')
        frequency = self.account and self.account.default_frequency or 'instant'
        purge_permitted = access.check_action_permitted(
            self.account, self.subdomain, 'purge')

        html = self.render_to_string(
            value_info_extractor.template_name,
            user=self.user,
            email=self.user and self.user.email() or '',
            login_url=login_url,
            edit_url=edit_url,
            settings_url=settings_url,
            edit_by_email_url=edit_by_email_url,
            show_edit_by_email=show_edit_by_email,
            subdomain=self.subdomain,
            subscribed=subscribed,
            frequency=frequency,
            subject_name=self.params.subject_name,
            last_updated=max(detail.date for detail in details),
            special=special,
            general=general,
            details=details,
            purge_permitted=purge_permitted)
        json = to_minimal_subject_jobject(self.subdomain, subject)

        self.response.headers['Content-Type'] = "application/json"
        self.write(to_json(
            {'html': html, 'json': json, 'login_url': login_url}))

if __name__ == '__main__':
    run([('/bubble', Bubble)], debug=True)
