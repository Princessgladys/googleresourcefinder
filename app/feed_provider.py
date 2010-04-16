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

"""Handler for feed retrieval requests."""

from edxl_have import URI_PREFIXES
from feeds.feedutils import handle_entry_get, handle_feed_get
from utils import ErrorMessage, Handler, run


def get_feed_id(request, feed_name):
    return request.host_url + '/feeds/' + feed_name

class Feed(Handler):
    def get(self, feed_name):
        feed_id = get_feed_id(self.request, feed_name)
        handle_feed_get(self.request, self.response, feed_id, URI_PREFIXES)


class Entry(Handler):
    def get(self, feed_name, entry_id):
        feed_id = get_feed_id(self.request, feed_name)
        try:
            handle_entry_get(
                self.request, self.response, feed_id, entry_id, URI_PREFIXES)
        except EntryNotFoundError:
            raise ErrorMessage(404, _('No such entry'))


if __name__ == '__main__':
    run([('/feeds/([^/]+)', Feed),
         ('/feeds/([^/]+)/([^/]+)', Entry)], debug=True)
