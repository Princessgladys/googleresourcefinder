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
        ('facility_name', lambda f, r: f.title),
        ('facility_healthc_id', lambda f, r: getattr(r, 'healthc_id', None)),
        ('facility_pcode', lambda f, r: re.sub(r'.*\.\.(.*)', r'\1',
                                               f.key().name())),
        ('available_beds', lambda f, r: getattr(r, 'available_beds', None)),
        ('total_beds', lambda f, r: getattr(r, 'total_beds', None)),
        ('services', lambda f, r: getattr(r, 'services', None)),
        ('contact_name', lambda f, r: getattr(r, 'contact_name', None)),
        ('contact_phone', lambda f, r: getattr(r, 'phone', None)),
        ('contact_email', lambda f, r: getattr(r, 'email', None)),
        ('department', lambda f, r: getattr(r, 'departemen', None)),
        ('district', lambda f, r: getattr(r, 'district', None)),
        ('commune', lambda f, r: getattr(r, 'commune', None)),
        ('address', lambda f, r: getattr(r, 'address', None)),
        ('latitude', lambda f, r: f.location.lat),
        ('longitude', lambda f, r: f.location.lon),
        ('organization', lambda f, r: getattr(r, 'organization', None)),
        ('type', lambda f, r: getattr(r, 'type', None)),
        ('category', lambda f, r: getattr(r, 'category', None)),
        ('construction', lambda f, r: getattr(r, 'construction', None)),
        ('damage', lambda f, r: getattr(r, 'damage', None)),
        ('comments', lambda f, r: getattr(r, 'comments', None)),
        ('reachable_by_road', lambda f, r: getattr(r, 'reachable_by_road',
                                                   None)),
        ('can_pick_up_patients', lambda f, r: getattr(r, 'can_pick_up_patients',
                                                      None)),
        ('region_id', lambda f, r: getattr(r, 'region_id', None)),
        ('district_id', lambda f, r: getattr(r, 'district_id', None)),
        ('commune_id', lambda f, r: getattr(r, 'commune_id', None)),
        ('commune_code', lambda f, r: getattr(r, 'commune_code', None)),
        ('sante_id', lambda f, r: getattr(r, 'sante_id', None)),
        ('entry_last_updated', lambda f, r: getattr(r, 'timestamp', None))
      ],
  }

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

def get_districts(version):
    return get_all(lambda: Division.all().ancestor(version))

def write_csv(out, version, facility_type):
    """Dump the stock level reports for all facilities of the given type
       in CSV format, with a row for each facility"""
    writer = csv.writer(out)

    # Get the base version and its country.
    version = get_base(version)
    country = version.parent()

    # Get the facilities.
    facilities = get_all(lambda: Facility.all().ancestor(version))

    # Get the reports.
    reports = get_all(lambda: Report.all().ancestor(version))

    # Organize the reports by facility, keep only the last one
    reports_by_facility = dict((f.key().name(), None) for f in facilities)
    for report in reports:
        reports_by_facility[report.facility_name] = report

    columns = COLUMNS_BY_FACILITY_TYPE[facility_type.key().name()]
    if columns:
        row = list(column[0] for column in columns)
    else:
        row = ['Facilities (%d)' % len(facilities)]
        row += facility_type.attribute_names
    writer.writerow(row)

    # Write a row for each facility.
    country_code = country.key().name()
    for facility in sorted(facilities, key=lambda f: f.title):
        report = reports_by_facility[facility.key().name()]
        if columns:
            row = []
            for column in columns:
                row.append(format(column[1](facility, report)))
        else:
            row = [facility.key().name()]
            for name in facility_type.attribute_names:
                value = getattr(report, name, None)
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
        # TODO(shakusa) Use timezone of cc instead of hard-coding Haitian time
        timestamp = value.replace(microsecond=0)
        timestamp_ht = timestamp - datetime.timedelta(hours=5)
        return timestamp_ht.isoformat(' ') + '-05:00'
    return value

class Export(Handler):
    def get(self):
        country_code = self.request.get('cc')
        if country_code:
            # Get the selected facility type.
            version = get_latest_version(country_code)
            facility_type = FacilityType.get_by_key_name(
                self.request.get('facility_type'), version)

            # Construct a reasonable filename.
            timestamp = datetime.datetime.utcnow()
            country = version.parent()
            filename = '%s.%s.csv' % (country_code, facility_type.key().name())
            self.response.headers['Content-Type'] = 'text/csv'
            self.response.headers['Content-Disposition'] = \
                'attachment; filename=' + filename

            # Write out the CSV data.
            write_csv(self.response.out, version, facility_type)
        else:
            self.write('<html><head>')
            self.write('<title>%s</title>' % to_unicode(_("Resource Finder")))
            self.write('<link rel=stylesheet href="static/style.css">')
            self.write('</head><body>')
            for country in Country.all():
                version = get_latest_version(country.key().name())
                self.write('<h2>%s</h2>' % country.title)
                self.write('<p><form>')
                self.write('<input type=hidden name="cc" value="%s">' %
                           country.key().name())
                self.write('<p>%s' % to_unicode(_(
                    #i18n: Label for a selector to export data to CSV
                    'Select facility type to export:')))
                self.write('<select name="facility_type">')
                for facility_type in FacilityType.all().ancestor(version):
                    # TODO(shakusa) FacilityType should have translated messages
                    self.write(
                        '<option value="%s">%s</option>' % (
                        facility_type.key().name(),
                        facility_type.key().name()))
                self.write('<p><input type=submit value="%s">' %
                    #i18n: Button to export data to comma-separated-values
                    #i18n: format.
                    to_unicode(_('Export CSV')))
                self.write('</form>')
            self.write('</body></html>')

if __name__ == '__main__':
    run([('/export', Export)], debug=True)
