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

format_email_subject(subdomain, frequency): generates an e-mail subject line
get_timedelta(account, subject): returns a text frequency as a timedelta
fetch_updates(): returns a dictionary of updated values for the given subject
order_and_format_updates(updates, subject_type, locale): sorts and formats the
    updates as specified by the subject type for the updates
format_update(update, locale): translates and formats a particular update
send_email(): sends an e-mail with the supplied information
update_account_alert_time(): updates an account's next_%freq%_alert time
EmailFormatter: base class to create formatted text for e-mail updates
HospitalEmailFormatter(EmailFormatter): extension for formatting specific to
    hospital e-mail updates
MailAlerts(utils.Handler): handler class to send e-mail updates
"""

__author__ = 'pfritzsche@google.com (Phil Fritzsche)'

import datetime
import logging
import os
import pickle
from copy import deepcopy
from operator import itemgetter

from google.appengine.api import mail
from google.appengine.ext import db
from google.appengine.ext.webapp import template

import cache
import simplejson
import utils
from feeds.xmlutils import Struct
from model import Account, PendingAlert, Subdomain, Subject
from model import Subscription
from utils import _, format, get_last_updated_time, Handler

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

def format_email_subject(subdomain, frequency):
    """Given a subdomain and frequency, formats an appropriate subject line for
    an update e-mail."""
    frequency = _(str(frequency.title()))
    subject = '%s %s: %s' % (
        subdomain.title(),
        #i18n: subject of e-mail -> Resource Finder Update
        utils.to_unicode(_('Resource Finder %s Update' % frequency)),
        utils.to_local_isotime_day(datetime.datetime.now()))
    return subject


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
            updated_attrs.append({'attribute': attribute,
                                  'old_value': alert_val,
                                  'new_value': value,
                                  'author': author})
    return updated_attrs


def order_and_format_updates(updates, subject_type, locale):
    """Orders attribute updates in the same order specified by
    subject_type.attribute_names, in the given locale."""
    updates_by_name = dict((update['attribute'], update) for update in updates)
    formatted_attrs = []
    for name in subject_type.attribute_names:
        if name in updates_by_name:
            formatted_attrs.append(format_update(updates_by_name[name],
                                                 locale))
    return formatted_attrs


def format_update(update, locale):
    """Insures that the attribute and old/new values of an update are translated
    and properly formatted."""
    update['attribute'] = utils.get_message('attribute_name',
                                            update['attribute'],
                                            locale)
    update['new_value'] = format(update['new_value'], True)
    update['old_value'] = format(update['old_value'], True)
    return update


def send_email(locale, sender, to, subject, body, format):
    """Sends a single e-mail update.

    Args:
        locale: the locale whose language to use for the email
        sender: the e-mail address of the person sending the e-mail
        to: the user to send the update to
        subject: the subject line of the e-mail
        body: the text/html to use as the body of the e-mail
        format: the form [text or html] the body is in
    """
    django.utils.translation.activate(locale)

    message = mail.EmailMessage()
    message.sender = sender
    message.to = to
    message.subject = subject
    if format == 'plain':
        message.body = body
    elif format == 'html':
        message.html = body

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


class EmailFormatter:
    """Base class to format update e-mails.

    Attributes:
        email_format: the preferred e-mail format for this account
        locale: the account's locale

    Methods:
        __init__: constructor; requires the user's account
        format_body: formats the body of an e-mail according to the account's
            local and e-mail format preferences
        format_plain_body: formats a generic plain text e-mail update
        format_html_body: placeholder; override in subclass for HTML formatting
    """

    def __init__(self, account):
        self.email_format = account.email_format
        self.locale = account.locale

    def format_body(self, data):
        if self.email_format == 'plain':
            return self.format_plain_body(data)
        else:
            return self.format_html_body(data)

    def format_plain_body(self, data):
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
            subject = Subject.get_by_key_name(subject_name)
            subdomain = subject_name.split(':')[0]
            subject_type = cache.SUBJECT_TYPES[subdomain][subject.type]
            updates = order_and_format_updates(updates, subject_type,
                                               self.locale)
            body += subject_title.upper() + '\n'
            for update in updates:
                body += '-> %s: %s [%s: %s; %s: %s]\n' % (
                    update['attribute'],
                    utils.to_unicode(format(update['new_value'], True)),
                    #i18n: old value for the attribute
                    utils.to_unicode(_('Previous value')),
                    utils.to_unicode(format(update['old_value'], True)),
                    #i18n: who the attribute was updated by
                    utils.to_unicode(_('Updated by')),
                    utils.to_unicode(update['author']))
            body += '\n'
        return body

    def format_html_body(self, data):
        """Placeholder function. Requires override by subclass [example in
        HospitalEmailFormatter].

        Returns NotImplementedErrors if not overridden."""
        raise NotImplementedError


class HospitalEmailFormatter(EmailFormatter):
    """Class to format update e-mails for hospital subject types.
    
    Methods:
        format_html_body: formats an HTML e-mail update
    """

    def format_html_body(self, data):
        """Forms the HTML body for an e-mail. Expects the data to be input in
        the same format as in format_plain_body(), with the optional addition of
        an 'unchanged_subjects' field of the Struct. These will be displayed at
        the bottom of the HTML e-mail for the purposes of digest information.
        The 'unchanged_subjects' field, if present, should be a list of
        subject names, i.e.:
            [ subject_name1, subject_name2, subject_name3, ... ]
        """
        changed_subjects = []
        for subject_name in data.changed_subjects:
            subject = Subject.get_by_key_name(subject_name)
            subdomain, no_subdomain_name = subject_name.split(':')
            subject_type = cache.SUBJECT_TYPES[subdomain][subject.type]
            updates = order_and_format_updates(
                data.changed_subjects[subject_name][1], subject_type,
                self.locale)
            changed_subjects.append({
                'name': subject_name,
                'no_subdomain_name': no_subdomain_name,
                'title': format(subject.get_value('title')),
                'address': format(subject.get_value('address')),
                'contact_number': format(subject.get_value('phone')),
                'contact_email': format(subject.get_value('email')),
                'available_beds': format(subject.get_value('available_beds')),
                'total_beds': format(subject.get_value('total_beds')),
                'last_updated': format(get_last_updated_time(subject)),
                'changed_vals': updates
            })
        changed_subjects = sorted(changed_subjects, key=itemgetter('title'))

        unchanged_subjects = []
        if 'unchanged_subjects' in data:
            for subject in data.unchanged_subjects:
                subject_name = subject.key().name()
                no_subdomain_name = subject_name.split(':')[1]
                unchanged_subjects.append({
                    'name': subject_name,
                    'no_subdomain_name': no_subdomain_name,
                    'title': subject.get_value('title'),
                    'address': format(subject.get_value('address')),
                    'contact_number': format(subject.get_value('phone')),
                    'contact_email': format(subject.get_value('email')),
                    'available_beds': format(
                        subject.get_value('available_beds')),
                    'total_beds': format(subject.get_value('total_beds')),
                    'last_updated': format(get_last_updated_time(subject))
                })
            unchanged_subjects = sorted(unchanged_subjects,
                                        key=itemgetter('title'))

        template_values = {
            'nickname': data.nickname,
            'domain': data.domain,
            'subdomain': data.subdomain,
            'changed_subjects': changed_subjects,
            'unchanged_subjects': unchanged_subjects
        }

        path = os.path.join(os.path.dirname(__file__),
                            'templates/hospital_email.html')
        return template.render(path, template_values)


FORMAT_EMAIL = {
    'hospital': HospitalEmailFormatter
}

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
        self.appspot_email = 'updates@resource-finder.appspotmail.com'
        self.action = self.request.get('action')

        # Calls made from taskqueue don't have a 'Host' attribute in the headers
        # dictionary. Domain must be parsed out from the full url.
        self.domain = self.request.url[
            :self.request.url.find(self.request.path)]

    def post(self):
        """Responds to HTTP POST requests. This function either (queues up
        future daily/weekly/monthly updates and sends instant updates) or
        (sends out daily/weekly/monthly digest updates).
        """
        self.init()

        if self.action == 'subject_changed':
            # Values encoded to latin-1 before unpickling due to pickle
            # needing 8-bit input, matching its original output.
            self.changed_request_data = pickle.loads(simplejson.loads(
                self.request.get('changed_data')).encode('latin-1'))
            self.unchanged_request_data = pickle.loads(simplejson.loads(
                self.request.get('unchanged_data')).encode('latin-1'))
            self.update_and_add_pending_alerts()
        else:
            for subdomain in Subdomain.all():
                for freq in ['daily', 'weekly', 'monthly']:
                    self.send_digests(freq, subdomain.key().name())

    def update_and_add_pending_alerts(self):
        """Called when a subject is changed. It creates PendingAlerts for
        any subscription for the changed subject. Also sends out alerts to
        users who were subscribed to instant updates for this particular
        subject.
        """
        subject = Subject.get_by_key_name(self.params.subject_name)
        subdomain = self.params.subject_name.split(':')[0]

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
                    for update in self.changed_request_data:
                        # None type objects come back from being pickled as the
                        # unicode dash. If one is found, set the attribute in
                        # the PendingAlert to None.
                        if update['old_value'] == '\xe2\x80\x93':
                            setattr(pa, update['attribute'], None)
                        else:
                            setattr(pa, update['attribute'],
                                    update['old_value'])
                    for attribute in self.unchanged_request_data:
                        setattr(pa, attribute,
                                self.unchanged_request_data[attribute])
                    pa.timestamp = datetime.datetime.now()
                    db.put(pa)

            else:
                # send out alerts for those with instant update subscriptions
                account = Account.all().filter('email =',
                                               subscription.user_email).get()
                email_data = Struct(
                    nickname=account.nickname or account.email,
                    domain=self.domain,
                    subdomain=subdomain,
                    changed_subjects={self.params.subject_name: (
                        subject.get_value('title'),
                        deepcopy(self.changed_request_data))}
                )
                email_formatter = FORMAT_EMAIL[subject.type](account)
                body = email_formatter.format_body(email_data)
                email_subject = format_email_subject(subdomain,
                                                     subscription.frequency)
                send_email(account.locale, self.appspot_email,
                           account.email, email_subject,
                           body, account.email_format)

    def send_digests(self, frequency, subdomain):
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
            unchanged_subjects = []
            changed_subjects = {}
            for subscription in Subscription.all().filter('user_email =',
                                                          account.email):
                subject = Subject.get_by_key_name(subscription.subject_name)
                pa = PendingAlert.get(frequency, account.email,
                                      subscription.subject_name)
                if pa:
                    values = fetch_updates(pa, subject)
                    changed_subjects[subject.key().name()] = (
                        subject.get_value('title'), values)
                    alerts_to_delete.append(pa)
                else:
                    unchanged_subjects.append(subject)

            if not changed_subjects and (account.email_format == 'plain' or
                not unchanged_subjects):
                continue

            email_data = Struct(
                nickname=account.nickname or account.email,
                domain=self.domain,
                subdomain=subdomain,
                changed_subjects=changed_subjects,
                unchanged_subjects=unchanged_subjects
            )
            email_formatter = FORMAT_EMAIL[subject.type](account)
            body = email_formatter.format_body(email_data)
            email_subject = format_email_subject(subdomain, frequency)
            send_email(account.locale, self.appspot_email,
                       account.email, email_subject,
                       body, account.email_format)
            update_account_alert_time(account, frequency)
            db.delete(alerts_to_delete)
            db.put(account)


if __name__ == '__main__':
    utils.run([('/mail_alerts', MailAlerts)], debug=True)
