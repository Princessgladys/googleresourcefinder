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
    filename, observed, user, source, source_affiliation):
    """Loads the PAHO master list as a CSV file.

    Args:
      filename: name of the file
      observed: datetime.datetime when the data was observed to be valid
      user: users.User who will own the changes made during loading
      source: source of the changes, may just be nickname for the user
      source_affiliation: if source is a proper name, this is the
                          organizational affiliation of the source, otherwise
                          can be empty"""

    if not filename or not observed or not user or not source:
        raise Exception('filename, observed, user, and source are required')

    facilities = []
    reports = []

    # Create a dump of the raw file
    Dump(source=filename, data=open(filename, 'rb').read()).put()

    for record in csv.DictReader(open(filename)):
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
            # TODO(shakusa) There are ~70 that cause this warning. Isn't this
            # a problem?
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
            user=user)
        facilities.append(facility)
        Facility.user.validate(user)

        utcnow = datetime.datetime.utcnow().replace(microsecond=0)

        # Create a report for this row. Attributes that have a different
        # observed date than 'observed' will be reported in a separate report
        report = Report(
            facility,
            arrived=utcnow,
            observed=observed,
            user=user,
            source=source,
            source_affiliation=source_affiliation)
        reports.append(report)

        for (name, attr) in attrs.items():
            if not attr.value and attr.value != 0:
                continue

            current_report = report
            if ((attr.source and source != attr.source)
                or (attr.observed and observed != attr.observed)):
                # Separate out this change into a new report
                current_report = Report(
                    facility,
                    arrived=utcnow,
                    observed=attr.observed or observed,
                    user=user,
                    source=attr.source or source,
                    source_affiliation=(
                        not attr.source and source_affiliation or None))
                reports.append(current_report)

            setattr(current_report, '%s__' % name, attr.value)
            setattr(facility, '%s__' % name, attr.value)

            if attr.comment:
                setattr(current_report, '%s__comment' % name, attr.comment)
                setattr(facility, '%s__comment' % name, attr.comment)

            if not attr.source:
                setattr(facility, '%s__affiliation' % name, source_affiliation)

            setattr(facility, '%s__source' % name, attr.source or source)
            setattr(facility, '%s__user' % name, user)
            setattr(facility, '%s__observed' % name, attr.observed or observed)

    put_batches(facilities + reports)

class Attribute:
    """Keeps track of an attribute value and metadata."""
    def __init__(self, value, observed=None, source=None, comment=None):
        self.value = strip_or_none(value)
        self.observed = parse_paho_date(strip_or_none(observed))
        self.source = strip_or_none(source)
        self.comment = strip_or_none(comment)

def strip_or_none(value):
    if isinstance(value, basestring):
        value = value.strip()
    return value or None

def parse_paho_date(date):
    """Parses a period-separated (month.day.year) date.
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
