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
form_plain_body(values): forms the e-mail body for an update e-mail in text
send_email(): sends an e-mail with the supplied information
update_account_alert_time(): updates an account's next_%freq%_alert time
MailUpdateSystem(utils.Handler): handler class to send e-mail updates
"""

__author__ = 'pfritzsche@google.com (Phil Fritzsche)'

import datetime
import logging
import os
import pickle

from google.appengine.api import mail
from google.appengine.ext import db
from google.appengine.ext.webapp import template

import cache
import utils
from bubble import format
from export import get_last_updated_time
from feeds.xmlutils import Struct
from model import Account, PendingAlert, Subject, SubjectType, Subscription
from utils import _, Handler, simplejson

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
    'immediate': datetime.timedelta(0),
    'daily': datetime.timedelta(1),
    'weekly': datetime.timedelta(7),
    'monthly': datetime.timedelta(30) # note: 'monthly' is every 30 days
}

def get_timedelta(frequency):
    """Given a text frequency, converts it to a timedelta."""
    if frequency in FREQUENCY_TO_TIMEDELTA:
        return FREQUENCY_TO_TIMEDELTA[frequency]
    return None


def fetch_updates(alert, subject):
    """For a given alert and subject, finds any updated values.
    
    Returns:
        A list of dictionary mappings of attributes and their updated
        values, including the attribute, the old/new values, and the
        most recent author to update the value. Example:
        
            [ [attribute, new_value, old_value, author_foo ],
              [attribute, new_value, old_value, author_foo ],
              [attribute, new_value, old_value, author_foo ] ]
    """
    if not (alert and subject):
        return
    updated_attrs = []
    subject_type = cache.SUBJECT_TYPES[subject.type]
    
    old_values = alert.dynamic_properties()
    for i in range(len(old_values)):
        value = subject.get_value(old_values[i])
        author = subject.get_author_nickname(old_values[i])
        alert_val = getattr(alert, old_values[i])
        if value != alert_val:
            updated_attrs.append({
                'attribute': old_values[i], # attribute
                'old_value': alert_val, # old
                'new_value': value, # new
                'author': author # author of the change
            })
    
    return updated_attrs


def form_plain_body(data):
    """Forms the plain text body for an e-mail. Expects the data to be input
    in the following format:
        
        Struct(
            date=datetime
            changed_subjects={subject_key: {subject_title: [
                { attribute: attr_foo,
                  old_value: value_foo,
                  new_value: value_bar,
                  author: author_foo },
                { attribute: attr_foo,
                  old_value: value_foo,
                  new_value: value_bar,
                  author: author_foo }
            ]}}
        )
    """
    body = ''
    for subject_name in data.changed_subjects:
        subject_title = data.changed_subjects[subject_name].keys()[0]
        updates = data.changed_subjects[subject_name][subject_title]
        body += subject_title.upper() + '\n'
        for update in updates:
            body += '-> ' + str(update['attribute']) + ": "
            body += str(update['new_value']) + ' ' + '[Old Value: '
            body += str(update['old_value']) + '; Updated by: '
            body += str(update['author']) + ']\n'
        body += '\n'
    return body

def form_html_body(data):
    """Forms the HTML body for an e-mail. Expects the data to be input in
    the same format as in form_plain_body(), with the optional addition of
    an 'unchanged_subjects' field of the Struct. These will be displayed at
    the bottom of the HTML e-mail for the purposes of digest information.
    The 'unchanged_subjects' field, if present, should be a list of
    subject names, i.e.:
        [ subject_name1, subject_name2, subject_name3, ... ]
    """
    changed_subjects = []
    for subject_key in data.changed_subjects:
        subject = Subject.get_by_key_name(subject_key)
        changed_subjects.append({
            'name': subject_key,
            'title': subject.get_value('title'),
            'address': subject.get_value('address'),
            'contact_number': subject.get_value('phone'),
            'contact_email': subject.get_value('email'),
            'available_beds': subject.get_value('available_beds'),
            'total_beds': subject.get_value('total_beds'),
            'last_updated': format(get_last_updated_time(subject)),
            'changed_vals': data.changed_subjects[subject_key][
                subject.get_value('title')]
        })
    
    if 'unchanged_subjects' not in data:
        data.unchanged_subjects = []
    unchanged_subjects = []
    for subject_key in data.unchanged_subjects:
        subject = Subject.get_by_key_name(subject_key)
        unchanged_subjects.append({
            'name': subject_key,
            'title': subject.get_value('title'),
            'address': subject.get_value('address'),
            'contact_number': subject.get_value('phone'),
            'contact_email': subject.get_value('email'),
            'available_beds': subject.get_value('available_beds'),
            'total_beds': subject.get_value('total_beds'),
            'last_updated': format(get_last_updated_time(subject))
        })
    
    template_values = {
        'date': data.time,
        'nickname': data.nickname,
        'changed_subjects': changed_subjects,
        'unchanged_subjects': unchanged_subjects
    }
    
    path = os.path.join(os.path.dirname(__file__),
                        'templates/hospital_email.html')
    return template.render(path, template_values)


def send_email(locale, sender, to, subject, text_body, html_body):
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
    message.html = html_body
    
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

class MailUpdateSystem(Handler):
    """Handler for /mail_update_system. Used to handle e-mail update sending.
    
    Attributes:
        action: the specific action to be taken by the class
            
    Methods:
        init(): handles initialization tasks for the class
        post(): responds to HTTP POST requests
        update_and_add_pending_subs(): queues up future digest alerts and
            sends out immediate updates; called when a subject is changed
        send_digests(): sends out a digest update for the specified frequency
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
            self.request_data = pickle.loads(str(simplejson.loads(
                                             self.request.get('data'))))
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
        subject_type = SubjectType.get(subject.key().name().split(':')[0],
                                       subject.type)
        values = []
        for arg in self.request_data:
            values.append({
                'attribute': arg, # attribute
                'old_value': self.request_data[arg][0], # old value
                'new_value': self.request_data[arg][1], # new value
                'author': self.request_data[arg][2] # author of update
            })
        
        subscriptions = Subscription.get_by_subject(self.params.subject_name)
        for subscription in subscriptions:
            if subscription.frequency != 'immediate':
                # queue pending alerts for non-immediate update subscriptions
                key_name = '%s:%s:%s' % (subscription.frequency,
                                         subscription.user_email,
                                         subscription.subject_name)
                pa = PendingAlert.get_or_insert(key_name,
                    type=subject.type, user_email=subscription.user_email,
                    subject_name=subscription.subject_name,
                    frequency=subscription.frequency)
                if not pa.timestamp:
                    for value in values:
                        setattr(pa, value[0], value[1]) #(attr, old_value)
                    for attribute in filter(lambda a: a not in
                        pa.dynamic_properties(), subject_type.attribute_names):
                        setattr(pa, attribute, subject.get_value(attribute))
                    pa.timestamp = datetime.datetime.now()
                    db.put(pa)
            
            else:
                # send out alerts for those with immediate update subscriptions
                account = Account.all().filter('email =',
                                               subscription.user_email).get()
                email_data = Struct()
                email_data.time = format(datetime.datetime.now())
                email_data.nickname = account.nickname or account.email
                email_data.changed_subjects = {self.params.subject_name: {
                    subject.get_value('title'): values}}
                text_body = form_plain_body(email_data)
                html_body = form_html_body(email_data)
                send_email(account.locale,
                           'updates@resource-finder.appspotmail.com',
                           account.email, utils.to_unicode(
                           _('Resource Finder Updates')), text_body, html_body)
    
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
                subjects[subj.key().name()] = {subj.get_value('title'):
                    values}
                alerts_to_delete.append(alert)
            
            if not subjects:
                continue
                
            email_data = Struct()
            email_data.time = format(datetime.datetime.now())
            email_data.nickname = account.nickname or account.email
            email_data.changed_subjects = subjects
            text_body = form_plain_body(email_data)
            html_body = form_html_body(email_data)
            send_email(account.locale,
                       'updates@resource-finder.appspotmail.com',
                       account.email, utils.to_unicode(
                       _('Resource Finder Updates')), text_body, html_body)
            update_account_alert_time(account, frequency)
            db.delete(alerts_to_delete)
            db.put(account)


if __name__ == '__main__':
    utils.run([('/mail_update_system', MailUpdateSystem)], debug=True)
