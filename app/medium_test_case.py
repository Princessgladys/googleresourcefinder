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

import os
import sets
import unittest

from google.appengine.api import apiproxy_stub_map
from google.appengine.api import datastore_file_stub
from google.appengine.api.memcache import memcache_stub
from google.appengine.api import user_service_stub

APP_ID = 'test'
os.environ['APPLICATION_ID'] = APP_ID
os.environ['USER_EMAIL'] = ''
os.environ['SERVER_NAME'] = 'localhost'
os.environ['SERVER_PORT'] = '80'

class MediumTestCase(unittest.TestCase):
    """Sets up stubs to be able to tset against the datastore and various other
    appengine services."""
    def setUp(self):
        apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()
        stub = datastore_file_stub.DatastoreFileStub(APP_ID,'/dev/null',
                                                     '/dev/null')
        apiproxy_stub_map.apiproxy.RegisterStub('datastore_v3', stub)

        apiproxy_stub_map.apiproxy.RegisterStub(
            'memcache', memcache_stub.MemcacheServiceStub())

        apiproxy_stub_map.apiproxy.RegisterStub(
            'user', user_service_stub.UserServiceStub())

    def assert_same_elements(self, expected_coll, actual_coll):
        """Assert that two collections hav the same elements (in any order)"""
        expected = sets.Set(expected_coll)
        actual = sets.Set(actual_coll)
        missing = [elem for elem in expected if elem not in actual]
        unexpected = [elem for elem in actual if elem not in expected]
        errors = []
        if missing:
            missing.sort()
            errors.append('Expected, but missing: %r\n' % missing)
        if unexpected:
            unexpected.sort()
            errors.append('Unexpected, but present: %r' % unexpected)
        if errors:
            self.fail(''.join(errors))
