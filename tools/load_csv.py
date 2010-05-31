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
from model import *
import csv
import datetime
import logging
import re

SHORELAND_URL = 'http://shoreland.com/'
SHORELAND_EMAIL = 'admin@shoreland.com'
SHORELAND_NICKNAME = 'Shoreland Contact Name'
SHORELAND_AFFILIATION = 'Shoreland Inc.'

def convert_paho_record(record):
    """Converts a dictionary of values from one row of a PAHO CSV file
    into a dictionary of ValueInfo objects for our datastore."""
    key_name = 'mspphaiti.org/' + record['PCode']
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
        'damage': ValueInfo(record['Damage'], observed=record['DateDamage'],
                            source=record['SourceDamage']),
        'operational_status': ValueInfo(
            record['OperationalStatus'],
            observed=record['DateOperationalStatus'],
            source=record['SourceOperationalStatus']),
        'comments': ValueInfo(record['Comment']),
        'region_id': ValueInfo(record['RegionId']),
        'district_id': ValueInfo(record['DistrictId']),
        'commune_id': ValueInfo(record['CommuneId']),
        'commune_code': ValueInfo(record['CodeCommun']),
        'sante_id': ValueInfo(record['SanteID'])
    }

def convert_shoreland_record(record):
    """Converts a dictionary of values from one row of a Shoreland CSV file
    into a dictionary of ValueInfo objects for our datastore."""
    key_name = 'mspphaiti.org/' + record['facility_pcode']
    title = record['facility_name'].strip()
    alt_title = record['alt_facility_name'].strip()
    try:
        latitude = float(record['latitude'])
        longitude = float(record['longitude'])
    except ValueError:
        # TODO(shakusa) Fix this. We should be importing all facilities.
        logging.warn('Skipping %r (%s): latitude=%r longitude=%r' % (
            title, key_name, record.get('latitude'),
            record.get('longitude')))
        return None, None, None
    observed = None
    if record['entry_last_updated']:
        observed = parse_shoreland_datetime(record['entry_last_updated'])

    # The CSV 'type' column corresponds to our 'category' attribute.
    CATEGORY_MAP = {
        '': '',
        'Hospital': 'HOP',
        'Clinic': '???',  # TODO
        'Dispensary': 'DISP'
        # TODO(kpy): What happened to all the other values that were in v7?
    }

    # The CSV 'category' column corresponds to our 'organization_type' attribute.
    ORGANIZATION_TYPE_MAP = {
        '': '',
        'Faith-Based Org': '???',  # TODO
        'For Profit': 'PRI',
        'Mixed': 'MIX',
        'NGO': 'NGO',
        'Public': 'PUB'
        # TODO(kpy): What happened to all the other values that were in v7?
    }

    OPERATIONAL_STATUS_MAP = {
        '': '',
        'Open': 'OPERATIONAL',
        'Closed or Closing': 'CLOSED_OR_CLOSING'
    }

    return key_name, observed, {
        'title': ValueInfo(title),
        'alt_title': ValueInfo(alt_title),
        'healthc_id': ValueInfo(record['facility_healthc_id']),
            # TODO(kpy) comment=record['AlternateHealthCIDDeleted']
        'available_beds': ValueInfo(
            record['available_beds'] and int(record['available_beds'])),
        'total_beds': ValueInfo(
            record['total_beds'] and int(record['total_beds'])),
        # Didn't bother to convert the 'services' field because it's empty
        # in the CSV from Shoreland.
        'contact_name': ValueInfo(record['contact_name']),
        'phone': ValueInfo(record['contact_phone']),
        'email': ValueInfo(record['contact_email']),
        'department': ValueInfo(record['department']),
        'district': ValueInfo(record['district']),
        'commune': ValueInfo(record['commune']),
        'address': ValueInfo(record['address']),
        'location': ValueInfo(db.GeoPt(latitude, longitude)),
            # TODO(kpy) source=record['SourceHospitalCoordinates']
            # TODO(kpy) comment=record['AlternateCoordinates']
        'organization': ValueInfo(record['organization']),
        # The 'type' and 'category' columns are swapped.
        'organization_type':
            ValueInfo(ORGANIZATION_TYPE_MAP[record['category']]),
        'category': ValueInfo(CATEGORY_MAP[record['type']]),
        # Didn't bother to convert the 'construction' field because it's empty
        # in the CSV from Shoreland.
        'damage': ValueInfo(record['damage']),
            # TODO(kpy) observed=record['DateDamage']
            # TODO(kpy) source=record['SourceDamage']
        'operational_status':
            ValueInfo(OPERATIONAL_STATUS_MAP[record['operational_status']]),
            # TODO(kpy) observed=record['DateOperationalStatus']
            # TODO(kpy) source=record['SourceOperationalStatus']
        'comments': ValueInfo(record['comments']),
        'region_id': ValueInfo(record['region_id']),
        'district_id': ValueInfo(record['district_id']),
        'commune_id': ValueInfo(record['commune_id']),
        'commune_code': ValueInfo(record['commune_code']),
        'sante_id': ValueInfo(record['sante_id'])
    }

