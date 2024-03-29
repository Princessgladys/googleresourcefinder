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

from google.appengine.api import users

import csv
import datetime
import logging
import re
import zipfile
from StringIO import StringIO

import kml
import setup
from feedlib.geo import point_inside_polygon
from model import *
from pakistan_data import *

SHORELAND_URL = 'http://shoreland.com/'
SHORELAND_EMAIL = 'haitiaid@shoreland.com'
SHORELAND_NICKNAME = 'Shoreland Editor'
SHORELAND_AFFILIATION = 'Shoreland Inc.'

PAKISTAN_URL = 'http://www.google.com/mapmaker/'
PAKISTAN_EMAIL = 'resource-finder-discussion@googlegroups.com'
PAKISTAN_NICKNAME = 'Google MapMaker'
PAKISTAN_AFFILIATION = 'Google Inc.'

def strip_or_none(value):
    """Converts strings to their stripped values or None, while preserving
    values of other types."""
    if isinstance(value, db.Text):
        # We have to preserve db.Text as db.Text, or the datastore might
        # reject it.  (Strings longer than 500 characters are not storable.)
        return db.Text(value.strip()) or None
    if isinstance(value, basestring):
        return value.strip() or None
    return value


class ValueInfo:
    """Keeps track of an attribute value and metadata."""
    def __init__(self, value, observed=None, source=None, comment=None):
        self.value = strip_or_none(value)
        self.observed = observed
        self.comment = self.combine_comment(source, comment)

    def combine_comment(self, source, comment):
        source = strip_or_none(source)
        comment = strip_or_none(comment)
        if source is not None:
            source = 'Source: %s' % source
            comment = comment and '%s; %s' % (source, comment) or source
        return comment

    def __repr__(self):
      return 'ValueInfo(%r, observed=%r, comment=%r)' % (
          self.value, self.observed, self.comment)

def convert_paho_record(record):
    """Converts a dictionary of values from one row of a PAHO CSV file
    into a dictionary of ValueInfo objects for our datastore."""

    title = (record['Fac_NameFr'].strip() or record['NomInstitu'].strip())

    if not record.get('HealthC_ID').strip():
        # TODO(shakusa) Fix this. We should be importing all facilities.
        logging.warn('Skipping %r (%s): Invalid HealthC_ID: "%s"' % (
            title, record.get('PCode'), record.get('HealthC_ID')))
        return None, None, None

    key_name = 'paho.org/HealthC_ID/' + record['HealthC_ID'].strip()
    title = (record['Fac_NameFr'].strip() or record['NomInstitu'].strip())
    alt_title = (title == record['Fac_NameFr'].strip() and
                 record['NomInstitu'].strip() or '')
    try:
        latitude = float(record['X_DDS'])
        longitude = float(record['Y_DDS'])
    except ValueError:
        # TODO(shakusa) Fix this. We should be importing all facilities.
        logging.warn('Skipping %r (%s): X_DDS=%r Y_DDS=%r' % (
            title, key_name, record.get('X_DDS'), record.get('Y_DDS')))
        return None, None, None

    return key_name, None, {
        'title': ValueInfo(title),
        'alt_title': ValueInfo(alt_title),
        'healthc_id': ValueInfo(
            record['HealthC_ID'],
            comment=record['AlternateHealthCIDDeleted']),
        'pcode': ValueInfo(record['PCode']),
        'organization': ValueInfo(record['Oorganisat']),
        'department': ValueInfo(record['Departemen']),
        'district': ValueInfo(record['DistrictNom']),
        'commune': ValueInfo(record['Commune']),
        'address': ValueInfo(record['Address']),
        'location': ValueInfo(db.GeoPt(latitude, longitude),
                              source=record['SourceHospitalCoordinates'],
                              comment=record['AlternateCoordinates']),
        'accuracy': ValueInfo(record['Accuracy']),
        'phone': ValueInfo(record['Telephone']),
        'email': ValueInfo(record['email']),
        'organization_type': ValueInfo(record['Type']),
        'category': ValueInfo(record['Categorie']),
        'damage': ValueInfo(record['Damage'],
                            observed=parse_paho_date(record['DateDamage']),
                            source=record['SourceDamage']),
        'operational_status': ValueInfo(
            record['OperationalStatus'],
            observed=parse_paho_date(record['DateOperationalStatus']),
            source=record['SourceOperationalStatus']),
        'comments': ValueInfo(db.Text(record['Comment'])),
        'region_id': ValueInfo(record['RegionId']),
        'district_id': ValueInfo(record['DistrictId']),
        'commune_id': ValueInfo(record['CommuneId']),
        'commune_code': ValueInfo(record['CodeCommun']),
        'sante_id': ValueInfo(record['SanteID'])
    }

