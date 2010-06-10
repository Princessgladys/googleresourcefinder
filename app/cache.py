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
import sets
import time
import UserDict

"""Caching layer for Resource Finder, taking advantage of both memcache
and in-memory caches."""

class JsonCache:
    """Memcache layer for JSON rendered by rendering.py. Offers significant
    startup performance increase."""
    def __init__(self):
        self.locales = sets.Set()

    def _key(self, locale):
        return '%s_%s' % (self.__class__.__name__, locale)

    def set(self, locale, json):
        """Sets the value in this cache"""
        if memcache.add(self._key(locale), json):
            self.locales.add(locale)
        else:
            logging.error('Memcache set of %s failed' % self._key(locale))

    def get(self, locale):
        """Gets the value in this cache"""
        return memcache.get(self._key(locale))

    def flush(self):
        """Flushes the value in this cache."""
        memcache.delete_multi([self._key(locale) for locale in self.locales])

class Cache(UserDict.DictMixin):
    """A cache that looks first in memory, then at memcache, then finally
    loads data from the datastore. The in-memory cache lives for ttl seconds,
    then is refreshed from memcache. The cache exposes a dictionary
    interface."""
    def __init__(self, json_cache, ttl=30):
        assert ttl > 0
        self.entities = None
        self.last_refresh = 0
        self.json_cache = json_cache
        self.ttl = ttl

    def __getitem__(self, key):
        self.load()
        return self.entities[key]

    def keys(self):
        self.load()
        return self.entities.keys()

    def load(self):
        """Load entities into memory, if necessary."""
        now = time.time()
        if now - self.last_refresh > self.ttl:
            self.entities = memcache.get(self.__class__.__name__)
            if self.entities is None:
                self.json_cache.flush()
                self.entities = self.fetch_entities()
                # TODO(shakusa) memcache has a 1MB limit for values. If any
                # cache gets larger, we need to revisit this.
                if not memcache.add(self.__class__.__name__, self.entities):
                    logging.error('Memcache set of %s failed'
                                  % self.__class__.__name__)
            self.last_refresh = now

    def fetch_entities(self):
        """Fetch entities on a cache miss."""
        raise NotImplementedError()

    def _query_in_batches(self, query, batch_size=1000):
        """Helper to run the query in batches of size batch_size and return
        all entities."""
        entities = []
        batch = query.fetch(batch_size)
        cursor = query.cursor()
        while batch:
            entities += batch
            if len(batch) < batch_size:
                break
            batch = query.with_cursor(cursor).fetch(batch_size)
            cursor = query.cursor()
        return entities

    def flush(self, flush_memcache=True):
        """Flushes the in-memory cache and optionally memcache"""
        if flush_memcache:
            memcache.delete(self.__class__.__name__)
            self.json_cache.flush()
        self.entities = None
        self.last_refresh = 0

class AttributeCache(Cache):
    def fetch_entities(self):
        entities = self._query_in_batches(model.Attribute.all())
        return dict((e.key().name(), e) for e in entities)

class FacilityTypeCache(Cache):
    def fetch_entities(self):
        entities = self._query_in_batches(model.FacilityType.all())
        return dict((e.key().name(), e) for e in entities)

class MessageCache(Cache):
    def fetch_entities(self):
        entities = self._query_in_batches(model.Message.all())
        return dict(((e.namespace, e.name), e) for e in entities)

class MinimalFacilityCache(Cache):
    def fetch_entities(self):
        entities = self._query_in_batches(model.MinimalFacility.all())
        return dict((e.parent_key(), e) for e in entities)

JSON_CACHE = JsonCache()
ATTRIBUTES = AttributeCache(JSON_CACHE)
FACILITY_TYPES = FacilityTypeCache(JSON_CACHE)
MESSAGES = MessageCache(JSON_CACHE)
MINIMAL_FACILITIES = MinimalFacilityCache(JSON_CACHE)
