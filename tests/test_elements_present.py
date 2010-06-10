from selenium_test_case import SeleniumTestCase
import unittest

# services listed in the drop down box on top of the list
SERVICES = ['All',
            'General surgery',
            'Orthopedics',
            'Neurosurgery',
            'Vascular surgery',
            'General medicine',
            'Cardiology',
            'Infectious disease',
            'Pediatrics',
            'Postoperative care',
            'Obstetrics and gynecology',
            'Dialysis',
            'Lab',
            'X-ray',
            'CT scan',
            'Blood bank',
            'Corpse removal']

class MainTestCase(SeleniumTestCase):
    def setUp(self):
        SeleniumTestCase.setUp(self)
        f = Facility(key_name='example.org..123', type='hospital')
        f.set_attribute('title1', 'title_foo1', datetime.datetime.now(),
                        users.User('test@example.com'),
                        'nickname_foo', 'affiliation_foo', 'comment_foo')
        f.set_attribute('location', db.GeoPt(51.5, 0), datetime.datetime.now(),
                        users.User('test@example.com'),
                        'nickname_foo', 'affiliation_foo', 'comment_foo')
        f.put()
        f = Facility(key_name='example.org..234', type='hospital')
        f.set_attribute('title2', 'title_foo2', datetime.datetime.now(),
                        users.User('test@example.com'),
                        'nickname_foo', 'affiliation_foo', 'comment_foo')
        f.set_attribute('location', db.GeoPt(50.5, 1), datetime.datetime.now(),
                        users.User('test@example.com'),
                        'nickname_foo', 'affiliation_foo', 'comment_foo')
        f.put()


    def tearDown(self):
        Facility.get_by_key_name('example.org..123').delete()
        SeleniumTestCase.tearDown(self)
    def test_elements_present(self):
        """Confirms that listbox and maps with elements are present and
        interaction between a list and a map works."""    
        self.login('/')
        # Check that all services are listed in the drop down
        for service in SERVICES:
            self.assert_element("//select[option='" + service + "']" )

        # Check list column names        
        self.failUnless(self.is_text_present("Facility"))
        self.failUnless(self.is_text_present("Services"))
        self.failUnless(self.is_text_present("Total Beds"))

        # Make sure facilities are visible    
        self.failUnless(self.is_visible("//tr[@id='facility-1']"))
        self.failUnless(self.is_visible("//tr[@id='facility-500']"))

        # Check map is present with zoom elements
        self.failUnless(self.is_element_present('map'), 'map is not present')
        self.failUnless(self.is_element_present("//div[@title='Zoom in']"))
        self.failUnless(self.is_element_present("//div[@title='Zoom out']"))
 
        # Click on facility name and make sure it results in a bubble with correct name
        facility_xpath = "//tr[@id='facility-1']"
        facility_name = self.get_text(facility_xpath + '/td')
        bubble_xpath = "//div[@class='bubble']/span/span[@class='title']"
        self.click(facility_xpath)
        self.wait_for_element(bubble_xpath)
        self.assert_text(facility_name, bubble_xpath)

if __name__ == "__main__":
    unittest.main()
