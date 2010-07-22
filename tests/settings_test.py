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

"""Server tests for settings."""

__author__ = 'pfritzsche@google.com (Phil Fritzsche)'

import datetime
import logging

import scrape

from model import Account, db, Subject, Subscription
from selenium_test_case import Regex, SeleniumTestCase

class SettingsTest(SeleniumTestCase):
    def setUp(self):
        SeleniumTestCase.setUp(self)
        self.email = 'test@example.com'
        self.put_subject('haiti', 'example.org/123', title='title_foo')
        self.put_subject('haiti', 'example.org/456', title='title_bar')
        self.put_account(default_frequency='immediate',
                         locale='en',
                         email_format='html',
                         actions=['*:*'])
        self.s = scrape.Session()

        self.subscription1 = Subscription(
            key_name='%s:%s' % ('haiti:example.org/123',
                                self.email),
            subject_name='haiti:example.org/123',
            frequency='daily',
            user_email=self.email)
        self.subscription2 = Subscription(
            key_name='%s:%s' % ('haiti:example.org/456',
                                self.email),
            subject_name='haiti:example.org/456',
            frequency='monthly',
            user_email=self.email)

        db.put([self.subscription1, self.subscription2])

    def tearDown(self):
        self.delete_subject('haiti', 'example.org/123')
        self.delete_subject('haiti', 'example.org/456')
        self.delete_account()
        for s in Subscription.all():
            db.delete(s)
        SeleniumTestCase.tearDown(self)

    def test_header(self):
        """Confirms that the print and settings links are not present in the
        header."""
        self.login_to_settings_page()
        self.assert_text(Regex('Resource Finder.*'), '//title')
        self.assert_text(self.email, '//div[@class="user"]//strong')
        self.assert_text(Regex('.*Home.*'), '//div[@class="user"]')
        self.assert_no_text(Regex('.*Settings.*'), '//div[@class="user"]')
        self.assert_no_text(Regex('.*Print.*'), '//div[@class="user"]')

    def test_options(self):
        """Confirms that the e-mail format, language, and account default
        frequency options rendered properly."""
        # make sure all three buttons load properly
        self.login_to_settings_page()
        assert (['immediate'] ==
                self.get_selected_values('//*[@name="default-frequency"]'))
        assert self.is_checked('//*[@name="email-type"][@value="html"]')

        # change account and reload; make sure change was saved
        account = Account.all().filter('email =', self.email).get()
        account.default_frequency = 'monthly'
        db.put(account)
        self.open_path(self.get_location())
        self.wait_for_load()
        assert (['monthly'] ==
                self.get_selected_values('//*[@name="default-frequency"]'))
 
    def test_subjects(self):
        """Confirms that the facilities list loaded properly."""
        # make sure all subjects are present
        self.login_to_settings_page()
        self.assert_text_present('title_foo')
        self.assert_text_present('title_bar')
        assert self.is_checked(
            '//*[@name="haiti:example.org/123_freq"][@value="daily"]')
        assert self.is_checked(
            '//*[@name="haiti:example.org/456_freq"][@value="monthly"]')
        
        # make sure that check all and set checked to default work as expected
        self.click('//*[@name="subjects-check-all"]')
        self.click('//*[@id="button-set-to-default"]')

        assert self.is_checked(
            '//*[@name="haiti:example.org/123_freq"][@value="immediate"]')
        assert self.is_checked(
            '//*[@name="haiti:example.org/456_freq"][@value="immediate"]')

        # make sure that unsubscribe from checked works; remove only one subject
        self.click(
            '//*[@name="subject-checkboxes"][@value="haiti:example.org/123"]')
        self.click('//*[@id="button-unsubscribe-checked"]')
        self.wait_for_load()
        self.assert_text_present('title_foo')
        self.assert_text_not_present('title_bar')

        # make sure that changing frequency by radio button changes datastore
        # without requiring clicking any save buttons
        self.click('//*[@name="haiti:example.org/123_freq"][@value="monthly"]')
        # there should be only one subscription left; no need to filter
        assert Subscription.all().get().frequency == 'monthly'

        self.click('//*[@name="subjects-check-all"]')
        self.click('//*[@id="button-unsubscribe-checked"]')
        self.wait_for_load()
        self.assert_text_not_present('title_bar')
        self.assert_text_present('No facilities to display.')

    def login_to_settings_page(self):
        self.login('/settings?subdomain=haiti')
        self.assert_text(Regex('Settings.*'), '//td[@class="settings-title"]')
