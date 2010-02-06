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
    type = DivisionType.get_by_key_name('district', version)
    return get_all(
        lambda: Division.all().ancestor(version).filter('type =', type))

def write_csv(out, version, supply_keys=None):
    """Dump the stock level reports for all facilities in CSV format,
    with a row for each facility and a group of N columns for each week,
    where N is the number of supplies."""
    writer = csv.writer(out)

    # Get the base version and its country.
    timestamp = version.timestamp.replace(microsecond=0).isoformat() + 'Z'
    version = get_base(version)
    country = version.parent()

    # Get the divisions.
    divisions = get_districts(version)

    # Get the supply keys, if none were specified.
    if supply_keys is None:
        supply_keys = [s.name() for s in version.supplies]

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
    reports_by_facility = dict((f.key(), [None]*num_weeks) for f in facilities)
    for report in reports:
        week = (report.date - min_date).days / 7
        reports_by_facility[report._facility][week] = report

    # Produce the header rows.
    row = [country.name, '%s: %d reports' % (timestamp, len(reports))]
    group = [None] * len(supply_keys)
    d = min_date
    for week in range(num_weeks):
        group[0] = '%s - %s' % (short_date(d), short_date(d + TimeDelta(6)))
        row += group
        d += TimeDelta(7)
    writer.writerow(row)

    row = ['%d districts' % len(divisions), '%d facilities' % len(facilities)]
    row += supply_keys*num_weeks
    writer.writerow(row)

    # Write a row for each facility.
    sorted_facilities = sorted(facilities, key=lambda f: f.name)
    for division in sorted(divisions, key=lambda d: d.name):
        for facility in sorted_facilities:
            if facility._division == division.key():
                row = [division.name, facility.name]
                reports = reports_by_facility[facility.key()]
                for week in range(num_weeks):
                    if reports[week]:
                        for supply_key in supply_keys:
                            value = getattr(reports[week], supply_key, None)
                            if value is not None:
                                value = int(value)
                            row.append(value)
                    else:
                        row += [None]*len(supply_keys)
                writer.writerow(row)

class Export(Handler):
    def get(self):
        auth = access.check_and_log(self.request, users.get_current_user())
        if auth:
            country_code = self.request.get('cc')
            if country_code:
                # Determine which supplies were selected.
                version = get_latest_version(country_code)
                supply_keys = []
                for supply in get_base(version).supplies:
                    key = supply.name()
                    if self.request.get('supply.' + key):
                        supply_keys.append(key)
                supply_code = ''.join(key[0] for key in supply_keys)

                # Construct a reasonable filename.
                timestamp = version.timestamp.replace(microsecond=0)
                country = version.parent()
                filename = '%s.%s.%s.csv' % (country.name, supply_code,
                    timestamp.isoformat().replace(':', '_'))
                self.response.headers['Content-Type'] = 'text/csv'
                self.response.headers['Content-Disposition'] = \
                    'attachment; filename=' + filename

                # Write out the CSV data.
                write_csv(self.response.out, version, supply_keys)
            else:
                self.write('<link rel=stylesheet href="static/style.css">')
                for country in Country.all():
                    version = get_latest_version(country.key().name())
                    self.write('<h2>%s</h2>' % country.name)
                    self.write('<p>Last updated: %s' % version.timestamp)
                    self.write('<p><form>')
                    self.write('<input type=hidden name="cc" value="%s">' %
                               country.key().name())
                    self.write('<p>Select supplies to export:')
                    for supply in get_base(version).supplies:
                        self.write(
                            '<br><input type=checkbox name="%s" checked>%s' % (
                            'supply.' + supply.name(), supply.name()))
                    self.write('<p><input type=submit value="Export CSV">')
                    self.write('</form>')
        else:
            self.redirect(users.create_login_url('/'))

if __name__ == '__main__':
    run([('/export', Export)], debug=True)
