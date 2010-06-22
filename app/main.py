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

from utils import Handler, Redirect, get_secret, run, users, _
import access
import cache
import rendering

# We use a Secret in the db to determine whether or not the app should be
# configured to require login to view and 'editor' role to edit. Whitelists
# are on by default. To allow anyone to view and logged-in users to edit, run
# Secret(key_name='use_whitelists', value='FALSE').put() in a console
USE_WHITELISTS = get_secret('use_whitelists') != 'FALSE'

def get_export_link():
    """If only one subject type, return the direct download link,
    otherwise return a link to the download page"""
    link = '/export'
    if len(cache.SUBJECT_TYPES) > 1:
        # The /export page can handle rendering multiple subject types
        return link
    # Shortcut to bypass /export when we have only one subject type
    return link + '?subject_type=%s' % cache.SUBJECT_TYPES.keys()[0]

class Main(Handler):

    def get(self):
        if USE_WHITELISTS:
            self.require_logged_in_user()

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
                    data=rendering.render_json(center, self.params.rad),
                    export_link=get_export_link(),
                    instance=self.request.host.split('.')[0])

if __name__ == '__main__':
    run([('/', Main)], debug=True)
