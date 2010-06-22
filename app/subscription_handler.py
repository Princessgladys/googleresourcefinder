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

"""Acts on HTTP POST requests to /subscription_handler and adds subscriptions to a user's
alert information in the datastore.

SubscriptionHandler(utils.Handler): handles calls to /subscription_handler
"""

__author__ = 'pfritzsche@google.com (Phil Fritzsche)'

from model import PendingAlert, Subscription
from utils import db, Handler, run

class SubscriptionHandler(Handler):
    """Handler for /subscription_handler. Used to handle subscription changes.
    
    Attributes:
        email: logged in user's email
        account: current user's Account object from datastore [see model.py]
        alert: current user's Alert object from datastore [see model.py]
        frequencies: dictionary of frequencies for each facility the user is
            subscribed to
            
    Functions:
        get(): responds to HTTP GET requests; do nothing
        post(): responds to HTTP POST requests; add facility to subscription
    """
    
    def init(self):
        """Checks for logged-in user and gathers necessary information."""
        self.action = self.request.get('action')
        self.require_logged_in_user()
        self.email = self.user.email()
        if not self.account:
            #i18n: Error message for request missing facility name.
            raise ErrorMessage(404, _('Invalid or missing account e-mail.'))
    
    def post(self):
        """Responds to HTTP POST requests to /subscription_handler by adding / subtracting
        user subscriptions to / from the datastore, as necessary."""
        self.init()
        
        if self.action == 'subscribe':
            self.subscribe()
        elif self.action == 'unsubscribe':
            self.unsubscribe()
        elif self.action == 'change_subscription_frequency':
            self.change_sub_frequency()
    
    def subscribe(self):
        self.require_user()
        email = self.user.email()
        key_name = '%s:%s' % (email, self.params.facility_name)
        frequency = (self.request.get('frequency') or
                     self.account.default_frequency)
        Subscription(key_name=key_name, frequency=frequency,
                     facility_name=facility_name, user_email=email).put()
        
        # update account to include next send time
        account = Account.all().filter('email =', email)
        if frequency == 'daily' and not account.next_daily_alert:
            account.next_daily_alert = (datetime.datetime.now +
                get_timedelta(frequency))
        elif frequency == 'weekly' and not account.next_weekly_alert:
            account.next_weekly_alert = (datetime.datetime.now +
                get_timedelta(frequency))
        elif frequency == 'monthly' and not account.next_monthly_alert:
            account.next_monthly_alert = (datetime.datetime.now +
                get_timedelta(frequency))
        db.put(account)
    
    def unsubscribe(self):
        self.require_user()
        email = self.user.email()
        key_name = '%s:%s' % (email, self.params.facility_name)
        subcription = Subscription.get_by_key_name(key_name)
        if subscription:
            db.delete(subscription)
        
        for freq in ['daily', 'weekly', 'monthly']:
            alert = PendingAlert.get_by_key_name('%s:%s:%s' %
                (freq, email, self.params.facility_name))
            if alert:
                db.delete(alert)
    
    def change_sub_frequency(self):
        self.require_user()
        email = self.user.email()
        key_name = '%s:%s' % (email, self.params.facility_name)
        old_frequency = self.request.get('old_frequency')
        frequency = (self.request.get('frequency') or
                     self.account.default_frequency)
        Subscription(key_name=key_name, user_email=email,
                     facility_name=self.params.facility_name,
                     frequency=frequency).put()
        
        old_pending_key_name = ('%s:%s:%s' %
            (old_frequency, email, self.params.facility_name))
        old_alert = PendingAlert.get_by_key_name(old_pending_key_name)
        if old_alert:
            new_key_name = '%s:%s:%s' % (frequency, email,
                                         self.params.facility_name)
            PendingAlert(key_name=new_key_name,
                         user_email=old_alert.user_email,
                         facility_name=old_alert.facility_name,
                         old_values=old_alert.old_values,
                         frequency=frequency).put()
            db.delete(old_alert)

if __name__ == '__main__':
    run([('/subscription_handler', SubscriptionHandler)], debug=True)