def convert_shoreland_record(record):
    """Converts a dictionary of values from one row of a Shoreland CSV file
    into a dictionary of ValueInfo objects for our datastore."""
    title = record['facility_name'].strip()

    healthc_id = record.get(
        'healthc_id', record.get('facility_healthc_id', '')).strip()
    pcode = record.get('pcode', record.get('facility_pcode', '')).strip()

    if not healthc_id:
        # Every row in a Shoreland CSV file should have a non-blank healthc_id.
        logging.warn('Skipping %r (pcode %s): no HealthC_ID' % (title, pcode))
        return None, None, None

    subject_name = 'paho.org/HealthC_ID/' + healthc_id
    try:
        latitude = float(record['latitude'])
        longitude = float(record['longitude'])
        location = db.GeoPt(latitude, longitude)
    except (KeyError, ValueError):
        logging.warn('No location for %r (%s): latitude=%r longitude=%r' % (
            title, healthc_id, record.get('latitude'), record.get('longitude')))
        location = None
    observed = None
    if record.get('entry_last_updated'):
        observed = parse_shoreland_datetime(record['entry_last_updated'])

    # The CSV 'type' column maps to our 'category' attribute.
    CATEGORY_MAP = {
        None: '',
        '': '',
        'Clinic': 'CLINIC',
        'Dispensary': 'DISPENSARY',
        'Hospital': 'HOSPITAL',
        'Mobile Clinic': 'MOBILE_CLINIC'
    }

    # The CSV 'category' column maps to our 'organization_type' attribute.
    ORGANIZATION_TYPE_MAP = {
        None: '',
        '': '',
        'Community': 'COMMUNITY',
        'Faith-Based Org': 'FAITH_BASED',
        'For Profit': 'FOR_PROFIT',
        'Military': 'MILITARY',
        'Mixed': 'MIXED',
        'NGO': 'NGO',
        'Public': 'PUBLIC',
        'University': 'UNIVERSITY'
    }

    # The CSV 'operational_status' column has two possible values.
    OPERATIONAL_STATUS_MAP = {
        None: '',
        '': '',
        'Open': 'OPERATIONAL',
        'Closed or Closing': 'CLOSED_OR_CLOSING'
    }

    # The CSV 'services' column contains space-separated abbreviations.
    SERVICE_MAP = {
        'GenSurg': 'GENERAL_SURGERY',
        'Ortho': 'ORTHOPEDICS',
        'Neuro': 'NEUROSURGERY',
        'Vascular': 'VASCULAR_SURGERY',
        'IntMed': 'INTERNAL_MEDICINE',
        'Cardiology': 'CARDIOLOGY',
        'ID': 'INFECTIOUS_DISEASE',
        'Peds': 'PEDIATRICS',
        'OB': 'OBSTETRICS_GYNECOLOGY',
        'Dialysis': 'DIALYSIS',
        'MentalHealth': 'MENTAL_HEALTH',
        'Rehab': 'REHABILITATION'
    }
    service_list = []
    for keyword in record.get('services', '').split():
        service_list.append(SERVICE_MAP[keyword])
    if record.get('services_last_updated'):
        services = ValueInfo(service_list, parse_shoreland_datetime(
            record['services_last_updated']))
    else:
        services = ValueInfo(service_list)

    return subject_name, observed, {
        'title': ValueInfo(title),
        'healthc_id': ValueInfo(healthc_id),
        'pcode': ValueInfo(pcode),
        # Bill Lang recommends (2010-06-07) ignoring the available_beds column.
        'available_beds': ValueInfo(None),
        # NOTE(kpy): Intentionally treating total_beds=0 as "number unknown".
        'total_beds': ValueInfo(
            record.get('total_beds') and int(record['total_beds']) or None,
            comment=record.get('BED TRACKING COMMENTS')),
        # Didn't bother to convert the 'services' field because it's empty
        # in the CSV from Shoreland.
        'contact_name': ValueInfo(record.get('contact_name')),
        'phone': ValueInfo(record.get('contact_phone')),
        'email': ValueInfo(record.get('contact_email')),
        'department': ValueInfo(record.get('department')),
        'district': ValueInfo(record.get('district')),
        'commune': ValueInfo(record.get('commune')),
        'address': ValueInfo(record.get('address')),
        'location': ValueInfo(location),
        'accuracy': ValueInfo(record.get('accuracy')),
        'organization': ValueInfo(record.get('organization')),
        # The 'type' and 'category' columns are swapped.
        'organization_type':
            ValueInfo(ORGANIZATION_TYPE_MAP[record.get('category')]),
        'category': ValueInfo(CATEGORY_MAP[record.get('type')]),
        # Didn't bother to convert the 'construction' field because it's empty
        # in the CSV from Shoreland.
        'damage': ValueInfo(record.get('damage')),
        'operational_status':
            ValueInfo(OPERATIONAL_STATUS_MAP[record.get('operational_status')]),
        'services': services,
        'comments': ValueInfo(db.Text(record.get('comments', ''))),
        'region_id': ValueInfo(record.get('region_id')),
        'district_id': ValueInfo(record.get('district_id')),
        'commune_id': ValueInfo(record.get('commune_id')),
        'sante_id': ValueInfo(record.get('sante_id'))
    }

