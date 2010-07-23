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

INT_FIELDS = [
    'available_beds',
    'total_beds',
    'healthc_id',
    'pcode',
    'region_id',
    'commune_id',
    'sante_id',
    'district_id',
    'commune_code'
]

SERVICES = [
    'GENERAL_SURGERY',
    'LAB',
    'X_RAY',
    'CT_SCAN',
    'BLOOD_BANK',
    'MORTUARY_SERVICES'
]

STR_FIELDS = [
    'title',
    'alt_title',
    'contact_name',
    'phone',
    'email',
    'department',
    'district',
    'commune',
    'address',
    'organization',
    'damage',
    'comments'
]

BOOL_FIELDS = {
    'reachable_by_road': True,
    'can_pick_up_patients': False
}

SELECT_FIELDS = {
    'organization_type': 'MIL',
    'category': 'DISP',
    'construction': 'WOOD_FRAME',
    'operational_status': 'OPERATIONAL'
}


class ExportTest(MediumTestCase):
    def setUp(self):
        def set_attr(subject, key, value):
            subject.set_attribute(key, value, self.time, self.user,
                                  self.nickname, self.affiliation,
                                  self.comment)
        MediumTestCase.setUp(self)
        min_attrs = [u'title', u'pcode', u'healthc_id', u'available_beds',
                     u'total_beds', u'services', u'contact_name', u'phone',
                     u'address', u'location']
        self.time = datetime.datetime(2010, 06, 01, 12, 30, 50)
        self.user = users.User('test@example.com')
        self.nickname = 'nickname_foo'
        self.affiliation = 'affiliation_foo'
        self.comment = 'comment_foo'
        self.st = model.SubjectType(key_name='haiti:hospital',
                                    timestamp=datetime.datetime(2010, 06, 01),
                                    attribute_names=['title', 'pcode'],
                                    minimal_attribute_names=min_attrs)
        self.s = model.Subject(key_name='haiti:example.org/123',
                               type='hospital')
        text_fields = dict((name, name + '_foo') for name in STR_FIELDS)
        set_attr(self.s, 'location', db.GeoPt(50.0, 0.1))
        set_attr(self.s, 'services', SERVICES)
        for field in text_fields:
            set_attr(self.s, field, text_fields[field])
        for i in range(len(INT_FIELDS)):
            set_attr(self.s, INT_FIELDS[i], i)
        for key in BOOL_FIELDS:
            set_attr(self.s, key, BOOL_FIELDS[key])
        for key in SELECT_FIELDS:
            set_attr(self.s, key, SELECT_FIELDS[key])
        
        db.put(self.s)
        db.put(self.st)
        
    def tearDown(self):
        db.delete(self.s)
        db.delete(self.st)
    
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
        subject_type = model.SubjectType.get('haiti', 'hospital')
        fin = open('app/testdata/golden_file.csv', 'r')
        sout = StringIO.StringIO()
        export.write_csv(sout, subject_type)
        assert sout.getvalue().strip() == fin.read().strip()
