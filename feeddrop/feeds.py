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

"""Handler for feed posting and retrieval."""

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import config
from feedlib import report_feeds


class HttpsRequestHandler(webapp.RequestHandler):
    def initialize(self, request, response, user_for_test=None):
        webapp.RequestHandler.initialize(self, request, response)
        if request.scheme != 'https':
            self.error(403)
            self.response.out.write('HTTPS is required.')
            self.get = lambda *args: None
            self.post = lambda *args: None


class Feed(HttpsRequestHandler):
    def get(self, feed_name):
        """Emits the entries in the specified feed."""
        report_feeds.handle_feed_get(
            self.request, self.response, feed_name, config.get('hub_url'))

    def post(self, feed_name):
        """Stores the posted entries on the specified feed."""
        report_feeds.handle_feed_post(
            self.request, self.response, feed_name, config.get('hub_url'),
            store_as_original=True)


class Entry(HttpsRequestHandler):
    def get(self, feed_name, entry_key):
        """Emits a single entry of the specified feed."""
        report_feeds.handle_entry_get(self.request, self.response, feed_name)


if __name__ == '__main__':
    run_wsgi_app(webapp.WSGIApplication([
        (r'/feeds/(\w+)', Feed),
        (r'/feeds/(\w+)/(\d+)', Entry)
    ]))
