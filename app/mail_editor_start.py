# Copyright 2010 by Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Handles requests from a UI hook to get users started with email update."""

__author__ = 'shakusa@google.com'

import re

import cache
import mail_editor
import utils

from feedlib.errors import ErrorMessage
from feedlib.struct import Struct

EMAIL_PATTERN = re.compile(
    r'(?:^|\s)[-a-z0-9_.%+]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)',re.IGNORECASE)

def is_valid_email(email):
    """Basic validation for an email address,
    returns True if valid, False if invalid, None if empty string."""
    if not email:
        return None
    if EMAIL_PATTERN.match(email):
        return True

class MailEditorStart(utils.Handler):
    """Handler for /mail_editor_start, which is a UI hook to get
    users started with RF's email update feature.  The handler
    sends a template email for updating the provided facility
    to the provided address.

    Attributes:
        email: the email address to mail

    Methods:
        init(): handles initialization tasks for the class
        post(): responds to HTTP POST requests
    """

    def init(self):
        """Handles any initialization tasks for the class."""
        self.email = self.request.get('email')

    def post(self):
        """Responds to HTTP POST requests."""
        self.init()

        if not is_valid_email(self.email):
            #i18n: Error message for invalid email address
            self.write(_('Email address is invalid.'))
            return

        self.minimal_subject = cache.MINIMAL_SUBJECTS[
            self.subdomain].get(self.params.subject_name)
        if not self.minimal_subject:
            #i18n: Error message for invalid subject
            raise ErrorMessage(400, _('Invalid subject'))

        title = self.minimal_subject.get_value('title', '')
        min_subjects = mail_editor.get_min_subjects_by_lowercase_title(
            self.subdomain, title)
        if len(min_subjects) > 1:
            title = '%s (%s)' % (title, self.params.subject_name)

        to = '%s-updates@%s' % (self.subdomain, self.get_parent_domain()
                                .replace('appspot.com', 'appspotmail.com'))

        message = Struct()
        message.sender = self.email
        message.to = to
        message.subject = ('Resource Finder: Email update instructions for %s'
                           % title)

        editor = mail_editor.MailEditor()
        editor.request = self.request
        editor.init(message)
        editor.send_template_email(message, self.minimal_subject, title)

        self.write('OK')

if __name__ == '__main__':
    utils.run([('/mail_editor_start', MailEditorStart)], debug=True)
