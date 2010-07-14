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
        
class XMLUtilsTest(unittest.TestCase):
    def setUp(self):
        self.tag = 'testing'
        self.attributes_dict = {'attr1': 'hey', 'attr2': 'you'}
        self.attributes_list = ['hi', 'you']
        self.e1 = xmlutils.element(self.tag, self.attributes_dict)
        self.e2 = xmlutils.element(self.tag, self.attributes_list)
        self.e3 = xmlutils.element(self.tag, [self.e1, self.e2])
        
    def test_element(self):
        assert self.e1.items() == self.attributes_dict.items()
        assert self.e1.attrib == self.attributes_dict
        assert self.e2.text == ''.join(self.attributes_list)
        assert self.e3.getchildren() == [self.e1, self.e2]