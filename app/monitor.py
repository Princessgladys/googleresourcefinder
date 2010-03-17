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

"""Handler for notifying JavaScript of changes."""

from model import Report
from utils import get_latest_version, Handler, run
import datetime
import time


class Monitor(Handler):
    def get(self):
        version = get_latest_version('ht')
        start = time.time()
        min_time = datetime.datetime.utcnow()
        self.response.headers['Content-Type'] = 'text/plain'
        while time.time() < start + 20:
            report = Report.all().ancestor(version).order(
                '-timestamp').filter('timestamp >=', min_time).get()
            if report:
                for name in ['patient_capacity', 'patient_count']:
                    if hasattr(report, name):
                        self.write('''%s %s %r''' % (report.facility_name,
                            name, getattr(report, name)))
                        break


if __name__ == '__main__':
    run([('/monitor', Monitor)], debug=True)
