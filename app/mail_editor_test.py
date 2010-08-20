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

"""Tests for mail_alerts.py."""

import datetime
import re

import django.utils.translation
from google.appengine.api import mail
from google.appengine.api import users

import cache
import export_test
import mail_editor
from feeds.xmlutils import Struct
from medium_test_case import MediumTestCase
from model import Account, Attribute, Subdomain, MinimalSubject, Subject
from model import SubjectType
from utils import db

SAMPLE_EMAIL_WORKING = '''UPDATE title_foo (example.org/123)
Available beds 18
Total beds: 222
Email; test@example.com
Commune= foo@bar!
Can pick_up patients yes'''

SAMPLE_EMAIL_AUTHENTICATION = '''nickname nickname_foo
affiliation affiliation_foo

UPDATE title_foo (example.org/123)
Available beds 18
Total beds 222
Email test@example.com
Commune foo@bar!
Can pick up patients yes'''

SAMPLE_EMAIL_BROKEN = '''UPDATE title_foo (example.org/123)
Available beds d
Total beds 222
Email test@example.com
Commune foo@bar!
Can pick up patients yes'''

SAMPLE_EMAIL_QUOTED = '''>> UPDATE title_foo (example.org/123)
>> Available beds 18
>> Total beds 222
>> Email test@example.com
>> Commune foo@bar!
>> Can pick up patients yes'''

SAMPLE_EMAIL_STOP = '''UPDATE title_foo (example.org/123)
Available beds 18
Total beds 222
Email test@example.com
Commune foo@bar!
--- --- --- ---
Can pick up patients yes'''

SAMPLE_EMAIL_MIXED = '''UPDATE title_foo (example.org/123)
Available beds 18
Total beds 222
Email test@example.com
Commune foo@bar!
Can pick up patients yes

>> UPDATE title_foo (example.org/123)
>> Available beds d
>> Total beds 222
>> Email test@example.com
>> Commune foo@bar!
>> Can pick up patients yes'''

SAMPLE_EMAIL_MULTIPLE = '''UPDATE title_foo (example.org/123)
Available beds 18
Total beds 222
Email test@example.com
Commune foo@bar!
Can pick up patients yes

UPDATE title_bar
Available beds 20'''

SAMPLE_EMAIL_AMBIGUOUS = '''UPDATE title_foobar
Total beds 77'''

SAMPLE_EMAIL_AMBIGUOUS_DETAIL = '''update title_foobar (example.org/789)
Total beds 77

update title_foobar (example.org/012)
total beds 76'''

