# Copyright 2010 Google Inc.
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

import config
import logging
import model
import time
import utils
import UserDict

from google.appengine.api import memcache

"""Caching layer for Resource Finder, taking advantage of both memcache
and in-memory caches."""


class JsonCache:
    """Memcache layer for JSON rendered by rendering.py. Offers significant
    startup performance increase."""
    def get_memcache_key(self, locale):
        return '%s_%s' % (self.__class__.__name__, locale)

    def set(self, locale, json):
        """Sets the value in this cache for the given locale"""
        key = self.get_memcache_key(locale)
        if not memcache.set(key, json):
            logging.error('Memcache set of %s failed' % key)

    def get(self, locale):
        """Gets the value in this cache for the given locale"""
        return memcache.get(self.get_memcache_key(locale))

    def flush(self):
        """Flushes the values in this cache for all locales."""
        locales = map(utils.get_locale, dict(config.LANGUAGES).keys())
        memcache.delete_multi(map(self.get_memcache_key, locales))


class Cache(UserDict.DictMixin):
    """A cache that looks first in memory, then at memcache, then finally
    loads data from the datastore. The in-memory cache lives for ttl seconds,
    then is refreshed from memcache. The cache exposes a dictionary
    interface."""
    def __init__(self, ttl=30):
        assert ttl > 0
        self.entities = None
        self.last_refresh = 0
        self.ttl = ttl
        self.memcache_key = self.__class__.__name__

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
            self.entities = memcache.get(self.memcache_key)
            if self.entities is None:
                self.entities = self.fetch_entities()
                # TODO(shakusa) memcache has a 1MB limit for values. If any
                # cache gets larger, we need to revisit this.
                if not memcache.set(self.memcache_key, self.entities):
                    logging.error('Memcache set of %s failed'
                                  % self.memcache_key)
            self.last_refresh = now
        return self.entities

    def fetch_entities(self):
        """Fetch entities on a cache miss."""
        raise NotImplementedError()

    def flush(self, flush_memcache=True):
        """Flushes the in-memory cache and optionally memcache"""
        if flush_memcache:
            memcache.delete(self.memcache_key)
        self.entities = None
        self.last_refresh = 0


class AttributeCache(Cache):
    def fetch_entities(self):
        entities = utils.fetch_all(model.Attribute.all())
        return dict((e.key().name(), e) for e in entities)


class SubjectTypeCache(Cache):
    def fetch_entities(self):
        entities = utils.fetch_all(model.SubjectType.all())
        return dict((e.key().name(), e) for e in entities)


class MessageCache(Cache):
    def fetch_entities(self):
        entities = utils.fetch_all(model.Message.all())
        return dict(((e.namespace, e.name), e) for e in entities)


class MinimalSubjectCache(Cache):
    def fetch_entities(self):
        entities = utils.fetch_all(model.MinimalSubject.all())
        return dict((e.parent_key(), e) for e in entities)


JSON = JsonCache()
ATTRIBUTES = AttributeCache()
SUBJECT_TYPES = SubjectTypeCache()
MESSAGES = MessageCache()
MINIMAL_SUBJECTS = MinimalSubjectCache()

CACHES = [JSON, ATTRIBUTES, SUBJECT_TYPES, MESSAGES, MINIMAL_SUBJECTS]

def flush_all():
    """Flush all caches"""
    for cache in CACHES:
        cache.flush()
