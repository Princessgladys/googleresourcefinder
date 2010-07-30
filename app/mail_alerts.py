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
fetch_updates(): returns a dictionary of updated values for the given subject
format_plain_body(values): forms the e-mail body for an update e-mail in text
send_email(): sends an e-mail with the supplied information
update_account_alert_time(): updates an account's next_%freq%_alert time
MailAlerts(utils.Handler): handler class to send e-mail updates
"""

__author__ = 'pfritzsche@google.com (Phil Fritzsche)'

import datetime
import logging
import os

from google.appengine.api import mail
from google.appengine.ext import db

import bubble
import cache
import utils
from model import Account, PendingAlert, Subject, SubjectType, Subscription
from utils import _, Handler, Struct

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

FREQUENCY_TO_TIMEDELTA = {
    'instant': datetime.timedelta(0),
    'daily': datetime.timedelta(1),
    'weekly': datetime.timedelta(7)
}

def get_timedelta(frequency, now=None):
    """Given a text frequency, converts it to a timedelta."""
    if frequency in FREQUENCY_TO_TIMEDELTA:
        return FREQUENCY_TO_TIMEDELTA[frequency]
    elif frequency == 'monthly':
        if not now:
            now = datetime.datetime.now()
        next_month = datetime.datetime(now.year + (now.month / 12),
                                       (now.month % 12) + 1, 1, now.hour,
                                       now.minute, now.second, now.microsecond)
        return next_month - now
    return None


def fetch_updates(alert, subject):
    """For a given alert and subject, finds any updated values.
    
    Returns:
        A list of dictionary mappings of attributes and their updated
        values, including the attribute, the old/new values, and the
        most recent author to update the value. Example:
        
            [(attribute, {'old_value': value_foo,
                          'new_value': value_bar,
                          'author': author_foo})]
    """
    if not (alert and subject):
        return []
    updated_attrs = []
    
    old_values = alert.dynamic_properties()
    for attribute in old_values:
        value = subject.get_value(attribute)
        author = subject.get_author_nickname(attribute)
        alert_val = getattr(alert, attribute)
        if value != alert_val:
            updated_attrs.append((attribute, {'old_value': alert_val,
                                              'new_value': value,
                                              'author': author}))
    
    return updated_attrs


def format_plain_body(data):
    """Forms the plain text body for an e-mail. Expects the data to be input
    in the following format:
        
        Struct(
            date=datetime
            changed_subjects={subject_key: (subject_title, (attribute,
                {'old_value': value_foo,
                 'new_value': value_bar,
                 'author': author_foo}))})
    """
    body = u''
    for subject_name in data.changed_subjects:
        (subject_title, updates) = data.changed_subjects[subject_name]
        body += subject_title.upper() + '\n'
        for attribute, info in updates:
            body += '-> %s: %s [%s: %s; %s: %s]\n' % (
                #i18n: changed attribute name
                attribute,
                utils.to_unicode(utils.value_or_dash(info['new_value'])),
                #i18n: old value for the attribute
                utils.to_unicode(_('Previous value')),
                utils.to_unicode(utils.value_or_dash(info['old_value'])),
                #i18n: who the attribute was updated by
                utils.to_unicode(_('Updated by')),
                utils.to_unicode(info['author']))
        body += '\n'
    return body


def send_email(locale, sender, to, subject, text_body):
    """Sends a single e-mail update.
    
    Args:
        locale: the locale whose language to use for the email
        sender: the e-mail address of the person sending the e-mail
        to: the user to send the update to
        subject: the subject line of the e-mail
        text_body: the text to use as the body of the e-mail [plain text]
    """
    django.utils.translation.activate(locale)
    
    message = mail.EmailMessage()
    message.sender = sender
    message.to = to
    message.subject = subject
    message.body = text_body
    
    message.send()


def update_account_alert_time(account, frequency, now=None, initial=False):
    """Updates a particular account to send an alert at the appropriate
    later date, depending on the given frequency.
    
    Args:
        account: the account whose time is to be updated
        frequency: used to determine how much to update by
        initial: (optional) tells the function to check if this is the first
            time setting the account's update times"""
    if not now:
        now = datetime.datetime.now()
        new_time = now + get_timedelta(frequency)
    else:
        new_time = now + get_timedelta(frequency, now)
    
    if initial:
        if frequency == 'daily' and not account.next_daily_alert:
            account.next_daily_alert = new_time
        elif frequency == 'weekly' and not account.next_weekly_alert:
            account.next_weekly_alert = new_time
        elif frequency == 'monthly' and not account.next_monthly_alert:
            account.next_monthly_alert = new_time
    else:
        if frequency == 'daily':
            account.next_daily_alert = new_time
        elif frequency == 'weekly':
            account.next_weekly_alert = new_time
        elif frequency == 'monthly':
            account.next_monthly_alert = new_time

