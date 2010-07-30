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

import calendar
import csv
import datetime

import access
import bubble
import cache
from model import *
from utils import *

# Maps a SubjectType key name to a list of tuples, one per column.
# Each tuple has the column header and a lambda function that takes a
# subject and a report and returns the column value
COLUMNS_BY_SUBJECT_TYPE = {
    ('haiti', 'hospital'): [
        ('name', lambda f: f.get_value('title')),
        ('alt_name', lambda f: f.get_value('alt_title')),
        ('healthc_id', lambda f: f.get_value('healthc_id')),
        ('pcode', lambda f: f.get_value('pcode')),
        ('available_beds', lambda f: f.get_value('available_beds')),
        ('total_beds', lambda f: f.get_value('total_beds')),
        ('services', lambda f: f.get_value('services')),
        ('contact_name', lambda f: f.get_value('contact_name')),
        ('contact_phone', lambda f: f.get_value('phone')),
        ('contact_email', lambda f: f.get_value('email')),
        ('department', lambda f: f.get_value('department')),
        ('district', lambda f: f.get_value('district')),
        ('commune', lambda f: f.get_value('commune')),
        ('address', lambda f: f.get_value('address')),
        ('latitude', lambda f: (f.get_value('location') and
                                f.get_value('location').lat)),
        ('longitude', lambda f: (f.get_value('location') and
                                 f.get_value('location').lon)),
        ('organization', lambda f: f.get_value('organization')),
        ('organization_type', lambda f: f.get_value('organization_type')),
        ('category', lambda f: f.get_value('category')),
        ('construction', lambda f: f.get_value('construction')),
        ('damage', lambda f: f.get_value('damage')),
        ('operational_status', lambda f: f.get_value('operational_status')),
        ('comments', lambda f: f.get_value('comments')),
        ('reachable_by_road', lambda f: f.get_value('reachable_by_road')),
        ('can_pick_up_patients', lambda f: f.get_value('can_pick_up_patients')),
        ('region_id', lambda f: f.get_value('region_id')),
        ('district_id', lambda f: f.get_value('district_id')),
        ('commune_id', lambda f: f.get_value('commune_id')),
        ('commune_code', lambda f: f.get_value('commune_code')),
        ('sante_id', lambda f: f.get_value('sante_id')),
        ('entry_last_updated', lambda f: get_last_updated_time(f))
    ],
}

def get_last_updated_time(subject):
    subdomain, subject_name = split_key_name(subject)
    type_name = subject.type
    attribute_names = cache.SUBJECT_TYPES[subdomain][type_name].attribute_names
    value_info_extractor = bubble.VALUE_INFO_EXTRACTORS[subdomain][type_name]
    (special, general, details) = value_info_extractor.extract(
        subject, attribute_names)
    return max(detail.date for detail in details)

def short_date(date):
    return '%s %d' % (calendar.month_abbr[date.month], date.day)

def write_csv(out, subdomain, type_name):
    """Dump the attributes for all subjects of the given type
       in CSV format, with a row for each subject"""
    writer = csv.writer(out)

    subject_type = cache.SUBJECT_TYPES[subdomain][type_name]
    subjects = fetch_all(
        Subject.all_in_subdomain(subdomain).filter('type =', type_name))
    columns = COLUMNS_BY_SUBJECT_TYPE[(subdomain, type_name)]
    if columns:
        row = list(column[0] for column in columns)
    else:
        row = [type_name] + subject_type.attribute_names
    writer.writerow(row)

    # Write a row for each subject.
    for subject in sorted(subjects, key=lambda f: f.get_value('title')):
        if columns:
            row = []
            for column in columns:
                row.append(format(column[1](subject)))
        else:
            subdomain, subject_name = split_key_name(subject)
            row = [subject_name]
            for name in subject_type.attribute_names:
                value = get_value(subject, name)
                row.append(format(value))
        writer.writerow(row)

def format(value):
    """Format value in a way suitable for CSV export."""
    if isinstance(value, unicode):
        return value.encode('utf-8')
    if isinstance(value, str):
        return value.replace('\n', ' ')
    if isinstance(value, list):
        return ', '.join(value)
    if isinstance(value, datetime.datetime):
        return to_local_isotime(value.replace(microsecond=0))
    return value

class Export(Handler):
    def get(self):
        type_name = self.params.subject_type

        if type_name:
            # Construct a reasonable filename.
            timestamp = datetime.datetime.utcnow()
            filename = '%s.%s.csv' % (self.subdomain, type_name)
            self.response.headers['Content-Type'] = 'text/csv'
            self.response.headers['Content-Disposition'] = \
                'attachment; filename=' + filename

            # Write out the CSV data.
            write_csv(self.response.out, self.subdomain, type_name)
        else:
            self.write('<html><head>')
            self.write('<title>%s</title>' % to_unicode(_("Resource Finder")))
            self.write('<link rel=stylesheet href="static/style.css">')
            self.write('</head><body>')
            #i18n: Save a copy of the data in CSV format
            self.write('<h2>%s</h2>' % to_unicode(_("CSV Export")))
            self.write('<form>')
            self.write('<p>%s' % to_unicode(_(
                #i18n: Label for a selector to export data to CSV
                'Select subject type to export:')))
            self.write('<select name="subject_type">')
            for subject_type in SubjectType.all_in_subdomain(self.subdomain):
                # TODO(shakusa) SubjectType should have translated messages
                subdomain, type_name = split_key_name(subject_type)
                self.write('<option value="%s">%s</option>' %
                           (type_name, type_name))
            self.write('<p><input type=submit value="%s">' %
                #i18n: Button to export data to comma-separated-value format.
                to_unicode(_('Export CSV')))
            self.write('</form>')
            self.write('</body></html>')

if __name__ == '__main__':
    run([('/export', Export)], debug=True)
