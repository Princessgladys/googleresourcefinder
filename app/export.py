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

from model import *
from utils import *
import access
import calendar
import csv
import datetime

# Maps a FacilityType key name to a list of tuples, one per column.
# Each tuple has the column header and a lambda function that takes a
# facility and a report and returns the column value
COLUMNS_BY_FACILITY_TYPE = {
    'hospital': [
        ('facility_name', lambda f: get_value(f, 'title')),
        ('alt_facility_name', lambda f: get_value(f, 'alt_title')),
        ('facility_healthc_id', lambda f: get_value(f, 'healthc_id')),
        ('facility_pcode', lambda f: re.sub(r'.*\.\.(.*)', r'\1',
                                            f.key().name())),
        ('available_beds', lambda f: get_value(f, 'available_beds')),
        ('total_beds', lambda f: get_value(f, 'total_beds')),
        ('services', lambda f: get_value(f, 'services')),
        ('contact_name', lambda f: get_value(f, 'contact_name')),
        ('contact_phone', lambda f: get_value(f, 'phone')),
        ('contact_email', lambda f: get_value(f, 'email')),
        ('department', lambda f: get_value(f, 'departemen')),
        ('district', lambda f: get_value(f, 'district')),
        ('commune', lambda f: get_value(f, 'commune')),
        ('address', lambda f: get_value(f, 'address')),
        ('latitude', lambda f: (get_value(f, 'location') and
                                get_value(f, 'location')).lat),
        ('longitude', lambda f: (get_value(f, 'location') and
                                 get_value(f, 'location')).lon),
        ('organization', lambda f: get_value(f, 'organization')),
        ('type', lambda f: get_value(f, 'facility_type')),
        ('category', lambda f: get_value(f, 'category')),
        ('construction', lambda f: get_value(f, 'construction')),
        ('damage', lambda f: get_value(f, 'damage')),
        ('operational_status', lambda f: get_value(f, 'operational_status')),
        ('comments', lambda f: get_value(f, 'comments')),
        ('reachable_by_road', lambda f: get_value(f, 'reachable_by_road')),
        ('can_pick_up_patients', lambda f: get_value(f, 'can_pick_up_patients')),
        ('region_id', lambda f: get_value(f, 'region_id')),
        ('district_id', lambda f: get_value(f, 'district_id')),
        ('commune_id', lambda f: get_value(f, 'commune_id')),
        ('commune_code', lambda f: get_value(f, 'commune_code')),
        ('sante_id', lambda f: get_value(f, 'sante_id')),
        ('entry_last_updated', lambda f: get_value(f, 'timestamp'))
    ],
}

def get_value(facility, name, default=None):
    return getattr(facility, '%s__' % name, default)

def get_all(query_maker, batch_size=500):
    results = []
    query = query_maker().order('__key__')
    batch = query.fetch(batch_size)
    while batch:
        results += batch
        query = query_maker().order('__key__').filter(
            '__key__ >', batch[-1].key())
        batch = query.fetch(batch_size)
    return results

def short_date(date):
    return '%s %d' % (calendar.month_abbr[date.month], date.day)

def write_csv(out, facility_type):
    """Dump the attributes for all facilities of the given type
       in CSV format, with a row for each facility"""
    writer = csv.writer(out)

    # Get the facilities.
    facilities = get_all(lambda: Facility.all())

    columns = COLUMNS_BY_FACILITY_TYPE[facility_type.key().name()]
    if columns:
        row = list(column[0] for column in columns)
    else:
        row = ['Facilities (%d)' % len(facilities)]
        row += facility_type.attribute_names
    writer.writerow(row)

    # Write a row for each facility.
    for facility in sorted(facilities, key=lambda f: get_value(f, 'title')):
        if columns:
            row = []
            for column in columns:
                row.append(format(column[1](facility)))
        else:
            row = [facility.key().name()]
            for name in facility_type.attribute_names:
                value = get_value(facility, name)
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
        facility_type = self.request.get('facility_type')
        if facility_type:
            # Get the selected facility type.
            facility_type = FacilityType.get_by_key_name(facility_type)

            # Construct a reasonable filename.
            timestamp = datetime.datetime.utcnow()
            filename = '%s.csv' % facility_type.key().name()
            self.response.headers['Content-Type'] = 'text/csv'
            self.response.headers['Content-Disposition'] = \
                'attachment; filename=' + filename

            # Write out the CSV data.
            write_csv(self.response.out, facility_type)
        else:
            self.write('<html><head>')
            self.write('<title>%s</title>' % to_unicode(_("Resource Finder")))
            self.write('<link rel=stylesheet href="static/style.css">')
            self.write('</head><body>')
            #i18n: Save a copy of the data in CSV format
            self.write('<h2>%s</h2>' % to_unicode(_("CSV Export")))
            for ftype in FacilityType.all():
                self.write('<form>')
                self.write('<p>%s' % to_unicode(_(
                    #i18n: Label for a selector to export data to CSV
                    'Select facility type to export:')))
                self.write('<select name="facility_type">')
                for facility_type in FacilityType.all():
                    # TODO(shakusa) FacilityType should have translated messages
                    self.write(
                        '<option value="%s">%s</option>' % (
                        get_message('facility_type', facility_type.key().name()),
                        facility_type.key().name()))
                self.write('<p><input type=submit value="%s">' %
                    #i18n: Button to export data to comma-separated-values
                    #i18n: format.
                    to_unicode(_('Export CSV')))
                self.write('</form>')
            self.write('</body></html>')

if __name__ == '__main__':
    run([('/export', Export)], debug=True)
