# Copyright 2009-2010 by Ka-Ping Yee
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

"""
NOTE: THIS MODULE IS CURRENTLY UNUSED.

The current permissions scheme for resource finder is:
- Anyone (logged-in and non-logged-in users) can view and print
- Any logged-in user can edit data

THE CODE BELOW IS UNNECESSARY WITH THIS PERMISSION SCHEME

Handler for allowing a logged-in user to request access to view the app.
Requests can be handled by accounts with 'grant' action permission
in grant_access.py
"""

import model
import utils
from utils import DateTime, ErrorMessage, Redirect
from utils import db, html_escape, users, _


class RequestAccess(utils.Handler):
    def get(self):
        if not self.account:
            raise Redirect(users.create_login_url(self.request.uri))

        self.render('templates/request_access.html', action='edit');


    def post(self):
        if not self.account:
            raise Redirect(users.create_login_url(self.request.uri))
        action = self.params.action

        if action in self.account.actions:
            #i18n: Requested permission action has been previously granted
            message = _('You are already %(action)s' % {'action': action})
        elif action in self.account.requested_actions:
            message = _(
                #i18n: Requested permission action has already been granted
                'Your request for %(action)s is already registered'
                % {'action': action})
        else:
            self.account.requested_actions.append(action)
            #i18n: Requested permission action was registered
            message = _('Request for becoming %(action)s was registered.'
                        % {'action': action})
            self.account.put()

        if self.params.embed:
            self.write(message)
        else:
            raise Redirect('/')

if __name__ == '__main__':
    utils.run([('/request_access', RequestAccess)], debug=True)
