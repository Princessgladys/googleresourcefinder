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

import datetime

from google.appengine.api import users

from model import db, Facility, MinimalFacility
from selenium_test_case import Regex, SeleniumTestCase

class PrintTest(SeleniumTestCase):
    def setUp(self):
        SeleniumTestCase.setUp(self)
        self.put_facility('example.org/10', title='title_within_10_miles',
                          location=db.GeoPt(51.5, 0))
        self.put_facility('example.org/11', title='title_center',
                          location=db.GeoPt(51.5, 0.01))
        self.put_facility('example.org/12', title='title_outside_10_miles',
                          location=db.GeoPt(51.6, 0.2))

    def tearDown(self):
        SeleniumTestCase.tearDown(self)
        self.delete_facility('example.org/10')
        self.delete_facility('example.org/11')
        self.delete_facility('example.org/12')

    def test_print_page(self):
        """Confirms that the print page renders correctly."""
        # Print link should be initially disabled
        self.login('/')
        self.click('link=Print')
        assert self.get_alert().startswith('First select a hospital')

        existing_windows = self.get_all_window_names()
        print 'names', self.get_all_window_names()
        print 'IDs', self.get_all_window_ids()
        print 'titles', self.get_all_window_titles()

        # After a facility is selected, the Print link should work
        self.click('id=facility-1')
        self.wait_for_element('//div[@class="bubble"]//span')

        # Click the link and switch to the new window
        self.click_and_wait_for_new_window('link=Print')

        # Verify that this looks like a print window
        print self.get_all_window_names()
        print self.get_location()
        assert ('/?print=yes&lat=51.500000&lon=0.010000&rad=16093.'
                in self.get_location())
        self.assert_text(
            Regex('Displaying facilities within.*'),
            '//span[@id="header-print-subtitle" and @class="print-subtitle"]')

        # Check map is present with zoom elements
        self.assert_element('map')
        self.wait_for_element('//div[@title="Zoom in"]')
        self.assert_element('//div[@title="Zoom in"]')
        self.assert_element('//div[@title="Zoom out"]')

        # Assert two facilities are present
        self.assert_text(Regex('title_center.*'),
                         "//tr[@id='facility-1']/*[@class='facility-title']")
        self.assert_text(Regex('title_within_10_miles.*'),
                         "//tr[@id='facility-2']/*[@class='facility-title']")
        self.assert_no_element(
                         "//tr[@id='facility-3']/*[@class='facility-title']")