class MailAlerts(Handler):
    """Handler for /mail_alerts. Used to handle e-mail update sending.
    
    Attributes:
        action: the specific action to be taken by the class
            
    Methods:
        init(): handles initialization tasks for the class
        post(): responds to HTTP POST requests
        update_and_add_pending_alerts(): queues up future digest alerts and
            sends out instant updates; called when a subject is changed
        send_digests(): sends out a digest update for the specified frequency
    """
    
    def init(self):
        """Handles any useful initialization tasks for the class."""
        self.action = self.request.get('action')
    
    def post(self):
        """Responds to HTTP POST requests. This function either (queues up
        future daily/weekly/monthly updates and sends instant updates) or
        (sends out daily/weekly/monthly digest updates).
        """
        self.init()
        
        if self.action == 'subject_changed':
            self.changed_request_data = utils.url_unpickle(
                self.request.get('changed_data'))
            self.unchanged_request_data = utils.url_unpickle(
                self.request.get('unchanged_data'))
            self.update_and_add_pending_alerts()
        else:
            for freq in ['daily', 'weekly', 'monthly']:
                self.send_digests(freq)
    
    def update_and_add_pending_alerts(self):
        """Called when a subject is changed. It creates PendingAlerts for
        any subscription for the changed subject. Also sends out alerts to
        users who were subscribed to instant updates for this particular
        subject.
        """
        subject = Subject.get_by_key_name(self.params.subject_name)
        subject_type = SubjectType.get(self.subdomain, subject.type)
        
        email_data = Struct()
        email_data.time = utils.to_local_isotime(datetime.datetime.now(),
                                                 clear_ms=True)
        email_data.changed_subjects = {self.params.subject_name: (
            subject.get_value('title'), self.changed_request_data.items())}
        text_body = format_plain_body(email_data)
        
        subscriptions = Subscription.get_by_subject(self.params.subject_name)
        for subscription in subscriptions:
            if subscription.frequency != 'instant':
                # queue pending alerts for non-instant update subscriptions
                key_name = '%s:%s:%s' % (subscription.frequency,
                                         subscription.user_email,
                                         subscription.subject_name)
                pa = PendingAlert.get_or_insert(
                    key_name, type=subject.type,
                    user_email=subscription.user_email,
                    subject_name=subscription.subject_name,
                    frequency=subscription.frequency)
                if not pa.timestamp:
                    for attribute, info in self.changed_request_data.items():
                        setattr(pa, attribute, info['old_value'])
                    for attribute in self.unchanged_request_data:
                        setattr(pa, attribute,
                                self.unchanged_request_data[attribute])
                    pa.timestamp = datetime.datetime.now()
                    db.put(pa)
            
            else:
                # send out alerts for those with instant update subscriptions
                account = Account.all().filter('email =',
                                               subscription.user_email).get()
                send_email(account.locale,
                           'updates@resource-finder.appspotmail.com',
                           account.email,
                           # i18n: subject of e-mail -> Resource Finder Updates
                           utils.to_unicode(_('Resource Finder Updates')),
                           text_body)
    
    def send_digests(self, frequency):
        """Sends out a digest update for the specified frequency. Currently
        available choices for the supplied frequency are ['daily', 'weekly',
        'monthly']. Also removes pending alerts once an e-mail has been sent
        and updates the account's next alert times.
        """
        accounts = Account.all().filter('next_%s_alert <' % frequency,
                                        datetime.datetime.now())
        for account in accounts:
            pending_alerts = PendingAlert.get_by_frequency(frequency,
                                                           account.email)
            alerts_to_delete = []
            subjects = {}
            for alert in pending_alerts:
                subj = Subject.get_by_key_name(alert.subject_name)
                values = fetch_updates(alert, subj)
                subjects[subj.key().name()] = (subj.get_value('title'),
                    values)
                alerts_to_delete.append(alert)
            
            if not subjects:
                continue
            
            email_data = Struct()
            email_data.time = utils.to_local_isotime(datetime.datetime.now(),
                                                     clear_ms=True)
            email_data.changed_subjects = subjects
            text_body = format_plain_body(email_data)
            send_email(account.locale,
                       'updates@resource-finder.appspotmail.com',
                       account.email,
                       # i18n: subject of e-mail -> Resource Finder Updates
                       utils.to_unicode( _('Resource Finder Updates')),
                       text_body)
            update_account_alert_time(account, frequency)
            db.delete(alerts_to_delete)
            db.put(account)


if __name__ == '__main__':
    utils.run([('/mail_alerts', MailAlerts)], debug=True)
