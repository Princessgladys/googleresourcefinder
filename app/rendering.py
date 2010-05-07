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

from feeds.geo import distance
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
        jobject = transformer(index, entity, *args)
        if jobject is not None:
            jobjects.append(jobject)
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
            'attribute_is':
                [attribute_is[p] for p in facility_type.attribute_names]}

def user_transformer(user, hide_email):
    address = 'anonymous'
    if user:
        address = user.email()
        if hide_email:
            # Preserve the first letter of the username, then replace the
            # (up to) 3 last characters of the username with '...'.
            address = re.sub(r'^(\w+?)\w{0,3}@', r'\1...@', address)
    return {'email': address}

def facility_transformer(index, facility, attributes, report_map,
                         facility_type_is, facility_map, hide_email,
                         center, radius):
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
        reports.append({'date': report.date,
                        'values': values,
                        'user': user_transformer(report.user, hide_email)})

    # Pack the results into an object suitable for JSON serialization.
    facility_jobject = {
        'title': facility.title,
        'name': facility.key().name(),
        'type': facility_type_is[facility.type],
        'division_i': facility.division_name,
        'reports': reports and reports[-10:] or None,
        'last_report': reports and reports[-1] or None
    }
    if facility.location:
        facility_jobject['location'] = {
            'lat': facility.location.lat,
            'lon': facility.location.lon
        }
        if center:
            facility_jobject['distance_meters'] = distance(
                facility_jobject['location'], center)

    if facility_jobject.get('distance_meters') > radius > 0:
        return None

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

def version_to_json(version, hide_email, center=None, radius=None):
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
    num_reports = 0
    for report in Report.all().ancestor(version).order('-timestamp'):
        report_map.setdefault(report.facility_name, []).insert(0, report)
        num_reports = num_reports + 1
        #report_map.setdefault(report.facility_name, []).append(report)
    total_facility_count = len(report_map)
    logging.info("NUMBER OF FACILITIES %d, REPORTS %d"
                 % (total_facility_count, num_reports))

    # Make JSON objects for the facilities, while collecting lists of the
    # facilities in each division.
    facility_map = {}
    facility_jobjects, facility_is = make_jobjects(
        Facility.all().ancestor(version).order('title'), facility_transformer,
        attributes, report_map, facility_type_is, facility_map, hide_email,
        center, radius)

    # Make JSON objects for the districts.
    division_jobjects, division_is = make_jobjects(
        Division.all().ancestor(version).filter('type =', 'departemen'),
        division_transformer, facility_map)

    # Fix up the facilities to point at the districts.
    for facility_jobject in facility_jobjects:
        if facility_jobject:
            facility_jobject['division_i'] = division_is[
                facility_jobject['division_i']]

    # Sort by distance, if necessary.
    if center:
        facility_jobjects.sort(key=lambda f: f and f.get('distance_meters'))

    # Get all the messages for the current language.
    message_jobjects = {}
    for message in Message.all().ancestor(version):
        namespace = message_jobjects.setdefault(message.namespace, {})
        django_locale = django.utils.translation.to_locale(
            django.utils.translation.get_language())
        namespace[message.name] = getattr(message, django_locale)

    return clean_json(simplejson.dumps({
        'total_facility_count': total_facility_count,
        'timestamp': to_posixtime(timestamp),
        'attributes': attribute_jobjects,
        'facility_types': facility_type_jobjects,
        'facilities': facility_jobjects,
        'divisions': division_jobjects,
        'messages': message_jobjects
    }, indent=2, default=json_encode))
