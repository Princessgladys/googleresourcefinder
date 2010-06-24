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

import cache
import datetime
import re
import sets
import sys
from feeds.geo import distance
from model import Attribute, Subject, SubjectType, Message, MinimalSubject
from utils import Date, HIDDEN_ATTRIBUTE_NAMES, db, get_locale, simplejson

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

def subject_type_transformer(index, subject_type, attribute_is):
    """Construct the JSON object for a SubjectType."""
    return {'name': subject_type.key().name(),
            'attribute_is':
                [attribute_is[p] for p in filter(
                    lambda n: n not in HIDDEN_ATTRIBUTE_NAMES,
                    subject_type.minimal_attribute_names)]}

def get_subject_type(subject_types, subject):
    """In a list of SubjectType entities, finds the one for a given Subject."""
    for subject_type in subject_types:
        if subject_type.key().name() == subject.type:
            return subject_type

def minimal_subject_transformer(index, subject, attributes, subject_types,
                                subject_type_is, center, radius):
    """Construct the JSON object for a Subject."""
    # Gather all the attributes
    values = [None]

    subject_type = get_subject_type(subject_types, subject)
    for attribute in attributes:
        name = attribute.key().name()
        if name in subject_type.minimal_attribute_names:
            values.append(subject.get_value(name))
        else:
            values.append(None)

    # Pack the results into an object suitable for JSON serialization.
    subject_jobject = {
        'name': subject.parent_key().name(),
        'type': subject_type_is[subject.type],
        'values' : values,
    }
    if subject.has_value('location'):
        location = {
            'lat': subject.get_value('location').lat,
            'lon': subject.get_value('location').lon
        }
        if center:
            subject_jobject['distance_meters'] = distance(location, center)

    dist = subject_jobject.get('distance_meters')
    if center and (dist is None or dist > radius > 0):
        return None

    return subject_jobject

def json_encode(object):
    """Handle JSON encoding for non-primitive objects."""
    if isinstance(object, Date) or isinstance(object, datetime.datetime):
        return to_local_isotime(object)
    if isinstance(object, db.GeoPt):
        return {'lat': '%.6f' % object.lat, 'lon': '%.6f' % object.lon}
    raise TypeError(repr(object) + ' is not JSON serializable')

def clean_json(json):
    return re.sub(r'"(\w+)":', r'\1:', json)

def render_json(center=None, radius=None):
    """Dump the data as a JSON string."""
    locale = get_locale()
    json = cache.JSON.get(locale)
    if json and not center:
        return json

    subject_types = cache.SUBJECT_TYPES.values()

    # Get the set of attributes to return
    attr_names = sets.Set()
    for subject_type in subject_types:
        attr_names = attr_names.union(subject_type.minimal_attribute_names)
    attr_names = attr_names.difference(HIDDEN_ATTRIBUTE_NAMES)

    # Get the subset of attributes to render.
    attributes = [cache.ATTRIBUTES[a] for a in attr_names]
    attribute_jobjects, attribute_is = make_jobjects(
        attributes, attribute_transformer)

    # Make JSON objects for the subject types.
    subject_type_jobjects, subject_type_is = make_jobjects(
        subject_types, subject_type_transformer, attribute_is)

    # Make JSON objects for the subjects.
    mfs = cache.MINIMAL_SUBJECTS.values()
    subject_jobjects, subject_is = make_jobjects(
        sorted(cache.MINIMAL_SUBJECTS.values(),
               key=lambda s: s.get_value('title')),
        minimal_subject_transformer, attributes, subject_types,
        subject_type_is, center, radius)
    total_subject_count = len(subject_jobjects) - 1

    # Sort by distance, if necessary.
    if center:
        subject_jobjects.sort(key=lambda s: s and s.get('distance_meters'))

    # Get all the messages for the current language.
    message_jobjects = {}
    for message in cache.MESSAGES.values():
        namespace = message_jobjects.setdefault(message.namespace, {})
        namespace[message.name] = getattr(message, locale)

    json = clean_json(simplejson.dumps({
        'total_subject_count': total_subject_count,
        'attributes': attribute_jobjects,
        'subject_types': subject_type_jobjects,
        'subjects': subject_jobjects,
        'messages': message_jobjects
    # set indent=2 to pretty-print; it blows up download size, so defaults off
    }, indent=None, default=json_encode))
    if not center:
        cache.JSON.set(locale, json)
    return json
