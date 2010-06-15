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

"""Tests for utils.py."""

import datetime
import os
import webob
import sets

from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp

import access
import cache
import config
import medium_test_case
import utils

import django.utils.translation

from feeds.errors import ErrorMessage, Redirect
from medium_test_case import MediumTestCase
from model import Account, Message

class HandlerTest(MediumTestCase):
    def setUp(self):
        MediumTestCase.setUp(self)
        self.request = webapp.Request(webob.Request.blank(
            '/?embed=yes&action=view&rad=1.23').environ)
        self.response = webapp.Response()
        self.handler = utils.Handler()
        self.handler.initialize(self.request, self.response)

    def test_initialize(self):
        assert self.handler.params.rad == 1.23
        assert self.handler.params.embed == 'yes'
        assert self.handler.params.action == 'view'

    def test_require_action_permitted(self):
        """Confirms require_action_permitted is working correctly"""
        try:
            self.handler.require_action_permitted('grant')
            assert False # Should have failed
        except utils.Redirect, r:
            # expected
            pass

        self.handler.account = Account(email='foo@example.com',
                                       description='Test',
                                       actions = ['view', 'edit'])
        try:
            self.handler.require_action_permitted('grant')
            assert False # Should have failed
        except utils.ErrorMessage, e:
            # expected
            pass

        self.handler.require_action_permitted('view')

    def test_require_logged_in_user(self):
        """Confirms require_logged_in_user is working correctly"""
        try:
            self.handler.require_logged_in_user()
            assert False # Should have failed
        except utils.Redirect, r:
            # expected
            pass

        self.handler.user = users.User(email='foo@example.com')
        self.handler.require_logged_in_user()

    def test_select_locale(self):
        """Confirm select_locale works as expected"""
        # English by default
        self.handler.params.lang = ''
        self.handler.select_locale()
        assert self.handler.params.lang == 'en'
        assert self.handler.params.maps_lang == 'en'
        assert self.response.headers['Content-Language'] == 'en'

        # test cookie
        self.handler.params.lang = ''
        self.handler.request.cookies['django_language'] = 'fr'
        self.handler.select_locale()
        assert self.handler.params.lang == 'fr'
        assert self.handler.params.maps_lang == 'fr'

        # if self.params.lang is already set, don't change it.
        self.handler.params.lang = 'ht'
        self.handler.select_locale()
        assert self.handler.params.lang == 'ht'
        assert self.handler.params.maps_lang == 'fr'

        # test alternate language code
        alt_lang = config.ALTERNATE_LANG_CODES.keys()[0]
        self.handler.params.lang = alt_lang
        self.handler.select_locale()
        assert self.handler.params.lang == config.ALTERNATE_LANG_CODES[alt_lang]

        # test maps_lang and django language select
        self.handler.params.lang = 'es-419'
        self.handler.select_locale()
        assert self.handler.params.lang == 'es-419'
        assert django.utils.translation.get_language() == 'es-419'


