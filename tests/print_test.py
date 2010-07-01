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

from model import db, Subject, MinimalSubject
from selenium_test_case import Regex, SeleniumTestCase

class PrintTest(SeleniumTestCase):
    def setUp(self):
        SeleniumTestCase.setUp(self)
        self.put_account(actions=['*:view'])
        self.put_subject(
            'haiti', 'example.org/10',
            title='title_within_10_miles', location=db.GeoPt(51.5, 0),
            total_beds=10, available_beds=5, address='address_foo',
            contact_name='contact_name_foo')
        self.put_subject(
            'haiti', 'example.org/11',
            title='title_center', location=db.GeoPt(51.5, 0.01))
        self.put_subject(
            'haiti', 'example.org/12',
            title='title_outside_10_miles', location=db.GeoPt(51.6, 0.2))

    def tearDown(self):
        SeleniumTestCase.tearDown(self)
        self.delete_account()
        self.delete_subject('haiti', 'example.org/10')
        self.delete_subject('haiti', 'example.org/11')
        self.delete_subject('haiti', 'example.org/12')

    def test_print_page(self):
        """Confirms that the print page renders correctly."""
        # Print link should be initially disabled
        self.login('/?subdomain=haiti')
        self.click('link=Print')
        assert self.get_alert().startswith('First select a hospital')

        # After a subject is selected, the Print link should work
        self.click('id=subject-1')
        self.wait_for_element('//div[@class="bubble"]//span')

        # Click the link and switch to the new window
        self.click_and_wait_for_new_window('print-link')

        # Verify that this looks like a print window
        params = self.get_location().split('?', 1)[1]
        pairs = set(params.split('&'))
        assert 'subdomain=haiti' in pairs
        assert 'print=yes' in pairs
        assert 'lat=51.500000' in pairs
        assert 'lon=0.010000' in pairs
        assert any(pair.startswith('rad=16093.') for pair in pairs)
        self.assert_text(
            Regex('Displaying facilities within.*'),
            '//span[@id="header-print-subtitle" and @class="print-subtitle"]')

        # Check map is present with zoom elements
        self.assert_element('map')
        self.wait_for_element('//div[@title="Zoom in"]')
        self.assert_element('//div[@title="Zoom in"]')
        self.assert_element('//div[@title="Zoom out"]')

        # Confirm that exactly two subjects are present in the list.
        self.assert_text(Regex('title_center.*'),
                         "//tr[@id='subject-1']/*[@class='subject-title']")
        self.assert_text(Regex('title_within_10_miles.*'),
                         "//tr[@id='subject-2']/*[@class='subject-title']")
        self.assert_no_element(
                         "//tr[@id='subject-3']/*[@class='subject-title']")
        
        # Confirm that subject-2 shows the right available/total bed counts
        self.assert_text(Regex('5'),
                         "//tr[@id='subject-2']/*[@class='subject-beds-open']")
        self.assert_text(Regex('10'),
                         "//tr[@id='subject-2']/*" +
                         "[@class='subject-beds-total']")
        
        # Confirm that subject-2 shows the right distance to subject-1
        self.assert_text(Regex('0.4 miles.*'),
                         "//tr[@id='subject-2']/*[@class='subject-distance']")
        
        # Confirm that subject-2 shows the correct address
        self.assert_text(Regex('address_foo'),
                         "//tr[@id='subject-2']/*[@class='subject-address']")
        
        # Confirm that subject-2 shows the correct information section
        self.assert_text(Regex('contact_name_foo'),
                         "//tr[@id='subject-2']/*" +
                         "[@class='subject-general-info']")

        # Test to make sure the proper number of subjects are rendering.
        # td[1] is the number of total subjects
        # td[2] is the number of subjects less than 10 miles away
        # td[3] is the number of subjects with availability
        self.assert_text(Regex('3'), 
                         '//tbody[@id="print-summary-tbody"]//tr//td[1]')
        self.assert_text(Regex('2'), 
                         '//tbody[@id="print-summary-tbody"]//tr//td[2]')
        self.assert_text(Regex('1'), 
                         '//tbody[@id="print-summary-tbody"]//tr//td[3]')
