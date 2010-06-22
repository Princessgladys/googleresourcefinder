# Copyright 2009-2010 by Google Inc.
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

"""Sends facility updates to users per their subscriptions.

Accesses the Account data structure to retrieve facility updates for each user,
then sends out information to each user per their subscription settings.

get_frequency(alert, facility): returns a text frequency as a timedelta
form_body(values): forms the e-mail body for an update e-mail
EmailData: used as a structure to store useful information for an update
MailUpdateSystem(utils.Handler): handler class to send e-mail updates
"""

__author__ = 'pfritzsche@google.com (Phil Fritzsche)'

import datetime
import logging
import os

from google.appengine.api import mail
from google.appengine.ext import db

import cache
import utils
from model import Account, Facility, PendingAlert, Subscription
from utils import _, Handler

# Set up localization.
ROOT = os.path.dirname(__file__)
from django.conf import settings
try:
    settings.configure()
except:
    pass
settings.LANGUAGE_CODE = 'en'
settings.USE_I18N = True
settings.LOCALE_PATHS = (os.path.join(ROOT, 'locale'),)
import django.utils.translation

FREQUENCY_TO_DATETIME = {
    'daily': datetime.timedelta(1),
    'weekly': datetime.timedelta(7),
    'monthly': datetime.timedelta(30)
}

def get_timedelta(account, frequency):
    """Given a text frequency, converts it to a timedelta."""
    if frequency == 'default':
        return FREQUENCY_TO_DATETIME[account.default_frequency]
    return FREQUENCY_TO_DATETIME[frequency]


def form_body(values):
    """Forms the body text for an e-mail. """
    body = ''
    for facility_name in values:
        facility_title = values[facility_name].keys()[0]
        updates = values[facility_name][facility_title]
        body += facility_title.upper() + '\n'
        for update in updates:
            body += str(update[0]) + ": " + str(update[1]) + '\n'
        body += '\n'
    return body


class MailUpdateSystem(Handler):
    def init(self):
        self.action = self.request.get('action')
    
    def post(self):
        self.init()
        
        if self.action == 'facility_changed':
            self.update_and_add_pending_subs()
        else:
            for freq in ['daily', 'weekly', 'monthly']:
                self.send_digests('daily')
                self.send_digests('weekly')
                self.send_digests('monthly')
    
    def update_and_add_pending_subs(self):
        facility = Facility.get_by_key_name(self.params.facility_name)
        old_values = []
        for arg in self.request.arguments():
            if arg not in ['action', 'facility_name']:
                old_values.append((arg, self.request.get(arg)))
            
        subscriptions = Subscription.all().filter       ('facility_name =',
            self.params.facility_name)
        body = form_body({self.params.facility_name: {
            facility.get_value('title'): old_values}})
        for subscription in subscriptions:
            if subscription.frequency != 'immediate':
                # queue pending alerts for non-immediate update subscriptions
                key_name = '%s:%s:%s' % (subscription.frequency,
                                         subscription.user_email,
                                         subscription.facility_name)
                old_values_str=['%s:%s' % (x[0], x[1]) for x in old_values]
                pa = PendingAlert.get_or_insert(key_name,
                    user_email=subscription.user_email,
                    facility_name=subscription.facility_name,
                    frequency=subscription.frequency,
                    old_values=old_values_str)
                if pa and len(old_values) != len(pa.old_values):
                    for i in range(len(old_values)):
                        if old_values[i] not in pa.old_values[i]:
                            pa.old_values.append('%s:%s' %
                                (old_values[i][0], old_values[i][1]))
                    db.put(pa)
            else:
                # send out alerts for those with immediate update subscriptions
                account = Account.all().filter('email =',
                    subscription.user_email).get()
                self.send_email(account.locale, account.email, body)
    
    def send_digests(self, frequency):
        now = datetime.datetime.now()
        accounts = Account.all().filter('next_%s_alert <' % frequency, now)
        for account in accounts:
            min_key = db.Key.from_path('PendingAlert', '%s:%s:' %
                (frequency, account.email))
            max_key = db.Key.from_path('PendingAlert', u'%s:%s:\xff' %
                (frequency, account.email))
            pending_alerts = PendingAlert.all().filter('__key__ >', min_key
                ).filter('__key__ <', max_key)
            
            alerts_to_delete = []
            facilities = {}
            for alert in pending_alerts:
                fac = Facility.get_by_key_name(alert.facility_name)
                values = self.fetch_updates(alert, fac)
                facilities[fac.key().name()] = {fac.get_value('title'):
                    values}
                logging.info(facilities)
                alerts_to_delete.append(alert)
            
            if not facilities:
                continue
            
            body = form_body(facilities)
            self.send_email(account.locale, account.email, body)
            account.next_daily_alert = (datetime.datetime.now() + 
                get_timedelta(account, frequency))
            db.delete(alerts_to_delete)
            db.put(account)
            
    def fetch_updates(self, alert, facility):
        updated_attrs = []
        facility_type = cache.FACILITY_TYPES[facility.type]
        
        old_values = {}
        for value in alert.old_values:
            update = value.split(':')
            old_values[update[0]] = update[1]
            
        for attr in facility_type.attribute_names:
            value = facility.get_value(attr)
            if not value and value != 0:
                continue
            if attr in old_values and value != old_values[attr]:
                updated_attrs.append((attr, value))
        
        return updated_attrs
    
    def send_email(self, locale, to, body):
        """Sends a single e-mail update.
        
        Args:
            locale: the locale whose language to use for the email
            to: the user to send the update to
            body: the text to use as the body of the e-mail
        """
        django.utils.translation.activate(locale)
        
        message = mail.EmailMessage()
        message.sender = 'updates@resource-finder.appspotmail.com'
        message.to = to
        message.subject = utils.to_unicode(
            _('Resource Finder Facility Updates'))
        message.body = body
        
        message.send()


if __name__ == '__main__':
    utils.run([('/mail_update_system', MailUpdateSystem)], debug=True)
