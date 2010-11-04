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
import xml_utils
        
class XmlUtilsTest(unittest.TestCase):
    def test_create_element(self):
        e1 = xml_utils.create_element('a', p='hey', q='you')
        e2 = xml_utils.create_element('b', ['good', 'bye'])
        e3 = xml_utils.create_element('c', [e1, e2])
        e4 = xml_utils.create_element(('d', 'e'), [e1, e2])
        assert sorted(e1.items()) == [('p', 'hey'), ('q', 'you')]
        assert e1.tag == 'a'
        assert e1.attrib == {'p': 'hey', 'q': 'you'}
        assert e2.tag == 'b'
        assert e2.text == 'goodbye'
        assert e3.tag == 'c'
        assert e3.getchildren() == [e1, e2]
        assert e4.tag == '{d}e'
        assert xml_utils.serialize(e4) == '''\
<ns0:e xmlns:ns0="d">
  <a p="hey" q="you" />
  <b>goodbye</b>
</ns0:e>
'''
