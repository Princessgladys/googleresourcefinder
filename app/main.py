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

from model import FacilityType
from utils import Handler, Redirect, get_latest_version, run, users, _
import access
import rendering

# TODO(shakusa) Issue 55: When we are ready to launch, set this to False
VIEW_AND_PRINT_REQUIRE_LOGIN = True

def get_export_link(version):
    """If only one facility type, return the direct download link,
    otherwise return a link to the download page"""
    link = '/export'
    facility_type = None
    for ftype in FacilityType.all().ancestor(version):
        if facility_type is not None:
            # We have more than one facility type, just redirect to the /export
            # page
            return link
        facility_type = ftype.key().name()
    cc = version.parent().key().name()
    return link + '?cc=%s&facility_type=%s' % (cc, facility_type)

class Main(Handler):

    def get(self):
        if VIEW_AND_PRINT_REQUIRE_LOGIN:
            self.require_logged_in_user()

        version = get_latest_version('ht')
        user = self.user
        center = None
        if self.params.lat is not None and self.params.lon is not None:
            center = {'lat': self.params.lat, 'lon': self.params.lon}
        self.render('templates/map.html',
                    params=self.params,
                    #i18n: a user with no identity
                    authorization=user and user.email() or _('anonymous'),
                    loginout_url=(user and users.create_logout_url('/') or
                                  users.create_login_url('/')),
                    #i18n: Link to sign out of the app
                    loginout_text=(user and _('Sign out')
                                   #i18n: Link to sign into the app
                                   or _('Sign in')),
                    data=rendering.version_to_json(version,
                                                   hide_email=not user,
                                                   center=center,
                                                   radius=self.params.rad),
                    export_link=get_export_link(version),
                    instance=self.request.host.split('.')[0])

if __name__ == '__main__':
    run([('/', Main)], debug=True)
