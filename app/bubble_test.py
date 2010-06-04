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

from bubble import ValueInfoExtractor
from utils import db

import django.utils.translation

import bubble
import datetime
import model
import os
import unittest
import utils

SAN_FRANCISCO = {'lat': 40.7142, 'lon': -74.0064}
        
def fake_get_message(ns, n):
    message = model.Message(namespace = ns, name = n)
    message.en = 'foo'
    django_locale = 'en'
    
    return message and getattr(message, django_locale) or n

class BubbleTest(unittest.TestCase):
    def setUp(self):
        self.val = os.environ.get('AUTH_DOMAIN')
        os.environ['AUTH_DOMAIN'] = 'test'
        self.real_get_message = bubble.get_message
        bubble.get_message = fake_get_message   

    def tearDown(self):
        bubble.get_message = self.real_get_message
        if self.val:
            os.environ['AUTH_DOMAIN'] = self.val
        else:
            os.environ['AUTH_DOMAIN'] = ''

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
        assert bubble.format('') == ''
        assert bubble.format(13) == 13
        assert bubble.format(0) == 0

    def test_value_info_extractor(self):
        f = model.Facility(key_name='example.org/123', type='hospital')
        f.set_attribute('title', 'title_foo', datetime.datetime.now(),
                        users.User('test@example.com'),
                        'nickname_foo', 'affiliation_foo', 'comment_foo')
                    
        vai = ValueInfoExtractor(['title'], ['title'])
        (special, general, details) = vai.extract(f, ['title'])
        
        assert special.get('title').raw == 'title_foo'
        assert general == []
        assert details[0].raw == 'title_foo'