def convert_pakistan_record(record):
    """Converts a dictionary of values from one placemark of a Mapmaker-
    exported KML file into a dictionary of ValueInfo objects for our
    datastore."""

    title = ''
    type = ''
    description = ''
    comments = []
    CDATA_PATTERN = re.compile(r'<b>(.*):</b> <i>(.*)</i>.*')
    for line in record.get('comment', '').strip().split('\n'):
        line = line.strip()
        match = CDATA_PATTERN.match(line)
        if match:
            key = match.group(1)
            value = match.group(2)
            if key == 'ID':
                # ID is given as a pair of colon-separated hex strings
                # Only the second part is stable. It is more common externally
                # to see base-10 ids, so convert. Finally, the mapmaker URL
                # needs both parts.
                id_parts = value.split(':')
                int_id_parts = list(str(int(part, 16)) for part in id_parts)
                record['id'] = int_id_parts[1]
                record['maps_link'] = ('http://www.google.com/mapmaker?q=' +
                                       ':'.join(int_id_parts))
            if key == 'NAME1':
                title = value
            if key == 'TYPE' or key == 'ETYPE':
                type = value
            elif key == 'LANGNAME':
                record['alt_title'] = value
            elif key == 'PHONE':
                record['phone'] = value
            elif key == 'MOBILE':
                record['mobile'] = value
            elif key == 'FAX':
                record['fax'] = value
            elif key == 'EMAIL':
                record['email'] = value
            elif key == 'ADDRESS':
                record['address'] = value
            elif key == 'DESCRIPTIO':
                description = value
            elif value in PAKISTAN_ADMIN_AREAS:
                if value == 'North West Frontier':
                    # Officially renamed;
                    # See http://en.wikipedia.org/wiki/Khyber-Pakhtunkhwa
                    value = 'Khyber Pakhtunkhwa'
                record['admin_area'] = value
            elif value in PAKISTAN_DISTRICTS:
                record['sub_admin_area'] = value
            if key not in ['ADDRESS', 'CENTERTYPE', 'CNTRYCODE', 'DESCRIPTIO',
                           'EMAIL', 'FAX', 'ID', 'LANG1', 'LANGNAME', 'MOBILE',
                           'NAME1', 'PHONE']:
                comments.append('%s: %s' % (key, value))

    if not record.get('id'):
        logging.warn('SKIPPING, NO ID: %r' % record)
        return None, None, None

    try:
        latitude = float(record['location'][1])
        longitude = float(record['location'][0])
        location = db.GeoPt(latitude, longitude)
    except (KeyError, ValueError):
        logging.warn('No location for %r' % record)
        location = None

    if not (point_inside_polygon(
        {'lat': latitude, 'lon': longitude}, PAKISTAN_FLOOD_POLYGON) or
        record.get('sub_admin_area', '') in PAKISTAN_FLOOD_DISTRICTS):
        return None, None, None

    title = title or record.get('title', '').strip()
    if not title:
        logging.warn('SKIPPING, NO TITLE: %r' % record)
        return None, None, None

    if description:
        # Make sure it's the first comment
        comments.insert(0, description)

    subject_name = 'mapmaker.google.com/fid/' + record['id']

    title_lower = title.lower()
    if type == 'TYPE_HOSPITAL' or 'hospital' in title_lower:
        record['category'] = 'HOSPITAL'
    elif 'clinic' in title_lower:
        record['category'] = 'CLINIC'
    elif 'laborator' in title_lower or 'labs ' in title_lower:
        record['category'] = 'LABORATORY'
    elif 'dispensary' in title_lower:
        record['category'] = 'DISPENSARY'

    observed = None
    return subject_name, observed, {
        'id': ValueInfo(record['id']),
        'title': ValueInfo(title),
        'alt_title': ValueInfo(record.get('alt_title', '')),
        'address': ValueInfo(record.get('address', '')),
        'administrative_area': ValueInfo(record.get('admin_area', '')),
        'sub_administrative_area': ValueInfo(record.get('sub_admin_area', '')),
        'locality': ValueInfo(record.get('locality', '')),
        'location': ValueInfo(location),
        'maps_link': ValueInfo(record['maps_link']),
        'phone': ValueInfo(record.get('phone', '')),
        'mobile': ValueInfo(record.get('mobile', '')),
        'fax': ValueInfo(record.get('fax', '')),
        'email': ValueInfo(record.get('email', '')),
        'category': ValueInfo(record.get('category', '')),
        'comments': ValueInfo(db.Text('\n'.join(comments))),
    }

