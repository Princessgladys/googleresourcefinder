# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for cache.py."""

import cache
import medium_test_case
import os

from google.appengine.api import memcache
from google.appengine.ext import db
from medium_test_case import MediumTestCase
from model import Message

class JsonCacheTest(MediumTestCase):
    def setUp(self):
        MediumTestCase.setUp(self)
        cache.JSON.flush()

    def tearDown(self):
        cache.JSON.flush()

    def test_json_cache(self):
        """Confirms that the JsonCache works as expected."""
        en_json = 'fake en json'
        fr_json = 'fake fr json'

        # start out empty
        assert cache.JSON.get('en') == None
        assert cache.JSON.get('fr') == None

        # fill the cache for en only
        cache.JSON.set('en', en_json)
        assert cache.JSON.get('en') == en_json
        assert cache.JSON.get('fr') == None

        # now fill for fr
        cache.JSON.set('fr', fr_json)
        assert cache.JSON.get('en') == en_json
        assert cache.JSON.get('fr') == fr_json

        # flush should clear all locales
        cache.JSON.flush()
        assert cache.JSON.get('en') == None
        assert cache.JSON.get('fr') == None

class CacheTest(MediumTestCase):
    def setUp(self):
        MediumTestCase.setUp(self)
        for i in range(0, 10):
            Message(namespace='english', name='name_%d' % i).put()

        self.messages = list(m for m in Message.all(keys_only=True))
        cache.MESSAGES.flush()

    def tearDown(self):
        cache.MESSAGES.flush()
        messages = self.messages
        while messages:
            batch, messages = messages[:200], messages[200:]
            db.delete(batch)

    def test_cache(self):
        """Confirms that the Cache works as expected using MessageCache."""
        assert memcache.get(cache.MESSAGES.memcache_key) == None
        assert cache.MESSAGES.entities == None

        # Loads from the cache
        assert len(cache.MESSAGES) == 10
        key = ('english', 'name_0')
        assert key in cache.MESSAGES.keys()
        assert cache.MESSAGES[key] != None

        # Flush should clear out
        cache.MESSAGES.flush()
        assert memcache.get(cache.MESSAGES.memcache_key) == None
        assert cache.MESSAGES.entities == None

        # Loads from the cache again
        assert cache.MESSAGES[key] != None
        assert cache.MESSAGES.entities != None
        assert memcache.get(cache.MESSAGES.memcache_key) != None

        # Partial flush of in-memory cache only
        cache.MESSAGES.flush(flush_memcache=False)
        assert memcache.get(cache.MESSAGES.memcache_key) != None
        assert cache.MESSAGES.entities == None

    def test_query_in_batches(self):
      """Confirms that querying for entities in batches works correctly."""
      entries = cache.MESSAGES._query_in_batches(Message.all(), 1)
      assert len(entries) == 10
