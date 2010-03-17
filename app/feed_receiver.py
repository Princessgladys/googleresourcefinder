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

"""Handler for feed posting requests."""

from edxl_have import Hospital, URI_PREFIXES
from feeds import handle_feed_post
from model import Report
from utils import ErrorMessage, Handler, run
import datetime
import edxl_have_record  # register the EDXL-HAVE record type
import xmlutils

def datetime_to_date(dt):
    return datetime.date.fromordinal(dt.toordinal())


class Incoming(Handler):
    def post(self, token):
        records = handle_feed_post(self.request, self.response)

        from utils import get_latest_version
        import sys

        version = get_latest_version('ht')
        for record in records:
            hospital = Hospital.from_element(xmlutils.parse(record.content))
            if 'BedCapacity' in hospital:
                Report(version, facility_name=record.record_id,
                       patient_capacity=hospital['BedCapacity'],
                       date=datetime_to_date(record.observation_time)).put()


if __name__ == '__main__':
    run([('/incoming/([^/]+)', Incoming)], debug=True)
