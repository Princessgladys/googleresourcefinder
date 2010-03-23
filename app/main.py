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

from utils import Handler, Redirect, get_latest_version, run, users
import access
import rendering

class Main(Handler):
    
    def get(self):
        auth = self.auth
        self.render('templates/map.html',
                    params=self.params,
                    authorization=auth and auth.description or 'anonymous',
                    #is_editor=access.check_user_role(auth,'editor','ht'),
                    is_editor=True,
                    #TODO(eyalf): should remove the assumption there is an email
                    user=auth and {'email': auth.email} or {'email': 'anonymous'} ,
                    loginout_url=(auth and users.create_logout_url('/') or
                                  users.create_login_url('/')),
                    loginout_text=(auth and _("Sign out") or _("Sign in")),
                    data=rendering.version_to_json(get_latest_version('ht')),
                    instance=self.request.host.split('.')[0])

if __name__ == '__main__':
    run([('/', Main)], debug=True)
