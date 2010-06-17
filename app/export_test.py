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

import bubble
import csv
import datetime
import StringIO
import unittest

from google.appengine.api import users

import export
import model
from medium_test_case import MediumTestCase
from utils import db


KEY_MAP = {
    'facility_name': 'title',
    'alt_facility_name': 'alt_title',
    'facility_healthc_id': 'healthc_id',
    'facility_pcode': 'pcode',
    'contact_phone': 'phone',
    'contact_email': 'email'
}

class ExportTest(MediumTestCase):
    def setUp(self):
        def set_attr(facility, key, value):
            facility.set_attribute(key, value, self.time, self.user,
                                   self.nickname, self.affiliation,
                                   self.comment)
        MediumTestCase.setUp(self)
        min_attrs = [u'title', u'pcode', u'healthc_id', u'available_beds',
            u'total_beds', u'services', u'contact_name', u'phone', u'address',
            u'location']
        ft = model.FacilityType(key_name='hospital',
                                timestamp=datetime.datetime(2010, 06, 01),
                                attribute_names=['title', 'pcode'],
                                minimal_attribute_names=min_attrs)
        fin = open('app/testdata/golden_file.csv', 'r')
        self.time = datetime.datetime(2010, 06, 01, 12, 30, 50)
        self.user = users.User('test@example.com')
        self.nickname = 'nickname_foo'
        self.affiliation = 'affiliation_foo'
        self.comment = 'comment_foo'
        for record in csv.DictReader(fin):
            f = model.Facility(key_name='example.org/123', type='hospital')
            set_attr(f, 'location', db.GeoPt(record['latitude'],
                          record['longitude']))
            for key in record:
                if key == 'services':
                    set_attr(f, key, record[key].split(', '))
                elif key in ['available_beds' or 'total_beds' or 
                    'facility_healthc_id' or 'facility_pcode' or'region_id' or
                    'commune_id' or 'sante_id' or 'district_id' or
                    'commune_code']:
                    set_attr(f, key, int(record[key]))
                elif record[key] == 'True':
                    set_attr(f, key, True)
                elif record[key] == 'False':
                    set_attr(f, key, False)
                elif key in KEY_MAP:
                    set_attr(f, KEY_MAP[key], record[key])
                else:
                    set_attr(f, key, record[key])
        
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
        fin = open('app/testdata/golden_file.csv', 'r')
        sout = StringIO.StringIO()
        export.write_csv(sout, facility_type)
        assert sout.getvalue().strip() == fin.read().strip()
    
