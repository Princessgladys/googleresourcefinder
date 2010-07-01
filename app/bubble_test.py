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

"""Tests for bubble.py."""

from google.appengine.api import users

from bubble import HospitalValueInfoExtractor, ValueInfoExtractor
from utils import db, HIDDEN_ATTRIBUTE_NAMES

import django.utils.translation

import bubble
import datetime
import logging
import model
import os
import unittest
import utils

SAN_FRANCISCO = {'lat': 40.7142, 'lon': -74.0064}
        
def fake_get_message(ns, n):
    message = model.Message(namespace = ns, name = n)
    if ns == 'attribute_value' and n == 'fake_to_localize':
        message.en = 'fake_localized'
    else:
        message.en = 'foo'
    django_locale = 'en'
    
    return message and getattr(message, django_locale) or n

class BubbleTest(unittest.TestCase):
    def setUp(self):
        self.real_auth_domain = os.environ.get('AUTH_DOMAIN', '')
        os.environ['AUTH_DOMAIN'] = 'test'
        self.real_get_message = bubble.get_message
        bubble.get_message = fake_get_message   

    def tearDown(self):
        bubble.get_message = self.real_get_message
        os.environ['AUTH_DOMAIN'] = self.real_auth_domain

    def test_format(self):
        time = datetime.datetime(2010, 6, 2, 13, 21, 13, 97435)
        pt = utils.db.GeoPt(SAN_FRANCISCO['lat'], SAN_FRANCISCO['lon'])
        assert bubble.format(u'123\u26CC') == '123\xe2\x9b\x8c'
        assert bubble.format('12\n3') == bubble.format('12 3')
        assert bubble.format('123') == '123'
        assert bubble.format(['1', '2', '3']) == bubble.format('1, 2, 3') \
            == '1, 2, 3'
        assert bubble.format(time) == '2010-06-02 08:21:13 -05:00'
        assert bubble.format(pt) == '40.7142\xc2\xb0 N, 74.0064\xc2\xb0 W'
        assert bubble.format(True) == bubble.format(_('Yes')) == _('Yes')
        assert bubble.format(False) == bubble.format(_('No')) == _('No')
        assert bubble.format({'hey!' : 1}) == {'hey!' : 1}
        assert bubble.format(None) == u'\u2013'.encode('utf-8')
        assert bubble.format('') == u'\u2013'.encode('utf-8')
        assert bubble.format([]) == u'\u2013'.encode('utf-8')
        assert bubble.format({}) == u'\u2013'.encode('utf-8')
        assert bubble.format(13) == 13
        assert bubble.format(0) == 0
        assert bubble.format('fake_to_localize', True) == 'fake_localized'
        assert bubble.format(['fake_to_localize'], True == ['fake_localized'])

    def test_value_info_extractor(self):
        s = model.Subject(key_name='haiti:example.org/123', type='hospital')
        s.set_attribute('title', 'title_foo', datetime.datetime.now(),
                        users.User('test@example.com'),
                        'nickname_foo', 'affiliation_foo', 'comment_foo')
        s.set_attribute('attribute_value', 'fake_to_localize',
                        datetime.datetime.now(),
                        users.User('test@example.com'),
                        'nickname_foo', 'affiliation_foo', 'comment_foo')
                    
        vai = ValueInfoExtractor(['title'], ['attribute_value'])
        (special, general, details) = vai.extract(s, ['title'])
        
        assert special['title'].raw == 'title_foo'
        assert general == []
        assert details[0].raw == 'title_foo'
        
        (special, general, details) = vai.extract(s, ['attribute_value'])

        assert general[0].raw == 'fake_to_localize'
        assert general[0].value == 'fake_localized'
        assert general[0].label == 'foo'

    def test_hospital_value_info_extractor(self):
        user = users.User('test@example.com')
        now = datetime.datetime(2010, 6, 11, 14, 26, 52, 906773)
        nickname = 'nickname_foo'
        affiliation = 'affiliation_foo'
        comment = 'comment_foo'
        
        s = model.Subject(key_name='haiti:example.org/123', type='hospital')
        s.set_attribute('title', 'title_foo', now, user, nickname, affiliation,
                        comment)
        s.set_attribute(HIDDEN_ATTRIBUTE_NAMES[0], 'hidden_value_foo', now,
                        user, nickname, affiliation, comment)
        s.set_attribute('organization_name', 'value_foo', now, user, nickname,
                        affiliation, comment)

        attrs = ['title', 'organization_name', HIDDEN_ATTRIBUTE_NAMES[0]]
        vai = HospitalValueInfoExtractor()
        (special, general, details) = vai.extract(s, attrs)
        
        assert special['title'].date == '2010-06-11 09:26:52 -05:00'
        assert special['title'].raw == 'title_foo'
        assert HIDDEN_ATTRIBUTE_NAMES[0] not in special
        assert sorted(special) == sorted(vai.special_attribute_names)
        assert len(general) == 1
        assert len(details) == 2
        assert general[0].value == 'value_foo'
        for detail in details:
            assert detail.value == 'title_foo' or detail.value == 'value_foo'
            assert detail.value != 'hidden_value_foo'
