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

"""Tests for export.py."""

from export import format

import datetime
import unittest
        
class ExportTest(unittest.TestCase):                       
    def test_format(self):
        time = datetime.datetime(2010, 6, 6, 15, 17, 3, 52581)
        
        assert format(u'inf\xf6r') == 'inf\xc3\xb6r'
        assert format('foo\n!') == 'foo !'
        assert format(['foo_', '1']) == 'foo_, 1'
        assert format(['foo_', '']) == 'foo_, '
        assert format(time) == '2010-06-06 10:17:03 -05:00'
        assert format(u'') == ''
        assert format('') == ''
        assert format([]) == ''
        assert format({}) == {}
        assert format(0) == 0
