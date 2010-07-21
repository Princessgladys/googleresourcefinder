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

"""Tests for mail_alerts.py."""

import datetime
import os
import pickle
import webob

from google.appengine.api import mail
from google.appengine.ext import db, webapp

import mail_alerts
import utils
from feeds.xmlutils import Struct
from mail_alerts import get_timedelta, fetch_updates, format_plain_body
from mail_alerts import format_html_body, update_account_alert_time
from medium_test_case import MediumTestCase
from model import Account, PendingAlert, Subdomain, Subject, SubjectType
from model import Subscription
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

def fake_send_email(locale, sender, to, subject, body, email_format):
    global sent_emails
    sent_emails = []
    django.utils.translation.activate(locale)
    
    message = mail.EmailMessage()
    message.sender = sender
    message.to = to
    message.subject = subject
    if email_format == 'html':
        message.html = body
    else:
        message.body = body
    sent_emails.append(message)
    
    # add asserts for when testing the MailAlerts class
    assert locale and sender and to and subject and body
    assert '@' in (sender and to)
    assert sender.find('.org') or sender.find('.com')
    assert to.find('.org') or to.find('.com')
    return message

class MailAlertsTest(MediumTestCase):
    def setUp(self):
        MediumTestCase.setUp(self)
        self.time = datetime.datetime(2010, 06, 01)
        self.user = users.User('test@example.com')
        self.nickname = 'nickname_foo'
        self.affiliation = 'affiliation_foo'
        self.comment = 'comment_foo'
        self.description = 'test@example.com'
        self.account = Account(email=self.user.email(), actions=['*:*'],
                               locale='en', nickname=self.nickname,
                               affiliation=self.affiliation,
                               description=self.description,
                               email_format='plain')
        self.sub_immed = Subscription(key_name='haiti:example.org/123:' +
                                      self.user.email(),
                                      user_email=self.user.email(),
                                      frequency='immediate',
                                      subject_name='haiti:example.org/123')
        self.sub_daily = Subscription(key_name='haiti:example.org/456:' +
                                      self.user.email(), 
                                      user_email=self.user.email(),
                                      frequency='daily',
                                      subject_name='haiti:example.org/456')
        self.pa = PendingAlert(key_name='daily:test@example.com:haiti:' +
                               'example.org/123',
                               user_email='test@example.com',
                               timestamp=datetime.datetime(2010, 07, 01, 12,
                               30, 5), subject_name='haiti:example.org/123',
                               frequency='daily', type='hospital',
                               test_attr_foo='attr_foo',
                               test_attr_bar='attr_bar',
                               test_attr_xyz='attr_xyz')
        self.subject = Subject(key_name='haiti:example.org/123',
                               type='hospital', author=self.user)
        self.set_attr(self.subject, 'title', 'title_foo')
        self.set_attr(self.subject, 'test_attr_foo', 'attr_foo_new')
        self.set_attr(self.subject, 'test_attr_bar', 'attr_bar_new')
        self.set_attr(self.subject, 'test_attr_xyz', 'attr_xyz')
        self.subject2 = Subject(key_name='haiti:example.org/456',
                                type='hospital', author=self.user)
        self.set_attr(self.subject2, 'title', 'title_foo')
        self.set_attr(self.subject2, 'test_attr_foo', 'attr_foo_new')
        self.set_attr(self.subject2, 'test_attr_bar', 'attr_bar_new')
        self.set_attr(self.subject2, 'test_attr_xyz', 'attr_xyz')
        self.subject_type = SubjectType(key_name='haiti:hospital',
                                        attribute_names=['title',
                                        'test_attr_foo', 'test_attr_bar',
                                        'test_attr_xyz'],
                                        minimal_attribute_names=['title'])
        self.subdomain = Subdomain(key_name='haiti')
        self.send_real_email = mail_alerts.send_email
        mail_alerts.send_email = fake_send_email
        db.put([self.account, self.subject, self.subject2,
                self.sub_immed, self.sub_daily, self.subject_type,
                self.subdomain])

    def tearDown(self):
        mail_alerts.send_email = self.send_real_email
        db.delete([self.account, self.subject, self.subject2,
                   self.sub_immed, self.sub_daily, self.subject_type,
                   self.subdomain])

    def test_get_timedelta(self):
        """Confirms that get_timedelta returns the correct timedeltas."""
        assert get_timedelta('daily') == datetime.timedelta(1)
        assert get_timedelta('weekly') == datetime.timedelta(7)
        assert get_timedelta('immediate') == datetime.timedelta(0)
        
        now = datetime.datetime(2010, 01, 01, 01, 30, 30, 567)
        assert get_timedelta('monthly', now) == datetime.timedelta(31)
        
        now = datetime.datetime(2010, 02, 01, 01, 30, 30, 567)
        assert get_timedelta('monthly', now) == datetime.timedelta(28)
        
        assert get_timedelta('!') == None
    
    def test_fetch_updates(self):
        """Confirms that fetch_updates returns updated attributes in the
        appropriate format."""
        # if updates have been made, should return a list of lists. each
        # sublist should contain the changed attribute, its old/new values,
        # and the author that made the change
        assert fetch_updates(self.pa, self.subject) == [
            {'attribute': 'test_attr_bar',
             'old_value': 'attr_bar',
             'new_value': 'attr_bar_new',
             'author': 'nickname_foo'},
            {'attribute': 'test_attr_foo',
             'old_value': 'attr_foo',
             'new_value': 'attr_foo_new',
             'author': 'nickname_foo'}
        ]
        self.set_attr(self.subject, 'test_attr_bar', 'attr_bar')
        assert fetch_updates(self.pa, self.subject) == [
            {'attribute': 'test_attr_foo',
             'old_value': 'attr_foo',
             'new_value': 'attr_foo_new',
             'author': 'nickname_foo'}]
        
        # should return nothing if there are no updates
        self.set_attr(self.subject, 'test_attr_foo', 'attr_foo')
        assert not fetch_updates(self.pa, self.subject)
        
        # if either value is equal to None, should return nothing
        assert not fetch_updates('', self.subject)
        assert not fetch_updates(self.pa, '')
        assert not fetch_updates('', '')
    
    def test_format_plain_body(self):
        """Confirms that the right attributes and their changes show up in
        the text to be sent to the user."""
        values = fetch_updates(self.pa, self.subject)
        data = Struct(changed_subjects={self.subject.key().name(): (
            self.subject.get_value('title'), values)})
        plain_body = format_plain_body(data, 'en')
        
        # formatting may change but the title, attribute names, new/old values,
        # and the author should all be somewhere in the update. similarly,
        # values that have not changed should not be present
        assert 'title_foo' in plain_body.lower()
        assert ('test_attr_bar' and 'test_attr_foo') in plain_body
        assert ('attr_bar_new' and 'attr_foo_new') in plain_body
        assert ('attr_bar' and 'attr_foo') in plain_body
        assert 'nickname_foo' in plain_body
        assert not 'xyz' in plain_body

    def test_format_html_body(self):
        """Confirms that the right attributes and their changes show up in the
        html to be sent to the user."""
        values = fetch_updates(self.pa, self.subject)
        data = Struct(changed_subjects={self.subject.key().name(): (
            self.subject.get_value('title'), values)},
            time=utils.to_local_isotime(datetime.datetime.now(), clear_ms=True),
            nickname='nickname_bar', subdomain='haiti')
        html_body = format_html_body(data, 'en')

        # ditto above comment in test_format_plain_body
        assert 'title_foo' in html_body.lower()
        assert ('test_attr_bar' and 'test_attr_foo') in html_body
        assert ('attr_bar_new' and 'attr_foo_new') in html_body
        assert ('attr_bar' and 'attr_foo') in html_body
        assert 'nickname_foo' in html_body
        assert 'nickname_bar' in html_body
        assert not 'xyz' in html_body
    
    def test_send_email(self):
        """Confirms that the send_email function properly formats a message
        in the mail.EmailMessage structure while updating the django
        translation to the given locale."""
        email = mail_alerts.send_email('en',
                                       'test@example.com',
                                       'test@example.org',
                                       'subject_foo',
                                       'body_foo',
                                       'plain')
        assert django.utils.translation.get_language() == 'en'
        
        email = mail_alerts.send_email('fr',
                                       'test@example.com', 
                                       'test@example.org',
                                       'subject_foo',
                                       'body_foo',
                                       'plain')
        assert django.utils.translation.get_language() == 'fr'
    
    def test_update_account_alert_time(self):
        """Confirms that the given account's next_%freq%_alert datetimes are
        updated according to the given frequency."""
        # For initial updates, set the time if no current time is specified.
        # Once one has been specified, do not change it if the initial flag
        # is set to True.
        update_account_alert_time(self.account, 'daily', self.time, True)
        assert self.account.next_daily_alert == datetime.datetime(2010, 06, 2)
        update_account_alert_time(self.account, 'daily', datetime.datetime(
            2010, 06, 5), True)
        assert self.account.next_daily_alert == datetime.datetime(2010, 06, 2)
        
        # When initial flag is not set to true, update accordingly.
        update_account_alert_time(self.account, 'daily', self.time)
        assert self.account.next_daily_alert == datetime.datetime(2010, 06, 2)
        update_account_alert_time(self.account, 'weekly', self.time)
        assert (self.account.next_weekly_alert ==
            datetime.datetime(2010, 06, 8))
        update_account_alert_time(self.account, 'monthly', self.time)
        assert (self.account.next_monthly_alert ==
            datetime.datetime(2010, 07, 1))

        # Test monthly updates; insure that it always returns the first of
        # the next month.
        update_account_alert_time(self.account, 'monthly', datetime.datetime(
            2010, 12, 9))
        assert self.account.next_monthly_alert == datetime.datetime(
            2011, 01, 1)
        update_account_alert_time(self.account, 'monthly', datetime.datetime(
            2010, 03, 31))
        assert self.account.next_monthly_alert == datetime.datetime(
            2010, 04, 1)
        update_account_alert_time(self.account, 'monthly', datetime.datetime(
            2010, 11, 8))
        assert self.account.next_monthly_alert == datetime.datetime(
            2010, 12, 01)
    
    def test_mail_alerts(self):
        """Simulates the class being called when a subject is changed and when
        a subject is not changed."""
        global sent_emails
        sent_emails = []
        
        # test to send and immediate e-mail update with a None value
        # should render u'\u2013' instead of None
        changed_vals = [{'attribute': 'test_attr_foo',
                         'old_value': None,
                         'new_value': u'attr_new\xef',
                         'author': 'author_foo'}]
        unchanged_vals = {'test_attr_bar': 'attr_bar'}
        json_pickle_attrs_c = simplejson.dumps(unicode(
            pickle.dumps(changed_vals), 'latin-1'))
        json_pickle_attrs_uc = simplejson.dumps(unicode(
            pickle.dumps(unchanged_vals), 'latin-1'))
        path = '/mail_alerts?action=subject_changed&' + \
               'subject_name=haiti:example.org/123&' + \
               'changed_data=' + json_pickle_attrs_c + '&' + \
               'unchanged_data=' + json_pickle_attrs_uc
        handler = self.simulate_request(path)
        handler.post()
        assert len(sent_emails) == 1
        assert u'\u2013' in sent_emails[0].body
        assert u'\xef' in sent_emails[0].body
        assert 'attr_new' in sent_emails[0].body
        assert sent_emails[0].body.count(u'\u2013') == 1
        sent_emails = []

        # test to send and immediate e-mail update with a None value
        # should render u'\u2013' instead of None
        changed_vals = [{'attribute': 'test_attr_foo',
                         'old_value': 'attr_old',
                         'new_value': None,
                         'author': 'author_foo'}]
        json_pickle_attrs_c = simplejson.dumps(pickle.dumps(changed_vals))
        path = '/mail_alerts?action=subject_changed&' + \
               'subject_name=haiti:example.org/123&' + \
               'changed_data=' + json_pickle_attrs_c + '&' + \
               'unchanged_data=' + json_pickle_attrs_uc
        handler = self.simulate_request(path)
        handler.post()
        assert len(sent_emails) == 1
        assert u'\u2013' in sent_emails[0].body
        assert 'attr_old' in sent_emails[0].body
        assert sent_emails[0].body.count(u'\u2013') == 1
        sent_emails = []

        # test to send an immediate e-mail update
        # should not raise an error if the e-mail was sent
        changed_vals = [{'attribute': 'test_attr_foo',
                         'old_value': 'attr_old',
                         'new_value': 'attr_new',
                         'author': 'author_foo'}]
        json_pickle_attrs_c = simplejson.dumps(pickle.dumps(changed_vals))
        path = '/mail_alerts?action=subject_changed&' + \
               'subject_name=haiti:example.org/123&' + \
               'changed_data=' + json_pickle_attrs_c + '&' + \
               'unchanged_data=' + json_pickle_attrs_uc
        handler = self.simulate_request(path)
        handler.post()
        assert len(sent_emails) == 1
        assert 'title_foo' in sent_emails[0].body.lower()
        assert 'test_attr_foo' in sent_emails[0].body
        assert 'attr_old' in sent_emails[0].body
        assert 'attr_new' in sent_emails[0].body
        assert 'author_foo' in sent_emails[0].body
        sent_emails = []
       
        # test to make sure a pending alert is created when a subject is
        # changed for a non-immediate subscription
        path = '/mail_alerts?action=subject_changed&' + \
               'subject_name=haiti:example.org/456&' + \
               'changed_data=' + json_pickle_attrs_c + '&' + \
               'unchanged_data=' + json_pickle_attrs_uc
        handler = self.simulate_request(path)
        handler.post()
        assert PendingAlert.get('daily', 'test@example.com',
                                'haiti:example.org/456')
        
        # now send the alert
        handler = self.simulate_request('/mail_alerts')
        handler.post()
        assert not PendingAlert.get('daily', 'test@example.com',
                                    'haiti:example.org/456')
        assert len(sent_emails) == 1
        assert 'title_foo' in sent_emails[0].body.lower()
        assert 'test_attr_bar' in sent_emails[0].body
        assert 'test_attr_foo' in sent_emails[0].body
        assert 'attr_bar_new' in sent_emails[0].body
        assert 'attr_foo_new' in sent_emails[0].body
        assert 'attr_bar' in sent_emails[0].body
        assert 'attr_foo' in sent_emails[0].body
        assert 'nickname_foo' in sent_emails[0].body

    def test_html_mail_alerts(self):
        """Simulates the class being called when a subject is changed with HTML
        e-mails being preferred."""
        self.account.email_format = 'html'
        db.put(self.account)

        global sent_emails
        sent_emails = []

        changed_vals = [{'attribute': 'test_attr_foo',
                         'old_value': None,
                         'new_value': u'attr_new\xef',
                         'author': 'author_foo'}]
        unchanged_vals = {'test_attr_bar': 'attr_bar'}
        json_pickle_attrs_c = simplejson.dumps(unicode(
            pickle.dumps(changed_vals), 'latin-1'))
        json_pickle_attrs_uc = simplejson.dumps(unicode(
            pickle.dumps(unchanged_vals), 'latin-1'))
        path = '/mail_alerts?action=subject_changed&' + \
               'subject_name=haiti:example.org/123&' + \
               'changed_data=' + json_pickle_attrs_c + '&' + \
               'unchanged_data=' + json_pickle_attrs_uc
        handler = self.simulate_request(path)
        handler.post()
        assert len(sent_emails) == 1
        assert sent_emails[0].html
        assert 'title_foo' in sent_emails[0].html.lower()
        assert 'test_attr_foo' in sent_emails[0].html
        assert 'test_attr_bar' not in sent_emails[0].html

    def set_attr(self, subject, key, value):
        subject.set_attribute(key, value, self.time, self.user, self.nickname,
                              self.affiliation, self.comment)
    
    def simulate_request(self, path):
        request = webapp.Request(webob.Request.blank(path).environ)
        response = webapp.Response()
        handler = mail_alerts.MailAlerts()
        handler.initialize(request, response, self.user)
        return handler
