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

Handler for allowing a superuser to grant access using the permission scheme
provided in access.py
"""

import logging
import model
import utils
from utils import DateTime, ErrorMessage, Redirect
from utils import db, html_escape, users
from access import check_user_role
from access import Authorization


class GrantAccess(utils.Handler):
    def get(self):
        """ Shows all requests for waiting for approval"""

        self.require_user_role('superuser', self.params.cc)

        q = Authorization.all().filter('requested_roles !=', None)

        requests = []
        for auth in q.fetch(100):
          for ccrole in auth.requested_roles:
            cc, role = ccrole.split(':')
            if check_user_role(self.auth, 'superuser', cc):
              requests.append({'email': auth.email,
                               'requested_role': ccrole,
                               'key': auth.key()})

        self.render('templates/grant_access.html',
                    requests=requests,
                    params=self.params,
                    logout_url=users.create_logout_url('/'))

    def post(self):
        """ Shows all requests for waiting fro approval"""

        ccrole = self.request.get('ccrole')
        if not ccrole:
            raise ErrorMessage(404, 'missing ccrole (requested_role) params')
        cc, role = ccrole.split(':')

        self.require_user_role('superuser', cc)

        auth = Authorization.get(self.request.get('key'))
        if not auth:
            raise ErrorMessage(404, 'bad key given')

        #TODO(eyalf): define auth.display_name() or something
        name = auth.email
        if not ccrole in auth.requested_roles:
            #i18n: Error message
            raise ErrorMessage(404, _('No pending request for '
                                      '%(authorization_role)s by %(user)s')
                               % (ccrole, name))
        auth.requested_roles.remove(ccrole)
        action = self.request.get('action', 'deny')
        if action == 'approve':
            auth.user_roles.append(ccrole)
        auth.put()
        logging.info('%s request for %s was %s' % (auth.email,
                                                   ccrole,
                                                   action))

        if self.params.embed:
            if action == 'approve':
                self.write(
                    #i18n: Application for the given permission role approved
                    _('Request for becoming %(role)s was approved.') % role)
            else:
                self.write(
                    #i18n: Application for the given permission role denied
                    _('Request for becoming %(role)s was denied.') % role)
        else:
            raise Redirect('/grant_access')

if __name__ == '__main__':
    utils.run([('/grant_access', GrantAccess)], debug=True)
