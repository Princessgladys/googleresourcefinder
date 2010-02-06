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

from utils import *
from html import *

class Load(Handler):
    def get(self):
        options = []
        for country in Country.all():
            cc = country.key().name()
            version = get_latest_version(cc)
            if version:
                description = '#%s (%s)' % (
                    version.key().id(), to_isotime(version.timestamp))
            else:
                description = '(no data)'
            options.append('<option value="%s">%s %s</option>' % (
                cc, country.name, description))
        self.render('templates/load.html', cc_options=''.join(options))

    def post(self):
        loader = __import__(self.request.get('loader'))
        cc = self.request.get('cc')
        url = self.request.get('url')
        payload = self.request.get('payload') or None
        logging.info('load.py: loader=%r, cc=%r, url=%r, payload=%r' %
                     (self.request.get('loader'), cc, url, payload))

        latest_version = get_latest_version(cc)
        if latest_version:
            base_version = get_base(latest_version)
            logging.info('load.py: comparing to %r, base %r, dump %r' %
                         (latest_version, base_version, base_version.dump))
            base_data = get_base(base_version.dump).data
        else:
            base_data = None
        dump = fetch(cc, url, payload, base_data)

        if dump:
            try:
                version = db.run_in_transaction(load, loader, dump)
                logging.info('load.py: loaded %r as %r' % (dump, version))
            except:
                logging.exception('load.py: loading failed for %r' % dump)
        else:
            version = Version(base_version.parent(), base=base_version)
            version.put()
            logging.info('load.py: added %r with base %r' %
                         (version, base_version))

        # Only redirect if invoked by form submission, not cron or taskqueue.
        if self.request.get('submit'):
            self.redirect('/dump?cc=' + cc)

if __name__ == '__main__':
    run([('/load', Load)], debug=True)
