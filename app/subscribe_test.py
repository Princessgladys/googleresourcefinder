# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for subscribe.py."""

import datetime
import os
import pickle
import webob

from google.appengine.api import mail
from google.appengine.ext import db, webapp
from google.appengine.ext.db import BadValueError

import model
import simplejson
import subscribe
import utils
from medium_test_case import MediumTestCase
from model import Account, PendingAlert, Subject, SubjectType, Subscription
from utils import users

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

sent_emails = []

def fake_send_email(locale, sender, to, subject, body, format):
    global sent_emails
    sent_emails = []
    django.utils.translation.activate(locale)
    
    message = mail.EmailMessage()
    message.sender = sender
    message.to = to
    message.subject = subject
    if format == 'html':
        message.html = body
    else:
        message.body = body
    sent_emails.append(message)
    
    # add asserts for when testing the MailUpdateSystem class
    assert locale and sender and to and subject and body
    assert '@' in (sender and to)
    assert sender.find('.org') or sender.find('.com')
    assert to.find('.org') or to.find('.com')
    return message

class MailUpdateSystemTest(MediumTestCase):
    def setUp(self):
        MediumTestCase.setUp(self)
        self.send_real_email = subscribe.send_email
        subscribe.send_email = fake_send_email
        self.time = datetime.datetime(2010, 06, 01)
        self.user = users.User('test@example.com')
        self.nickname = 'nickname_foo'
        self.affiliation = 'affiliation_foo'
        self.comment = 'comment_foo'
        self.email = self.user.email()
        self.default_frequency = 'instant'
        self.locale = 'en'
        self.default_alert_time = datetime.datetime(2000, 1, 1)
        self.account = Account(email=self.email, actions=['*:*'],
                               default_frequency=self.default_frequency,
                               locale=self.locale, email_format='plain',
                               next_daily_alert=self.default_alert_time,
                               next_weekly_alert=self.default_alert_time,
                               next_monthly_alert=self.default_alert_time)
        db.put(self.account)

    def tearDown(self):
        subscribe.send_email = self.send_real_email
        for s in Subscription.all():
            db.delete(s)
    
    def test_subscribe(self):
        """Confirm that a subscription is added on post request."""
        # send request with frequency
        handler = self.simulate_request('/subscribe?action=subscribe&' +
                                        'subject_name=haiti:example.org/123&' +
                                        'frequency=daily')
        handler.post()
        s = Subscription.get('haiti:example.org/123', 'test@example.com')
        assert s
        assert s.frequency == 'daily'
        
        # send request without frequency; the subscription should have
        # account's default_frequency as its frequency
        handler = self.simulate_request('/subscribe?action=subscribe&' +
                                        'subject_name=haiti:example.org/123')
        handler.post()
        s = Subscription.get('haiti:example.org/123', 'test@example.com')
        assert s
        assert s.frequency == 'instant'

    def test_unsubscribe(self):
        """Confirm that a subscription is removed on post request."""
        # insure that the subscription is removed
        key_name_s = 'haiti:example.org/123:test@example.com'
        s = Subscription(key_name=key_name_s,
                         frequency=self.default_frequency,
                         subject_name='haiti:example.org/123',
                         user_email=self.email)
        db.put(s)
        handler = self.simulate_request('/subscribe?action=unsubscribe&' +
                                        'subject_name=haiti:example.org/123')
        handler.post()
        assert not Subscription.get_by_key_name(key_name_s)

        # should also remove pending alerts if they exist, though there is
        # another subscription so the next_daily_alert time should stay as is
        key_name_s2 = 'haiti:example.org/456:test@example.com'
        s2 = Subscription(key_name=key_name_s2,
                          frequency='daily',
                          subject_name='haiti:example.org/456',
                          user_email=self.email)
        s.frequency = 'daily'
        key_name_pa = 'daily:test@example.com:haiti:example.org/123'
        pa = PendingAlert(key_name=key_name_pa, frequency='daily',
                          subject_name='haiti:example.org/123',
                          type='hospital', user_email='test@example.com')
        db.put([s, s2, pa])
        handler.post()
        assert not Subscription.get_by_key_name(key_name_s)
        assert not PendingAlert.get_by_key_name(key_name_pa)
        assert Account.all().get().next_daily_alert == self.default_alert_time

        # remove the last daily subscription -- user's next_daily_alert time
        # should now match model.MAX_DATE
        handler = self.simulate_request('/subscribe?action=unsubscribe&' +
                                        'subject_name=haiti:example.org/456')
        handler.post()
        assert not Subscription.get_by_key_name(key_name_s2)
        assert Account.all().get().next_daily_alert == model.MAX_DATE

        # should not raise an error if an invalid subscription is given
        handler = self.simulate_request('/subscribe?action=unsubscribe&' +
                                        'subject_name=haiti:example.org/789')
        handler.post()


    def test_unsubscribe_multiple(self):
        """Confirm that all specified subscriptions are removed per post
        request."""
        s1 = Subscription(key_name='haiti:example.org/123:test@example.com',
                          user_email='test@example.com', frequency='instant',
                          subject_name='haiti:example.org/123')
        s2 = Subscription(key_name='haiti:example.org/456:test@example.com',
                          user_email='test@example.com', frequency='instant',
                          subject_name='haiti:example.org/456')
        db.put([s1, s2])

        json = simplejson.dumps(['haiti:example.org/123',
                                 'haiti:example.org/456'])
        handler = self.simulate_request('/subscribe?subdomain=haiti&' +
                                        'action=unsubscribe_multiple&' +
                                        'subjects=' + json)
        handler.post()
        assert not Subscription.all().get()

        db.put([s1, s2])
        json = simplejson.dumps(['haiti:example.org/123'])
        handler = self.simulate_request('/subscribe?subdomain=haiti&' +
                                        'action=unsubscribe_multiple&' +
                                        'subjects=' + json)
        handler.post()
        assert not Subscription.get('haiti:example.org/123', self.email)
        assert Subscription.get('haiti:example.org/456', self.email)

        db.put([s1, s2])
        json = simplejson.dumps([])
        handler = self.simulate_request('/subscribe?subdomain=haiti&' +
                                        'action=unsubscribe_multiple&' +
                                        'subjects=' + json)
        handler.post()
        assert Subscription.get('haiti:example.org/123', self.email)
        assert Subscription.get('haiti:example.org/456', self.email)

        # confirm that it does not max the next_daily_alert time when there are
        # daily subscriptions left for the user
        s1.frequency = 'daily'
        s2.frequency = 'daily'
        db.put([s1, s2])
        json = simplejson.dumps(['haiti:example.org/123'])
        handler = self.simulate_request('/subscribe?subdomain=haiti&' +
                                        'action=unsubscribe_multiple&' +
                                        'subjects=' + json)
        handler.post()
        assert not Subscription.get('haiti:example.org/123', self.email)
        assert Subscription.get('haiti:example.org/456', self.email)
        assert Account.all().get().next_daily_alert == self.default_alert_time

        # confirm that it does max the next_daily_alert time when there aren't
        db.put([s1, s2])
        json = simplejson.dumps(['haiti:example.org/123',
                                 'haiti:example.org/456'])
        handler = self.simulate_request('/subscribe?subdomain=haiti&' +
                                        'action=unsubscribe_multiple&' +
                                        'subjects=' + json)
        handler.post()
        assert not Subscription.all().get()
        assert Account.all().get().next_daily_alert == model.MAX_DATE

    def test_change_locale(self):
        """Confirm that the account's locale parameter is changed."""
        handler = self.simulate_request('/subscribe?subdomain=haiti&' +
                                        'action=change_locale&' +
                                        'locale=fr')
        handler.post()
        assert Account.all().get().locale == 'fr'

        handler = self.simulate_request('/subscribe?subdomain=haiti&' +
                                        'action=change_locale')
        handler.post()
        assert Account.all().get().locale == 'fr'

    def test_change_email_format(self):
        """Confirm that the account's email_format parameter is changed."""
        handler = self.simulate_request('/subscribe?subdomain=haiti&' +
                                        'action=change_email_format&' +
                                        'email_format=plain')
        handler.post()
        assert Account.all().get().email_format == 'plain'

        handler = self.simulate_request('/subscribe?subdomain=haiti&' +
                                        'action=change_email_format&' +
                                        'email_format=html')
        handler.post()
        assert Account.all().get().email_format == 'html'

        handler = self.simulate_request('/subscribe?subdomain=haiti&' +
                                        'action=change_email_format&' +
                                        'email_format=plane')
        self.assertRaises(BadValueError, handler.post)

    def test_change_subscriptions(self):
        """Confirm that subscriptions are changed properly and PendingAlerts
        are removed / changed as appropriate."""
        # change subscription w/o pending alert from instant to daily
        global sent_emails
        subject_name = 'haiti:example.org/123'
        key_name_s = '%s:%s' % (subject_name, self.email)
        s = Subscription(key_name=key_name_s,
                         frequency=self.default_frequency,
                         subject_name='haiti:example.org/123',
                         user_email=self.email)
        db.put(s)
        subject_changes = [{'subject_name': subject_name, 'old_frequency':
                            'instant', 'new_frequency': 'daily'}]
        json_pickle_changes = simplejson.dumps(subject_changes)
        handler = self.simulate_request('/subscribe?subdomain=haiti&' +
                                        'action=change_subscriptions&' +
                                        'subject_changes=%s' %
                                        json_pickle_changes)
        handler.post()
        assert Subscription.get_by_key_name(key_name_s).frequency == 'daily'

        # change subscription with pending alert from daily to weekly
        key_name_pa = 'daily:%s:%s' % (self.email, subject_name)
        pa = PendingAlert(key_name=key_name_pa, frequency='daily',
                          subject_name='haiti:example.org/123',
                          type='hospital', user_email='test@example.com')
        setattr(pa, 'title', 'title_bar')
        db.put(pa)
        subject_changes = [{'subject_name': subject_name, 'old_frequency':
                            'daily', 'new_frequency': 'weekly'}]
        json_pickle_changes = simplejson.dumps(subject_changes)
        handler = self.simulate_request('/subscribe?subdomain=haiti&' +
                                        'action=change_subscriptions&' +
                                        'subject_changes=%s' %
                                        json_pickle_changes)
        handler.post()
        assert Subscription.get_by_key_name(key_name_s).frequency == 'weekly'
        assert not PendingAlert.get_by_key_name(key_name_pa)
        assert PendingAlert.get('weekly', self.email, subject_name)
        assert Account.all().get().next_daily_alert == model.MAX_DATE
        assert Account.all().get().next_weekly_alert != model.MAX_DATE

        # change subscription from weekly back to daily; make sure that
        # account.next_daily_alert is reset from MAX_DATE to tomorrow
        key_name_pa = 'weekly:%s:%s' % (self.email, subject_name)
        subject_changes = [{'subject_name': subject_name, 'old_frequency':
                            'weekly', 'new_frequency': 'daily'}]
        json_pickle_changes = simplejson.dumps(subject_changes)
        handler = self.simulate_request('/subscribe?subdomain=haiti&' +
                                        'action=change_subscriptions&' +
                                        'subject_changes=%s' %
                                        json_pickle_changes)
        handler.post()
        assert Subscription.get_by_key_name(key_name_s).frequency == 'daily'
        assert not PendingAlert.get_by_key_name(key_name_pa)
        assert PendingAlert.get('daily', self.email, subject_name)
        assert Account.all().get().next_daily_alert != model.MAX_DATE
        assert Account.all().get().next_weekly_alert == model.MAX_DATE

        # change subscription with pending alert to instant. make sure
        # that pending alerts are deleted and no errors are thrown when
        # the e-mail is sent
        s = Subject(key_name=subject_name, type='hospital', author=self.user)
        self.set_attr(s, 'title', 'title_foo')
        self.set_attr(s, 'healthc_id', 123)
        st = SubjectType(key_name='haiti:hospital')
        db.put([s, st])

        subject_changes = [{'subject_name': subject_name, 'old_frequency':
                            'daily', 'new_frequency': 'instant'}]
        json_pickle_changes = simplejson.dumps(subject_changes)
        handler = self.simulate_request('/subscribe?subdomain=haiti&' +
                                        'action=change_subscriptions&' +
                                        'subject_changes=%s' %
                                        json_pickle_changes)
        handler.post()
        assert (Subscription.get_by_key_name(key_name_s).frequency ==
                'instant')
        for freq in ['daily', 'weekly', 'monthly']:
            assert not PendingAlert.get(freq, self.email, subject_name)
        assert len(sent_emails) == 1
        assert 'UPDATE title_foo (example.org/123)' in sent_emails[0].body
        assert Account.all().get().next_weekly_alert == model.MAX_DATE
        db.delete([s, st])

    def test_change_default_frequency(self):
        """Confirms that the account's default frequency is changed."""
        assert Account.all().get().default_frequency == 'instant'
        handler = self.simulate_request('/subscribe?subdomain=haiti&' +
                                        'action=change_default_frequency&' +
                                        'frequency=monthly')
        handler.post()
        assert Account.all().get().default_frequency == 'monthly'

    def test_check_and_update_next_alert_times(self):
        """Confirms that next_%freq%_alert times are changed appropriately to
        the max value we are using when no subscriptions exist."""
        subscribe_ = subscribe.Subscribe()
        Subscription(key_name='haiti:example.org/123:test@example.com',
                     user_email='test@example.com',
                     subject_name='haiti:example.org/123',
                     frequency='daily').put()
        subscribe_.account = self.account
        subscribe_.email = self.email

        # user has daily subscriptions; next alert time should remain the same
        subscribe_.check_and_update_next_alert_times('daily')
        assert Account.all().get().next_daily_alert == self.default_alert_time

        # user has no weekly subscriptions; next alert time should max out
        subscribe_.check_and_update_next_alert_times('weekly')
        assert Account.all().get().next_weekly_alert == model.MAX_DATE

        # ditto weekly comment above
        subscribe_.check_and_update_next_alert_times('monthly')
        assert Account.all().get().next_weekly_alert == model.MAX_DATE

    def simulate_request(self, path):
        request = webapp.Request(webob.Request.blank(path).environ)
        response = webapp.Response()
        handler = subscribe.Subscribe()
        handler.initialize(request, response, self.user)
        return handler

    def set_attr(self, subject, key, value):
        subject.set_attribute(key, value, self.time, self.user, self.nickname,
                              self.affiliation, self.comment)
