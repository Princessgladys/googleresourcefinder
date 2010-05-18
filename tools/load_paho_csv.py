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

def load_paho_csv(filename,
                  user=users.get_current_user(),
                  account_nickname=users.get_current_user().nickname(),
                  account_affiliation=''):
    """Loads the PAHO master list as a CSV file."""
    facilities = []
    reports = []

    # TODO: Create a Dump record with the filename?

    def strip_or_none(value):
        if isinstance(value, basestring):
            value = value.strip()
        return value or None

    def attr(value, date=None, source=None, comment=None):
        return {'value': strip_or_none(value),
                'date': strip_or_none(date),
                'source': strip_or_none(source),
                'comment': strip_or_none(comment)}

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
            'title': attr(title),
            'alt_title': attr(alt_title),
            'healthc_id': attr(record['HealthC_ID'],
                               comment=record['AlternateHealthCIDDeleted']),
            'organization': attr(record['Oorganisat']),
            'departemen': attr(record['Departemen']),
            'district': attr(record['DistrictNom']),
            'commune': attr(record['Commune']),
            'address': attr(record['Address']),
            'location': attr(db.GeoPt(latitude, longitude),
                                source=record['SourceHospitalCoordinates'],
                                comment=record['AlternateCoordinates']),
            'accuracy': attr(record['Accuracy']),
            'phone': attr(record['Telephone']),
            'email': attr(record['email']),
            'facility_type': attr(record['Type']),
            'category': attr(record['Categorie']),
            'damage': attr(record['Damage'], date=record['DateDamage'],
                           source=record['SourceDamage']),
            'operational_status': attr(record['OperationalStatus'],
                                       date=record['DateOperationalStatus'],
                                       source=record['SourceOperationalStatus']),
            'comments': attr(record['Comment']),
            'region_id': attr(record['RegionId']),
            'district_id': attr(record['DistrictId']),
            'commune_id': attr(record['CommuneId']),
            'commune_code': attr(record['CodeCommun']),
            'sante_id': attr(record['SanteID'])
        }

        facility = Facility(
            key_name=facility_name,
            type='hospital',
            user=user)
        facilities.append(facility)
        Facility.user.validate(user)

        utcnow = datetime.datetime.utcnow().replace(microsecond=0)

        report = FacilityReport(
            facility,
            observation_timestamp=utcnow,
            user=user)
        reports.append(report)

        for (name, attrib) in attrs.items():
            if not attrib['value'] and attrib['value'] != 0:
                continue

            setattr(report, name, attrib['value'])
            setattr(facility, name, attrib['value'])

            if attrib['comment']:
                setattr(report, '%s__comment' % name, attrib['comment'])
                setattr(facility, '%s__comment' % name, attrib['comment'])

            if attrib['source']:
                setattr(facility, '%s__nickname' % name, attrib['source'])
            else:
                if account_nickname:
                    setattr(facility, '%s__nickname' % name, account_nickname)
                if account_affiliation:
                    setattr(facility, '%s__affiliation' % name,
                            account_affiliation)

            setattr(facility, '%s__user' % name, user)

            if attrib['date']:
                (month, day, year) = attrib['date'].split('.')
                timestamp = datetime.datetime(int(year), int(month), int(day))
                setattr(report, '%s__timestamp' % name, timestamp)
            else:
                timestamp = utcnow
            setattr(facility, '%s__timestamp' % name, timestamp)

    put_batches(facilities + reports)

def put_batches(entities):
    """Works around annoying limitations of App Engine's datastore."""
    while entities:
        batch, entities = entities[:200], entities[200:]
        db.put(batch)
