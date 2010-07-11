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


class CacheGroup:
    """A group of caches, keyed by subdomain.  Instantiates the given cache
    class for each subdomain the first time that cache is requested."""
    def __init__(self, cache_class):
        """'cache_class' should be a class that (a) has a flush() method and
        (b) has a constructor taking one argument, a subdomain."""
        self.cache_class = cache_class
        self.caches = {}

    def __getitem__(self, subdomain):
        """Gets (and optionally creates) the cache for the given subdomain."""
        if subdomain not in self.caches:
            self.caches[subdomain] = self.cache_class(subdomain)
        return self.caches[subdomain]

    def flush(self):
        """Flushes all the underlying caches."""
        for cache in self.caches.values():
            cache.flush()


class JsonCache:
    """Memcache layer for JSON rendered by rendering.py."""
    def __init__(self, subdomain):
        self.subdomain = subdomain

    def get_memcache_key(self, locale):
        return '%s:%s.%s' % (self.subdomain, self.__class__.__name__, locale)

    def set(self, locale, json):
        """Sets the value in this cache for the given locale."""
        key = self.get_memcache_key(locale)
        if not memcache.set(key, json):
            logging.error('Memcache set of %s failed' % key)

    def get(self, locale):
        """Gets the value in this cache for the given locale."""
        return memcache.get(self.get_memcache_key(locale))

    def flush(self):
        """Flushes the values in this cache for all locales."""
        locales = map(utils.get_locale, dict(config.LANGUAGES).keys())
        memcache.delete_multi(map(self.get_memcache_key, locales))


class Cache(UserDict.DictMixin):
    """A cache that looks first in local memory, then in a remote memcache,
    then finally loads data from the datastore.  The local in-memory cache
    lives for ttl seconds, then is refreshed from memcache.  Transparently
    exposes a dictionary interface to the underlying cached dictionary."""
    def __init__(self, subdomain='', ttl=30):
        assert ttl > 0
        self.subdomain = subdomain
        self.entities = None
        self.last_refresh = 0  # last time data was loaded into local memory
        self.ttl = ttl  # maximum age in seconds for data in local memory
        self.memcache_key = subdomain + ':' + self.__class__.__name__

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

    def flush_local(self):
        """Flushes the local in-memory cache."""
        self.last_refresh = 0
        self.entities = None

    def flush(self):
        """Flushes the local in-memory cache and the remote memcache."""
        self.flush_local()
        memcache.delete(self.memcache_key)


class SubjectTypeCache(Cache):
    def fetch_entities(self):
        entities = utils.fetch_all(
            model.SubjectType.all_in_subdomain(self.subdomain))
        return dict((e.key().name().split(':', 1)[1], e) for e in entities)


class MinimalSubjectCache(Cache):
    def fetch_entities(self):
        entities = utils.fetch_all(
            model.MinimalSubject.all_in_subdomain(self.subdomain))
        return dict((e.key().name().split(':', 1)[1], e) for e in entities)


class AttributeCache(Cache):
    def fetch_entities(self):
        entities = utils.fetch_all(model.Attribute.all())
        return dict((e.key().name(), e) for e in entities)


class MessageCache(Cache):
    def fetch_entities(self):
        entities = utils.fetch_all(model.Message.all())
        return dict(((e.namespace, e.name), e) for e in entities)


# These types have a separate cache for each subdomain.
JSON = CacheGroup(JsonCache)
SUBJECT_TYPES = CacheGroup(SubjectTypeCache)
MINIMAL_SUBJECTS = CacheGroup(MinimalSubjectCache)

# Each of these caches is shared across all subdomains.
ATTRIBUTES = AttributeCache()
MESSAGES = MessageCache()

CACHES = [JSON, SUBJECT_TYPES, MINIMAL_SUBJECTS, ATTRIBUTES, MESSAGES]

def flush_all():
    """Flush all caches."""
    for cache in CACHES:
        cache.flush()
