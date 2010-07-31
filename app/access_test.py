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

import datetime
import unittest

from google.appengine.api import users

import test_config  # must be imported first in unit tests
import access
from medium_test_case import MediumTestCase
from model import Account
from utils import Struct, db
        
class AccessTest(MediumTestCase):
    def setUp(self):
        MediumTestCase.setUp(self)
        self.user = users.User(email='test@example.com')
        self.user2 = users.User(email='test@example.com')
        self.no_token_req = Struct(access_token='')
        self.foo_token_req = Struct(access_token='token_foo')
        self.bar_token_req = Struct(access_token='token_bar')
        self.account = Account(timestamp=datetime.datetime.now(),
                               description='description',
                               email='test@example.com', user_id='test',
                               nickname='test', affiliation='test',
                               actions=['*:view', 'foo:add', 'bar:*'],
                               requested_actions=['xyz:remove'],
                               token='token_foo')

        db.put(self.account)
    
    def tearDown(self):
        for account in Account.all():
            db.delete(account)
    
    def test_check_request(self):
        self.run_check_request_asserts(access.check_request)
        
        # if an incorrect token is supplied, should return as None even if
        # there is a user also supplied
        assert access.check_request(self.bar_token_req, self.user) == None
    
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
    
    def test_check_and_log(self):
        # should produce same results as access.check_request() in 
        # most situations
        self.run_check_request_asserts(access.check_and_log)
        
        # if there is an invalid token requested, but still a user, it should
        # create a new account and return that instead
        assert (access.check_and_log(self.no_token_req, self.user).email ==
            self.user.email())
        assert (access.check_and_log(self.bar_token_req, self.user).email ==
            self.user.email())
    
    def run_check_request_asserts(self, check_request_function):
        # with or without a token on the request, it should return the account
        # with the same e-mail as the user
        assert (check_request_function(self.foo_token_req, self.user).email ==
            self.account.email)
        assert (check_request_function(self.no_token_req, self.user).email ==
            self.account.email)
        
        # should return appropriate account given a token, but no user
        assert (check_request_function(self.foo_token_req, '').email ==
            self.account.email)
            
        # if no token is supplied, or an incorrect token is supplied,
        # without a correct user, this should return None
        assert check_request_function(self.no_token_req, '') == None
        assert check_request_function(self.bar_token_req, '') == None

        # if a token is supplied that differs from the given user, it should
        # still return the account that matches the token
        assert (check_request_function(self.foo_token_req, self.user2).email ==
            self.account.email)
