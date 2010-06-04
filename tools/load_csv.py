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

from google.appengine.api import memcache
from google.appengine.api import users

from model import *
from simplejson import decoder

import csv
import datetime
import logging
import re
import setup
import urllib

SHORELAND_URL = 'http://shoreland.com/'
SHORELAND_EMAIL = 'admin@shoreland.com'
SHORELAND_NICKNAME = 'Shoreland Contact Name'
SHORELAND_AFFILIATION = 'Shoreland Inc.'

US_HOSPITAL_URL = 'http://www.google.com/'
US_HOSPITAL_EMAIL = 'us_hospital@resourcefinder.appspotmail.com'
US_HOSPITAL_NICKNAME = 'US Hospital Contact Name'
US_HOSPITAL_AFFILIATION = 'United States of America'

json_decoder = decoder.JSONDecoder()

delay = 0
num_sans_delay = 0

def convert_paho_record(record):
    """Converts a dictionary of values from one row of a PAHO CSV file
    into a dictionary of ValueInfo objects for our datastore."""

    title = (record['Fac_NameFr'].strip() or record['NomInstitu'].strip())

    if not record.get('HealthC_ID').strip():
        # TODO(shakusa) Fix this. We should be importing all facilities.
        logging.warn('Skipping %r (%s): Invalid HealthC_ID: "%s"' % (
            title, record.get('PCode'), record.get('HealthC_ID')))
        return None, None, None

    key_name = 'paho.org/HealthC_ID/' + record['HealthC_ID']
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
    """Converts a dictionary of values from one row of a US Hospital CSV file
    into a dictionary of ValueInfo objects for our datastore."""
    title = record['facility_name'].strip()

    if not record.get('facility_healthc_id').strip():
        # TODO(shakusa) Fix this. We should be importing all facilities.
        logging.warn('Skipping %r (%s): Invalid HealthC_ID: "%s"' % (
            title, record.get('facility_pcode'),
            record.get('facility_healthc_id')))
        return None, None, None

    key_name = 'paho.org/HealthC_ID/' + record['facility_healthc_id']
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
        'pcode': ValueInfo(record['facility_pcode']),
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
    
