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

"""Sends subject updates to users per their subscriptions.

Accesses the Account data structure to retrieve subject updates for each user,
then sends out information to each user per their subscription settings.

get_timedelta(account, subject): returns a text frequency as a timedelta
form_body(values): forms the e-mail body for an update e-mail
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
from model import Account, Subject, PendingAlert, Subscription
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
    """Forms the body text for an e-mail. Expects the data to be input in the
    following format:
    
        { subject_key { subject_title [
            (attribute, value),
            (attribute, value) ] },
          subject_key { subject_title [
            (attribute, value),
            (attribute, value) ] } }
    """
    body = ''
    for subject_name in values:
        subject_title = values[subject_name].keys()[0]
        updates = values[subject_name][subject_title]
        body += subject_title.upper() + '\n'
        for update in updates:
            body += str(update[0]) + ": " + str(update[1]) + '\n'
        body += '\n'
    return body


class MailUpdateSystem(Handler):
    """Handler for /mail_update_system. Used to handle e-mail update sending.
    
    Attributes:
        action: the specific action to be taken by the class
            
    Functions:
        init(): handles initialization tasks for the class
        post(): responds to HTTP POST requests
        update_and_add_pending_subs(): queues up future digest alerts and sends
            out immediate updates; called when a subject is changed
        send_digests(): sends out a digest update for the specified frequency
        fetch_updates(): returns a dictionary of updated values for the given
            subject
        send_email(): sends an e-mail with the supplied information
    """
    
    def init(self):
        """Handles any useful initialization tasks for the class."""
        self.action = self.request.get('action')
    
    def post(self):
        """Responds to HTTP POST requests. This function either (queues up
        future daily/weekly/monthly updates and sends immediate updates) or
        (sends out daily/weekly/monthly digest updates).
        """
        self.init()
        
        if self.action == 'subject_changed':
            self.update_and_add_pending_subs()
        else:
            for freq in ['daily', 'weekly', 'monthly']:
                self.send_digests(freq)
    
    def update_and_add_pending_subs(self):
        """Called when a subject is changed. It creates PendingAlerts for
        any subscription for the changed subject. Also sends out alerts to
        users who were subscribed to immediate updates for this particular
        subject.
        """
        subject = Subject.get_by_key_name(self.params.subject_name)
        old_values = {}
        new_values = []
        for arg in self.request.arguments():
            if arg not in ['action', 'subject_name']:
                if arg == '%s__old' % arg[:-5]:
                    old_values[arg[:-5]] = self.request.get(arg)
                elif arg == '%s__new' % arg[:-5]:
                    new_values.append((arg[:-5], self.request.get(arg)))
        
        subscriptions = Subscription.all().filter('subject_name =',
            self.params.subject_name)
        body = form_body({self.params.subject_name: {
            subject.get_value('title'): new_values}})
        for subscription in subscriptions:
            if subscription.frequency != 'immediate':
                # queue pending alerts for non-immediate update subscriptions
                key_name = '%s:%s:%s' % (subscription.frequency,
                                         subscription.user_email,
                                         subscription.subject_name)
                old_values_str=['%s:%s' % (x, old_values[x])
                                for x in old_values]
                pa = PendingAlert.get_or_insert(key_name,
                    user_email=subscription.user_email,
                    subject_name=subscription.subject_name,
                    frequency=subscription.frequency,
                    old_values=old_values_str)
                
                # if new values have been changed after the pending alert was
                # originally created, store their original values as well
                pa_old_value_keys = []
                for value in pa.old_values:
                    pa_old_value_keys.append(value[:value.find(':')])
                    
                for key in old_values:
                    if key not in pa_old_value_keys:
                        pa.old_values.append('%s:%s' % (key, old_values[key]))
                db.put(pa)
            else:
                # send out alerts for those with immediate update subscriptions
                account = Account.all().filter('email =',
                    subscription.user_email).get()
                self.send_email(account.locale, account.email, body)
    
    def send_digests(self, frequency):
        """Sends out a digest update for the specified frequency. Currently
        available choices for the supplied frequency are ['daily', 'weekly',
        'monthly']. Also removes pending alerts once an e-mail has been sent
        and updates the account's next alert times.
        """
        accounts = Account.all().filter('next_%s_alert <' % frequency,
            datetime.datetime.now())
        for account in accounts:
            min_key = db.Key.from_path('PendingAlert', '%s:%s:' %
                (frequency, account.email))
            max_key = db.Key.from_path('PendingAlert', u'%s:%s:\xff' %
                (frequency, account.email))
            pending_alerts = PendingAlert.all().filter('__key__ >', min_key
                ).filter('__key__ <', max_key)
            
            alerts_to_delete = []
            subjects = {}
            for alert in pending_alerts:
                subj = Subject.get_by_key_name(alert.subject_name)
                values = self.fetch_updates(alert, subj)
                subjects[subj.key().name()] = {subj.get_value('title'):
                    values}
                alerts_to_delete.append(alert)
            
            if not subjects:
                continue
            
            body = form_body(subjects)
            self.send_email(account.locale, account.email, body)
            self.update_account_alert_time(account, frequency)
            db.delete(alerts_to_delete)
            db.put(account)
            
    def fetch_updates(self, alert, subject):
        """For a given alert and subject, finds any updated values.
        
        Returns:
            A dictionary mapping attributes to updated values. Example:
            
                { attr1: new_value1,
                  attr2: new_value2,
                  ... }
        """
        updated_attrs = []
        subject_type = cache.SUBJECT_TYPES[subject.type]
        
        old_values = {}
        for value in alert.old_values:
            update = value.split(':')
            old_values[update[0]] = update[1]
            
        for attr in subject_type.attribute_names:
            value = subject.get_value(attr)
            if not value and value != 0:
                continue
            if attr in old_values and value != old_values[attr]:
                updated_attrs.append((attr, value))
        
        return updated_attrs
    
    def update_account_alert_time(self, account, frequency):
        """Updates a particular account to send an alert at the appropriate
        later date, depending on the given frequency."""
        if frequency == 'daily':
            account.next_daily_alert = (datetime.datetime.now() + 
                get_timedelta(account, frequency))
        elif frequency == 'weekly':
            account.next_weekly_alert = (datetime.datetime.now() + 
                get_timedelta(account, frequency))
        elif frequency == 'monthly':
            account.next_monthly_alert = (datetime.datetime.now() + 
                get_timedelta(account, frequency))
    
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
            _('Resource Finder subject Updates'))
        message.body = body
        
        message.send()


if __name__ == '__main__':
    utils.run([('/mail_update_system', MailUpdateSystem)], debug=True)
