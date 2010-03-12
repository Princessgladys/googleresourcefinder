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

import model
import utils
from utils import DateTime, ErrorMessage, Redirect
from utils import db, get_message, html_escape, users
from access import check_user_role
from access import Authorization


class RequestAccess(utils.Handler):
    def post(self):
        if not self.auth:
            raise Redirect(users.create_login_url(self.request.uri))
        role = "%s:%s" % (self.params.cc, self.params.role)
        if not role in self.auth.user_roles:
            self.auth.requested_roles.append(role)
            self.auth.put()
        
        if self.params.embed:
            self.write('Request for becoming %s was registered.' % role)
        else:
            raise Redirect('/')

if __name__ == '__main__':
    utils.run([('/request_access', RequestAccess)], debug=True)
