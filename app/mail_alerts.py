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
format_update(update, locale): translates and formats a particular update
send_email(): sends an e-mail with the supplied information
update_account_alert_time(): updates an account's next_%freq%_alert time
EmailFormatter: base class to create formatted text for e-mail updates
HospitalEmailFormatter(EmailFormatter): extension for formatting specific to
    hospital e-mail updates
MailAlerts(utils.Handler): handler class to send e-mail updates
"""

# TODO(kpy): Add an end-to-end test for the subscription system as a whole. 

__author__ = 'pfritzsche@google.com (Phil Fritzsche)'

import datetime
import logging
import os
from copy import deepcopy
from operator import itemgetter

from google.appengine.api import mail
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.runtime import DeadlineExceededError
from google.appengine.runtime.apiproxy_errors import OverQuotaError

import cache
import model
import utils
from feedlib.xml_utils import Struct
from model import Account, PendingAlert, Subject, Subscription
from utils import _, format, get_last_updated_time, order_and_format_updates

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
    if format == 'html':
        message.html = body
    else:
        message.body = body

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
    new_time = now + get_timedelta(frequency, now)

    if (getattr(account, 'next_%s_alert' % frequency) == model.MAX_DATE or
        not initial):
        setattr(account, 'next_%s_alert' % frequency, new_time)


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
        if self.email_format == 'html':
            return self.format_html_body(data)
        else:
            return self.format_plain_body(data)

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
            subdomain = subject.get_subdomain()
            subject_type = cache.SUBJECT_TYPES[subdomain][subject.type]
            updates = order_and_format_updates(updates, subject_type,
                                               self.locale, format_update)
            body += 'UPDATE %s (%s)\n\n' % (subject_title, subject.get_name())
            for update in updates:
              body += '%s: %s\n-- %s: %s. %s: %s\n' % (
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
                self.locale, format_update)
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


EMAIL_FORMATTERS = {
    'haiti': {
        'hospital': HospitalEmailFormatter
    },
    'pakistan': {
        'hospital': HospitalEmailFormatter
    }
}

class MailAlerts(utils.Handler):
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
        self.appspot_email = 'updates@%s' % (
            self.get_parent_domain().replace('appspot.com', 'appspotmail.com'))
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
            self.changed_request_data = utils.url_unpickle(
                self.request.get('changed_data'))
            self.unchanged_request_data = utils.url_unpickle(
                self.request.get('unchanged_data'))
            self.update_and_add_pending_alerts()
        else:
            try:
                for subdomain in cache.SUBDOMAINS.keys():
                    for freq in ['daily', 'weekly', 'monthly']:
                        self.send_digests(freq, subdomain)
            except DeadlineExceededError:
                # The cron job will automatically be run every 5 minutes. We
                # expect that in some situations, this will not finish in 30
                # seconds. It is designed to simply pick up where it left off
                # in the next queue of the file, so we pass off this exception
                # to avoid having the system automatically restart the request.
                # NOTE: this only applies to the digest system. If this script
                # is run because a facility is changed, we let the AppEngine
                # error management system kick in.
                logging.info('mail_alerts.py: deadline exceeded error raised')

    def update_and_add_pending_alerts(self):
        """Called when a subject is changed. It creates PendingAlerts for
        any subscription for the changed subject. Also sends out alerts to
        users who were subscribed to instant updates for this particular
        subject.
        """
        subject = Subject.get(self.subdomain, self.params.subject_name)
        subject_key_name = self.subdomain + ':' + self.params.subject_name
        subscriptions = Subscription.get_by_subject(subject_key_name)
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
                        setattr(pa, update['attribute'], update['old_value'])
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
                    subdomain=self.subdomain,
                    changed_subjects={subject_key_name: (
                        subject.get_value('title'),
                        deepcopy(self.changed_request_data))}
                )
                email_formatter = EMAIL_FORMATTERS[
                    self.subdomain][subject.type](account)
                body = email_formatter.format_body(email_data)
                email_subject = format_email_subject(self.subdomain,
                                                     subscription.frequency)
                send_email(account.locale,
                           '%s-%s' % (self.subdomain, self.appspot_email),
                           account.email, email_subject,
                           body, account.email_format)

    def send_digests(self, frequency, subdomain):
        """Sends out a digest update for the specified frequency. Currently
        available choices for the supplied frequency are ['daily', 'weekly',
        'monthly']. Also removes pending alerts once an e-mail has been sent
        and updates the account's next alert times.
        """
        # Accounts with no daily/weekly/monthly subscriptions will be filtered
        # out in this call as their next alert dates will always be set
        # to an arbitrarily high constant date [see model.MAX_DATE].
        query = Account.all().filter(
            'next_%s_alert <' % frequency, datetime.datetime.now()).order(
                'next_%s_alert' % frequency)
        accounts = [account for account in query if account.email != None]
        for account in accounts:
            alerts_to_delete = []
            unchanged_subjects = []
            changed_subjects = {}
            for subscription in Subscription.all().filter('user_email =',
                account.email).filter('frequency =', frequency):
                subject = Subject.get_by_key_name(subscription.subject_name)
                pa = PendingAlert.get(frequency, account.email,
                                      subscription.subject_name)
                if pa:
                    values = fetch_updates(pa, subject)
                    changed_subjects[subscription.subject_name] = (
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
            email_formatter = EMAIL_FORMATTERS[
                subdomain][subject.type](account)
            body = email_formatter.format_body(email_data)
            email_subject = format_email_subject(subdomain, frequency)
            try:
                send_email(account.locale,
                           '%s-%s' % (subdomain, self.appspot_email),
                           account.email, email_subject,
                           body, account.email_format)
                update_account_alert_time(account, frequency)
                db.delete(alerts_to_delete)
                db.put(account)
            except OverQuotaError, message:
                # Throw the error here in order to avoid mass duplication of
                # the mail alerts task. If you let the system automatically
                # handle the error, the combination of cron jobs and re-created
                # tasks will overflow the task queue.
                logging.error(message)


if __name__ == '__main__':
    utils.run([('/mail_alerts', MailAlerts)], debug=True)
