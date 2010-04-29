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

def write_csv(out, version, facility_type, attribute_names=None):
    """Dump the stock level reports for all facilities of the given type
    in CSV format, with a row for each facility and a group of N columns
    for each week, where N is the number of properties."""
    writer = csv.writer(out)

    # Get the base version and its country.
    timestamp = version.timestamp.replace(microsecond=0).isoformat() + 'Z'
    version = get_base(version)
    country = version.parent()

    # Get the attribute names.
    attribute_names = attribute_names or facility_type.attribute_names

    # Get the divisions.
    divisions = get_districts(version)

    # Get the facilities.
    facilities = get_all(lambda: Facility.all().ancestor(version))

    # Get the reports.
    reports = get_all(lambda: Report.all().ancestor(version))

    # Determine the date range.
    dates = [r.date for r in reports]
    min_date, max_date = min(dates), max(dates)
    while min_date.isoweekday() != 3:  # Find the preceding Wednesday
        min_date -= TimeDelta(1)
    num_weeks = (max_date + TimeDelta(7) - min_date).days / 7

    # Organize the reports by facility and week.
    reports_by_facility = dict((f.key().name(), [None]*num_weeks) 
                               for f in facilities)
    for report in reports:
        week = (report.date - min_date).days / 7
        reports_by_facility[report.facility_name][week] = report

    # Produce the header rows.
    row = [country.title, '%s: %d reports' % (timestamp, len(reports))]
    group = [None] * len(attribute_names)
    d = min_date
    for week in range(num_weeks):
        group[0] = '%s - %s' % (short_date(d), short_date(d + TimeDelta(6)))
        row += group
        d += TimeDelta(7)
    writer.writerow(row)

    row = ['Districts (%d)' % len(divisions),
           'Facilities (%d)' % len(facilities)]
    row += attribute_names*num_weeks
    writer.writerow(row)

    # Write a row for each facility.
    sorted_facilities = sorted(facilities, key=lambda f: f.title)
    for division in sorted(divisions, key=lambda d: d.title):
        for facility in sorted_facilities:
            if facility.division_name == division.key().name():
                row = [division.key().name(), facility.key().name()]
                reports = reports_by_facility[facility.key().name()]
                for week in range(num_weeks):
                    if reports[week]:
                        for name in attribute_names:
                            value = getattr(reports[week], name, None)
                            if isinstance(value, unicode):
                                value = value.encode('utf-8')
                            if isinstance(value, str):
                                value = value.replace('\n', ' ')
                            if isinstance(value, list):
                                value = ', '.join(value)
                            row.append(value)
                    else:
                        row += [None]*len(attribute_names)
                writer.writerow(row)

class Export(Handler):
    def get(self):
        country_code = self.request.get('cc')
        if country_code:
            # Get the selected facility type.
            version = get_latest_version(country_code)
            facility_type = FacilityType.get_by_key_name(
                self.request.get('facility_type'), version)

            # Construct a reasonable filename.
            timestamp = version.timestamp.replace(microsecond=0)
            country = version.parent()
            filename = '%s.%s.%s.csv' % (
                country_code, facility_type.key().name(),
                timestamp.isoformat().replace(':', '_'))
            self.response.headers['Content-Type'] = 'text/csv'
            self.response.headers['Content-Disposition'] = \
                'attachment; filename=' + filename

            # Write out the CSV data.
            write_csv(self.response.out, version, facility_type)
        else:
            self.write('<link rel=stylesheet href="static/style.css">')
            for country in Country.all():
                version = get_latest_version(country.key().name())
                self.write('<h2>%s</h2>' % country.title)
                self.write('<p>%s %s' %
                    (_('Last updated:'), version.timestamp))
                self.write('<p><form>')
                self.write('<input type=hidden name="cc" value="%s">' %
                           country.key().name())
                self.write('<p>Select facility type to export:')
                self.write('<select name="facility_type">')
                for facility_type in FacilityType.all().ancestor(version):
                    self.write(
                        '<option value="%s">%s</option>' % (
                        facility_type.key().name(),
                        facility_type.key().name()))
                self.write('<p><input type=submit value="%s">' %
                    _('Export CSV'))
                self.write('</form>')

if __name__ == '__main__':
    run([('/export', Export)], debug=True)
