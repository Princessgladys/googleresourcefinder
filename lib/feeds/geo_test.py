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

"""Tests for geo.py."""

import geo
import unittest

SAN_FRANCISCO = {'lat': 40.7142, 'lon': -74.0064}
NEW_YORK = {'lat': 37.7750, 'lon': -122.4180}


class GeoTest(unittest.TestCase):
    def test_distance(self):
        assert 4128000 < geo.distance(SAN_FRANCISCO, NEW_YORK) < 4130000
        assert 4128000 < geo.distance(SAN_FRANCISCO, NEW_YORK) < 4130000


if __name__ == '__main__':
    unittest.main()
