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

"""Internal task to add an entry to the delta feed."""

from feedlib import report_feeds, xml_utils
import row_utils
from utils import Handler, run, url_unpickle


class AddDeltaEntry(Handler):
    def post(self):
        user_email = self.request.get('user_email')
        author_uri = user_email and 'mailto:' + user_email or ''
        subject_name = self.request.get('subject_name')
        observed = url_unpickle(self.request.get('observed'))
        changes = url_unpickle(self.request.get('changed_data'))
        type_name = xml_utils.qualify(report_feeds.REPORT_NS, 'row')
        row = xml_utils.create_element(type_name)
        for name in changes:
            row.append(xml_utils.create_element(
                (report_feeds.SPREADSHEETS_NS, 'field'),
                {'name': name},
                row_utils.serialize(name, changes[name]['new_value'])))
        report_feeds.ReportEntry.create_original(
            self.subdomain + '/delta', '', author_uri,
            subject_name, observed, type_name, xml_utils.serialize(row)
        ).put()


if __name__ == '__main__':
    run([('/tasks/add_delta_entry', AddDeltaEntry)], debug=True)
