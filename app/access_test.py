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

"""Tests for access.py."""

from access import ACTIONS
from feeds.xmlutils import Struct
from model import Account

import access
import datetime
import unittest
        
class AccessTest(unittest.TestCase):
    def setUp(self):
        self.account = Account(timestamp=datetime.datetime.now(),
                               description='description',
                               email='test@example.com', user_id='test',
                               nickname='test', affiliation='test',
                               actions=['*:view', 'foo:add', 'bar:*'],
                               requested_actions=['xyz:remove'])
                       
    def test_action_permitted(self):
        # 'foo:add' should apply only to subdomain 'foo' and verb 'add'
        assert access.check_action_permitted(self.account, 'foo', 'add')
        assert not access.check_action_permitted(self.account, 'foo', 'edit')
        assert not access.check_action_permitted(self.account, 'foo', 'remove')
        assert not access.check_action_permitted(self.account, 'xyz', 'add')

        # 'bar:*' should work for any verb
        assert access.check_action_permitted(self.account, 'bar', 'add')
        assert access.check_action_permitted(self.account, 'bar', 'edit')
        assert access.check_action_permitted(self.account, 'bar', 'remove')
        assert not access.check_action_permitted(self.account, 'xyz', 'remove')

        # '*:view' should work for any subdomain
        assert access.check_action_permitted(self.account, 'foo', 'view')
        assert access.check_action_permitted(self.account, 'bar', 'view')
        assert access.check_action_permitted(self.account, 'xyz', 'view')
        assert not access.check_action_permitted(self.account, 'xyz', 'grant')
