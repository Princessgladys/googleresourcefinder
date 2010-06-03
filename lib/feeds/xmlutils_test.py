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

import unittest
import xmlutils

TAG = 'testing'
ATTRIBUTES_DICT = {'attr1': 'hey', 'attr2': 'you'}
ATTRIBUTES_LIST = ['hi', 'you']
E1 = xmlutils.element(TAG, ATTRIBUTES_DICT)
E2 = xmlutils.element(TAG, ATTRIBUTES_LIST)
E3 = xmlutils.element(TAG, [E1, E2])
        
class XMLUtilsTest(unittest.TestCase):
    def test_element(self):
        assert E1.items() == ATTRIBUTES_DICT.items()
        assert E1.attrib == ATTRIBUTES_DICT
        assert E2.text == ''.join(ATTRIBUTES_LIST)
        assert E3.getchildren() == [E1, E2]