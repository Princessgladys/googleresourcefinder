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
from edxl_have import URI_PREFIXES, Hospital
from feeds.feedutils import handle_entry_get, handle_feed_get, notify_hub
from feeds.records import create_record
from utils import ErrorMessage, Handler, run, taskqueue, _


def schedule_add_record(request, user, subject,
                        changed_attributes_dict, observed_time):
    """Enqueue a task to create a record."""
    record = create_record(
        request.host_url + '/feeds/delta',
        user.email(),
        '', # title
        subject.key().name(), # subject_id
        observed_time,
        Hospital.to_element(changed_attributes_dict))

    taskqueue.add(url='/tasks/add_feed_record',
        payload=pickle.dumps(record),
        transactional=True)


class Feed(Handler):
    def get(self):
        handle_feed_get(self.request, self.response, URI_PREFIXES)


class Entry(Handler):
    def get(self):
        handle_entry_get(self.request, self.response, URI_PREFIXES)


class AddRecord(Handler):
    def post(self):
        # todo: decide if idempotence here is required
        record = pickle.loads(self.request.body)
        record.put()
        notify_hub(record.feed_id)


if __name__ == '__main__':
    run([(r'/feeds/\w+', Feed),
         (r'/feeds/\w+/\d+', Entry),
         ('/tasks/add_feed_record', AddRecord),
         ], debug=True)