def convert_us_hospital_record(record):
    """Converts a dictionary of values from one row of a Shoreland CSV file
    into a dictionary of ValueInfo objects for our datastore."""
    title = record['Hospital Name'].strip()
    key_name = 'paho.org/Provider_Number/' + record['Provider Number'].strip()
    observed = None
    
    geocode_base_url = 'http://maps.google.com/maps/api/geocode/json?address='
    address = re.sub('\s+', '+', record['Address'].strip())
    db_form_address = re.sub('\s+', ' ', record['Address'].strip())
    url = geocode_base_url + address + '&sensor=false'
    
    geocode_pending = True
    while geocode_pending:
        result = urllib.urlopen(url).read()
        dict_result = json_decoder.decode(result)
        if dict_result[u'status'] != 'OK':
            if delay == 0:
                delay = 1
            else:
                delay += delay
            num_sans_delay = 0
        else:
            logging.info('here')
            num_sans_delay += 1
            geocode_pending = False
        logging.info(dict_result[u'status'] + ' ' + record['Hospital Name'])

    if num_sans_delay == 5 and delay > 0:
        delay -= 1
        num_sans_delay = 0
               
    loc = dict_result[u'results'][0][u'geometry'][u'location']
    latitude = loc[u'lat']
    longitude = loc[u'lng']

    return key_name, observed, {
        'title': ValueInfo(title),
        'Provider_Number': ValueInfo(record['Provider Number']),
        'Hospital_Type': ValueInfo(record['Hospital Type']),
        'Emergency_Services': ValueInfo(record['Emergency Services']),
        'Contact_Name': ValueInfo(US_HOSPITAL_NICKNAME),
        'Phone_Number': ValueInfo(record['Phone Number']),
        'Email': ValueInfo(US_HOSPITAL_EMAIL),
        'Address': ValueInfo(db_form_address),
        'City': ValueInfo(record['City']),
        'State': ValueInfo(record['State']),
        'ZIP_Code': ValueInfo(record['ZIP Code']),
        'location': ValueInfo(db.GeoPt(latitude, longitude)),
        'Heart_Attack_30-Day_Mortality': ValueInfo(
            record['Heart Attack 30-Day Mortality']),
        'Heart_Failure_30-Day_Mortality': ValueInfo(
            record['Heart Failure 30-Day Mortality']),
        'Pneumonia_30-Day_Mortality': ValueInfo(
            record['Pneumonia 30-Day Mortality']),
        'Heart_Attack_30-Day_Readmission': ValueInfo(
            record['Heart Attack 30-Day Readmission']),
        'Heart_Failure_30-Day_Readmission': ValueInfo(
            record['Heart Failure 30-Day Readmission']),
        'Pneumonia_30-Day_Readmission': ValueInfo(
            record['Pneumonia 30-Day Readmission']),
        'Aspirin_on_Heart_Attack_Arrival': ValueInfo(
            record['Aspirin on Heart Attack Arrival']),
        'Aspirin_on_Heart_Attack_Discharge': ValueInfo(
            record['Aspirin on Heart Attack Discharge']),
        'ACE_or_ARB_for_Heart_Attack_and_LVSD': ValueInfo(
            record['ACE or ARB for Heart Attack and LVSD']),
        'Beta_Blocker_on_Heart_Attack_Discharge': ValueInfo(
            record['Beta Blocker on Heart Attack Discharge']),
        'Smoking_Cessation_Heart_Attack': ValueInfo(
            record['Smoking Cessation Heart Attack']),
        'Fibrinolytic_Within_30_Minutes_Heart_Attack_Arrival': ValueInfo(
            record['Fibrinolytic Within 30 Minutes Heart Attack Arrival']),
        'PCI_Within_90_Minutes_Heart_Attack_Arrival': ValueInfo(
            record['PCI Within 90 Minutes Heart Attack Arrival']),
        'LV_Systolic_Eval_for_Heart_Failure': ValueInfo(
            record['LV Systolic Eval for Heart Failure']),
        'ACE_or_ARB_for_Heart_Failure_and_LVSD': ValueInfo(
            record['ACE or ARB for Heart Failure and LVSD']),
        'Discharge_Instructions_Heart_Failure': ValueInfo(
            record['Discharge Instructions Heart Failure']),
        'Smoking_Cessation_Heart_Failure': ValueInfo(
            record['Smoking Cessation Heart Failure']),
        'Pneumococcal_Vaccine_for_Pneumonia': ValueInfo(
            record['Pneumococcal Vaccine for Pneumonia']),
        'Antibiotics_within_6_Hours_for_Pneumonia': ValueInfo(
            record['Antibiotics within 6 Hours for Pneumonia']),
        'Blood_Culture_Before_Antibiotics_for_Pneumonia': ValueInfo(
            record['Blood Culture Before Antibiotics for Pneumonia']),
        'Smoking_Cessation_Heart_Failure_2': ValueInfo(
            record['Smoking Cessation Heart Failure 2']),
        'Most_Appropriate_Antibiotic_for_Pneumonia': ValueInfo(
            record['Most Appropriate Antibiotic for Pneumonia']),
        'Flu_Vaccine_for_Pneumonia': ValueInfo(
            record['Flu Vaccine for Pneumonia']),
        'Antibiotics_Within_1_Hour_Before_Surgery': ValueInfo(
            record['Antibiotics Within 1 Hour Before Surgery']),
        'Antibiotics_Stopped_Within_24_hours_After_Surgery': ValueInfo(
            record['Antibiotics Stopped Within 24 hours After Surgery']),
        'Appropriate_Antibiotics_for_Surgery': ValueInfo(
            record['Appropriate Antibiotics for Surgery']),
        'Blood_Clot_Prevention_Within 24_hours_Before_or_After_Surgery':
            ValueInfo(record[
            'Blood Clot Prevention Within 24 hours Before or After Surgery']),
        'Blood_Clot_Prevention_After_Certain_Surgeries': ValueInfo(
            record['Blood Clot Prevention After Certain Surgeries']),
        'Sugar_Control_after_Heart_Surgery': ValueInfo(
            record['Sugar Control after Heart Surgery']),
        'Safer_Hair_Removal_for_Surgery': ValueInfo(
            record['Safer Hair Removal for Surgery']),
        'Beta_Blockers_Maintained_for_Surgery': ValueInfo(
            record['Beta Blockers Maintained for Surgery']),
        'Pain_Relief_Children_Asthma_Admission': ValueInfo(
            record['Pain Relief Children Asthma Admission']),
        'Corticosteroid_Children_Asthma_Admission': ValueInfo(
            record['Corticosteroid Children Asthma Admission']),
        'Caregiver_Plan_Children_Asthma_Admission': ValueInfo(
            record['Caregiver Plan Children Asthma Admission']),
        'Nurses_"Always"_Communicated_Well': ValueInfo(
            record['Nurses "Always" Communicated Well']),
        'Doctors_"Always"_Communicated_Well': ValueInfo(
            record['Doctors "Always" Communicated Well']),
        'Patients_"Always"_Received_Help_When_Wanted': ValueInfo(
            record['Patients "Always" Received Help When Wanted']),
        'Pain_"Always"_Well_Controlled': ValueInfo(
            record['Pain "Always" Well Controlled']),
        'Medicines_"Always"_Explained_Before_Administered': ValueInfo(
            record['Medicines "Always" Explained Before Administered']),
        'Room_and_Bathroom_"Always"_Clean': ValueInfo(
            record['Room and Bathroom "Always" Clean']),
        'Room_"Always"_Quiet_at_Night': ValueInfo(
            record['Room "Always" Quiet at Night']),
        'Home_Recovery_Instructions_Given': ValueInfo(
            record['Home Recovery Instructions Given']),
        'Patient_Rating_of_9-10': ValueInfo(
            record['Patient Rating of 9-10']),
        'Patient_Recommended_Hospital': ValueInfo(
            record['Patient Recommended Hospital'])
    }

