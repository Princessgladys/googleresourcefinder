from model import db
from selenium_test_case import Regex, SeleniumTestCase
import datetime

# services listed in the drop down box on top of the list
SERVICES = ['All',
            'General Surgery',
            'Orthopedics',
            'Neurosurgery',
            'Vascular Surgery',
            'Internal Medicine',
            'Cardiology',
            'Infectious Disease',
            'Pediatrics',
            'Postoperative Care',
            'Obstetrics and Gynecology',
            'Dialysis',
            'Lab',
            'X-Ray',
            'CT Scan',
            'Blood Bank',
            'Mortuary Services']

class MainTestCase(SeleniumTestCase):
    def setUp(self):
        SeleniumTestCase.setUp(self)
        self.put_facility(
            'example.org/1000', title='title_foo1', location=db.GeoPt(51.5, 0))
        self.put_facility(
            'example.org/1001', title='title_foo2', location=db.GeoPt(50.5, 1),
            operational_status='CLOSED_OR_CLOSING')

    def tearDown(self):
        self.delete_facility('example.org/1000')
        self.delete_facility('example.org/1001')
        SeleniumTestCase.tearDown(self)

    def test_elements_present(self):
        """Confirms that listbox and maps with elements are present and
        interaction between a list and a map works."""    
        self.login('/')
 
        # Check list column names        
        assert self.is_text_present('Facility')
        assert self.is_text_present('Services')
        assert self.is_text_present('Total Beds')

        # Check that all services are listed in the drop down
        for service in SERVICES:
            self.assert_element('//select[option=%r]' % service)

        # Make sure facilities are visible    
        assert self.is_visible('//tr[@id="facility-1"]')
        assert self.is_visible('//tr[@id="facility-2"]')

        # Check map is present with zoom elements
        self.assert_element('map')
        self.assert_element('//div[@title="Zoom in"]')
        self.assert_element('//div[@title="Zoom out"]')
 
        # Click on facility name and make sure it results in a bubble 
        # with correct name
        facility_xpath = '//tr[@id="facility-1"]'
        facility_title = self.get_text(facility_xpath + '/td')
        bubble_xpath = "//div[@class='bubble']/span/span[@class='title']"
        self.click(facility_xpath)
        self.wait_for_element(bubble_xpath)
        self.assert_text(facility_title, bubble_xpath)

    def test_closed_facilities(self):
        self.login('/')

        # Wait for list to populate
        self.wait_for_element('facility-2')

        # Facility 1000 is open
        assert 'disabled' not in self.get_attribute('//tr[@id="facility-1"]/@class')
        self.click('id=facility-1')
        bubble_xpath = "//div[@class='bubble']/span/span[@class='title']"
        self.wait_for_element(bubble_xpath)
        assert not self.is_text_present('Note: This facility has been marked closed')

        # Facility 1001 is closed
        assert 'disabled' in self.get_attribute('//tr[@id="facility-2"]/@class')
        self.click('id=facility-2')
        self.wait_for_element(bubble_xpath)
        assert self.is_text_present('Note: This facility has been marked closed')

        # Change facility 1000 to closed
        self.put_facility(
            'example.org/1000', title='title_foo1', location=db.GeoPt(51.5, 0),
            operational_status='CLOSED_OR_CLOSING')
        self.open_path('/?flush=yes')
        assert 'disabled' in self.get_attribute('//tr[@id="facility-1"]/@class')

        # TODO(kpy): The just-closed facility should have a new message in its
        # bubble; however the bubble survives in the browser cache.  This is a
        # real bug that needs to be fixed.
        # self.click('id=facility-1')
        # self.wait_for_element(bubble_xpath)
        # assert self.is_text_present('Note: This facility has been marked closed')
