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

import django.utils.translation
from google.appengine.api import mail
from google.appengine.api import users

import cache
import export_test
import mail_editor
from medium_test_case import MediumTestCase
from model import Account, Attribute, Subdomain, MinimalSubject, Subject
from model import SubjectType
from utils import db

SAMPLE_EMAIL_WORKING = '''UPDATE title_foo (haiti 123)
Available beds 18
Total beds 222
Email test@example.com
Commune foo@bar!
Can pick up patients yes'''

SAMPLE_EMAIL_AUTHENTICATION = '''nickname nickname_foo
affiliation affiliation_foo

UPDATE title_foo (haiti 123)
Available beds 18
Total beds 222
Email test@example.com
Commune foo@bar!
Can pick up patients yes'''

SAMPLE_EMAIL_BROKEN = '''UPDATE title_foo (haiti 123)
Available beds d
Total beds 222
Email test@example.com
Commune foo@bar!
Can pick up patients yes'''

SAMPLE_EMAIL_QUOTED = '''>> UPDATE title_foo (haiti 123)
>> Available beds 18
>> Total beds 222
>> Email test@example.com
>> Commune foo@bar!
>> Can pick up patients yes'''

SAMPLE_EMAIL_STOP = '''UPDATE title_foo (haiti 123)
Available beds 18
Total beds 222
Email test@example.com
Commune foo@bar!
--- --- --- ---
Can pick up patients yes'''

SAMPLE_EMAIL_MIXED = '''UPDATE title_foo (haiti 123)
Available beds 18
Total beds 222
Email test@example.com
Commune foo@bar!
Can pick up patients yes

>> UPDATE title_foo (haiti 123)
>> Available beds d
>> Total beds 222
>> Email test@example.com
>> Commune foo@bar!
>> Can pick up patients yes'''

sent_emails = []

def fake_send_email(self, original_message, updates, errors):
    global sent_emails
    sent_emails.append({
        'original_message': original_message,
        'updates': updates,
        'errors': errors
    })


