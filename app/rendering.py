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
from model import Attribute, Division, Facility, FacilityType, Message, Report
import sys

def make_jobjects(entities, transformer, *args):
    """Run a sequence of entities through a transformer function that produces
    objects suitable for serialization to JSON, returning a list of objects
    and a dictionary that maps each entity's key_name to its index in the list.
    Item 0 of the list is always None."""
    jobjects = [None]
    indexes = {}
    for entity in entities:
        index = len(jobjects)
        jobjects.append(transformer(index, entity, *args))
        indexes[entity.key().name()] = index
    return jobjects, indexes

def attribute_transformer(index, attribute):
    """Construct the JSON object for an Attribute."""
    return {'name': attribute.key().name(),
            'type': attribute.type,
            'values': attribute.values}

def facility_type_transformer(index, facility_type, attribute_is):
    """Construct the JSON object for a FacilityType."""
    return {'name': facility_type.key().name(),
            'attribute_is': [attribute_is[p] for p in facility_type.attributes]}

def facility_transformer(
    index, facility, attributes, report_map, facility_type_is, facility_map):
    """Construct the JSON object for a Facility."""
    # Add the facility to the facility lists for its containing divisions.
    for name in facility.division_names:
        facility_map.setdefault(name, []).append(index)

    # Gather all the reports.
    reports = []
    for report in report_map.get(facility.key().name(), []):
        values = [None]
        for attribute in attributes:
            values.append(getattr(report, attribute.key().name(), None))
        reports.append({'date': report.date, 'values': values})

    # Pack the results into an object suitable for JSON serialization.
    facility_jobject = {
        'title': facility.title,
        'name': facility.key().name(),
        'type': facility_type_is[facility.type],
        'division_i': facility.division_name,
        'last_report': reports and reports[-1] or None
    }
    if facility.location is not None:
        facility_jobject['location'] = {
            'lat': facility.location.lat, 'lon': facility.location.lon
        }
    return facility_jobject

def division_transformer(index, division, facility_map):
    """Construct the JSON object for a division."""
    return {
        'title': division.title,
        'facility_is': facility_map.get(division.key().name(), [])
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

    # Get all the attributes.
    attributes = list(Attribute.all().ancestor(version).order('__key__'))
    attribute_jobjects, attribute_is = make_jobjects(
        attributes, attribute_transformer)

    # Make JSON objects for the facility types.
    facility_type_jobjects, facility_type_is = make_jobjects(
        FacilityType.all().ancestor(version),
        facility_type_transformer, attribute_is)

    # Gather all the reports by facility ID.
    report_map = {}
    for report in Report.all().ancestor(version).order('-timestamp').fetch(500):
        report_map.setdefault(report.facility_name, []).insert(0, report)

    # Make JSON objects for the facilities, while collecting lists of the
    # facilities in each division.
    facility_map = {}
    facility_jobjects, facility_is = make_jobjects(
        Facility.all().ancestor(version), facility_transformer,
        attributes, report_map, facility_type_is, facility_map)

    # Make JSON objects for the districts.
    division_jobjects, division_is = make_jobjects(
        Division.all().ancestor(version).filter('type =', 'arrondissement'),
        division_transformer, facility_map)

    # Fix up the facilities to point at the districts.
    for facility_jobject in facility_jobjects:
        if facility_jobject:
            facility_jobject['division_i'] = division_is[
                facility_jobject['division_i']]

    # Get all the messages.
    message_jobjects = {}
    for message in Message.all().ancestor(version):
        namespace = message_jobjects.setdefault(message.namespace, {})
        namespace[message.name] = dict((lang, getattr(message, lang))
                                       for lang in message.dynamic_properties())

    return clean_json(simplejson.dumps({
        'timestamp': to_posixtime(timestamp),
        'attributes': attribute_jobjects,
        'facility_types': facility_type_jobjects,
        'facilities': facility_jobjects,
        'divisions': division_jobjects,
        'messages': message_jobjects
    }, indent=2, default=json_encode))
