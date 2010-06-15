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

from google.appengine.api import users

from access import ACTIONS
from feeds.xmlutils import Struct
from medium_test_case import MediumTestCase
from model import Account
from utils import db

import access
import datetime
import unittest
        
class AccessTest(MediumTestCase):
    def setUp(self):
        MediumTestCase.setUp(self)
        self.user = users.User(email='test@example.com')
        self.request = Struct(access_token='')
        self.request2 = Struct(access_token='token_foo')
        self.request3 = Struct(access_token='token_bar')
        self.account = Account(timestamp=datetime.datetime.now(),
                               description='description',
                               email='test@example.com', user_id='id_foo',
                               nickname='test', affiliation='test',
                               token='token_foo',
                               actions=[ACTIONS[0], ACTIONS[1]],
                               requested_actions=[ACTIONS[2]])

        db.put(self.account)
        
    def tearDown(self):
        for account in Account.all():
            db.delete(account)
    
    def test_check_request(self):
        assert (access.check_request(self.request2, self.user).email ==
            self.account.email)
        assert (access.check_request(self.request, self.user).email ==
            self.account.email)
        assert (access.check_request(self.request2, '').email ==
            self.account.email)
        assert access.check_request(self.request, '') == None
        assert access.check_request(self.request3, '') == None
                       
    def test_action_permitted(self):
        for action in ACTIONS:
            if action in self.account.actions:
                assert access.check_action_permitted(self.account, action) == True
            else:
                assert (access.check_action_permitted(self.account, action) ==
                    False)

    def test_check_and_log(self):
        assert (access.check_and_log(self.request2, self.user).email ==
            self.account.email)
        assert (access.check_and_log(self.request, self.user).email ==
            self.account.email)
        assert (access.check_and_log(self.request2, '').email ==
            self.account.email)
        assert access.check_and_log(self.request, '') == None
        assert (access.check_and_log(self.request, self.user).email ==
            self.user.email())
        assert (access.check_and_log(self.request3, self.user).email ==
            self.user.email())
