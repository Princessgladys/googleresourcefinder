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

from google.appengine.api import memcache
import logging
import model

"""Caching layer for Resource Finder, taking advantage of both memcache
and in-memory caches."""

class _Cache:
    """Private in-memory cache of long-lived datastore objects. This avoids
    even a memcache lookup for values that are very unlikely to change,
    but it does mean that you have to restart the servers and flush them
    from memcache when you do want to change them."""
    _attributes = None
    _facility_types = None
    _messages = None

class AttributeCache:
    @staticmethod
    def get():
        if _Cache._attributes is None:
            _Cache._attributes = _check_memcache(
                'AttributeCache',
                ((a.key().name(), a) for a in model.Attribute.all()))
        return _Cache._attributes

    @staticmethod
    def values():
      return AttributeCache.get().values()

    @staticmethod
    def flush():
        memcache.delete('AttributeCache')
        _Cache._attributes = None

class FacilityTypeCache:
    @staticmethod
    def get():
        if _Cache._facility_types is None:
            _Cache._facility_types = _check_memcache(
                'FacilityTypeCache',
                ((f.key().name(), f) for f in model.FacilityType.all()))
        return _Cache._facility_types

    @staticmethod
    def values():
      return FacilityTypeCache.get().values()

    @staticmethod
    def flush():
        memcache.delete('FacilityTypeCache')
        _Cache._facility_types = None

class MessageCache:
    @staticmethod
    def get():
        if _Cache._messages is None:
            _Cache._messages = _check_memcache(
                'MessageCache',
                (((m.namespace, m.name), m) for m in model.Message.all()))
        return _Cache._messages

    @staticmethod
    def values():
      return MessageCache.get().values()

    @staticmethod
    def flush():
        memcache.delete('MessageCache')
        _Cache._messages = None

class MinimalFacilityCache:
    @staticmethod
    def get():
        # Don't use an in-memory cache here, minimal_facility changes too
        # frequently
        # TODO(shakusa) This works only as long as size of all
        # MinimalFacilities stays below 1MB. When that changes, need to revisit
        return _check_memcache(
                'MinimalFacilityCache',
                ((mf.parent_key(), mf) for mf in
                 model.MinimalFacility.all().order(
                     model.MinimalFacility.get_stored_name('title'))))

    @staticmethod
    def values():
      return MinimalFacilityCache.get().values()

    @staticmethod
    def flush():
        memcache.delete('MinimalFacilityCache')

def _check_memcache(key, generator):
    ret = memcache.get(key)
    if not ret:
        ret = dict(generator)
        if not memcache.add(key, ret):
            logging.error('Memcache set of %s failed' % key)
    return ret
