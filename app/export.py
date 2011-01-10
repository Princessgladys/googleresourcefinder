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
import zipfile
import StringIO

import access
import bubble
import cache
import utils
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
        ('entry_last_updated', lambda f: get_last_updated_time(f)),
        ('alert_status', lambda f: f.get_value('alert_status')),
        ('other_services', lambda f: f.get_value('other_services'))
    ],
    ('pakistan', 'hospital'): [
        ('name', lambda f: f.get_value('title')),
        ('alt_name', lambda f: f.get_value('alt_title')),
        ('id', lambda f: f.get_value('id')),
        ('alt_id', lambda f: f.get_value('alt_id')),
        ('available_beds', lambda f: f.get_value('available_beds')),
        ('total_beds', lambda f: f.get_value('total_beds')),
        ('services', lambda f: f.get_value('services')),
        ('contact_name', lambda f: f.get_value('contact_name')),
        ('contact_phone', lambda f: f.get_value('phone')),
        ('contact_fax', lambda f: f.get_value('fax')),
        ('contact_email', lambda f: f.get_value('email')),
        ('administrative_area', lambda f: f.get_value('administrative_area')),
        ('sub_administrative_area', lambda f: f.get_value(
            'sub_administrative_area')),
        ('locality', lambda f: f.get_value('locality')),
        ('address', lambda f: f.get_value('address')),
        ('latitude', lambda f: (f.get_value('location') and
                                f.get_value('location').lat)),
        ('longitude', lambda f: (f.get_value('location') and
                                 f.get_value('location').lon)),
        ('maps_link', lambda f: f.get_value('maps_link')),
        ('organization', lambda f: f.get_value('organization')),
        ('organization_type', lambda f: f.get_value('organization_type')),
        ('category', lambda f: f.get_value('category')),
        ('construction', lambda f: f.get_value('construction')),
        ('damage', lambda f: f.get_value('damage')),
        ('operational_status', lambda f: f.get_value('operational_status')),
        ('comments', lambda f: f.get_value('comments')),
        ('reachable_by_road', lambda f: f.get_value('reachable_by_road')),
        ('can_pick_up_patients', lambda f: f.get_value('can_pick_up_patients')),
        ('entry_last_updated', lambda f: get_last_updated_time(f)),
        ('alert_status', lambda f: f.get_value('alert_status')),
        ('other_services', lambda f: f.get_value('other_services'))
    ],
}

KML_PROLOGUE = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>%s</name>
    <Snippet>%s</Snippet>
    <Style id="s">
      <IconStyle>
        <scale>0.3</scale>
        <Icon>
          <href>%s</href>
        </Icon>
      </IconStyle>
    </Style>
    <Folder>
      <name>%s</name>
'''

KML_EPILOGUE = '''    </Folder>
  </Document>
