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

# TODO(shakusa) Issue 55: When we are ready to launch, set this to False
VIEW_AND_PRINT_REQUIRE_LOGIN = True

class Main(Handler):

    def get(self):
        if VIEW_AND_PRINT_REQUIRE_LOGIN:
            self.require_logged_in_user()

        user = self.user
        center = None
        if self.params.lat is not None and self.params.lon is not None:
            center = {'lat': self.params.lat, 'lon': self.params.lon}
        self.render('templates/map.html',
                    params=self.params,
                    authorization=user and user.email() or 'anonymous',
                    loginout_url=(user and users.create_logout_url('/') or
                                  users.create_login_url('/')),
                    #i18n: Link to sign out of the app
                    loginout_text=(user and _("Sign out")
                                   #i18n: Link to sign into the app
                                   or _("Sign in")),
                    data=rendering.version_to_json(get_latest_version('ht'),
                                                   hide_email=not user,
                                                   center=center,
                                                   radius=self.params.rad),
                    instance=self.request.host.split('.')[0])

if __name__ == '__main__':
    run([('/', Main)], debug=True)
