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

from google.appengine.api import mail
from google.appengine.ext import db

import utils
from model import PendingAlert, Subscription
from utils import _, Handler

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
    for facility_name in values.keys():
        facility_title = values[facility_name].keys()[0]
        updates = values[facility_name][facility_title]
        body += facility_title.upper() + '\n'
        for update in updates:
            body += update[0] + ": " + str(update[1]) + '\n'
        body += '\n'
    return body


class MailUpdateSystem(Handler):
    def init(self):
        self.action = self.request.get('action')
    
    def post(self):
        self.init()
        
        if self.action == 'facility_changed':
            self.update_and_add_pending_subs()
        elif self.action == 'daily_digest':
            self.send_digests('daily')
        elif self.action == 'weekly_digest':
            self.send_digests('weekly')
        elif self.action == 'monthly_digest':
            self.send_digests('monthly')
    
    def update_and_add_pending_subs(self):
        facility = Facility.get_by_key_name(self.params.facility_name)
        old_values = []
        for arg in self.request.arguments():
            if key not in ['action', 'facility_name']:
                old_values.append((arg, self.request.get(arg)))
            
        subscriptions = Subscription.all().filter('facility_name =',
            self.params.facility_name)
        body = form_body({self.params.facility_name: {
            facility.get_value('title'): old_values}})
        for subscription in subscriptions:
            if subscription.frequency != 'immediate':
                # queue pending alerts for non-immediate update subscriptions
                key_name = '%s:%s:%s' % (subscription.frequency,
                                         subscription.user_email,
                                         subscription.facility_name)
                PendingAlert.get_or_insert(key_name,
                    user_email=subscription.user_email,
                    facility_name=subscription.facility_name,
                    frequency=subscription.frequency,
                    old_values=old_values)
            else:
                # send out alerts for those with immediate update subscriptions
                account = Account.filter('email =', subscription.user_email
                    ).get()
                self.send_update_email(account.email, account.locale, body)
    
    def send_digests(self, frequency):
        now = datetime.datetime.now()
        accounts = Account.all().filter('next_%s_alert <' % frequency, now)
        for account in accounts:
            min_key = db.Key.from_path('PendingAlert', '%s:%s:' %
                (frequency, account.email))
            max_key = db.Key.from_path('PendingAlert', '%s:%s:\xff' %
                (frequency, account.email))
            pending_alerts = PendingAlert.all().filter('__key__ >' min_key
                ).filter('__key__ <', max_key)
            
            facilities = {}
            for alert in pending_alerts:
                fac = Facility.get_by_key_name(alert.facility_name)
                values = self.fetch_updates(alert, fac)
                if values:
                    facilities[fac.key().name()] = {fac.get_value('title'):
                        values}
                    alerts_to_delete.append(alert)
            
            body = form_body(facilities)
            self.send_update_email(account.email, account.locale, body)
            db.delete(alerts_to_delete)
            account.next_daily_alert += get_timedelta(frequency)
            db.put(account)
    
    def send_email(self, locale, to, body):
        """Sends a single e-mail update.
        
        Args:
            locale: the locale whose language to use for the email
            to: the user to send the update to
            body: the text to use as the body of the e-mail
        """
        django.utils.translation.activate(locale)
        
        message = mail.EmailMessage()
        message.sender = 'updates@resource-finder@appspotmail.com'
        message.to = to
        message.subject = utils.to_unicode(
            _('Resource Finder Facility Updates'))
        message.body = body
        
        message.send()


if __name__ == '__main__':
    utils.run([('/mail_update_system', MailUpdateSystem)], debug=True)