def load_csv(
    filename, record_converter, source_url, default_observed,
    author, author_nickname, author_affiliation, limit=None):
    """Loads a CSV file of records into the datastore.

    Args:
      filename: name of the csv file to load
      record_converter: function that takes a CSV row and returns a
          (key_name, observed, values) triple, where observed is a datetime
          and values is a dictionary of attribute names to ValueInfo objects
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

    facilities = []
    minimal_facilities = []
    reports = []
    arrived = datetime.datetime.utcnow().replace(microsecond=0)

    # Store the raw file contents in a Dump.
    Dump(source=source_url, data=open(filename, 'rb').read()).put()

    facility_type = FacilityType.get_by_key_name('hospital')
    count = 0
    for record in csv.DictReader(open(filename)):
        if limit and count >= limit:
            break
        count += 1

        for key in record:
            record[key] = (record[key] or '').decode('utf-8')
        key_name, observed, value_infos = record_converter(record)
        if not key_name:  # if key_name is None, skip this record
            continue
        observed = observed or default_observed

        facility = Facility(key_name=key_name, type='hospital', author=author)
        facilities.append(facility)
        Facility.author.validate(author)

        minimal_facility = MinimalFacility(facility, type='hospital')
        minimal_facilities.append(minimal_facility)

        # Create a report for this row. ValueInfos that have a different
        # observed date than 'observed' will be reported in a separate report
        report = Report(
            facility,
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
                    facility,
                    arrived=arrived,
                    source=source_url,
                    author=author,
                    observed=info.observed)
                reports.append(current_report)

            facility.set_attribute(name, info.value, observed, author,
                                   author_nickname, author_affiliation,
                                   info.comment)
            current_report.set_attribute(name, info.value, info.comment)
            if name in facility_type.minimal_attribute_names:
                minimal_facility.set_attribute(name, info.value)

    put_batches(facilities + minimal_facilities + reports)

class ValueInfo:
    """Keeps track of an attribute value and metadata."""
    def __init__(self, value, observed=None, source=None, comment=None):
        self.value = strip_or_none(value)
        self.observed = parse_paho_date(strip_or_none(observed))
        self.comment = self.combine_comment(source, comment)

    def combine_comment(self, source, comment):
        source = strip_or_none(source)
        comment = strip_or_none(comment)
        if source is not None:
            source = 'Source: %s' % source
            comment = comment and '%s; %s' % (source, comment) or source
        return comment

def strip_or_none(value):
    """Converts strings to their stripped values or None, while preserving
    values of other types."""
    if isinstance(value, basestring):
        return value.strip() or None
    return value

def parse_paho_date(date):
    """Parses a period-separated (month.day.year) date, passes through None.
    For example, May 19, 2010 would be represented as '05.19.2010'"""
    if date is not None:
        (month, day, year) = date.split('.')
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
    while entities:
        batch, entities = entities[:200], entities[200:]
        db.put(batch)

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

def load_shoreland(filename, observed)
    """Loads a Shoreland CSV file using defaults for thee URL and author."""
    user = users.User(SHORELAND_EMAIL)
    load_csv(filename, convert_shoreland_record, SHORELAND_URL, observed, user,
             SHORELAND_NICKNAME, SHORELAND_AFFILIATION)

def wipe_and_load_shoreland(filename, observed):
    """Wipes the entire datastore and then loads a Shoreland CSV file."""
    open(filename)  # Ensure the file is readable before wiping the datastore.
    import setup
    setup.reset_datastore()
    load_shoreland(filename, observed)