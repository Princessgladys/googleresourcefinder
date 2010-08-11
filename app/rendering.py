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
import re
import sets
import simplejson
import sys
from feeds.geo import distance
from model import Attribute, Subject, SubjectType, Message, MinimalSubject
from utils import Date, DateTime, HIDDEN_ATTRIBUTE_NAMES
from utils import db, get_locale

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
    return {'name': subject_type.name,
            'attribute_is': [attribute_is[name]
                             for name in subject_type.minimal_attribute_names
                             if name not in HIDDEN_ATTRIBUTE_NAMES]}

def minimal_subject_transformer(index, minimal_subject, attributes,
                                subject_types, subject_type_is, center, radius):
    """Construct the JSON object for a MinimalSubject."""
    subdomain, type = minimal_subject.subdomain, minimal_subject.type

    # Gather all the attributes
    values = [None]  # attributes are indexed starting from 1
    for attribute in attributes:
        name = attribute.key().name()
        if name in subject_types[type].minimal_attribute_names:
            values.append(minimal_subject.get_value(name))
        else:
            values.append(None)

    # Pack the results into an object suitable for JSON serialization.
    subject_jobject = {
        'name': minimal_subject.name,
        'type': subject_type_is[subdomain + ':' + type],
        'values': values,
    }
    if minimal_subject.has_value('location'):
        location = {
            'lat': minimal_subject.get_value('location').lat,
            'lon': minimal_subject.get_value('location').lon
        }
        if center:
            subject_jobject['distance_meters'] = distance(location, center)

    dist = subject_jobject.get('distance_meters')
    if center and (dist is None or dist > radius > 0):
        return None

    return subject_jobject

def get_attributes_to_render(subject_types):
    """Returns the attributes of the given subject_types to be rendered.
    Enforces hiding of attributes in HIDDEN_ATTRIBUTE_NAMES."""
    attr_names = sets.Set()
    for subject_type in subject_types.values():
        attr_names = attr_names.union(subject_type.minimal_attribute_names)
    attr_names = attr_names.difference(HIDDEN_ATTRIBUTE_NAMES)
    return [cache.ATTRIBUTES[a] for a in attr_names]

def json_encode(object):
    """Handle JSON encoding for non-primitive objects."""
    if isinstance(object, Date) or isinstance(object, DateTime):
        return to_local_isotime(object)
    if isinstance(object, db.GeoPt):
        return {'lat': '%.6f' % object.lat, 'lon': '%.6f' % object.lon}
    raise TypeError(repr(object) + ' is not JSON serializable')

def compress_json(json):
    """Compresses json output by removing quotes from keys. This makes the
       return value invalid json (all json keys must be double-quoted), but
       the result is still valid javascript."""
    return re.sub(r'"(\w+)":', r'\1:', json)

def to_json(obj, indent=None):
    """Invokes simplejson.dumps to serialize the given object."""
    # set indent=2 to pretty-print; it blows up download size, so defaults off
    return simplejson.dumps(obj, indent=indent, default=json_encode)

def to_minimal_subject_jobject(subdomain, minimal_subject):
    """Converts the given MinimalSubject of Subject into an object that
    can be passed to to_json()."""
    subject_types = cache.SUBJECT_TYPES[subdomain]
    attributes = get_attributes_to_render(subject_types)
    attribute_jobjects, attribute_is = make_jobjects(
        attributes, attribute_transformer)

    subject_type_jobjects, subject_type_is = make_jobjects(
        subject_types.values(), subject_type_transformer, attribute_is)

    # Note index is irrelevant when transforming one object, so just pass -1
    return minimal_subject_transformer(-1, minimal_subject, attributes,
                                       subject_types, subject_type_is,
                                       center=None, radius=None)

def render_json(subdomain, center=None, radius=None):
    """Dump the data for a subdomain as a JSON string."""
    locale = get_locale()
    json = cache.JSON[subdomain].get(locale)
    if json and not center:
        return json

    subject_types = cache.SUBJECT_TYPES[subdomain]

    # Get the subset of attributes to render.
    attributes = get_attributes_to_render(subject_types)
    attribute_jobjects, attribute_is = make_jobjects(
        attributes, attribute_transformer)

    # Make JSON objects for the subject types.
    subject_type_jobjects, subject_type_is = make_jobjects(
        subject_types.values(), subject_type_transformer, attribute_is)

    # Make JSON objects for the subjects.
    # Because storing the MinimalSubject entities into memcache is fairly
    # slow (~3s for 1000 entities) and the JSON cache already provides almost
    # all the benefit, we fetch the MinimalSubject entities directly from the
    # datastore every time instead of letting the cache cache them.
    minimal_subjects = \
        cache.MINIMAL_SUBJECTS[subdomain].fetch_entities().values()
    subject_jobjects, subject_is = make_jobjects(
        sorted(minimal_subjects, key=lambda s: s.get_value('title')),
        minimal_subject_transformer, attributes, subject_types,
        subject_type_is, center, radius)
    total_subject_count = len(minimal_subjects)

    # Sort by distance, if necessary.
    if center:
        subject_jobjects.sort(key=lambda s: s and s.get('distance_meters'))

    # Get all the messages for the current language.
    message_jobjects = {}
    for message in cache.MESSAGES.values():
        namespace = message_jobjects.setdefault(message.namespace, {})
        namespace[message.name] = getattr(message, locale)

    json = compress_json(to_json({
        'total_subject_count': total_subject_count,
        'attributes': attribute_jobjects,
        'subject_types': subject_type_jobjects,
        'subjects': subject_jobjects,
        'messages': message_jobjects}))
    if not center:
        cache.JSON[subdomain].set(locale, json)
    return json
