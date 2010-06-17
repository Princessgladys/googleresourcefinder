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

import csv
import datetime
import StringIO
import unittest

from google.appengine.api import users

import export
import model
from medium_test_case import MediumTestCase
from utils import db
        
class ExportTest(MediumTestCase):
    def setUp(self):
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
            f.set_attribute('title', record['facility_name'], self.time,
                            self.user, self.nickname, self.affiliation,
                            self.comment)
            f.set_attribute('alt_title', record['alt_facility_name'],
                            self.time, self.user, self.nickname,
                            self.affiliation, self.comment)
            f.set_attribute('healthc_id', record['facility_healthc_id'],
                            self.time, self.user, self.nickname,
                            self.affiliation, self.comment)
            f.set_attribute('pcode', record['facility_pcode'],
                            self.time, self.user, self.nickname,
                            self.affiliation, self.comment)
            f.set_attribute('location', db.GeoPt(record['latitude'],
                            record['longitude']), self.time, self.user,
                            self.nickname, self.affiliation, self.comment)
            for key in record:
                if key == 'services':
                    record[key] = record[key].split(', ')
                if key == ('available_beds' or 'total_beds' or
                    'facility_healthc_id' or 'facility_pcode' or'region_id' or
                    'commune_id' or 'sante_id' or 'district_id'):
                    record[key] = int(record[key])
                if record[key] == 'True':
                    record[key] = True
                elif record[key] == 'False':
                    record[key] = False
                f.set_attribute(key, record[key], self.time, self.user,
                                self.nickname, self.affiliation, self.comment)
        
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
