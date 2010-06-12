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

from google.appengine.api import users
from model import db, Facility, MinimalFacility
from selenium_test_case import Regex, SeleniumTestCase
import datetime

class PrintTest(SeleniumTestCase):
    def setUp(self):
        SeleniumTestCase.setUp(self)
        self.put_facility(
            'example.org/10', title='title_foo1', location=db.GeoPt(51.5, 0))
        self.put_facility(
            'example.org/11', title='title_foo2', location=db.GeoPt(51.5, 0.01))

    def tearDown(self):
        SeleniumTestCase.tearDown(self)
        self.delete_facility('example.org/10')
        self.delete_facility('example.org/11')

    def test_print_page(self):
        """Confirms that the print page renders correctly."""
        self.login('/?print=yes&lat=51.5&lon=0.01&rad=16093')
        self.assert_text(
            Regex('Displaying facilities within.*'),
            '//span[@id="header-print-subtitle" and @class="print-subtitle"]')

        # Check map is present with zoom elements
        self.assert_element('map')
        self.wait_for_element('//div[@title="Zoom in"]')
        self.assert_element('//div[@title="Zoom in"]')
        self.assert_element('//div[@title="Zoom out"]')

        # Assert two facilities are present
        self.assert_text(Regex('title_foo2.*'),
                         "//tr[@id='facility-1']/*[@class='facility-title']")
        self.assert_text(Regex('title_foo.*'),
                         "//tr[@id='facility-2']/*[@class='facility-title']")