class MailAlertsTest(MediumTestCase):
    def setUp(self):
        MediumTestCase.setUp(self)
        django.utils.translation.activate('en')
        cache.flush_all()
        self.time = datetime.datetime(2010, 06, 01)
        self.user = users.User('test@example.com')
        self.nickname = 'nickname_foo'
        self.affiliation = 'affiliation_foo'
        self.comment = 'comment_foo'
        self.description = 'test@example.com'
        self.account = Account(email=self.user.email(), actions=['*:*'],
                               locale='en', nickname=self.nickname,
                               affiliation=self.affiliation)
        self.subject = Subject(key_name='haiti:example.org/123',
                               type='hospital', author=self.user,
                               title__='title_foo', healthc_id__='123')
        self.minimal_subject = MinimalSubject(self.subject, type='hospital')
        attribute_names = export_test.STR_FIELDS + \
                          export_test.INT_FIELDS + \
                          export_test.BOOL_FIELDS.keys() + \
                          export_test.SELECT_FIELDS.keys()
        self.subject_type = SubjectType(key_name='haiti:hospital',
                                        attribute_names=attribute_names)
        self.subdomain = Subdomain(key_name='haiti')
        db.put([self.account, self.subject, self.subject_type,
                self.subdomain, self.minimal_subject])

        for field in export_test.STR_FIELDS:
            Attribute(key_name=field, type='str').put()
        for field in export_test.INT_FIELDS:
            Attribute(key_name=field, type='int').put()
        for field in export_test.BOOL_FIELDS:
            Attribute(key_name=field, type='bool').put()
        for field in export_test.SELECT_FIELDS:
            Attribute(key_name=field, type='choice').put()

    def tearDown(self):
        db.delete([self.account, self.subject, self.subject_type,
                   self.subdomain, self.minimal_subject])
        for attribute in Attribute.all():
            db.delete(attribute)

    def test_get_updates(self):
        """Confirm that get_updates() properly parses through a set of lines
        from an email message pertaining to a subject."""
        # test a simple, properly formatted email
        working_updates_results = [('available_beds', 18), ('total_beds', 222),
                                   ('email', 'test@example.com'),
                                   ('commune', 'foo@bar!'),
                                   ('can_pick_up_patients', True)]
        update_lines = SAMPLE_EMAIL_WORKING.split('\n')[1:]
        updates, errors, stop = mail_editor.get_updates(
            update_lines, self.subject, self.subject_type, False, [])
        assert updates == working_updates_results
        assert errors == []
        assert not stop

        # test a simple email with one malformed update
        update_lines = SAMPLE_EMAIL_BROKEN.split('\n')[1:]
        updates, errors, stop = mail_editor.get_updates(
            update_lines, self.subject, self.subject_type, False, [])
        assert updates == [('total_beds', 222),
                           ('email', 'test@example.com'),
                           ('commune', 'foo@bar!'),
                           ('can_pick_up_patients', True)]
        assert errors == [('"d" is not a valid value for available_beds',
                           'Available beds d')]
        assert not stop

        # test a simple correctly formed and quoted email
        update_lines = SAMPLE_EMAIL_QUOTED.split('\n')[1:]
        updates, errors, stop = mail_editor.get_updates(
            update_lines, self.subject, self.subject_type, True, [])
        assert updates == working_updates_results
        assert not errors and not stop

        # make sure that same email finds nothing when told it is not quoted
        updates, errors, stop = mail_editor.get_updates(
            update_lines, self.subject, self.subject_type, False, [])
        assert not updates and not errors and not stop

        # test a simple email with the stop delimeter in the middle
        update_lines = SAMPLE_EMAIL_STOP.split('\n')[1:]
        updates, errors, stop = mail_editor.get_updates(
            update_lines, self.subject, self.subject_type, False, [])
        assert updates == working_updates_results[:-1]
        assert not errors and stop

        # test an email with both quoted and non quoted regions
        update_lines = SAMPLE_EMAIL_MIXED.split('\n')[1:]
        updates, errors, stop = mail_editor.get_updates(
            update_lines, self.subject, self.subject_type, False, [])
        assert updates == working_updates_results
        assert not errors and not stop

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
            to='updates@resource-finder.appspotmail.com',
            subject='Resource Finder Updates',
            body=SAMPLE_EMAIL_WORKING)

        mail_editor_ = mail_editor.MailEditor()
        assert mail_editor_.authenticate(message)

        db.delete(self.account)
        assert not mail_editor_.authenticate(message)

    def test_mail_editor_is_authentication(self):
        """Confirm that is_authentication() identifies messages sent with
        authentication information for the user."""
        message = mail_editor.mail.EmailMessage(
            sender=self.account.email,
            to='updates@resource-finder.appspotmail.com',
            subject='Resource Finder Updates',
            html=SAMPLE_EMAIL_AUTHENTICATION)
        mail_editor_ = mail_editor.MailEditor()
        mail_editor_.account = None # is_authentication is always run after
                                    # authenticate, so it will always have
                                    # an account, though it may be None
        assert mail_editor_.is_authentication(message)

        message.html=SAMPLE_EMAIL_WORKING
        assert not mail_editor_.is_authentication(message)

    def test_mail_editor_receive(self):
        """Confirm that it receives and properly sends an email with the
        information from the received update."""
        self.sent_messages = []
        message = mail.InboundEmailMessage(
            sender=self.account.email,
            to='updates@resource-finder.appspotmail.com',
            subject='Resource Finder Updates',
            html=SAMPLE_EMAIL_WORKING,
            date='Wed, 04 Aug 2010 13:07:18 -0400')
        mail_editor_ = mail_editor.MailEditor()

        # check working update email
        mail_editor_.receive(message)
        body = self.sent_messages[0].textbody()
        assert len(self.sent_messages) == 1
        self.check_for_correct_update(body, self.sent_messages[0])

        # check broken email
        message.html = SAMPLE_EMAIL_BROKEN
        mail_editor_.receive(message)
        body = self.sent_messages[1].textbody()
        assert len(self.sent_messages) == 2
        assert 'ERROR' in self.sent_messages[1].subject()
        assert '"d" is not a valid value for available_beds' in body
        assert body.count('--- --- --- ---') == 2
        assert 'REFERENCE DOCUMENT' in body
        assert 'REFERENCE DOCUMENT @' not in body

        # check working quoted email
        message.html = SAMPLE_EMAIL_QUOTED
        mail_editor_.receive(message)
        body = self.sent_messages[2].textbody()
        assert len(self.sent_messages) == 3
        self.check_for_correct_update(body, self.sent_messages[2])

        # check working mixed email
        message.html = SAMPLE_EMAIL_MIXED
        mail_editor_.receive(message)
        body = self.sent_messages[3].textbody()
        assert len(self.sent_messages) == 4
        self.check_for_correct_update(body, self.sent_messages[3])

        db.delete(self.account)
        # check working but not authenticated email
        message.html = SAMPLE_EMAIL_WORKING
        mail_editor_.receive(message)
        body = self.sent_messages[4].textbody()
        assert len(self.sent_messages) == 5
        assert mail_editor_.need_authentication
        assert 'nickname' in body
        assert 'affiliation' in body
        assert 'pending updates' in body
        assert not Account.all().get()

        # send it an authentication email
        message.html = SAMPLE_EMAIL_AUTHENTICATION
        mail_editor_.receive(message)
        body = self.sent_messages[5].textbody()
        assert Account.all().get()
        assert len(self.sent_messages) == 6
        assert not mail_editor_.need_authentication
        self.check_for_correct_update(body, self.sent_messages[5])

    def test_mail_editor_process_email(self):
        """Confirms that process_email() returns a properly formatted structure
        of updates and errors, given the body of an email."""
        mail_editor_ = mail_editor.MailEditor()

        # check working email body
        updates, errors = mail_editor_.process_email(SAMPLE_EMAIL_WORKING)
        assert updates[0][0].key().name() == 'haiti:example.org/123'
        # updates[first_update][subject_data][attribute_#]
        assert 'available_beds' in updates[0][1][0]
        assert 'total_beds' in updates[0][1][1]
        assert 'email' in updates[0][1][2]
        assert 'commune' in updates[0][1][3]
        assert 'can_pick_up_patients' in updates[0][1][4]
        assert not errors

        # check broken email body
        updates, errors = mail_editor_.process_email(SAMPLE_EMAIL_BROKEN)
        assert updates[0][0].key().name() == 'haiti:example.org/123'
        assert 'Available beds d' in errors[0][1][0][1]
        assert len(updates[0][1]) == 4

        # check quoted email body
        updates, errors = mail_editor_.process_email(SAMPLE_EMAIL_QUOTED)
        assert updates[0][0].key().name() == 'haiti:example.org/123'
        assert 'available_beds' in updates[0][1][0]
        assert 'total_beds' in updates[0][1][1]
        assert 'email' in updates[0][1][2]
        assert 'commune' in updates[0][1][3]
        assert 'can_pick_up_patients' in updates[0][1][4]
        assert not errors

        # check mixed email body
        updates, errors = mail_editor_.process_email(SAMPLE_EMAIL_MIXED)
        assert updates[0][0].key().name() == 'haiti:example.org/123'
        assert 'available_beds' in updates[0][1][0]
        assert 'total_beds' in updates[0][1][1]
        assert 'email' in updates[0][1][2]
        assert 'commune' in updates[0][1][3]
        assert 'can_pick_up_patients' in updates[0][1][4]
        assert not errors

        # check stop delimeter'd body
        updates, errors = mail_editor_.process_email(SAMPLE_EMAIL_STOP)
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
        updates, errors = mail_editor_.process_email(SAMPLE_EMAIL_WORKING)
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
            to='updates@resource-finder.appspotmail.com',
            subject='Resource Finder Updates',
            html=SAMPLE_EMAIL_WORKING,
            date='Wed, 04 Aug 2010 13:07:18 -0400')
        mail_editor_ = mail_editor.MailEditor()
        mail_editor_.account = self.account
        mail_editor_.need_authentication = False
        updates, errors = mail_editor_.process_email(SAMPLE_EMAIL_WORKING)
        mail_editor_.send_email(message, updates, errors)

        # updates, no errors
        assert len(self.sent_messages) == 1
        body = self.sent_messages[0].textbody()
        self.check_for_correct_update(body, self.sent_messages[0])

        # updates, errors
        message.html = SAMPLE_EMAIL_BROKEN
        updates, errors = mail_editor_.process_email(SAMPLE_EMAIL_BROKEN)
        mail_editor_.send_email(message, updates, errors)
        assert len(self.sent_messages) == 2
        body = self.sent_messages[1].textbody()
        assert 'ERROR' in self.sent_messages[1].subject()
        assert 'UPDATE' in body
        assert 'REFERENCE DOCUMENT' in body
        assert 'REFERENCE DOCUMENT @' not in body

        mail_editor_.account = None
        mail_editor_.need_authentication = True
        db.delete(self.account)
        # need authentication
        message.html = SAMPLE_EMAIL_WORKING
        updates, errors = mail_editor_.process_email(SAMPLE_EMAIL_WORKING)
        mail_editor_.send_email(message, updates, errors)
        assert len(self.sent_messages) == 3
        body = self.sent_messages[2].textbody()
        assert 'ERROR' not in self.sent_messages[2].subject()
        assert 'nickname' in body
        assert 'affiliation' in body
        assert 'pending updates' in body

    def check_for_correct_update(self, body, message):
        assert body.count('--- --- --- ---') == 2
        assert 'title_foo (haiti 123)\n' in body
        assert 'Email' in body and 'test@example.com' in body
        assert 'Commune' in body and 'foo@bar!' in body
        assert 'Available beds' in body and '18' in body
        assert 'Total beds' in body and '222' in body
        assert 'Can pick up patients' in body and 'Yes' in body
        assert 'http://resource-finder.appspot.com/help/email' in body
        assert 'UPDATE' not in body
        assert 'ERROR' not in message.subject()
        assert self.user.email() == message.to_list()[0]
        assert 'updates@resource-finder.appspotmail.com' == message.sender()
