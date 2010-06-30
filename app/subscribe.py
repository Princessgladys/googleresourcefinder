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

import utils
from mail_update_system import fetch_updates, form_body, send_email
from model import PendingAlert, Subscription
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
        elif self.action == 'change_subscriptions':
            self.change_subscriptions()
    
    def subscribe(self):
        """Subscribes the current user to a particular subject."""
        key_name = '%s:%s' % (self.params.subject_name, self.email)
        frequency = (self.request.get('frequency') or
                     self.account.default_frequency)
        Subscription(key_name=key_name, frequency=frequency,
                     subject_name=subject_name, user_email=self.email).put()
        update_account_alert_time(self.account, frequency, initial=True)
        db.put(self.account)
    
    def unsubscribe(self):
        """Unsubscribes the current user from a particular subject."""
        subcription = Subscription.get(self.params.subject_name, email)
        if subscription:
            db.delete(subscription)
        for freq in ['daily', 'weekly', 'monthly']:
            alert = PendingAlert.get(freq, email, self.params.subject_name)
            if alert:
                db.delete(alert)
    
    def change_subscriptions(self):
        """Change's the current user's subscription to a list of subjects."""
        for change in self.request.get('subject_changes'):
            subject_key = change[0]
            old_frequency = change[1]
            new_frequency = change[2] or self.account.default_frequency
            
            key_name = '%s:%s' % (subject_key, self.email)
            Subscription(key_name=key_name, user_email=self.email,
                         subject_name=subject_key,
                         frequency=new_frequency).put()
            old_alert = PendingAlert.get(old_frequency, email, subject_key)
            if old_alert:
                if new_frequency == 'immediate':
                    subject = Subject.get_by_key_name(old_alert.subject_name)
                    values = fetch_updates(old_alert, subject)
                    body = form_plain_body({old_alert.subject_name: {
                        subject.get_value('title'): values}})
                    send_email(self.account.locale,
                               'updates@resource-finder.appspotmail.com',
                               self.account.email, utils.to_unicode(
                               _('Resource Finder Updates')), body)
                else:
                    new_key_name = '%s:%s:%s' % (frequency, email,
                                                 self.params.subject_name)
                    alert = PendingAlert(key_name=new_key_name,
                                         user_email=old_alert.user_email,
                                         subject_name=old_alert.subject_name,
                                         frequency=frequency)
                    old_values = old_alert.dynamic_properties()
                    for i in range(len(old_values)):
                        alert.set_attribute(old_values[i],
                                            getattr(old_alert, old_values[i]))
                    db.put(alert)
                db.delete(old_alert)

if __name__ == '__main__':
    run([('/subscribe', Subscribe)], debug=True)
