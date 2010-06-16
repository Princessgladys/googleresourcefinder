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

import datetime
import StringIO
import unittest

from google.appengine.api import users

from medium_test_case import MediumTestCase
from utils import db
import export
import model
        
class ExportTest(MediumTestCase):
    def setUp(self):
        MediumTestCase.setUp(self)
        f = model.Facility(key_name='example.org/123', type='hospital')
        f.set_attribute('title', 'title_foo', datetime.datetime.now(),
                        users.User('test@example.com'),
                        'nickname_foo', 'affiliation_foo', 'comment_foo')
        f.set_attribute('pcode', 'pcode_foo',
                        datetime.datetime.now(),
                        users.User('test@example.com'),
                        'nickname_foo', 'affiliation_foo', 'comment_foo')
        ft = model.FacilityType(key_name='hospital',
                                timestamp=datetime.datetime(2010, 06, 01),
                                attribute_names=['title', 'pcode'],
                                minimal_attribute_names=['title'])
        db.put(f)
        db.put(ft)
    
    def test_format(self):
        time = datetime.datetime(2010, 6, 6, 15, 17, 3, 52581)
        
        assert export.format(u'inf\xf6r') == 'inf\xc3\xb6r'
        assert export.format('foo\n!') == 'foo !'
        assert export.format(['foo_', '1']) == 'foo_, 1'
        assert export.format(['foo_', '']) == 'foo_, '
        assert export.format(time) == '2010-06-06 10:17:03 -05:00'
        assert export.format(u'') == ''
        assert export.format('') == ''
        assert export.format([]) == ''
        assert export.format({}) == {}
        assert export.format(0) == 0

    def test_write_csv(self):
        facility_type = model.FacilityType.get_by_key_name('hospital')
        fin = open('app/testdata/test_export_out.csv', 'r')
        sout = StringIO.StringIO()
        export.write_csv(sout, facility_type)
        
        assert sout.getvalue() == fin.read()