</kml>'''

def short_date(date):
    return '%s %d' % (calendar.month_abbr[date.month], date.day)

def write_csv(out, subdomain, type_name):
    """Dump the attributes for all subjects of the given type
       in CSV format, with a row for each subject"""
    writer = csv.writer(out)

    subject_type = cache.SUBJECT_TYPES[subdomain][type_name]
    subject_query = Subject.all_in_subdomain(subdomain
        ).filter('type =', type_name)
    columns = COLUMNS_BY_SUBJECT_TYPE[(subdomain, type_name)]
    if columns:
        row = list(column[0] for column in columns)
    else:
        row = [type_name] + subject_type.attribute_names
    writer.writerow(row)

    # To avoid out-of-memory errors, we cannot fetch all Subjects at one time.
    # So we process batches.  There's a delicate balance here; batching is
    # slower, and we also have to be careful of the 30s request limit, so
    # large batches are preferred.
    # Also, we want to sort by title, which we cannot do by adding .order()
    # to subject_query. This is because .all_in_subdomain() adds an inequality
    # filter on the key_name and appengine prohibits a sort on a field that is
    # different from the field involved in the inequality. Therefore, we
    # read all the rows into an array, then sort and write the output, knowing
    # title is the first field in each row.
    rows = []
    batch_size = 500
    subjects = subject_query.fetch(batch_size)
    while subjects:
        for subject in subjects:
            if columns:
                row = []
                for column in columns:
                    row.append(format(column[1](subject)))
            else:
                row = [subject.name]
                for name in subject_type.attribute_names:
                    value = get_value(subject, name)
                    row.append(format(value))
            rows.append(row)
        subject_query.with_cursor(subject_query.cursor())
        subjects = subject_query.fetch(batch_size)

    # Write a row for each subject.
    for row in sorted(rows):
        writer.writerow(row)

def write_kml(out, subdomain, type_name, icon_url, now, render_to_string):
    """Dump the attributes for all subjects of the given type
       in kml format, with a placemark for each subject"""
    subject_type = cache.SUBJECT_TYPES[subdomain][type_name]
    subject_query = Subject.all_in_subdomain(subdomain
        ).filter('type =', type_name)
    value_info_extractor = bubble.VALUE_INFO_EXTRACTORS[subdomain][type_name]
    attributes_by_title_and_name = {}

    # Same as write_csv: To avoid out-of-memory errors, process Subjects in
    # batches. read all the rows into a map, then sort and write the output,
    # because we cannot add .order() to subject_query.
    batch_size = 400
    subjects = subject_query.fetch(batch_size)
    while subjects:
        for subject in subjects:
            title = subject.get_value('title')
            (special, general, details) = value_info_extractor.extract(
                subject, subject_type.attribute_names)
            attributes_by_title_and_name[(title, subject.get_name())] = (
                special, general, max(detail.date for detail in details))
        subject_query.with_cursor(subject_query.cursor())
        subjects = subject_query.fetch(batch_size)
    subdomain_cap = to_utf8(subdomain[0].upper() + subdomain[1:])

    #i18n: Name of the application.
    title = to_utf8(subdomain_cap + ' ' + _('Resource Finder'))
    #i18n: Label for a timestamp when a file was created
    created = to_utf8(_('Created') + ': ' + now)
    out.write(KML_PROLOGUE % (title, created, icon_url, to_utf8(type_name)))
    for key in sorted(attributes_by_title_and_name.keys()):
        special, general, last_updated = attributes_by_title_and_name[key]
        placemark = render_to_string('templates/hospital_placemark.kml',
                                     special=special, general=general,
                                     last_updated=last_updated)
        out.write(placemark)
    out.write(KML_EPILOGUE)

def write_kmz(out, subdomain, type_name, render_to_string):
    """Dump the attributes for all subjects of the given type
       in kmz format, with a placemark for each subject"""
    # TODO(shakusa) Because this is so slow, it probably makes sense to cache
    # the result in memcache by (subdomain, type_name, lang), purge it when
    # editing, and reload like refresh_json_cache does

    kml_out = StringIO.StringIO()
    now = to_local_isotime(datetime.datetime.now(), True)
    write_kml(kml_out, subdomain, type_name, 'reddot.png', now,
              render_to_string)

    # Zip up the KML and associated icon
    zipstream = StringIO.StringIO()
    zfile = zipfile.ZipFile(file=zipstream, mode="w",
                            compression=zipfile.ZIP_DEFLATED)
    zfile.writestr('%s.%s.kml' % (
        to_utf8(subdomain), to_utf8(type_name)), kml_out.getvalue())
    zfile.write('templates/reddot.png', 'reddot.png')
    zfile.close()
    zipstream.seek(0)

    # Finally, write the kmz to the output stream
    out.write(zipstream.getvalue())

# TODO(kpy): This should probably reuse row_utils.serialize().  It's here for
# now since it converts to local time; serialize() formats times as UTC.
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
        output = self.request.get('output', 'csv')
        if output != 'csv':
            output = 'kmz'

        if type_name:
            # Construct a reasonable filename.
            timestamp = datetime.datetime.utcnow()
            filename = '%s.%s.%s' % (self.subdomain, type_name, output)
            self.response.headers['Content-Disposition'] = \
                'attachment; filename=' + filename
            if output == 'csv':
                self.response.headers['Content-Type'] = 'text/csv'
                # Write out the CSV data.
                write_csv(self.response.out, self.subdomain, type_name)
            else:
                self.response.headers['Content-Type'] = \
                    'application/vnd.google-earth.kmz'
                # Write out the KMZ data.
                write_kmz(self.response.out, self.subdomain, type_name,
                          self.render_to_string)
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
                self.write('<option value="%s">%s</option>' %
                           (subject_type.name, subject_type.name))
            self.write('<p><input type=submit value="%s">' %
                #i18n: Button to export data to comma-separated-value format.
                to_unicode(_('Export CSV')))
            self.write('</form>')
            self.write('</body></html>')

if __name__ == '__main__':
    run([('/export', Export)], debug=True)