def load(
    filename, record_reader, record_converter, subdomain, subject_type_name,
    source_url, default_observed, author, author_nickname, author_affiliation,
    limit=None):
    """Loads a file of records into the datastore.

    Args:
      filename: name of the file to load
      record_reader: function that takes a file and returns a record iterator
      record_converter: function that takes a parsed record and returns a
          (subject_name, observed, values) triple, where observed is a datetime
          and values is a dictionary of attribute names to ValueInfo objects
      subdomain: name of the subdomain to load subjects into
      subject_type_name: name of the subject type for these subjects
      source_url: where filename was downloaded, stored in Report.source
      default_observed: datetime.datetime when data was observed to be valid,
          for records that do not have their own observed timestamp
      author: users.User who will own the changes made during loading
      author_nickname: nickname for the author
      author_affiliation: organizational affiliation of the author
      limit: maximum number of records to load (default: load all)"""

    if (not filename or not source_url or not default_observed or not author or
        not author_nickname or not author_affiliation):
        raise Exception('All arguments must be non-empty.')

    subjects = []
    minimal_subjects = []
    reports = []
    arrived = datetime.datetime.utcnow().replace(microsecond=0)

    # Store the raw file contents in a Dump.
    Dump(source=source_url, data=open(filename, 'rb').read()).put()

    if filename.endswith('zip'):
        archive = zipfile.ZipFile(filename, 'r')
        file = StringIO(archive.read(archive.namelist()[0]))
    else:
        file = open(filename)

    subject_type = SubjectType.get(subdomain, subject_type_name)
    count = 0
    for record in record_reader(file):
        if limit and count >= limit:
            break
        count += 1

        for key in record:
            if record[key] is None or type(record[key]) is str:
                record[key] = (record[key] or '').decode('utf-8')
        subject_name, observed, value_infos = record_converter(record)
        if not subject_name:  # if converter returned None, skip this record
            continue
        observed = observed or default_observed

        subject = Subject.create(subdomain, subject_type, subject_name, author)
        subjects.append(subject)
        Subject.author.validate(author)
        minimal_subject = MinimalSubject.create(subject)
        minimal_subjects.append(minimal_subject)

        # Create a report for this row. ValueInfos that have a different
        # observed date than 'observed' will be reported in a separate report
        report = Report(
            subject,
            arrived=arrived,
            source=source_url,
            author=author,
            observed=observed)
        reports.append(report)

        for (name, info) in value_infos.items():
            if not info.value and info.value != 0:
                continue

            current_report = report
            if info.observed and observed != info.observed:
                # Separate out this change into a new report
                current_report = Report(
                    subject,
                    arrived=arrived,
                    source=source_url,
                    author=author,
                    observed=info.observed)
                reports.append(current_report)

            subject.set_attribute(name, info.value, observed, author,
                                   author_nickname, author_affiliation,
                                   info.comment)
            current_report.set_attribute(name, info.value, info.comment)
            if name in subject_type.minimal_attribute_names:
                minimal_subject.set_attribute(name, info.value)

    put_batches(subjects + minimal_subjects + reports)