def load_csv(
    filename, record_converter, source_url, default_observed,
    author, author_nickname, author_affiliation, facility_type_str, limit=None):
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
    # TODO(pfritzsche) upload files > 1mb
    #Dump(source=source_url, data=open(filename, 'rb').read()).put()

    facility_type = FacilityType.get_by_key_name(facility_type_str)
    count = 0
    delay = 0
    num_sans_delay = 0
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

        facility = Facility(key_name=key_name, type=facility_type_str,
                            author=author)
        facilities.append(facility)
        Facility.author.validate(author)

        minimal_facility = MinimalFacility(facility, type=facility_type_str)
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
    count, total = 0, len(entities)
    while entities:
        batch, entities = entities[:50], entities[50:]
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
    setup.setup_new_datastore()
    if isinstance(observed, basestring):
        observed = parse_datetime(observed)
    user = users.User(SHORELAND_EMAIL)
    load_csv(filename, convert_shoreland_record, SHORELAND_URL, observed, user,
             SHORELAND_NICKNAME, SHORELAND_AFFILIATION, 'hospital')

def wipe_and_load_shoreland(filename, observed):
    """Wipes the entire datastore and then loads a Shoreland CSV file."""
    open(filename)  # Ensure the file is readable before wiping the datastore.
    setup.wipe_datastore()
    load_shoreland(filename, observed)

def load_us_hospital(filename, observed):
    """Loads a US Hospital CSV file using defaults for the URL and author."""
    setup.setup_new_datastore()
    if isinstance(observed, basestring):
        observed = parse_datetime(observed)
    user = users.User(US_HOSPITAL_EMAIL)
    load_csv(filename, convert_us_hospital_record, US_HOSPITAL_URL, observed,
             user, US_HOSPITAL_NICKNAME, US_HOSPITAL_AFFILIATION, 'us_hospital')
             
def wipe_and_load_us_hospital(filename, observed):
    """Wipes the entire datastore and then loads a US Hospital CSV file."""
    open(filename)
    setup.wipe_datastore()
    load_us_hospital(filename, observed)