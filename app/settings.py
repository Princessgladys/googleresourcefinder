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

__author__ = 'pfritzsche@google.com (Phil Fritzsche)'

import logging
from operator import itemgetter

from google.appengine.api import users

import config
from model import Subject, Subscription
from utils import _, Handler, run

SETTINGS_PATH = 'templates/settings.html'

class Settings(Handler):

    def init(self):
        """Checks for logged-in user and gathers necessary information."""
        self.require_logged_in_user()
        if not self.account:
            #i18n: Error message for request missing subject name.
            raise ErrorMessage(404, _('Invalid or missing account e-mail.'))

    def get(self):
        self.init()

        subscriptions = Subscription.all().filter('user_email =',
                                                  self.account.email)
        subjects = []
        for subscription in subscriptions:
            subject = Subject.get_by_key_name(subscription.subject_name)
            subjects.append({
                'name': subscription.subject_name,
                'title': subject.get_value('title'),
                'frequency': subscription.frequency
            })
        subjects = sorted(subjects, key=itemgetter('title'))

        home_url = self.get_url('/')
        feedback_url = config.FEEDBACK_URLS_BY_LANG.get(self.params.lang,
                                                        config.DISCUSSION_BOARD)
        logout_url = users.create_logout_url(home_url)
        frequencies = [
            #i18n: Label for instant e-mail updates
            {'value': 'instant', 'trans': _('Instant')},
            #i18n: Label for daily e-mail updates
            {'value': 'daily', 'trans': _('Daily')},
            #i18n: Label for weekly e-mail updates
            {'value': 'weekly', 'trans': _('Weekly')},
            #i18n: Label for monthly e-mail updates
            {'value': 'monthly', 'trans': _('Monthly')}
        ]

        self.render(SETTINGS_PATH,
                    params=self.params,
                    settings=True,
                    authorization=self.user.email(),
                    home_url=home_url,
                    feedback_url=feedback_url,
                    loginout_url=logout_url,
                    #i18n: Link to sign out of the app
                    loginout_text=_('Sign out'),
                    frequencies=frequencies,
                    user_frequency=self.account.default_frequency,
                    locale=self.account.locale,
                    subjects=subjects,
                    user_email_format=self.account.email_format,
                    user=self.user,
                    subdomain=self.subdomain)

if __name__ == '__main__':
    run([('/settings', Settings)], debug=True)
