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

import logging
import pickle
from edxl_have import URI_PREFIXES, serialize
from feeds.feedutils import handle_entry_get, handle_feed_get, notify_hub
from feeds.records import create_record
from utils import ErrorMessage, Handler, run, taskqueue, _


def get_feed_id(request, feed_name):
    return request.host_url + '/feeds/' + feed_name


def schedule_add_record(request, user, facility,
                        changed_attributes_dict, observed_time):
    """Enqueue a task to create a record."""
    edxl_change = serialize(changed_attributes_dict)
    record = create_record(
        get_feed_id(request, 'delta'),
        user.email(),
        '', # title
        facility.key().name(), # subject_id
        observed_time,
        edxl_change)

    taskqueue.add(url='/tasks/add_feed_record',
        payload=pickle.dumps(record),
        transactional=True)


class Feed(Handler):
    def get(self, feed_name):
        feed_id = get_feed_id(self.request, feed_name)
        handle_feed_get(self.request, self.response, feed_id, URI_PREFIXES)


class Entry(Handler):
    def get(self, feed_name, entry_id):
        feed_id = get_feed_id(self.request, feed_name)
        handle_entry_get(
            self.request, self.response, feed_id, entry_id, URI_PREFIXES)


class AddRecord(Handler):
    def post(self):
        # todo: decide if idempotence here is required
        record = pickle.loads(self.request.body)
        record.put()
        notify_hub(record.feed_id)


if __name__ == '__main__':
    run([('/feeds/([^/]+)', Feed),
         ('/feeds/([^/]+)/([^/]+)', Entry),
         ('/tasks/add_feed_record', AddRecord),
         ], debug=True)
