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

Handler for allowing an Account with 'grant' permission to grant access using
the permission scheme provided in access.py
"""

import logging
import model
import utils
from utils import DateTime, ErrorMessage, Redirect
from utils import db, html_escape, users, _
from access import check_action_permitted


class GrantAccess(utils.Handler):
    def get(self):
        """ Shows all requests for waiting for approval"""

        self.require_action_permitted('grant')

        q = model.Account.all().filter('requested_actions !=', None)

        requests = []
        for account in q.fetch(100):
          for action in account.requested_actions:
              if check_action_permitted(self.account, 'grant'):
                  requests.append({'email': account.email,
                                   'requested_action': action,
                                   'key': account.key()})

        self.render('templates/grant_access.html',
                    requests=requests,
                    params=self.params,
                    logout_url=users.create_logout_url('/'))

    def post(self):
        """ Shows all requests for waiting for approval"""

        action = self.request.get('action')
        if not action:
            raise ErrorMessage(404, 'missing action (requested_action) params')

        self.require_action_permitted('grant')

        account = model.Account.get(self.request.get('key'))
        if not account:
            raise ErrorMessage(404, 'bad key given')

        #TODO(eyalf): define account.display_name() or something
        name = account.email
        if not action in account.requested_actions:
            #i18n: Error message
            raise ErrorMessage(404, _('No pending request for '
                                      '%(account_action)s by %(user)s')
                               % (action, name))
        account.requested_actions.remove(action)
        grant = self.request.get('grant', 'deny')
        if grant == 'approve':
            account.actions.append(action)
        account.put()
        logging.info('%s request for %s was %s' % (account.email,
                                                   action,
                                                   grant))

        if self.params.embed:
            if grant == 'approve':
                self.write(
                    #i18n: Application for the given permission action approved
                    _('Request for becoming %(action)s was approved.') % action)
            else:
                self.write(
                    #i18n: Application for the given permission action denied
                    _('Request for becoming %(action)s was denied.') % action)
        else:
            raise Redirect('/grant_access')

if __name__ == '__main__':
    utils.run([('/grant_access', GrantAccess)], debug=True)
