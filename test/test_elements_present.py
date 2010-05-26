from resource_mapper_test_case import ResourceMapperTestCase
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

class ElementsTestCase(ResourceMapperTestCase):
    def test_elements_present(self):
        """Confirms that listbox and maps with elements are present and
        interaction between a list and a map works."""    
        self.login('/')
        sel = self.s
        # Check that all services are listed in the drop down
        for service in SERVICES:
            self.failUnless(sel.is_text_present(service))

        # Check list column names        
        self.failUnless(sel.is_text_present("Facility"))
        self.failUnless(sel.is_text_present("Services"))
        self.failUnless(sel.is_text_present("Total Beds"))

        # Make sure facilities are visible    
        self.failUnless(sel.is_visible("//tr[@id='facility-1']"))
        self.failUnless(sel.is_visible("//tr[@id='facility-500']"))

        # Check map is present with zoom elements
        self.failUnless(sel.is_element_present('map'), 'map is not present')
        self.failUnless(sel.is_element_present("//div[@title='Zoom in']"))
        self.failUnless(sel.is_element_present("//div[@title='Zoom out']"))
 
        # Click on facility name and make sure it results in a bubble with correct name
        facility_xpath = "//tr[@id='facility-1']"
        facility_name = sel.get_text(facility_xpath + '/td')
        bubble_xpath = "//div[@class='bubble']/span/span[@class='title']"
        sel.click(facility_xpath)
        self.wait_for_element(bubble_xpath)
        bubble_facility_name = self.s.get_text(bubble_xpath)
        self.failUnlessEqual(facility_name, bubble_facility_name)

if __name__ == "__main__":
    unittest.main()
