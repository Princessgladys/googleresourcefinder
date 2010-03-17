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

        version = get_latest_version('ht')
        for record in records:
            hospital = Hospital.from_element(xmlutils.parse(record.content))
            last_report = Report.all().ancestor(version).filter(
                'facility_name =', record.record_id).get()
            report = Report(version, facility_name=record.record_id)
            if last_report and hasattr(last_report, 'patient_capacity'):
                report.patient_capacity = last_report.patient_capacity
            if last_report and hasattr(last_report, 'patient_count'):
                report.patient_count = last_report.patient_count

            report.date = datetime_to_date(record.observation_time)
            if 'patient_capacity' in hospital:
                report.patient_capacity = hospital['patient_capacity']
            if 'patient_count' in hospital:
                report.patient_count = hospital['patient_count']
            report.put()

if __name__ == '__main__':
    run([('/incoming/([^/]+)', Incoming)], debug=True)