def parse_paho_date(date):
    """Parses a period-separated (month.day.year) date, passes through None.
    For example, May 19, 2010 would be represented as '05.19.2010'"""
    if date is not None:
        (month, day, year) = date.strip().split('.')
        date = datetime.datetime(int(year), int(month), int(day))
    return date

def parse_shoreland_datetime(timestamp):
    """Parses a timestamp in MM/DD/YYYY HH:MM ZZZ format (for example,
    02/07/2010 19:31 EST)."""
    match = re.match(r'(\d+)/(\d+)/(\d+) (\d+):(\d+) (\w+)', timestamp)
    month, day, year, hour, minute, zone = match.groups()
    offset = {
        'EST': datetime.timedelta(0, -5 * 3600, 0)
    }[zone]
    return datetime.datetime(
        int(year), int(month), int(day), int(hour), int(minute)) - offset

def put_batches(entities):
    """Works around annoying limitations of App Engine's datastore."""
    count, total = 0, len(entities)
    while entities:
        batch, entities = entities[:200], entities[200:]
        db.put(batch)
        count += len(batch)
        logging.info('Stored %d of %d entities.' % (count, total))

def parse_datetime(timestamp):
    """Parses a UTC timestamp in YYYY-MM-DD HH:MM:SS format.  Acceptable
    examples are "2010-02-07", "2010-02-07 19:31", "2010-02-07T13:02:03Z"."""
    match = re.match(r'(\d+)-(\d+)-(\d+)([ T](\d+):(\d+)(:(\d+))?)?', timestamp)
    year, month, day, time = match.groups()[:4]
    hour = match.group(5) or 0
    minute = match.group(6) or 0
    second = match.group(8) or 0
    return datetime.datetime(
        int(year), int(month), int(day), int(hour), int(minute), int(second))

def load_shoreland(filename, observed):
    """Loads a Shoreland CSV file using defaults for the URL and author."""
    setup.setup_datastore()
    if isinstance(observed, basestring):
        observed = parse_datetime(observed)
    user = users.User(SHORELAND_EMAIL)
    load(filename, csv.DictReader, convert_shoreland_record, 'haiti',
         'hospital', SHORELAND_URL, observed, user, SHORELAND_NICKNAME,
         SHORELAND_AFFILIATION)

