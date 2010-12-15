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

"""Generic handler for queueing tasks that call an external webhook."""

import urllib

from google.appengine.api.labs import taskqueue
from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

URL_PATH = '/tasks/external'


class External(webapp.RequestHandler):
    def post(self):
        urlfetch.fetch(self.request.get('url'), self.request.get('payload'),
                       self.request.get('method', 'POST'))


def add(external_url, external_params, method='POST'):
    """Queues a task to fetch an external URL."""
    external_payload = urllib.urlencode(external_params)
    taskqueue.add(url=URL_PATH, params={
        'url': external_url, 'payload': external_payload, 'method': method})


if __name__ == '__main__':
    run_wsgi_app(webapp.WSGIApplication([(URL_PATH, External)], debug=True))
