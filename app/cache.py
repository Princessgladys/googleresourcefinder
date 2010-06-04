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
import time

"""Caching layer for Resource Finder, taking advantage of both memcache
and in-memory caches."""

class Cache:
    """A cache that looks first in memory, then at memcache, then finally
    loads data from the datastore. The in-memory cache lives for ttl seconds,
    then is refreshed from memcache. The cache exposes a dictionary
    interface."""
    def __init__(self, ttl=30):
        self.entities = {}
        self.last_refresh = 0
        self.ttl = ttl

    def __getitem__(self, key):
        self.load()
        return self.entities[key]

    def __iter__(self):
        self.load()
        return iter(self.entities)

    def get(self, key, default=None):
        self.load()
        return self.entities.get(key, default)

    def values(self):
        self.load()
        return list(self.entities[key] for key in iter(self.entities))

    def load(self):
        """Load entities into memory, if necessary."""
        now = time.time()
        if now - self.last_refresh > self.ttl:
            self.entities = memcache.get(self.__class__.__name__)
            if self.entities is None:
                self.entities = self.fetch_entities()
                # TODO(shakusa) memcache has a 1MB limit for values. If any
                # cache gets larger, we need to revisit this.
                if not memcache.add(self.__class__.__name__, self.entities):
                    logging.error('Memcache set of %s failed' % key)
            self.last_refresh = now

    def fetch_entities(self):
        """Fetch entities on a cache miss."""
        raise NotImplementedError()

    def _query_in_batches(self, query, batch_size=1000):
        """Helper to run the query in batches of size batch_size and return
        all entities."""
        entities = []
        batch = query.fetch(batch_size)
        offset = 0
        while batch:
            entities = entities + batch
            if len(batch) < batch_size:
                break
            offset = offset + len(batch)
            batch =query.fetch(batch_size, offset=offset)
        return entities

    def flush(self, flush_memcache=True):
        if flush_memcache:
            memcache.delete(self.__class__.__name__)
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

ATTRIBUTES = AttributeCache()
FACILITY_TYPES = FacilityTypeCache()
MESSAGES = MessageCache()
MINIMAL_FACILITIES = MinimalFacilityCache()