class UtilsTest(MediumTestCase):
    def setUp(self):
        MediumTestCase.setUp(self)
        for i in range(0, 10):
            message = Message(namespace='attribute_value', name='name_%d' % i)
            setattr(message, 'en', 'en_%d' %i)
            setattr(message, 'fr', 'fr_%d' %i)
            setattr(message, 'es_419', 'es_419_%d' %i)
            message.put()

        self.messages = list(m for m in Message.all(keys_only=True))
        cache.MESSAGES.flush()

    def tearDown(self):
        django.utils.translation.activate('en')
        cache.MESSAGES.flush()
        messages = self.messages
        while messages:
            batch, messages = messages[:200], messages[200:]
            db.delete(batch)

    def test_fetch_all(self):
        """Confirm fetch_all works as expected"""
        query = Message.all()
        results = utils.fetch_all(query)
        assert len(results) == 10
        self.assert_same_elements(self.messages, [r.key() for r in results])

        # Make sure it works twice in a row
        results = utils.fetch_all(query)
        assert len(results) == 10

    def test_validate_yes(self):
        """Confirm validate_yes works as expected"""
        assert utils.validate_yes('yes') == 'yes'
        assert utils.validate_yes('YeS') == 'yes'
        assert utils.validate_yes('no') == ''
        assert utils.validate_yes('foo') == ''
        assert utils.validate_yes('') == ''

    def test_validate_action(self):
        """Confirm validate_action works as expected"""
        for action in access.ACTIONS:
          assert utils.validate_action(action)
        assert not utils.validate_action('FOO')

    def test_validate_float(self):
        """Confirm validate_float works as expected"""
        assert utils.validate_float('1.25') == 1.25
        assert utils.validate_float('100') == 100
        assert utils.validate_float('abc') == None

    def test_get_message(self):
        """Confirm get_message works as expected"""
        django.utils.translation.activate('en')
        assert utils.get_message('attribute_value', 'name_1') == 'en_1'
        assert utils.get_message('attribute_value', 'unknown') == 'unknown'
        assert utils.get_message('attribute_value', '') == ''
        django.utils.translation.activate('fr')
        assert utils.get_message('attribute_value', 'name_1') == 'fr_1'
        django.utils.translation.activate('es_419')
        assert utils.get_message('attribute_value', 'name_1') == 'es_419_1'

    def test_make_name(self):
        """Confirm make_name works as expected"""
        assert utils.make_name(u'\u00C7  foo--bar') == 'c_foo_bar'
        assert utils.make_name(u'foo') == 'foo'

    def test_export(self):
        """Confirm export works as expected"""
        assert utils.export(Message) == '\n'.join(
            ['''Message(namespace=u'attribute_value', name=u'name_%d').put()'''
             % i for i in range(0, 10)]) + '\n'

    def test_to_utf8(self):
        """Confirm to_utf8 works as expected"""
        assert utils.to_utf8('') == ''
        assert utils.to_utf8('foo') == 'foo'
        assert utils.to_utf8(u'\u2012') == '\xe2\x80\x92'

    def test_urlencode(self):
        """Confirm urlencode works as expected"""
        params = {'q':u'\u2012', 'r':'http://foo 123'}
        assert utils.urlencode(params) == 'q=%E2%80%92&r=http%3A%2F%2Ffoo+123'

    def test_set_url_param(self):
        """Confirm set_url_param works as expected"""
        assert utils.set_url_param('/search', 'a', '1 2') == '/search?a=1+2'
        assert utils.set_url_param('/search?a=1', 'a', '2') == '/search?a=2'
        assert (utils.set_url_param(
            '/search?a=1&b=2', 'c', '3') == '/search?a=1&b=2&c=3')
        assert (utils.set_url_param(
            'http://foo.com/search?a=1', 'b', u'\u2012') ==
                'http://foo.com/search?a=1&b=%E2%80%92')

    def test_to_posixtime_to_datetime_to_isotime(self):
        """Confirm to_posixtime and to_datetime work as expected"""
        dt = datetime.datetime(2010, 6, 14)
        pt = utils.to_posixtime(dt)
        assert utils.to_datetime(pt) == dt
        assert utils.to_posixtime(dt) == pt

        it = utils.to_isotime(dt)
        it2 = utils.to_isotime(pt)
        assert it == it2 == '2010-06-14T00:00:00Z'

    def test_to_local_isotime(self):
        """Confirm to_local_isotime works as expected"""
        dt = datetime.datetime(2010, 6, 14, 9, 15, 12)
        assert utils.to_local_isotime(dt) == '2010-06-14 04:15:12 -05:00'

    def test_to_unicode(self):
        """Confirm to_unicode works as expected"""
        assert utils.to_unicode(None) == ''
        assert utils.to_unicode('') == ''
        assert utils.to_unicode('foo') == 'foo'
        assert utils.to_unicode('\xe2\x80\x92') == u'\u2012'
