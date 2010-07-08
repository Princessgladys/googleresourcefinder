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

from nose.tools import assert_raises

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
        Account(key_name='default', actions=['haiti:view']).put()
        Account(email='foo@example.com', actions=['*:edit']).put()

    def simulate_request(self, path, user_email=None, **cookies):
        request = webapp.Request(webob.Request.blank(path).environ)
        response = webapp.Response()
        for name, value in cookies.items():
            request.cookies[name] = value
        user = user_email and users.User(email=user_email)
        handler = utils.Handler()
        handler.initialize(request, response, user)
        return handler

    def tearDown(self):
        db.delete(Account.get_by_key_name('default'))
        db.delete(Account.all().filter('email =', 'foo@example.com').get())
        MediumTestCase.tearDown(self)

    def test_auto_params(self):
        handler = self.simulate_request('/?rad=1.23&embed=YES&action=view')
        assert handler.params.rad == 1.23
        assert handler.params.embed == 'yes'
        assert handler.params.action == 'view'

    def test_require_action_permitted(self):
        """Confirms require_action_permitted is working correctly."""
        # User not logged in
        handler = self.simulate_request('/?subdomain=haiti')
        # 'grant' is not allowed
        assert_raises(utils.Redirect, handler.require_action_permitted, 'grant')
        # 'edit' is not allowed
        assert_raises(utils.Redirect, handler.require_action_permitted, 'edit')
        # 'view' should be allowed (due to the default permissions)
        handler.require_action_permitted('view')

        # default 'view' permission should only apply to 'haiti' subdomain
        handler = self.simulate_request('/?subdomain=xyz')
        assert_raises(utils.Redirect, handler.require_action_permitted, 'view')

        # User is logged in, but has no Account entity
        handler = self.simulate_request('/?subdomain=haiti', 'bogus@bogus.com')
        # 'grant' is not allowed
        assert_raises(
            utils.ErrorMessage, handler.require_action_permitted, 'grant')
        # 'edit' is not allowed
        assert_raises(
            utils.ErrorMessage, handler.require_action_permitted, 'edit')
        # 'view' should be allowed (due to the default permissions)
        handler.require_action_permitted('view')

        # default 'view' permission should only apply to 'haiti' subdomain
        handler = self.simulate_request('/?subdomain=xyz', 'bogus@bogus.com')
        assert_raises(
            utils.ErrorMessage, handler.require_action_permitted, 'view')

        # User is logged in, and has an Account entity
        handler = self.simulate_request('/?subdomain=haiti', 'foo@example.com')
        # 'grant' is still not allowed
        assert_raises(
            utils.ErrorMessage, handler.require_action_permitted, 'grant')
        # 'edit' should be allowed
        handler.require_action_permitted('edit')
        # 'view' should still be allowed
        handler.require_action_permitted('view')

    def test_require_logged_in_user(self):
        """Confirms require_logged_in_user is working correctly"""
        # User not logged in
        handler = self.simulate_request('/?subdomain=haiti')
        assert_raises(utils.Redirect, handler.require_logged_in_user)

        # User is logged in
        handler = self.simulate_request('/?subdomain=haiti', 'foo@example.com')
        handler.require_logged_in_user()

    def test_select_lang(self):
        """Confirm select_lang works as expected"""
        # Default language should be English.
        handler = self.simulate_request('/')
        assert handler.params.lang == 'en'
        assert handler.params.maps_lang == 'en'
        assert handler.response.headers['Content-Language'] == 'en'
        assert django.utils.translation.get_language() == 'en'
        assert utils.get_lang() == 'en'
        assert utils.get_locale() == 'en'

        # Test the django_language cookie.
        handler = self.simulate_request('/', django_language='fr')
        assert handler.params.lang == 'fr'
        assert handler.params.maps_lang == 'fr'
        assert django.utils.translation.get_language() == 'fr'
        assert utils.get_lang() == 'fr'
        assert utils.get_locale() == 'fr'

        # Test the 'lang' query parameter.
        handler = self.simulate_request('/?lang=ht')
        assert handler.params.lang == 'ht'
        assert handler.params.maps_lang == 'fr'  # fallback
        assert django.utils.translation.get_language() == 'ht'
        assert utils.get_lang() == 'ht'
        assert utils.get_locale() == 'ht'

        # Test an alternate language code.
        handler = self.simulate_request('/?lang=es')
        assert handler.params.lang == 'es-419'
        assert handler.params.maps_lang == 'es-419'
        assert django.utils.translation.get_language() == 'es-419'
        assert utils.get_lang() == 'es-419'
        assert utils.get_locale() == 'es_419'

        # Force all the language settings to change.
        handler = self.simulate_request('/?lang=fr')
        assert handler.params.lang == 'fr'
        assert handler.params.maps_lang == 'fr'
        assert django.utils.translation.get_language() == 'fr'
        assert utils.get_lang() == 'fr'
        assert utils.get_locale() == 'fr'

        # Test a language with a subcode.
        handler = self.simulate_request('/?lang=es-419')
        assert handler.params.lang == 'es-419'
        assert handler.params.maps_lang == 'es-419'
        assert django.utils.translation.get_language() == 'es-419'
        assert utils.get_lang() == 'es-419'
        assert utils.get_locale() == 'es_419'


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
        self.assert_contents_any_order(
            self.messages, [r.key() for r in results])

        # Make sure it works twice in a row
        results = utils.fetch_all(query)
        assert len(results) == 10

    def test_validate_yes(self):
        """Confirm validate_yes works as expected"""
        assert utils.validate_yes('yes') == 'yes'
        assert utils.validate_yes('YeS') == 'yes'
        assert utils.validate_yes('y') == 'yes'
        assert utils.validate_yes('Y') == 'yes'
        assert utils.validate_yes('no') == ''
        assert utils.validate_yes('NO') == ''
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

        dt = datetime.datetime(2010, 6, 14, 9, 15, 12, 3867)
        assert (utils.to_local_isotime(dt) ==
            '2010-06-14 04:15:12.003867 -05:00')
        assert (utils.to_local_isotime(dt, clear_ms=True) == 
            '2010-06-14 04:15:12 -05:00')

    def test_to_unicode(self):
        """Confirm to_unicode works as expected"""
        assert utils.to_unicode(None) == ''
        assert utils.to_unicode('') == ''
        assert utils.to_unicode('foo') == 'foo'
        assert utils.to_unicode('\xe2\x80\x92') == u'\u2012'

    def test_value_or_dash(self):
        """Confirm that value_or_dash works as expected"""
        assert utils.value_or_dash(3) == 3
        assert utils.value_or_dash('3') == '3'
        assert utils.value_or_dash(0) == 0
        assert utils.value_or_dash(None) == u'\u2013'
        assert utils.value_or_dash([]) == u'\u2013'
