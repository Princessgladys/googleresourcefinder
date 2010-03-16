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

from utils import Handler, run
import atom
import edxl_have
import records
import time_formats
from crypto import sign, verify


class Feed(Handler):
    def check_request_etag(self):
        """Chooses limit and after_arrival_time based on request headers."""
        # TODO: If records A and B are written to different data centers,
        # and clock skew causes B to be written with an arrival_time earlier
        # than A, after a subscriber has previously fetched the feed with A
        # as the latest item, then B will be missed on the next fetch.
        if 'if-none-match' in self.request.headers:
            try:
                etag = self.request.headers['If-None-Match'].strip().strip('"')
                timestamp, signature = etag.split('/')
                if verify('etag_key', timestamp, signature):
                    return etag, None, time_formats.from_rfc3339(timestamp)
            except (KeyError, ValueError):
                pass
        return None, 20, None

    def create_response_etag(self, latest):
        """Determines ETag response header for the given records."""
        arrival_time = latest and latest[0].arrival_time or 0
        timestamp = time_formats.to_rfc3339(arrival_time)
        return '"' + timestamp + '/' + sign('etag_key', timestamp) + '"'

    def get(self, feed):
        """Produces the Atom feed of entries stored for the specified feed."""
        etag, limit, after_arrival_time = self.check_request_etag()
        latest = records.get_latest_arrived(feed, limit, after_arrival_time)

        self.response.headers['Content-Type'] = 'application/atom+xml'
        if latest:  # deliver the new entries
            self.response.headers['ETag'] = self.create_response_etag(latest)
            atom.write_feed(self, latest, edxl_have.URI_PREFIXES)
        elif etag:  # If-None-Match was specified, and there was nothing new
            self.response.set_status(304)
            self.response.headers['ETag'] = '"' + etag + '"'
        else:  # there are no entries in this feed
            atom.write_feed(self, latest, edxl_have.URI_PREFIXES)


class Entry(Handler):
    def get(self, feed, entry):
        """Produces the Atom entry for the specified entry."""
        try:
            id = int(entry)
        except ValueError:
            raise ErrorMessage(404, 'No such entry')
        record = records.Record.get_by_id(id)
        if not record or record.feed != feed:
            raise ErrorMessage(404, 'No such entry')

        self.response.headers['Content-Type'] = 'application/atom+xml'
        self.response.headers['Last-Modified'] = \
            time_formats.to_rfc1123(record.arrival_time)
        atom.write_entry(self, record)


if __name__ == '__main__':
    run([(r'/feeds/([^/]+)', Feed),
         (r'/feeds/([^/]+)/([^/]+)', Entry)])
