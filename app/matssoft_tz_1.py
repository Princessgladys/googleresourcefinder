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

"""Loader for Tanzania data from Matssoft."""

from google.appengine.ext import db
from utils import *

SUPPLY_ORDER = ['yellow', 'blue', 'red', 'green', 'quinine']

SUPPLIES = {
    'yellow': {'name': 'Coartem 6 yellow', 'abbreviation': 'Y'},
    'blue': {'name': 'Coartem 12 blue', 'abbreviation': 'B'},
    'red': {'name': 'Coartem 18 red', 'abbreviation': 'R'},
    'green': {'name': 'Coartem 24 green', 'abbreviation': 'G'},
    'quinine': {'name': 'Quinine injectables', 'abbreviation': 'Q'},
}

DIVISION_TYPES = {
    'region': {'singular': 'region', 'plural': 'regions'},
    'district': {'singular': 'district', 'plural': 'districts'},
}

class WriteBuffer:
    def __init__(self, batch_size=300, retries=3):
        self.pending = []
        self.batch_size = batch_size
        self.retries = 3

    def put(self, entities):
        if not isinstance(entities, list):
            entities = [entities]
        self.pending += entities
        while len(self.pending) >= self.batch_size:
            self.put_batch()

    def flush(self):
        while self.pending:
            self.put_batch()

    def put_batch(self):
        batch = self.pending[:self.batch_size]
        self.pending[:self.batch_size] = []
        logging.info('writing batch of size %d' % len(batch))
        exception = None
        for retry in range(self.retries):
            try:
                db.put(batch)
                return
            except Exception, e:
                exception = e
                logging.warn(e)
        raise exception
    
buffer = WriteBuffer()
put = buffer.put
flush = buffer.flush

def put_dump(version, dump):
    logging.info('put_dump started')
    root = simplejson.loads(dump)
    supplies = put_data(version, Supply, SUPPLIES)
    division_types = put_data(version, DivisionType, DIVISION_TYPES)
    version.supplies = [supplies[kn].key() for kn in SUPPLY_ORDER]
    version.put()

    REGION = division_types['region']
    DISTRICT = division_types['district']
    divisions, locations = {}, {}
    for facility in root['facilities']:
        rkn = make_division(divisions, version, REGION, facility['region_name'])
        dkn = make_division(
            divisions, version, DISTRICT, facility['district_name'], rkn)
        location = None
        if (facility.get('latitude', None) is not None and
            facility.get('longitude', None) is not None):
            location = db.GeoPt(
                float(facility['latitude']), float(facility['longitude']))
            locations[rkn] = locations.get(rkn, []) + [location]
            locations[dkn] = locations.get(dkn, []) + [location]
        put_facility(version, facility['id'], facility['name'], location,
                     divisions[rkn], divisions[dkn], facility.get('stock', []))

    # Patch up regions and districts with central geolocations.
    for kn in locations:
        divisions[kn].location = centroid(locations[kn])
    logging.info('divisions: %d' % len(divisions))
    put(divisions.values())

    flush()
    logging.info('put_dump finished')

def centroid(locations):
    return db.GeoPt(sum(location.lat for location in locations)/len(locations),
                    sum(location.lon for location in locations)/len(locations))

def put_data(version, Kind, data):
    entities = dict((key, Kind(version, key, **data[key])) for key in data)
    put(entities.values())
    return entities

def make_division(divisions, version, type, name, super_kn=None):
    id = make_identifier(name)
    kn = type.key().name() + '.' + id
    divisions[kn] = Division(version, key_name=kn, id=id, type=type,
                             superdivision=divisions.get(super_kn), name=name)
    return kn

def put_facility(version, id, name, location, region, district, reports):
    logging.info('facility: %s, reports: %d' % (name, len(reports)))
    facility = Facility(version, key_name=id, id=id, name=name,
                        location=location, division=district,
                        divisions=[region.key(), district.key()])
    put(facility)
    for report in reports:
        year, month, day = map(int, report['date'].split('-'))
        date = Date(year, month, day)
        entity = Report(version, facility=facility, date=date)
        for key in report:
            if key in SUPPLIES and report[key] is not None:
                setattr(entity, key, float(report[key]))
        put(entity)
    return facility
