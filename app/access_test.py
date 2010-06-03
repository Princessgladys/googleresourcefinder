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

import access
import datetime
import unittest
        
AUTH = Struct()
AUTH.timestamp = datetime.datetime.now()
AUTH.description = 'description'
AUTH.email = 'test@example.com'
AUTH.user_id = 'test'
AUTH.nickname = 'test'
AUTH.affiliation = 'test'
AUTH.token = 'test'
AUTH.actions = ['view', 'edit']
AUTH.requested_actions = ['advanced_edit']
        
class AccessTest(unittest.TestCase):
    def test_check_action_permitted(self):
        for action in ACTIONS:
            if action in AUTH.actions:
                assert access.check_action_permitted(AUTH, action) == True
            else:
                assert access.check_action_permitted(AUTH, action) == False
