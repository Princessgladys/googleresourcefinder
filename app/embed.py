# Copyright 2010 Google Inc.
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

import utils
from feeds.errors import Redirect

class Embed(utils.Handler):
    def get(self):
        host = 'http://%s' % self.request.headers['Host']
        if not self.subdomain:
            raise Redirect('/')
        locale = utils.get_locale()
        embed_url = self.get_url('/embed', subdomain=self.subdomain)
        iframe_url = '%s%s' % (host, self.get_url(
            '/', iframe='yes', subdomain=self.subdomain, lang=locale))
        self.render('locale/%s/embed.html' % locale,
                    params=self.params,
                    embed_url=embed_url,
                    iframe_url=iframe_url,
                    home_url=self.get_subdomain_root(self.subdomain))

if __name__ == '__main__':
    utils.run([('/embed', Embed)], debug=True)
