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

import datetime
import sys
from feeds.geo import distance
from utils import *
from model import Attribute, Facility, FacilityType, Message

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
                [attribute_is[p.name()] for p in filter(
                    lambda a: a.name() not in HIDDEN_ATTRIBUTE_NAMES,
                    facility_type.attributes)]}

def facility_transformer(index, facility, attributes, facility_type_is,
                         center, radius):
    """Construct the JSON object for a Facility."""
    # Gather all the attributes
    values = [None]
    nicknames = [None]
    affiliations = [None]
    timestamps = [None]
    comments = [None]

    # TODO(shakusa) It's probably too much data to send to include
    # all the change details. We should delay until an info bubble expansion.

    for attribute in attributes:
        name = attribute.key().name()
        values.append(getattr(facility, name, None))
        nicknames.append(getattr(facility, '%s__nickname' % name, None))
        affiliations.append(getattr(facility, '%s__affiliation' % name, None))
        timestamps.append(getattr(facility, '%s__timestamp' % name, None))
        comments.append(getattr(facility, '%s__comment' % name, None))

    # Pack the results into an object suitable for JSON serialization.
    facility_jobject = {
        'name': facility.key().name(),
        'type': facility_type_is[facility.type],
        'values' : values,
        'nicknames': nicknames,
        'affiliations': affiliations,
        'timestamps': timestamps,
        'comments': comments
    }
    if hasattr(facility, 'location'):
        location = {
            'lat': facility.location.lat,
            'lon': facility.location.lon
        }
        if center:
            facility_jobject['distance_meters'] = distance(location, center)

    if facility_jobject.get('distance_meters') > radius > 0:
        return None

    return facility_jobject

def json_encode(object):
    """Handle JSON encoding for non-primitive objects."""
    if isinstance(object, Date) or isinstance(object, datetime.datetime):
        return to_local_isotime(object)
    if isinstance(object, db.GeoPt):
        return {'lat': object.lat, 'lon': object.lon}
    raise TypeError(repr(object) + ' is not JSON serializable')

def clean_json(json):
    return re.sub(r'"(\w+)":', r'\1:', json)

def to_json(center=None, radius=None):
    """Dump the data as a JSON string."""

    # Get all the attributes.
    attributes = filter(lambda a: a.key().name() not in HIDDEN_ATTRIBUTE_NAMES,
                        list(Attribute.all().order('__key__')))
    attribute_jobjects, attribute_is = make_jobjects(
        attributes, attribute_transformer)

    # Make JSON objects for the facility types.
    facility_type_jobjects, facility_type_is = make_jobjects(
        FacilityType.all(), facility_type_transformer, attribute_is)

    # Make JSON objects for the facilities, while collecting lists of the
    # facilities in each division.
    facility_jobjects, facility_is = make_jobjects(
        Facility.all().order('title'), facility_transformer,
        attributes, facility_type_is, center, radius)
    total_facility_count = len(facility_jobjects) - 1
    logging.info("NUMBER OF FACILITIES %d" % total_facility_count)

    # Sort by distance, if necessary.
    if center:
        facility_jobjects.sort(key=lambda f: f and f.get('distance_meters'))

    # Get all the messages for the current language.
    message_jobjects = {}
    for message in Message.all():
        namespace = message_jobjects.setdefault(message.namespace, {})
        django_locale = django.utils.translation.to_locale(
            django.utils.translation.get_language())
        namespace[message.name] = getattr(message, django_locale)

    return clean_json(simplejson.dumps({
        'total_facility_count': total_facility_count,
        'attributes': attribute_jobjects,
        'facility_types': facility_type_jobjects,
        'facilities': facility_jobjects,
        'messages': message_jobjects
    }, indent=2, default=json_encode))
