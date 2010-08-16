# Copyright 2009-2010 by Google Inc.
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

"""Handles various limited-use administrative tasks."""

__author__ = 'pfritzsche@google.com'

import access
import cache
import logging
import model
import utils
from utils import db

class Purge(utils.Handler):
    """Handler for /purge. Used to carry out administrative tasks.

    Attributes:
        action: the specific action to be taken by the class

    Methods:
        init(): handles initialization tasks for the class
        post(): responds to HTTP POST requests
        purge_subject(): purges a subject from the datastore
    """

    def init(self):
        """Handles any initialization tasks for the class."""
        self.require_logged_in_user()
        self.action = self.request.get('action')

    def post(self):
        """Responds to HTTP POST requests. Reacts based on self.action."""
        self.init()
        self.purge_subject()

    def purge_subject(self):
        """Using the supplied subdomain and subject name from the user, removes
        the subject and associated minimal subject from the datastore. Reports
        are left in the database as a failsafe against accidental deletions."""
        subdomain = self.request.get('subdomain')
        subject_name = self.request.get('subject_name')

        # deletion of subject and minimal subject happens here 
        def work():
            subject = model.Subject.get(subdomain, subject_name)
            if subject:
                model.Subject.delete_complete(subject)
                logging.info('admin.py: %s deleted subject with name %s' %
                             (self.account.email, subject_name))
                cache.MINIMAL_SUBJECTS[subdomain].flush()
                cache.JSON[subdomain].flush()

        if access.check_action_permitted(self.account, subdomain, 'purge'):
            db.run_in_transaction(work)

if __name__ == '__main__':
    utils.run([('/purge', Purge)], debug=True)
