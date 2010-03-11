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

import logging
import model
import utils
from utils import DateTime, ErrorMessage, Redirect
from utils import db, get_message, html_escape, users
from access import check_user_role
from access import Authorization


class ProcessRoleRequest(utils.Handler):

    def post(self):
        """ Shows all requests for waiting fro approval"""
        if not self.auth:
            raise Redirect(users.create_login_url(self.request.uri))

        ccrole = self.request.get('ccrole')
        if not ccrole:
          raise ErrorMessage(404,'missing ccrole (requested_role) params')
        cc,role = ccrole.split(':')
        if not check_user_role(self.auth, 'superuser', cc):
            raise ErrorMessage(403, 'Unauthorized user.')

        auth = Authorization.get(self.request.get('key'))
        if not auth:
          raise ErrorMessage(404,'bad key given')
        
        if not ccrole in auth.requested_roles:
          raise ErrorMessage(404,"request doesn't exists %s %s"%(auth.email,
                                                                 ccrole))
        auth.requested_roles.remove(ccrole)
        action = 'deny'
        if self.request.get('action') == 'approve':
          auth.user_roles.append(ccrole)
          action = 'approve'
        auth.put()
        logging.info('%s request for %s was %s'%(auth.email,
                                                 ccrole,
                                                 action))

        if self.params.embed:
            self.write('Request for becoming %s was %s.'%(role,action))
        else:
            raise Redirect('/request_role')

if __name__ == '__main__':
    utils.run([('/process_role_request', ProcessRoleRequest)], debug=True)
