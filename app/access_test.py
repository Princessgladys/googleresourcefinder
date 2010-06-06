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
        self.auth = Account(timestamp=datetime.datetime.now(),
                            description='description',
                            email='test@example.com', user_id='test',
                            nickname='test', affiliation='test', token='test',
                            actions=[ACTIONS[0], ACTIONS[1]],
                            requested_actions=[ACTIONS[2]])
                       
    def test_check_user_role(self):
        for action in ACTIONS:
            if action in self.auth.actions:
                assert access.check_action_permitted(self.auth, action) == True
            else:
                assert access.check_action_permitted(self.auth, action) == False