def wipe_and_load_shoreland(filename, observed):
    """Wipes the entire datastore and then loads a Shoreland CSV file."""
    open(filename)  # Ensure the file is readable before wiping the datastore.
    setup.wipe_datastore()
    load_shoreland(filename, observed)

def load_pakistan_kml(filename, observed):
    """Loads a Pakistan MapMaker KML file w/ defaults for the URL and author."""
    setup.setup_datastore()
    if isinstance(observed, basestring):
        observed = parse_datetime(observed)
    user = users.User(PAKISTAN_EMAIL)
    load(filename, kml.parse_file, convert_pakistan_record, 'pakistan',
         'hospital', PAKISTAN_URL, observed, user, PAKISTAN_NICKNAME,
         PAKISTAN_AFFILIATION)

def delete_pakistan_kml():
    """Deletes Reports, MinimalSubjects, and Subjects created by
    load_pakistan_kml()."""
    prefix = 'pakistan:mapmaker'
    subjects = filter_by_prefix(Subject.all(keys_only=True), prefix)
    minimal_subjects = filter_by_prefix(MinimalSubject.all(keys_only=True),
                                        prefix, 'Subject')
    reports = Report.all(keys_only=True).filter('source =', PAKISTAN_URL)
    queries = {'Report': reports,
               'Subject': subjects,
               'MinimalSubject': minimal_subjects}

    for kind, query in queries.items():
        keys = query.fetch(200)
        while keys:
            logging.info('%s: deleting %d...' % (kind, len(keys)))
            db.delete(keys)
            keys = query.fetch(200)


def fix_batool():
    """HACK to fix up an entry that was edited via the UI before we switched
    out the mapmaker data.
    TODO(shakusa) Delete this method when we're done with it."""
    subject_type = SubjectType.get('pakistan', 'hospital')
    key_name = 'pakistan:mapmaker.google.com/fid/4414990288838998487'
    observed = parse_datetime('2010-08-13 19:58:25')
    source = 'http://pakistan.resource-finder.appspot.com'
    author = users.User('mustafasaboor@gmail.com')
    author_nickname = 'Mustafa Saboor'
    author_affiliation = 'Owner'

    subject=Subject.get_by_key_name(key_name)
    minimal_subject = MinimalSubject.get_by_subject(subject)
    report = Report(
        subject,
        arrived=observed,
        source=source,
        author=author,
        observed=observed)

    value_infos = {
        'total_beds': ValueInfo(22),
        'services': ValueInfo(['GENERAL_SURGERY', 'ORTHOPEDICS',
                               'INTERNAL_MEDICINE', 'INFECTIOUS_DISEASE',
                               'PEDIATRICS', 'POSTOPERATIVE_CARE',
                               'OBSTETRICS_GYNECOLOGY', 'LAB', 'X_RAY',
                               'BLOOD_BANK']),
        'contact_name': ValueInfo('Reception'),
        'phone': ValueInfo('03212437003'),
        'email': ValueInfo('mustafasaboor@gmail.com'),
        'locality': ValueInfo('Gulistan-e-Iqbal'),
        'organization': ValueInfo('BGH'),
        'construction': ValueInfo('REINFORCED_CONCRETE'),
        'operational_status': ValueInfo('OPERATIONAL'),
        'reachable_by_road': ValueInfo(True),
        'can_pick_up_patients': ValueInfo(False),
    }

    for (name, info) in value_infos.items():
        if not info.value and info.value != 0:
            continue

        subject.set_attribute(name, info.value, observed, author,
                              author_nickname, author_affiliation,
                              info.comment)
        report.set_attribute(name, info.value, info.comment)
        if name in subject_type.minimal_attribute_names:
            minimal_subject.set_attribute(name, info.value)
    subject.put()
    minimal_subject.put()
    report.put()
