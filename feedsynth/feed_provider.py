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

from feeds.feedutils import STATUS_NS, notify_hub
from feeds.feedutils import handle_entry_get, handle_feed_get, handle_feed_post
from feeds.records import create_record
import sys, cgitb


URI_PREFIXES = {STATUS_NS: 'status',
                'http://schemas.google.com/spreadsheets/2006': 'gs'}


class Feed(webapp.RequestHandler):
    def get(self):
        handle_feed_get(self.request, self.response, URI_PREFIXES)

    def post(self):
        handle_feed_post(self.request, self.response, self.request.uri)

    def handle_exception(self, exception, debug_mode):
        """Handles an exception thrown by a handler method."""
        self.error(500)
        self.response.clear()
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(cgitb.html(sys.exc_info()))


class Entry(webapp.RequestHandler):
    def get(self):
        handle_entry_get(self.request, self.response, URI_PREFIXES)


if __name__ == '__main__':
    run_wsgi_app(webapp.WSGIApplication([
        (r'/feeds/\w+', Feed),
        (r'/feeds/\w+/\d+', Entry)
    ]))
