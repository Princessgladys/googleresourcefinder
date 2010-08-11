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

"""Tests for edit.py."""

import datetime
import unittest
import webob

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp

import edit
import simplejson
import utils
from edit import ATTRIBUTE_TYPES
from feeds.xmlutils import Struct
from medium_test_case import MediumTestCase
from model import Account, Attribute, Subject, MinimalSubject, SubjectType
from model import Report

class EditTest(MediumTestCase):
    def setUp(self):
        MediumTestCase.setUp(self)
        self.subdomain = 'haiti'
        self.time = datetime.datetime(2010, 06, 15, 12, 30)
        self.change_time = datetime.datetime(2010, 06, 16, 12, 30)
        self.email = 'test@example.com'
        self.user = users.User(self.email)
        self.s = Subject.create(
            'haiti', 'hospital', 'example.org/123', self.user)
        self.s.set_attribute(
            'title', 'title_foo', self.time, self.user,
            'nickname_foo', 'affiliation_foo', 'comment_foo')
        self.s.set_attribute(
            'pcode', 'pcode_foo', self.time, self.user,
            'nickname_foo', 'affiliation_foo', 'comment_foo')
        self.ms = MinimalSubject.create(self.s)

        self.st = SubjectType.create('haiti', 'hospital')
        self.st.attribute_names = ['title', 'pcode']
        self.st.minimal_attribute_names = ['title', 'total_beds']

        self.report = Report(arrived=self.time, source='url_foo.bar',
                             author=self.user, observed=self.time)
        self.change_metadata = edit.ChangeMetadata(
            observed=self.change_time,
            author='author_bar', author_nickname='nickname_bar',
            author_affiliation='affiliation_bar')
        self.account = Account(email=self.email, actions=['*:view', '*:edit'], locale='en')

        db.put([self.s, self.ms, self.st])

    def tearDown(self):
        db.delete([self.s, self.ms, self.st])

    def test_str_attr_type_class(self):
        str_attr_type = ATTRIBUTE_TYPES['str']
        str_attr = Attribute(key_name='organization_name', type='str')

        # test make_input() function
        assert (str_attr_type.make_input('title', '') ==
                '<input name="title" value="" size=40>')
        assert (str_attr_type.make_input('title', 'title_foo') ==
                '<input name="title" value="title_foo" size=40>')
        assert (str_attr_type.make_input('title&foo', '') ==
                '<input name="title&amp;foo" value="" size=40>')

        # test to_stored_value() function
        assert (str_attr_type.to_stored_value(
                'title', 'title_foo', None, None) == 'title_foo')
        assert (str_attr_type.to_stored_value(
                'title', ' title_foo\n\t', None, None) == 'title_foo')
        assert (str_attr_type.to_stored_value(
                'title', u'\u2013', None, None) == u'\u2013')
        assert (str_attr_type.to_stored_value(
                'title', '', None, None) == None)

        # test apply_change() function
        request = webapp.Request(webob.Request.blank(
                                 '/?organization_name=org_foo&' +
                                 'organization_name__comment=comment_foo'
                                 ).environ)
        str_attr_type.apply_change(self.s, self.ms, self.report, self.st,
                                   request, str_attr, self.change_metadata)
        assert self.s.get_value('organization_name') == 'org_foo'
        assert self.s.get_observed('organization_name') == self.change_time
        assert self.s.get_author('organization_name') == 'author_bar'
        assert (self.s.get_author_nickname('organization_name') ==
                'nickname_bar')
        assert (self.s.get_author_affiliation('organization_name') ==
                'affiliation_bar')
        assert self.s.get_comment('organization_name') == 'comment_foo'
        assert self.report.get_value('organization_name') == 'org_foo'
        assert not self.ms.get_value('organization_name')

    def test_text_attr_type_class(self):
        text_attr = Attribute(key_name='text_attr', type='text')
        text_attr_type = ATTRIBUTE_TYPES['text']

        # test make_input() function
        assert (text_attr_type.make_input('title', '', text_attr) ==
                '<textarea name="title" rows=5 cols=34></textarea>')
        assert (text_attr_type.make_input('title', 'title_foo', text_attr) ==
                '<textarea name="title" rows=5 cols=34>title_foo</textarea>')
        assert (text_attr_type.make_input('title', 'title&foo', text_attr) ==
                '<textarea name="title" rows=5 cols=34>title&amp;foo' +
                '</textarea>')

        # test to_stored_value() function
        assert (text_attr_type.to_stored_value(
                'text_attr', 'value_foo', None, text_attr) == 'value_foo')
        assert type(text_attr_type.to_stored_value(
                    'text_attr', 'value_foo', None, text_attr)) == db.Text
        assert (text_attr_type.to_stored_value(
                'text_attr', 0, None, text_attr) == None)
        assert (text_attr_type.to_stored_value(
                'text_attr', [], None, text_attr) == None)
        assert (text_attr_type.to_stored_value(
                'text_attr', '', None, text_attr) == None)

    def test_contact_attr_type_class(self):
        contact_attr = Attribute(key_name='contact_information', type='contact')
        contact_attr_type = ATTRIBUTE_TYPES['contact']
        contact = 'Phil Fritzsche|555-555-3867|%s' % self.user.email()

        # test make_input() function
        input =  contact_attr_type.make_input(
            'contact_information', contact, contact_attr)
        assert 'contact_information.name' in input
        assert 'contact_information.phone' in input
        assert 'contact_information.email' in input
        assert 'value="Phil Fritzsche"' in input
        assert 'value="555-555-3867"' in input
        assert 'value="test@example.com"' in input

        assert 'value=""' in contact_attr_type.make_input(
            'contact_information', '', None)

        # test parse_input() function
        request = webapp.Request(webob.Request.blank(
                                 '/?contact_information.name=Phil Fritzsche&' +
                                 'contact_information.phone=555-555-3867&' +
                                 'contact_information.email=test@example.com'
                                 ).environ)
        assert (contact_attr_type.parse_input(None, 'contact_information',
                None, request, contact_attr) == contact)

        request = webapp.Request(webob.Request.blank(
                                 '/?contact_information.name=&' +
                                 'contact_information.phone=&' +
                                 'contact_information.email=').environ)
        assert (contact_attr_type.parse_input(None, 'contact_information',
                None, request, contact_attr) == None)

        request = webapp.Request(webob.Request.blank('/').environ)
        assert (contact_attr_type.parse_input(None, 'contact_information',
                None, request, contact_attr) == None)

    def test_date_attr_type_class(self):
        request = webapp.Request(webob.Request.blank('/').environ)
        date_attr = Attribute(key_name='date_attr', type='date')
        date_attr_type = ATTRIBUTE_TYPES['date']
        bad_date = '06-15-2010'
        date = '2010-06-15'

        assert (date_attr_type.to_stored_value('date_attr', date, request,
                date_attr) == datetime.datetime(2010, 06, 15))
        assert (date_attr_type.to_stored_value('date_attr', date + '\n',
                request, date_attr) == datetime.datetime(2010, 06, 15))

        assert (date_attr_type.to_stored_value('date_attr', '', request,
                date_attr) == None)
        assert (date_attr_type.to_stored_value('date_attr', ' \n', request,
                date_attr) == None)

        try:
            date_attr_type.to_stored_value('date_attr', bad_date, request,
                                           date_attr)
            assert False # if this did not raise an exception, break
        except:
            assert True # if the exception was properly raised

    def test_int_attr_type_class(self):
        # test to_stored_value() function
        int_attr = Attribute(key_name='total_beds', type='int')
        int_attr_type = ATTRIBUTE_TYPES['int']
        assert int_attr_type.to_stored_value(None, 10, None, None) == 10
        assert int_attr_type.to_stored_value(None, 10.0, None, None) == 10
        assert int_attr_type.to_stored_value(None, 0, None, None) == 0
        assert int_attr_type.to_stored_value(None, 3.5, None, None) == 3

        # test apply_change() function with minimal_attribute change
        request = webapp.Request(webob.Request.blank(
                                 '/?total_beds=37&total_beds__comment=' +
                                 'comment_bar').environ)
        int_attr_type.apply_change(self.s, self.ms, self.report, self.st,
                                   request, int_attr, self.change_metadata)
        assert self.s.get_value('total_beds') == 37
        assert self.s.get_comment('total_beds') == 'comment_bar'
        assert self.ms.get_value('total_beds') == 37

    def test_float_attr_type_class(self):
        float_attr_type = ATTRIBUTE_TYPES['float']
        float_attr = Attribute(key_name='ratio_foo', type='float')

        # test make_input() function
        assert (float_attr_type.make_input('ratio_foo', 3.867, float_attr) ==
                '<input name="ratio_foo" value="3.867" size=10>')
        assert (float_attr_type.make_input('ratio_foo', 3, float_attr) ==
                '<input name="ratio_foo" value="3" size=10>')
        assert (float_attr_type.make_input('ratio_foo', 0, float_attr) ==
                '<input name="ratio_foo" value="0" size=10>')

        # test to_stored_value() function
        assert float_attr_type.to_stored_value(None, 10, None, None) == 10.0
        assert float_attr_type.to_stored_value(None, 10.0, None, None) == 10.0
        assert float_attr_type.to_stored_value(None, 0, None, None) == 0.0
        assert float_attr_type.to_stored_value(None, 3.5, None, None) == 3.5

    def test_bool_attr_type_class(self):
        name = 'can_pick_up_patients'
        bool_attr_type = ATTRIBUTE_TYPES['bool']
        bool_attr = Attribute(key_name=name, type='bool')

        # test make_input() function
        input = bool_attr_type.make_input(name, True, bool_attr)
        assert 'name="can_pick_up_patients"' in input
        assert 'value=""' in input
        assert 'value="TRUE" selected' in input
        assert 'value="FALSE"' in input
        assert '<select ' in input
        assert input.count('selected') == 1

        input = bool_attr_type.make_input(name, False, bool_attr)
        assert 'value="FALSE" selected' in input
        assert input.count('selected') == 1

        input = bool_attr_type.make_input(name, None, bool_attr)
        assert 'value="" selected' in input
        assert input.count('selected') == 1

        input = bool_attr_type.make_input(name, 'test!', bool_attr)
        assert 'value="" selected' in input
        assert input.count('selected') == 1

        # test to_stored_value() function
        assert (bool_attr_type.to_stored_value(name, 'TRUE', None, bool_attr)
                == True)
        assert (bool_attr_type.to_stored_value(name, 'FALSE', None, bool_attr)
                == False)
        assert (bool_attr_type.to_stored_value(name, '', None, bool_attr) ==
                None)

    def test_choice_attr_type_class(self):
        choice_attr_type = ATTRIBUTE_TYPES['choice']
        choice_attr = Attribute(
            key_name='category', type='choice', values=['foo', 'bar'])

        # test make_input() function
        input = choice_attr_type.make_input('category', 'foo', choice_attr)
        assert 'name="category"' in input
        assert 'value="foo" selected' in input
        assert 'value="bar"' in input
        assert input.count('selected') == 1

        input = choice_attr_type.make_input('category', '', choice_attr)
        assert 'value=""' in input
        assert 'value="foo"' in input
        assert 'value="bar"' in input
        assert input.count('selected') == 1

        # test proper return when an invalid choice is supplied as the value
        choice_attr = Attribute(key_name='category', type='choice')
        input = choice_attr_type.make_input('category', 'foo', choice_attr)
        assert 'foo' not in input
        assert input.count('value=""') == 1
        assert input.count('selected') == 0

    def test_multi_attr_type_class(self):
        choices = ['foo', 'bar']
        multi_attr_type = ATTRIBUTE_TYPES['multi']
        multi_attr = Attribute(
            key_name='services', type='multi', values=choices)

        # test make_input() function
        input = multi_attr_type.make_input('services', ['foo', 'bar'],
                                           multi_attr)
        assert 'input type=checkbox' in input
        assert 'name="services.foo"' in input
        assert 'id="services.foo" checked' in input
        assert 'name="services.bar"' in input
        assert 'id="services.bar" checked' in input
        assert input.count('checked') == 2

        input = multi_attr_type.make_input('services', [], multi_attr)
        assert input.count('checked') == 0

        # test to_stored_value() function
        request = webapp.Request(webob.Request.blank(
                                 '/?services.foo=c&services.bar=c').environ)
        assert (multi_attr_type.to_stored_value('services', [], request,
                multi_attr) == choices)

        request = webapp.Request(webob.Request.blank('/').environ)
        assert not (multi_attr_type.to_stored_value('services', [], request,
                    multi_attr))

    def test_geopt_attr_type_class(self):
        geopt_attr_type = ATTRIBUTE_TYPES['geopt']
        geopt_attr = Attribute(key_name='location', type='multi')
        location = Struct(lat=40.7142, lon=-74.0064)

        # test make_input() function
        input = geopt_attr_type.make_input('location', location, geopt_attr)
        assert 'name="location.lat" value="%g"' % location.lat in input
        assert 'name="location.lon" value="%g"' % location.lon in input

        input = geopt_attr_type.make_input('location', None, geopt_attr)
        assert input.count('value=""') == 2
        assert input.count('location') == 2

        # test to_stored_value() function
        request = webapp.Request(webob.Request.blank(
                                 '/?location.lat=%g&location.lon=%g' %
                                 (location.lon, location.lat)).environ)
        assert (geopt_attr_type.to_stored_value('location', None, request,
                geopt_attr) == db.GeoPt(location.lon, location.lat))

        request = webapp.Request(webob.Request.blank(
                                 '/?location.lat=&location.lon=').environ)
        assert (geopt_attr_type.to_stored_value('location', None, request,
                geopt_attr) == None)

        request = webapp.Request(webob.Request.blank('/').environ)
        assert (geopt_attr_type.to_stored_value('location', None, request,
                geopt_attr) == None)

    def test_has_changed(self):
        str_attr = Attribute(key_name='title', type='str')

        request = webapp.Request(webob.Request.blank(
                                 '/?title=title_bar&editable.title="title_foo"'
                                 ).environ)
        assert edit.has_changed(self.s, request, str_attr)

        request = webapp.Request(webob.Request.blank(
                                 '/?title=title_foo&editable.title="title_foo"'
                                 ).environ)
        assert not edit.has_changed(self.s, request, str_attr)

    def test_has_comment_changed(self):
        str_attr = Attribute(key_name='title', type='str')

        request = webapp.Request(webob.Request.blank(
                                 '/?title__comment=comment_bar&' +
                                 'editable.title__comment="title_foo"'
                                 ).environ)
        assert edit.has_comment_changed(self.s, request, str_attr) == True

        request = webapp.Request(webob.Request.blank(
                                 '/?title__comment=comment_foo&' +
                                 'editable.title__comment="title_foo"'
                                 ).environ)
        assert edit.has_comment_changed(self.s, request, str_attr) == False

    def test_update(self):
        """Confirms that update works properly even when sent unicode
        unicode characters via post. The edit.update() calls will throw an
        error if the test fails."""
        # Submit an edit with non-Unicode content.
        request_text = '/?subdomain=haiti' + \
                       '&title=title_foo&editable.title="title_bar"' + \
                       '&pcode=pcode_foo&editable.pcode="pcode_bar"' + \
                       '&save=Save'
        request = webapp.Request(webob.Request.blank(request_text).environ)
        attributes = {
            u'title': Attribute(key_name='title', type='str'),
            u'pcode': Attribute(key_name='pcode', type='str')
        }
        edit.update(self.s.name, self.st, request, self.user, self.account,
                    attributes, self.subdomain, False, False)

        # Check that the Subject and MinimalSubject were indeed updated.
        subject = Subject.get('haiti', self.s.name)
        minimal_subject = MinimalSubject.get_by_subject(subject)
        assert subject.get_value('title') == 'title_foo'
        assert minimal_subject.get_value('title') == 'title_foo'

        # Submit an edit with Unicode content (UTF-8 encoded to \xc3\x89).
        request_text = '/?subdomain=haiti&' + \
                       'subject_name=paho.org%2FHealthC_ID%2F1129136&' + \
                       'title=Marriane+%C3%89&' + \
                       'editable.title=%22Marriane%22&title__comment=' + \
                       '&save=Save&pcode=pcode_foo&' + \
                       'editable.pcode="pcode_foo"&pcode__comment='
        request = webapp.Request(webob.Request.blank(request_text).environ)
        edit.update(self.s.name, self.st, request, self.user, self.account,
                    attributes, self.subdomain, False, False)

        # Check that the Subject and MinimalSubject were indeed updated.
        subject = Subject.get('haiti', self.s.name)
        minimal_subject = MinimalSubject.get_by_subject(subject)
        assert subject.get_value('title') == u'Marriane \xc9'
        assert minimal_subject.get_value('title') == u'Marriane \xc9'

    def test_create(self):
        """Tests creation of a new Subject with update()."""
        # Submit a form to create a new Subject.
        subject_name = Subject.generate_name('example.com', 'hospital')
        request_text = '/?subdomain=haiti' + \
                       '&title=title_new&editable.title=null' + \
                       '&pcode=pcode_new&editable.pcode=null' + \
                       '&save=Save'
        request = webapp.Request(webob.Request.blank(request_text).environ)
        attributes = {
            u'title': Attribute(key_name='title', type='str',
                                edit_action='advanced_edit'),
            u'pcode': Attribute(key_name='pcode', type='str')
        }

        # Make sure it breaks, as the user does not have permission
        names_before = [s.name for s in Subject.all_in_subdomain('haiti')]
        self.assertRaises(Exception, edit.update, subject_name, self.st, request,
                           self.user, self.account, attributes, self.subdomain,
                           False, False)

        # Grant user permission to add subjects and try again
        self.account.actions.append('*:add')
        edit.update(subject_name, self.st, request, self.user, self.account,
                    attributes, self.subdomain, True, False)
        names_after = [s.name for s in Subject.all_in_subdomain('haiti')]

        # Check that exactly one new Subject was created
        assert len(names_after) == len(names_before) + 1
        extra_names = list(set(names_after) - set(names_before))
        assert len(extra_names) == 1
        assert extra_names[0].startswith('example.com/')

        # Check the fields of the new Subject and MinimalSubject.
        subject = Subject.get('haiti', extra_names[0])
        minimal_subject = MinimalSubject.get_by_subject(subject)
        assert subject.get_value('title') == u'title_new'
        assert minimal_subject.get_value('title') == u'title_new'
