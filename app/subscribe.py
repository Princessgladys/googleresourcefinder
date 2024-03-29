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

"""Acts on HTTP POST requests to /subscribe and adds subscriptions to a user's
alert information in the datastore.

Subscribe(utils.Handler): handles calls to /subscribe
"""

__author__ = 'pfritzsche@google.com (Phil Fritzsche)'

import datetime
import logging
import pickle
import simplejson

from django.conf import settings

import config
import model
import utils
from bubble import format
from feedlib.xml_utils import Struct
from mail_alerts import EMAIL_FORMATTERS, fetch_updates, format_email_subject
from mail_alerts import send_email, update_account_alert_time
from model import PendingAlert, Subject, Subscription
from utils import _, db, Handler, run

class Subscribe(Handler):
    """Handler for /subscribe. Used to handle subscription changes.
    
    Attributes:
        action: the desired action for this instance of the handler
        email: logged in user's email
    
    Methods:
        init(): handles initialization tasks for the class
        post(): responds to POST requests; create/remove/edit subscriptions
        subscribe(): subscribes the current user to a particular subject
        unsubscribe(): desubscribes the current user from a particular subject
        change_sub_frequency(): changes a praticular subscription's frequency
    """
    
    def init(self):
        """Checks for logged-in user and gathers necessary information."""
        self.action = self.request.get('action')
        self.require_logged_in_user()
        self.email = self.user.email()
        self.subject_name = self.request.get('subject_name', '')
        self.domain = self.request.headers.get('Host', '')
        if not self.account:
            #i18n: Error message for request missing subject name.
            raise ErrorMessage(404, _('Invalid or missing account e-mail.'))
    
    def post(self):
        """Responds to HTTP POST requests to /subscribe by adding / subtracting
        user subscriptions to / from the datastore, as necessary."""
        self.init()
        
        if self.action == 'subscribe':
            self.subscribe()
        elif self.action == 'unsubscribe':
            self.unsubscribe()
        elif self.action == 'unsubscribe_multiple':
            self.unsubscribe_multiple()
        elif self.action == 'change_locale':
            self.change_locale()
        elif self.action == 'change_email_format':
            self.change_email_format()
        elif self.action == 'change_subscription':
            old_frequency = self.request.get('old_frequency')
            new_frequency = self.request.get('new_frequency',
                                             self.account.default_frequency)
            self.change_subscription(self.subject_name,
                                     old_frequency, new_frequency)
        elif self.action == 'change_subscriptions':
            self.change_subscriptions()
        elif self.action == 'change_default_frequency':
            self.change_default_frequency()
    
    def subscribe(self):
        """Subscribes the current user to a particular subject."""
        key_name = '%s:%s' % (self.subject_name, self.email)
        default = self.account.default_frequency if \
            self.account.default_frequency else 'instant'
        frequency = self.request.get('frequency', default)
        Subscription(key_name=key_name, frequency=frequency,
                     subject_name=self.subject_name,
                     user_email=self.email).put()
        if frequency != 'instant':
            update_account_alert_time(self.account, frequency, initial=True)
        db.put(self.account)
 
    def unsubscribe(self):
        """Unsubscribes the current user from a particular subject."""
        subscription = Subscription.get(self.subject_name, self.email)
        if subscription:
            alert = PendingAlert.get(subscription.frequency, self.email,
                                     self.subject_name)
            if alert:
                db.delete(alert)
            db.delete(subscription)
            self.check_and_update_next_alert_times(subscription.frequency)

    def unsubscribe_multiple(self):
        """Unsubscribes the current user from a specified list of subjects."""
        subjects = simplejson.loads(self.request.get('subjects'))
        for subject_name in subjects:
            subscription = Subscription.get(subject_name, self.email)
            if subscription:
                alert = PendingAlert.get(subscription.frequency, self.email,
                                         subscription.subject_name)
                if alert:
                    db.delete(alert)
                db.delete(subscription)
                self.check_and_update_next_alert_times(subscription.frequency)

    def change_locale(self):
        """Changes the current user's locale."""
        locale = self.request.get('locale', self.account.locale)
        if locale not in dict(config.LANGUAGES):
            locale = config.LANG_FALLBACKS.get(lang, settings.LANGUAGE_code)
        self.account.locale = locale
        db.put(self.account)

    def change_email_format(self):
        """Changes the current user's preferred e-mail format."""
        format = self.request.get('email_format', self.account.email_format)
        if format not in ['plain', 'html']:
            self.error(400) # bad request
        self.account.email_format = format
        db.put(self.account)

    def change_subscription(self, subject_name, old_frequency, new_frequency):
        """Change's the current user's subscription to a subject."""
        if ((old_frequency not in Subscription.frequency.choices) or
            (new_frequency not in Subscription.frequency.choices)):
            self.error(400) # bad request
        s = Subscription.get(subject_name, self.email)
        s.frequency = new_frequency
        db.put(s)
        old_alert = PendingAlert.get(old_frequency, self.email,
                                     subject_name)
        if old_alert:
            if new_frequency == 'instant':
                subject = Subject.get_by_key_name(old_alert.subject_name)
                values = fetch_updates(old_alert, subject)
                email_data = Struct(
                    nickname=self.account.nickname or self.account.email,
                    domain=self.domain,
                    subdomain=self.subdomain,
                    changed_subjects={subject_name: (
                        subject.get_value('title'), values)}
                )
                email_formatter = EMAIL_FORMATTERS[
                    self.subdomain][subject.type](self.account)
                body = email_formatter.format_body(email_data)
                email_subject = format_email_subject(self.subdomain,
                                                     old_frequency)

                sender = '%s-updates@%s' % (
                    self.subdomain, self.get_parent_domain().replace(
                        'appspot.com', 'appspotmail.com'))
                send_email(self.account.locale, sender,
                           self.account.email, email_subject,
                           body, self.account.email_format)
            else:
                new_key_name = '%s:%s:%s' % (new_frequency,
                                             old_alert.user_email,
                                             subject_name)
                alert = PendingAlert(key_name=new_key_name,
                                     user_email=old_alert.user_email,
                                     subject_name=old_alert.subject_name,
                                     frequency=new_frequency,
                                     type=old_alert.type)
                old_values = old_alert.dynamic_properties()
                for i in range(len(old_values)):
                    alert.set_attribute(old_values[i],
                                        getattr(old_alert, old_values[i]))
                db.put(alert)
            db.delete(old_alert)
            self.check_and_update_next_alert_times(old_frequency)
        self.check_and_update_next_alert_times(new_frequency)

    def change_subscriptions(self):
        """Change's the current user's subscription to a list of subjects."""
        subject_changes = simplejson.loads(self.request.get('subject_changes'))
        for change in subject_changes:
            self.change_subscription(change['subject_name'],
                                     change['old_frequency'],
                                     change['new_frequency'])

    def change_default_frequency(self):
        frequency = self.request.get('frequency',
                                     self.account.default_frequency)
        if frequency not in Subscription.frequency.choices:
            self.error(400) # bad request
        self.account.default_frequency = frequency
        db.put(self.account)

    def check_and_update_next_alert_times(self, frequency):
        """If a user is no longer subscribed to %frequency% digest updates, sets
        the next alert time to a high value to avoid being called in
        /mail_alerts. If being called during a change subscription operation, it
        will update the account alert time appropriately."""
        if frequency == 'instant':
            return
        if not Subscription.all().filter('user_email =', self.email).filter(
            'frequency =', frequency).count():
            setattr(self.account, 'next_%s_alert' % frequency, model.MAX_DATE)
            db.put(self.account)
        else:
            update_account_alert_time(self.account, frequency, initial=True)
            db.put(self.account)


if __name__ == '__main__':
    run([('/subscribe', Subscribe)], debug=True)
