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

import subscribe
import utils
from medium_test_case import MediumTestCase
from model import Account, PendingAlert, Subject, SubjectType, Subscription
from utils import simplejson, users

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

def fake_send_email(locale, sender, to, subject, text_body):
    global sent_emails
    sent_emails = []
    django.utils.translation.activate(locale)
    
    message = mail.EmailMessage()
    message.sender = sender
    message.to = to
    message.subject = subject
    message.body = text_body
    sent_emails.append(message)
    
    # add asserts for when testing the MailUpdateSystem class
    assert locale and sender and to and subject and text_body
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
        self.default_frequency = 'immediate'
        self.locale = 'en'
        self.account = Account(email=self.email, actions=['*:*'],
                               default_frequency=self.default_frequency,
                               locale=self.locale)
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
        assert s.frequency == 'immediate'
        
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
        
        # should also remove pending alerts if they exist
        key_name_pa = 'daily:test@example.com:haiti:example.org/123'
        pa = PendingAlert(key_name=key_name_pa, frequency='daily',
                          subject_name='haiti:example.org/123',
                          type='hospital', user_email='test@example.com')
        db.put([s, pa])
        handler.post()
        assert not Subscription.get_by_key_name(key_name_s)
        assert not PendingAlert.get_by_key_name(key_name_pa)
        
        # should not raise an error if an invalid subscription is given
        handler = self.simulate_request('/subscribe?action=unsubscribe&' +
                                        'subject_name=haiti:example.org/789')
        handler.post()
    
    def test_change_subscriptions(self):
        """Confirm that subscriptions are changed properly and PendingAlerts
        are removed / changed as appropriate."""
        # change subscription w/o pending alert from immediate to daily
        global sent_emails
        subject_name = 'haiti:example.org/123'
        key_name_s = '%s:%s' % (subject_name, self.email)
        s = Subscription(key_name=key_name_s,
                         frequency=self.default_frequency,
                         subject_name='haiti:example.org/123',
                         user_email=self.email)
        db.put(s)
        subject_changes = [{'subject_name': subject_name, 'old_frequency':
                            'immediate', 'new_frequency': 'daily'}]
        json_pickle_changes = simplejson.dumps(subject_changes)
        handler = self.simulate_request('/subscribe?' +
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
        handler = self.simulate_request('/subscribe?' +
                                        'action=change_subscriptions&' +
                                        'subject_changes=%s' %
                                        json_pickle_changes)
        handler.post()
        assert Subscription.get_by_key_name(key_name_s).frequency == 'weekly'
        assert not PendingAlert.get_by_key_name(key_name_pa)
        assert PendingAlert.get('weekly', self.email, subject_name)
        
        # change subscription with pending alert to immediate. make sure
        # that pending alerts are deleted and no errors are thrown when
        # the e-mail is sent
        s = Subject(key_name=subject_name, type='hospital', author=self.user)
        self.set_attr(s, 'title', 'title_foo')
        db.put(s)
        
        subject_changes = [{'subject_name': subject_name, 'old_frequency':
                            'weekly', 'new_frequency': 'immediate'}]
        json_pickle_changes = simplejson.dumps(subject_changes)
        handler = self.simulate_request('/subscribe?' +
                                        'action=change_subscriptions&' +
                                        'subject_changes=%s' %
                                        json_pickle_changes)
        handler.post()
        assert (Subscription.get_by_key_name(key_name_s).frequency ==
                'immediate')
        for freq in ['daily', 'weekly', 'monthly']:
            assert not PendingAlert.get(freq, self.email, subject_name)
        assert len(sent_emails) == 1
        assert 'title__' in sent_emails[0].body
        assert 'title_bar' in sent_emails[0].body
    
    def simulate_request(self, path):
        request = webapp.Request(webob.Request.blank(path).environ)
        response = webapp.Response()
        handler = subscribe.Subscribe()
        handler.initialize(request, response, self.user)
        return handler

    def set_attr(self, subject, key, value):
        subject.set_attribute(key, value, self.time, self.user, self.nickname,
                              self.affiliation, self.comment)
