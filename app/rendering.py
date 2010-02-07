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
import sys

def make_jobjects(entities, transformer, *args):
    """Run a sequence of entities through a transformer function that produces
    objects suitable for serialization to JSON, returning a list of objects
    and a dictionary that maps each entity's key to a positive numeric index
    (which is its index in the list).  Item 0 of the list is always None."""
    jobjects = [None]
    indexes = {}
    for entity in entities:
        index = len(jobjects)
        jobjects.append(transformer(index, entity, *args))
        indexes[entity.key()] = index
    return jobjects, indexes

def supply_transformer(index, supply):
    """Construct the JSON object for a Supply."""
    return {'name': supply.name, 'abbreviation': supply.abbreviation}

def facility_transformer(
    index, facility, facility_map, supplies, report_map, oldest_current_date):
    """Construct the JSON object for a facility."""
    # Add the facility to the facility lists for the containing divisions.
    for key in facility.divisions:
        facility_map.setdefault(key, []).append(index)

    # Gather all the stock level reports.
    reports = []
    for report in report_map.get(facility.key(), []):
        levels = [0 for supply in supplies]
        for supply_i, supply in enumerate(supplies):
            levels[supply_i] = getattr(report, supply.key().name(), None)
        reports.append({'date': report.date, 'levels': levels})

    # Gather the stock level history of each supply.
    histories = [[] for supply in supplies]
    for report in report_map.get(facility.key(), []):
        for supply_i, supply in enumerate(supplies):
            level = getattr(report, supply.key().name(), None)
            if level is not None:
                histories[supply_i].append(
                    {'date': report.date, 'level': level})

    # Get the last stock level of each supply.
    levels = []
    for supply_i, supply in enumerate(supplies):
        level = None
        if histories[supply_i]:
            history = histories[supply_i][-1]
            # if history['date'] >= oldest_current_date:
            level = history['level']
        levels.append(level)

    # Calculate an average daily consumption rate for each supply.
    rates = []
    for supply_i, supply in enumerate(supplies):
        last_date, last_level = None, None
        day_total = usage_total = 0.0
        for date, level in histories[supply_i]:
            if last_date is not None and last_level is not None:
                if level is not None and level < last_level:
                    day_total += (date - last_date).days
                    usage_total += last_level - level
            last_date, last_level = date, level
        rates.append(day_total and usage_total/day_total or None)

    # Pack the results into an object suitable for JSON serialization.
    facility_jobject = {
        'name': facility.name,
        'division_i': facility.division.key(),
        'stocks': [None] + levels,  # deprecated
        'histories': [None] + histories,  # unused
        'reports': reports,
        'levels': [None] + levels,
        'rates': [None] + rates
    }
    if facility.location is not None:
        facility_jobject['location'] = {
            'lat': facility.location.lat, 'lon': facility.location.lon
        }
    return facility_jobject

def district_transformer(index, district, facility_map):
    """Construct the JSON object for a district."""
    return {
        'name': district.name,
        'facility_is': facility_map.get(district.key(), [])
    }

def json_encode(object):
    """Handle JSON encoding for non-primitive objects."""
    if isinstance(object, Date):
        return object.isoformat()
    raise TypeError(repr(object) + ' is not JSON serializable')

def clean_json(json):
    return re.sub(r'"(\w+)":', r'\1:', json)

def version_to_json(version):
    """Dump the data for a given country version as a JSON string."""
    if version is None:
        return '{}'

    timestamp = version.timestamp
    version = get_base(version)

    # Get all the supply entities.
    supplies = db.get(version.supplies)

    # Make JSON objects for the supplies.
    supply_jobjects, supply_is = make_jobjects(supplies, supply_transformer)

    # Gather all the reports by facility key.
    report_map = {}
    for report in Report.all().ancestor(version).order('-date').fetch(500):
        report_map.setdefault(report._facility, []).insert(0, report)

    # Make JSON objects for the facilities, while collecting lists of the
    # facilities in each division.
    facility_map = {}
    facility_jobjects, facility_is = make_jobjects(
        Facility.all().ancestor(version).order('name'),
        facility_transformer, facility_map, supplies, report_map,
        timestamp.date() - TimeDelta(7))

    # Make JSON objects for the districts.
    districts = [district
        for district in Division.all().ancestor(version).order('name')
        if district.type.key().name() == 'arrondissement']
    division_jobjects, division_is = make_jobjects(
        districts, district_transformer, facility_map)

    # Fix up the facilities to point at the districts.
    for facility_jobject in facility_jobjects:
        if facility_jobject:
            facility_jobject['division_i'] = division_is[
                facility_jobject['division_i']]

    return clean_json(simplejson.dumps({
        'timestamp': to_posixtime(timestamp),
        'supplies': supply_jobjects,
        'facilities': facility_jobjects,
        'divisions': division_jobjects
    }, indent=2, default=json_encode))
