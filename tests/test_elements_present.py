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
            'LabX-ray',
            'CT scan',
            'Blood bank',
            'Corpse removal']

class ElementsTestCase(SeleniumTestCase):
    def test_elements_present(self):
        """Confirms that listbox and maps with elements are present and
        interaction between a list and a map works."""    
        self.login('/')
        # Check that all services are listed in the drop down
        for service in SERVICES:
            self.failUnless(self.is_text_present(service))

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
