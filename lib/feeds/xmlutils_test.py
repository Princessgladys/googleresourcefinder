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
        
class XmlUtilsTest(unittest.TestCase):
    def test_create_element(self):
        e1 = xmlutils.create_element('a', p='hey', q='you')
        e2 = xmlutils.create_element('b', ['good', 'bye'])
        e3 = xmlutils.create_element('c', [e1, e2])
        assert sorted(e1.items()) == [('p', 'hey'), ('q', 'you')]
        assert e1.tag == 'a'
        assert e1.attrib == {'p': 'hey', 'q': 'you'}
        assert e2.tag == 'b'
        assert e2.text == 'goodbye'
        assert e3.tag == 'c'
        assert e3.getchildren() == [e1, e2]
        assert xmlutils.serialize(e3) == '''\
<c>
  <a p="hey" q="you" />
  <b>goodbye</b>
</c>
'''
