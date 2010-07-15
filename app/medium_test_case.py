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
import unittest

from google.appengine.api import apiproxy_stub_map
from google.appengine.api import datastore_file_stub
from google.appengine.api.memcache import memcache_stub
from google.appengine.api import user_service_stub
from google.appengine.api.labs.taskqueue import taskqueue_stub

APP_ID = 'test'
os.environ['APPLICATION_ID'] = APP_ID
os.environ['USER_EMAIL'] = ''
os.environ['SERVER_NAME'] = 'localhost'
os.environ['SERVER_PORT'] = '80'

class MediumTestCase(unittest.TestCase):
    """Sets up stubs to be able to test against the datastore and various other
    appengine services."""
    def setUp(self):
        apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()
        stub = datastore_file_stub.DatastoreFileStub(APP_ID,'/dev/null',
                                                     '/dev/null')
        apiproxy_stub_map.apiproxy.RegisterStub('datastore_v3', stub)

        apiproxy_stub_map.apiproxy.RegisterStub(
            'memcache', memcache_stub.MemcacheServiceStub())

        apiproxy_stub_map.apiproxy.RegisterStub(
            'taskqueue', taskqueue_stub.TaskQueueServiceStub())

        apiproxy_stub_map.apiproxy.RegisterStub(
            'user', user_service_stub.UserServiceStub())

    def assert_contents_in_order(self, expected, actual):
        """"""
        if expected == actual:
            return
        len1 = len(expected)
        len2 = len(actual)
        for i in xrange(min(len1, len2)):
            if expected[i] != actual[i]:
                self.fail('First differing element %d:\n%s\n%s'
                          % (i, expected[i], actual[i]))
        if len1 < len2:
            self.fail('Actual contains %d extra elements' % (len2 - len1))
        elif len1 > len2:
            self.fail('Expected contains %d extra elements' % (len1 - len2))

    def assert_contents_any_order(self, expected, actual):
        """Assert that two collections have the same elements (in any order).
        If there are duplicates, they must be present the same number of
        times."""
        if expected == actual:
            return
        missing = list(expected)
        unexpected = list(actual)
        # Remove expected elements from the unexpected list
        for element in expected:
            if element in unexpected:
                unexpected.remove(element)
        # Remove actual elements from the missing list
        for element in actual:
            if element in missing:
                missing.remove(element)
        errors = []
        if missing:
            errors.append('Expected, but missing: %r\n' % sorted(missing))
        if unexpected:
            errors.append('Unexpected, but present: %r' % sorted(unexpected))
        if errors:
            self.fail(''.join(errors))
