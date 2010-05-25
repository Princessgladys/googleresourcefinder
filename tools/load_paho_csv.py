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
from setup import *
import csv
import datetime
import logging

def load_paho_csv(
    filename, source_url, observed, author, author_nickname,
    author_affiliation, limit=None):
    """Loads the PAHO master list as a CSV file.

    Args:
      filename: name of the csv file to load
      source_url: where filename was downloaded, stored in Report.source
      observed: datetime.datetime when the data was observed to be valid
      author: users.User who will own the changes made during loading
      author_nickname: nickname for the author
      author_affiliation: organizational affiliation of the author
      limit: maximum number of records to load (default: load all)"""

    if (not filename or not source_url or not observed or not author or
        not author_nickname or not author_affiliation):
        raise Exception('All arguments must be non-empty.')

    facilities = []
    minimal_facilities = []
    reports = []

    # Create a dump of the raw file
    Dump(source=source_url, data=open(filename, 'rb').read()).put()

    count = 0
    for record in csv.DictReader(open(filename)):
        if limit and count >= limit:
            break
        count += 1
        for key in record:
            record[key] = record[key].decode('utf-8')
        facility_name = 'mspphaiti.org..' + record['PCode']
        title = (record['Fac_NameFr'].strip() or record['NomInstitu'].strip())
        alt_title = (title == record['Fac_NameFr'].strip() and
                     record['NomInstitu'].strip() or '')
        try:
            latitude = float(record['X_DDS'])
            longitude = float(record['Y_DDS'])
        except ValueError:
            # TODO(shakusa) Fix this. We should be importing all facilities.
            logging.warning('Ignoring facility "%s" (%s) with invalid lat,lon',
                            title, facility_name)
            continue

        attrs = {
            'title': Attribute(title),
            'alt_title': Attribute(alt_title),
            'healthc_id': Attribute(
                record['HealthC_ID'],
                comment=record['AlternateHealthCIDDeleted']),
            'organization': Attribute(record['Oorganisat']),
            'departemen': Attribute(record['Departemen']),
            'district': Attribute(record['DistrictNom']),
            'commune': Attribute(record['Commune']),
            'address': Attribute(record['Address']),
            'location': Attribute(db.GeoPt(latitude, longitude),
                                  source=record['SourceHospitalCoordinates'],
                                  comment=record['AlternateCoordinates']),
            'accuracy': Attribute(record['Accuracy']),
            'phone': Attribute(record['Telephone']),
            'email': Attribute(record['email']),
            'facility_type': Attribute(record['Type']),
            'category': Attribute(record['Categorie']),
            'damage': Attribute(record['Damage'], observed=record['DateDamage'],
                                source=record['SourceDamage']),
            'operational_status': Attribute(
                record['OperationalStatus'],
                observed=record['DateOperationalStatus'],
                source=record['SourceOperationalStatus']),
            'comments': Attribute(record['Comment']),
            'region_id': Attribute(record['RegionId']),
            'district_id': Attribute(record['DistrictId']),
            'commune_id': Attribute(record['CommuneId']),
            'commune_code': Attribute(record['CodeCommun']),
            'sante_id': Attribute(record['SanteID'])
        }

        facility = Facility(
            key_name=facility_name,
            type='hospital',
            author=author)
        facilities.append(facility)
        Facility.author.validate(author)

        minimal_facility = MinimalFacility(facility, type='hospital')
        minimal_facilities.append(minimal_facility)

        utcnow = datetime.datetime.utcnow().replace(microsecond=0)

        # Create a report for this row. Attributes that have a different
        # observed date than 'observed' will be reported in a separate report
        report = Report(
            facility,
            arrived=utcnow,
            source=source_url,
            author=author,
            observed=observed)
        reports.append(report)

        for (name, attr) in attrs.items():
            if not attr.value and attr.value != 0:
                continue

            current_report = report
            if attr.observed and observed != attr.observed:
                # Separate out this change into a new report
                current_report = Report(
                    facility,
                    arrived=utcnow,
                    source=source_url,
                    author=author,
                    observed=attr.observed)
                reports.append(current_report)

            facility.set_attribute(name, attr.value, observed, author,
                                   author_nickname, author_affiliation,
                                   attr.comment)
            current_report.set_attribute(name, attr.value, attr.comment)
            if name in facility_type.minimal_attribute_names:
                minimal_facility.set_attribute(name, attr.value)

    put_batches(facilities + minimal_facilities + reports)

class Attribute:
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
    if isinstance(value, basestring):
        value = value.strip()
    return value or None

def parse_paho_date(date):
    """Parses a period-separated (month.day.year) date, passes through None.
    For example, May 19, 2010 would be represented as '05.19.2010'"""
    if date is not None:
        (month, day, year) = date.split('.')
        date = datetime.datetime(int(year), int(month), int(day))
    return date

def put_batches(entities):
    """Works around annoying limitations of App Engine's datastore."""
    while entities:
        batch, entities = entities[:200], entities[200:]
        db.put(batch)