class MailEditorTest(MediumTestCase):
    def setUp(self):
        MediumTestCase.setUp(self)
        django.utils.translation.activate('en')
        cache.flush_all()
        self.email = 'test@example.com'
        self.user = users.User(self.email)
        self.account = Account(email=self.email, actions=['*:*'],
                               locale='en', nickname='nickname_foo',
                               affiliation='affiliation_foo')
        self.subject = Subject(key_name='haiti:example.org/123',
                               type='hospital', author=self.user,
                               title__='title_foo', healthc_id__='123')
        self.subject2 = Subject(key_name='haiti:example.org/456',
                                type='hospital', author=self.user,
                                title__='title_bar', healthc_id__='456')
        self.subject3 = Subject(key_name='haiti:example.org/789',
                                type='hospital', author=self.user,
                                title__='title_foobar', healthc_id__='789')
        self.subject4 = Subject(key_name='haiti:example.org/012',
                                type='hospital', author=self.user,
                                title__='title_foobar', healthc_id__='012')
        self.ms = MinimalSubject(self.subject, type='hospital')
        self.ms2 = MinimalSubject(self.subject2, type='hospital')
        self.ms3 = MinimalSubject(self.subject3, type='hospital')
        self.ms4 = MinimalSubject(self.subject4, type='hospital')
        attribute_names = export_test.STR_FIELDS + \
                          export_test.INT_FIELDS + \
                          export_test.BOOL_FIELDS.keys() + \
                          export_test.SELECT_FIELDS.keys()
        self.subject_type = SubjectType(key_name='haiti:hospital',
                                        attribute_names=attribute_names)
        self.subdomain = Subdomain(key_name='haiti')
        db.put([self.account, self.subject, self.subject2, self.subject3,
                self.subject4, self.subject_type, self.subdomain,
                self.ms, self.ms2, self.ms3, self.ms4])

        for field in export_test.STR_FIELDS:
            Attribute(key_name=field, type='str').put()
        for field in export_test.INT_FIELDS:
            Attribute(key_name=field, type='int').put()
        for field in export_test.BOOL_FIELDS:
            Attribute(key_name=field, type='bool').put()
        for field in export_test.SELECT_FIELDS:
            Attribute(key_name=field, type='choice').put()

    def tearDown(self):
        db.delete([self.account, self.subject, self.subject2, self.subject3,
                   self.subject4, self.subject_type, self.subdomain,
                   self.ms, self.ms2, self.ms3, self.ms4])
        for attribute in Attribute.all():
            db.delete(attribute)

    def test_parse(self):
        """Confirm that the parse function properly translates string values
        into datastore-friendly values."""
        # test an int attribute
        attribute_name = 'available_beds'
        update = ['available_beds', '222']
        assert mail_editor.parse(attribute_name, update, 1) == 222

        update = ['available', 'beds', '222']
        assert mail_editor.parse(attribute_name, update, 2) == 222

        # make sure it throws an error when an int is expected but not received
        update = ['available', 'beds', 'd']
        self.assertRaises(ValueError, mail_editor.parse,
                          attribute_name, update, 2)

        # test a string attribute
        attribute_name = 'organization'
        update = ['organization', 'organization_foo']
        assert (mail_editor.parse(attribute_name, update, 1) ==
                'organization_foo')

        # test proper parsing of escaped strings
        attribute_name = 'commune'
        update = ['commune', '"code"']
        assert mail_editor.parse(attribute_name, update, 1) == 'code'

        # test like attributes names
        attribute_name = 'commune_code'
        update = ['commune', 'code', '12345']
        assert mail_editor.parse(attribute_name, update, 2) == 12345

        # test a bool attribute
        attribute_name = 'reachable_by_road'
        update = ['reachable_by', 'road', 'y']
        assert mail_editor.parse(attribute_name, update, 2)

        attribute_name = 'reachable_by_road'
        update = ['reachable_by', 'road', 'yEs']
        assert mail_editor.parse(attribute_name, update, 2)

        attribute_name = 'reachable_by_road'
        update = ['reachable_by', 'road', '!']
        assert not mail_editor.parse(attribute_name, update, 2)

        attribute_name = 'reachable_by_road'
        update = ['reachable_by', 'road', 'no']
        assert not mail_editor.parse(attribute_name, update, 2)

    def test_mail_editor_authenticate(self):
        """Confirms that authenticate() identifies existing users."""
        message = mail_editor.mail.EmailMessage(
            sender=self.account.email,
            to='haiti-updates@resource-finder.appspotmail.com',
            subject='Resource Finder Updates',
            body=SAMPLE_EMAIL_WORKING)

        mail_editor_ = mail_editor.MailEditor()
        mail_editor_.email = 'test@example.com'
        assert mail_editor_.authenticate(message)

        db.delete(self.account)
        assert not mail_editor_.authenticate(message)

    def test_mail_editor_is_authentication(self):
        """Confirm that is_authentication() identifies messages sent with
        authentication information for the user."""
        message = mail_editor.mail.EmailMessage(
            sender=self.account.email,
            to='haiti-updates@resource-finder.appspotmail.com',
            subject='Resource Finder Updates',
            body=SAMPLE_EMAIL_AUTHENTICATION)
        mail_editor_ = mail_editor.MailEditor()
        mail_editor_.email = 'test@example.com'
        mail_editor_.account = None # is_authentication is always run after
                                    # authenticate, so it will always have
                                    # an account, though it may be None
        assert mail_editor_.is_authentication(message)

        message.body=SAMPLE_EMAIL_WORKING
        assert not mail_editor_.is_authentication(message)

    def test_mail_editor_receive(self):
        """Confirm that it receives and properly sends an email with the
        information from the received update."""
        self.sent_messages = []
        message = mail.InboundEmailMessage(
            sender=self.account.email,
            to='haiti-updates@resource-finder.appspotmail.com',
            subject='Resource Finder Updates',
            body=SAMPLE_EMAIL_WORKING,
            date='Wed, 04 Aug 2010 13:07:18 -0400')
        request = Struct(url='test/path', path='/path',
                         headers={'Host': 'localhost:8080'},
                         domain='localhost:8080')
        mail_editor_ = mail_editor.MailEditor()
        mail_editor_.request = request

        # check working update email
        mail_editor_.receive(message)
        body = self.sent_messages[0].textbody()
        assert len(self.sent_messages) == 1
        self.check_for_correct_update(body, self.sent_messages[0])

        # check broken email
        message.body = SAMPLE_EMAIL_BROKEN
        mail_editor_.receive(message)
        body = self.sent_messages[1].textbody()
        assert len(self.sent_messages) == 2
        assert 'ERROR' in self.sent_messages[1].subject()
        assert '"d" is not a valid value for available_beds' in body
        assert body.count('--- --- --- ---') == 2
        assert 'REFERENCE DOCUMENT @' in body

        # check working quoted email
        message.body = SAMPLE_EMAIL_QUOTED
        mail_editor_.receive(message)
        body = self.sent_messages[2].textbody()
        assert len(self.sent_messages) == 3
        self.check_for_correct_update(body, self.sent_messages[2])

        # check working mixed email. should ignore the error in the quoted area
        message.body = SAMPLE_EMAIL_MIXED
        mail_editor_.receive(message)
        body = self.sent_messages[3].textbody()
        assert len(self.sent_messages) == 4
        self.check_for_correct_update(body, self.sent_messages[3])

        db.delete(self.account)
        # check working but not authenticated email
        message.body = SAMPLE_EMAIL_WORKING
        mail_editor_.receive(message)
        body = self.sent_messages[4].textbody()
        assert len(self.sent_messages) == 5
        assert mail_editor_.need_authentication
        assert 'nickname' in body
        assert 'affiliation' in body
        assert 'Pending updates' in body
        assert not Account.all().get()

        # send it an authentication email
        message.body = SAMPLE_EMAIL_AUTHENTICATION
        mail_editor_.receive(message)
        body = self.sent_messages[5].textbody()
        assert Account.all().get()
        assert len(self.sent_messages) == 6
        assert not mail_editor_.need_authentication
        self.check_for_correct_update(body, self.sent_messages[5])

        # do same with an already existing account sans nickname/affiliation
        self.account.nickname = None
        self.account.affiliation = None
        db.put(self.account)
        mail_editor_.receive(message)
        body = self.sent_messages[6].textbody()
        assert Account.all().get()
        assert len(self.sent_messages) == 7
        assert not mail_editor_.need_authentication
        self.check_for_correct_update(body, self.sent_messages[6])

        # check working email with stop delimeter
        message.body = SAMPLE_EMAIL_STOP
        mail_editor_.receive(message)
        body = self.sent_messages[7].textbody()
        assert len(self.sent_messages) == 8
        assert not 'update title_foo' in body
        assert 'title_foo' in body
        assert 'Available beds' in body and '18' in body
        assert 'Total beds' in body and '22' in body
        assert 'Email' in body and 'test@example.com' in body
        assert 'Commune' in body and 'foo@bar!' in body
        assert 'Can pick up patients' not in body and 'yes' not in body

        # check email with multiple subjects
        message.body = SAMPLE_EMAIL_MULTIPLE
        mail_editor_.receive(message)
        body = self.sent_messages[8].textbody()
        assert len(self.sent_messages) == 9
        assert 'title_foo' in body and 'title_bar' in body
        assert 'update title_foo' not in body
        assert 'update title_bar' not in body
        assert 'Available beds' in body and '18' in body and '20' in body

        # check email with an ambiguous subject
        message.body = SAMPLE_EMAIL_AMBIGUOUS
        mail_editor_.receive(message)
        body = self.sent_messages[9].textbody()
        assert len(self.sent_messages) == 10
        assert 'ERROR' in self.sent_messages[9].subject()
        assert 'title_foobar' in body and 'ambiguous' in body
        assert 'Try again with one of the following' in body
        assert 'example.org/789' in body
        assert 'example.org/012' in body
        assert 'Total beds 77' in body
        assert 'REFERENCE DOCUMENT @' in body

        # check email with multiple same title'd facilities [and unique keys]
        message.body = SAMPLE_EMAIL_AMBIGUOUS_DETAIL
        mail_editor_.receive(message)
        body = self.sent_messages[10].textbody()
        assert len(self.sent_messages) == 11
        assert 'ERROR' not in self.sent_messages[10].subject()
        assert 'title_foobar' in body and '789' in body and '012' in body
        assert 'Total beds' in body and '77' in body and '76' in body
        assert 'REFERENCE DOCUMENT @' in body

    def test_mail_editor_process_email(self):
        """Confirms that process_email() returns a properly formatted structure
        of updates and errors, given the body of an email."""
        mail_editor_ = mail_editor.MailEditor()
        mail_editor_.request = Struct(headers={'Host': 'localhost:8080'})
        mail_editor_.init(message=Struct(
            sender='test@example.com',
            to='haiti-updates@resource-finder.appspotmail.com'))

        # check working email body
        updates, errors, ambiguities = mail_editor_.process_email(
            SAMPLE_EMAIL_WORKING)
        assert updates[0][0].key().name() == 'haiti:example.org/123'
        # updates[first_update][subject_data][attribute_#]
        assert 'available_beds' in updates[0][1][0]
        assert 'total_beds' in updates[0][1][1]
        assert 'email' in updates[0][1][2]
        assert 'commune' in updates[0][1][3]
        assert 'can_pick_up_patients' in updates[0][1][4]
        assert not errors

        # check broken email body
        updates, errors, ambiguities = mail_editor_.process_email(
            SAMPLE_EMAIL_BROKEN)
        assert updates[0][0].key().name() == 'haiti:example.org/123'
        assert 'Available beds d' in errors[0][1][0]['original_line']
        assert len(updates[0][1]) == 4

        # check quoted email body
        updates, errors, ambiguities = mail_editor_.process_email(
            SAMPLE_EMAIL_QUOTED)
        assert updates[0][0].key().name() == 'haiti:example.org/123'
        assert 'available_beds' in updates[0][1][0]
        assert 'total_beds' in updates[0][1][1]
        assert 'email' in updates[0][1][2]
        assert 'commune' in updates[0][1][3]
        assert 'can_pick_up_patients' in updates[0][1][4]
        assert not errors

        # check mixed email body
        updates, errors, ambiguities = mail_editor_.process_email(
            SAMPLE_EMAIL_MIXED)
        assert updates[0][0].key().name() == 'haiti:example.org/123'
        assert 'available_beds' in updates[0][1][0]
        assert 'total_beds' in updates[0][1][1]
        assert 'email' in updates[0][1][2]
        assert 'commune' in updates[0][1][3]
        assert 'can_pick_up_patients' in updates[0][1][4]
        assert not errors

        # check stop delimeter'd body
        updates, errors, ambiguities = mail_editor_.process_email(
            SAMPLE_EMAIL_STOP)
        assert updates[0][0].key().name() == 'haiti:example.org/123'
        assert 'available_beds' in updates[0][1][0]
        assert 'total_beds' in updates[0][1][1]
        assert 'email' in updates[0][1][2]
        assert 'commune' in updates[0][1][3]
        assert not errors

    def test_mail_editor_update_subjects(self):
        """Confirm that update_subjects() properly updates the datastore."""
        mail_editor_ = mail_editor.MailEditor()
        mail_editor_.account = self.account
        mail_editor_.request = Struct(headers={'Host': 'localhost:8080'})
        mail_editor_.init(message=Struct(
            sender='test@example.com',
            to='haiti-updates@resource-finder.appspotmail.com'))
        updates, errors, ambiguities = mail_editor_.process_email(
            SAMPLE_EMAIL_WORKING)
        mail_editor_.update_subjects(updates, datetime.datetime(2010, 8, 4))

        subject = Subject.get('haiti', 'example.org/123')
        assert subject.get_value('available_beds') == 18
        assert subject.get_value('total_beds') == 222
        assert subject.get_value('commune') == 'foo@bar!'
        assert subject.get_value('email') == 'test@example.com'
        assert subject.get_value('can_pick_up_patients')

    def test_mail_editor_send_email(self):
        """Confirms that the appropriate information is sent in an email back to
        the user as a confirmation / response / request / whatever. Ignoring the
        formatting of the email, as that is subject to change."""
        self.sent_messages = []

        message = mail.InboundEmailMessage(
            sender=self.account.email,
            to='haiti-updates@resource-finder.appspotmail.com',
            subject='Resource Finder Updates',
            body=SAMPLE_EMAIL_WORKING,
            date='Wed, 04 Aug 2010 13:07:18 -0400')
        request = Struct(url='test/path', path='/path',
                         headers={'Host': 'localhost:8080'})
        mail_editor_ = mail_editor.MailEditor()
        mail_editor_.account = self.account
        mail_editor_.need_authentication = False
        mail_editor_.request = request
        mail_editor_.init(message=Struct(
            sender='test@example.com',
            to='haiti-updates@resource-finder.appspotmail.com'))
        updates, errors, ambiguities = mail_editor_.process_email(
            SAMPLE_EMAIL_WORKING)
        mail_editor_.send_email(message, updates, errors, ambiguities)

        # updates, no errors
        assert len(self.sent_messages) == 1
        body = self.sent_messages[0].textbody()
        self.check_for_correct_update(body, self.sent_messages[0])

        # updates, errors
        message.body = SAMPLE_EMAIL_BROKEN
        updates, errors, ambiguities = mail_editor_.process_email(
            SAMPLE_EMAIL_BROKEN)
        mail_editor_.send_email(message, updates, errors, ambiguities)
        assert len(self.sent_messages) == 2
        body = self.sent_messages[1].textbody()
        assert 'ERROR' in self.sent_messages[1].subject()
        assert 'update' in body
        assert 'REFERENCE DOCUMENT @' in body

        mail_editor_.account = None
        mail_editor_.need_authentication = True
        db.delete(self.account)
        # need authentication
        message.body = SAMPLE_EMAIL_WORKING
        updates, errors, ambiguities = mail_editor_.process_email(
            SAMPLE_EMAIL_WORKING)
        mail_editor_.send_email(message, updates, errors, ambiguities)
        assert len(self.sent_messages) == 3
        body = self.sent_messages[2].textbody()
        assert 'ERROR' not in self.sent_messages[2].subject()
        assert 'nickname' in body
        assert 'affiliation' in body
        assert 'Pending updates' in body

    def test_match_nickname_affiliation(self):
        s = 'nickname'
        assert mail_editor.match_nickname_affiliation(
            s, '%s John Smith' % s) == 'John Smith'
        assert (mail_editor.match_nickname_affiliation(s, '%s %s' % (s, s)) ==
                'nickname')
        assert not mail_editor.match_nickname_affiliation(s, 'nickname')
        assert not mail_editor.match_nickname_affiliation(s, '')
        assert not mail_editor.match_nickname_affiliation('', 'nickname')
        assert not mail_editor.match_nickname_affiliation('', '')

    def test_match_email(self):
        assert mail_editor.match_email('test@example.com') == 'test@example.com'
        assert (mail_editor.match_email(u't\u00e9st@example.com') ==
                u't\u00e9st@example.com')
        assert (mail_editor.match_email(' test@example.com  ') ==
                'test@example.com')
        assert not mail_editor.match_email('test@')
        assert not mail_editor.match_email('.com')
        assert not mail_editor.match_email('test@examplecom')
        assert not mail_editor.match_email('test')
        assert not mail_editor.match_email('')

    def test_update_line_regexes(self):
        mail_editor_ = mail_editor.MailEditor()
        mail_editor_.request = Struct(headers={'Host': 'localhost:8080'})
        mail_editor_.init(message=Struct(
            sender='test@example.com',
            to='haiti-updates@resource-finder.appspotmail.com'))

        line_title_key = 'update Title Foo (example.org/123)'
        line_key = 'update (example.org/123)'
        line_title = 'update Title Foo'
        line_extra_chars_key_title = 'update Title_foo (ICU) ' + \
                                     '(example.org/123)'
        line_extra_chars_title = 'update Title-foo (ICU)'
        line_extra_chars_title_snafu = 'update Title_foo (I:CU)'
        line_unicode_title_key = u'upDAte Titl\u00e9Foo (example.org/123)'
        line_unicode_title = u'update Titl\u00e9Foo'
        line_unicode_key = u'update (\u00e9xample.org/123)'

        def match(regex, line):
            return re.match(regex, line, flags=mail_editor_.update_line_flags)

        def check_regex_with_key(regex, prefix=''):
            m = match(regex, prefix + line_title_key).groupdict()
            assert m['title'].strip() == 'Title Foo'
            assert m['subject_name'] == 'example.org/123'

            m = match(regex, prefix + line_key).groupdict()
            assert m['subject_name'] == 'example.org/123'
            assert not m['title']

            m = match(regex, prefix + line_extra_chars_key_title).groupdict()
            assert m['title'].strip() == 'Title_foo (ICU)'
            assert m['subject_name'] == 'example.org/123'

            m = match(regex, prefix + line_unicode_title_key).groupdict()
            assert m['title'].strip() == u'Titl\u00e9Foo'
            assert m['subject_name'] == 'example.org/123'

            m = match(regex, prefix + line_unicode_key).groupdict()
            assert not m['title']
            assert m['subject_name'] == u'\u00e9xample.org/123'

            # Lines with only title should break. Next regex will cover that case.
            assert not match(regex, prefix + line_title)
            assert not match(regex, prefix + line_extra_chars_title)
            assert not match(regex, prefix + line_extra_chars_title_snafu)
            assert not match(regex, prefix + line_unicode_title)

        def check_regex_without_key(regex, prefix=''):
            m = match(regex, prefix + line_title_key).groupdict()
            assert m['title'].strip() == 'Title Foo (example.org/123)'

            m = match(regex, prefix + line_key).groupdict()
            assert m['title'].strip() == '(example.org/123)'

            m = match(regex, prefix + line_title).groupdict()
            assert m['title'].strip() == 'Title Foo'

            m = match(regex, prefix + line_extra_chars_key_title).groupdict()
            assert m['title'].strip() == 'Title_foo (ICU) (example.org/123)'

            m = match(regex, prefix + line_extra_chars_title).groupdict()
            assert m['title'].strip() == 'Title-foo (ICU)'

            m = match(regex, prefix + line_extra_chars_title_snafu).groupdict()
            assert m['title'].strip() == 'Title_foo (I:CU)'

            m = match(regex, prefix + line_unicode_title_key).groupdict()
            assert m['title'].strip() == u'Titl\u00e9Foo (example.org/123)'

            m = match(regex, prefix + line_unicode_title).groupdict()
            assert m['title'].strip() == u'Titl\u00e9Foo'

            m = match(regex, prefix + line_unicode_key).groupdict()
            assert m['title'].strip() == u'(\u00e9xample.org/123)'

        # test unquoted base with key
        regex = mail_editor_.update_line_regexes[0][0]
        check_regex_with_key(regex)

        # test unquoted base without key. this set will not process subject
        # names-- that should be handled by the previous regex. this one should
        # only trigger if there is no subject name in an update line
        regex = mail_editor_.update_line_regexes[0][1]
        check_regex_without_key(regex)

        # test quoted base with key. this will only fire once both unquoted
        # regexes have fired and found nothing.
        regex = mail_editor_.update_line_regexes[1][0]
        check_regex_with_key(regex, '>> ')

        # test quoted base without key. this will fire after everything else
        regex = mail_editor_.update_line_regexes[1][1]
        check_regex_without_key(regex, '>> ')

    def check_for_correct_update(self, body, message):
        assert body.count('--- --- --- ---') == 2
        assert 'title_foo (example.org/123)\n' in body
        assert 'Email' in body and 'test@example.com' in body
        assert 'Commune' in body and 'foo@bar!' in body
        assert 'Available beds' in body and '18' in body
        assert 'Total beds' in body and '222' in body
        assert 'Can pick up patients' in body and 'Yes' in body
        assert '/help/email' in body
        assert 'update title_foo' not in body
        assert 'ERROR' not in message.subject()
        assert self.email == message.to_list()[0]
        assert 'haiti-updates@resource-finder.appspotmail.com' == message.sender()
