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

from google.appengine.api import users
from utils import _
import access
import cache
import model
import rendering
import utils


class Main(utils.Handler):
    def get(self):
        if not self.subdomain:
            # Get the list of available subdomains.
            names = [s.key().name() for s in model.Subdomain.all()]

            # If there's only one subdomain, go straight there.
            if len(names) == 1:
                raise utils.Redirect(self.get_subdomain_root(names[0]))

            # Show the menu of available subdomains.
            self.render('templates/subdomain_menu.html', subdomains=[
                utils.Struct(name=name, url=self.get_subdomain_root(name))
                for name in names])
            return

        # Need 'view' permission to see the main page.
        self.require_action_permitted('view')

        user = self.user
        center = None
        if self.params.lat is not None and self.params.lon is not None:
            center = {'lat': self.params.lat, 'lon': self.params.lon}
        home_url = self.get_url('/')
        login_url = users.create_login_url(home_url)
        logout_url = users.create_logout_url(home_url)
        self.render('templates/map.html',
                    params=self.params,
                    #i18n: a user with no identity
                    authorization=user and user.email() or _('anonymous'),
                    loginout_url=user and logout_url or login_url,
                    #i18n: Link to sign out of the app
                    loginout_text=(user and _('Sign out')
                                   #i18n: Link to sign into the app
                                   or _('Sign in')),
                    data=rendering.render_json(
                        self.subdomain, center, self.params.rad),
                    home_url=home_url,
                    export_url=self.get_export_url(),
                    print_url=self.get_url('/?print=yes'),
                    bubble_url=self.get_url('/bubble'),
                    edit_url=self.get_url('/edit',
                                          subject_name=self.params.subject_name,
                                          embed='yes'),
                    subdomain=self.subdomain)

    def get_export_url(self):
        """If only one subject type, return the direct download link URL,
        otherwise return a link to the download page"""
        types = cache.SUBJECT_TYPES[self.subdomain].values()
        if len(types) == 1:
            # Shortcut to bypass /export when we have only one subject type
            subdomain, type_name = utils.split_key_name(types[0])
            return self.get_url('/export', subject_type=type_name)
        else:
            # The /export page can handle rendering multiple subject types
            return self.get_url('/export')


if __name__ == '__main__':
    utils.run([('/', Main)], debug=True)
