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

"""Tests for mail_editor_start.py."""

import django.utils.translation
import webob
from google.appengine.api import users
from google.appengine.ext import db, webapp
from nose.tools import assert_raises

import cache
import export_test
import mail_editor_start
from feedlib.errors import ErrorMessage
from feedlib.xml_utils import Struct
from medium_test_case import MediumTestCase
from model import Account, Attribute, MailUpdateText, Message, MinimalSubject
from model import Subdomain, Subject, SubjectType
from setup import setup_mail_update_texts, setup_subdomains, setup_subject_types
from utils import db, urlencode

class MailEditorStartTest(MediumTestCase):
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
                               title__='title_foo', healthc_id__='123',
                               services__=['X_RAY'])
        self.ms = MinimalSubject.create(self.subject)
        self.ms.set_attribute('title', 'title_foo')
        attribute_names = export_test.STR_FIELDS
        self.subject_type = SubjectType(key_name='haiti:hospital',
                                        attribute_names=attribute_names)
        self.subdomain = Subdomain(key_name='haiti')
        db.put([self.account, self.subject, self.subject_type, self.subdomain,
                self.ms])

        for field in export_test.STR_FIELDS:
            Attribute(key_name=field, type='str').put()
        Message(ns='attribute_name', en='Email', name='email').put()
        setup_mail_update_texts()

    def tearDown(self):
        db.delete([self.account, self.subject, self.subject_type,
                   self.subdomain, self.ms])
        for attribute in Attribute.all():
            db.delete(attribute)
        for attr_map in MailUpdateText.all():
            db.delete(attr_map)
        for message in Message.all():
            db.delete(message)

    def test_post(self):
        """Confirms that mail_editor_start sends emails as expected."""
        handler = self.simulate_request('/mail_editor_start?' + urlencode({
            'email': self.email, 'subject_name': self.subject.get_name(),
            'subdomain': self.subdomain.key().name()}))

        self.sent_messages = []
        handler.post()
        assert 'OK' == handler.response.out.getvalue()

        assert len(self.sent_messages) == 1
        message = self.sent_messages[0]
        assert message.to_list()[0] == self.email
        assert message.sender() == (
            "haiti-updates@resource-finder.appspotmail.com")
        assert message.subject() == (
            "Resource Finder: Email update instructions for title_foo")
        assert "update title_foo (example.org/123)" in message.textbody()

    def test_post_no_account(self):
        """Confirms that mail_editor_start sends emails as expected
        when the account doesn't exist."""
        no_account_email = 'a' + self.email
        handler = self.simulate_request('/mail_editor_start?' + urlencode({
            'email': no_account_email, 'subject_name': self.subject.get_name(),
            'subdomain': self.subdomain.key().name()}))

        self.sent_messages = []
        handler.post()
        assert 'OK' == handler.response.out.getvalue()

        assert len(self.sent_messages) == 1
        message = self.sent_messages[0]
        assert message.to_list()[0] == no_account_email
        assert message.sender() == (
            "haiti-updates@resource-finder.appspotmail.com")
        assert message.subject() == (
            "Resource Finder: Email update instructions for title_foo")
        assert "update title_foo (example.org/123)" in message.textbody()

    def test_invalid_subject(self):
        """Confirms mail_editor_start raises an exception for invalid
        subject."""
        handler = self.simulate_request('/mail_editor_start?' + urlencode({
            'email': self.email, 'subject_name': '',
            'subdomain': self.subdomain.key().name()}))
        assert_raises(ErrorMessage, handler.post)

    def test_invalid_email(self):
        """Confirms that mail_editor_start sends an error message when it
        receives an invalid email."""
        handler = self.simulate_request('/mail_editor_start?' + urlencode({
            'email': 'foo', 'subject_name': self.subject.get_name(),
            'subdomain': self.subdomain.key().name()}))
        handler.post()
        assert 'OK' != handler.response.out.getvalue()

    def test_validate_email(self):
        """Confirms the behavior of is_valid_email."""
        assert mail_editor_start.is_valid_email('test%123.E5+test@example.com')
        assert not mail_editor_start.is_valid_email('test')
        assert not mail_editor_start.is_valid_email('')
        assert not mail_editor_start.is_valid_email(None)

    def simulate_request(self, path):
        request = webapp.Request(webob.Request.blank(path).environ)
        request.headers['Host'] = 'resource-finder.appspot.com'
        response = webapp.Response()
        handler = mail_editor_start.MailEditorStart()
        handler.initialize(request, response, self.user)
        return handler
