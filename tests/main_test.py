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
        self.put_subject(
            'haiti', 'example.org/1000',
            title='title_foo1', location=db.GeoPt(51.5, 0))
        self.put_subject(
            'haiti', 'example.org/1001',
            title='title_foo2', location=db.GeoPt(50.5, 1),
            operational_status='CLOSED_OR_CLOSING')

    def tearDown(self):
        self.delete_subject('haiti', 'example.org/1000')
        self.delete_subject('haiti', 'example.org/1001')
        SeleniumTestCase.tearDown(self)

    def test_elements_present(self):
        """Confirms that listbox and maps with elements are present and
        interaction between a list and a map works."""    
        self.login('/?subdomain=haiti')
 
        # Check list column names        
        assert self.is_text_present('Facility')
        assert self.is_text_present('Services')
        assert self.is_text_present('Total Beds')

        # Check that all services are listed in the drop down
        for service in SERVICES:
            self.assert_element('//select[option=%r]' % service)

        # Make sure subjects are visible    
        assert self.is_visible('//tr[@id="subject-1"]')
        assert self.is_visible('//tr[@id="subject-2"]')

        # Check map is present with zoom elements
        self.wait_for_element('map')
        self.wait_for_element('//div[@title="Zoom in"]')
        self.wait_for_element('//div[@title="Zoom out"]')
 
        # Click on subject name and make sure it results in a bubble 
        # with correct name
        subject_xpath = '//tr[@id="subject-1"]'
        subject_title = self.get_text(subject_xpath + '/td')
        bubble_xpath = "//div[@class='bubble']/span/span[@class='title']"
        self.click(subject_xpath)
        self.wait_for_element(bubble_xpath)
        self.assert_text(subject_title, bubble_xpath)

    def test_closed_facilities(self):
        """Confirms that closed facilities appear grey in the facility list
        and have a warning message in their info bubble."""
        self.login('/?subdomain=haiti')

        # Wait for the facility list to populate.
        self.wait_for_element('subject-2')

        # Facility 1000 is open (black in list and no 'closed' message).
        assert 'disabled' not in self.get_attribute(
            '//tr[@id="subject-1"]/@class')
        self.click('id=subject-1')
        bubble_xpath = "//div[@class='bubble']/span/span[@class='title']"
        self.wait_for_element(bubble_xpath)
        assert not self.is_text_present(
            'Note: This facility has been marked closed')

        # Facility 1001 is closed (grey in list and 'closed' message in bubble).
        assert 'disabled' in self.get_attribute(
            '//tr[@id="subject-2"]/@class')
        self.click('id=subject-2')
        self.wait_for_element(bubble_xpath)
        assert self.is_text_present(
            'Note: This facility has been marked closed')

        # Make sure the message appears in other languages, too.
        self.open_path('/?subdomain=haiti&lang=fr')
        self.wait_for_element('subject-2')
        self.click('id=subject-2')
        self.wait_for_element(bubble_xpath)
        assert self.is_text_present(
            u'Note: Cet \xe9tablissement a \xe9t\xe9 marqu\xe9e ferm\xe9e.')

        # Change facility 1000 to closed.
        self.put_subject(
            'haiti', 'example.org/1000',
            title='title_foo1', location=db.GeoPt(51.5, 0),
            operational_status='CLOSED_OR_CLOSING')

        # Reload and flush the cache so we see the changes.
        self.open_path('/?subdomain=haiti&flush=yes')

        # Facility 1000 should now be grey and have a 'closed' message.
        assert 'disabled' in self.get_attribute('//tr[@id="subject-1"]/@class')
        self.click('id=subject-1')
        self.wait_for_element(bubble_xpath)
        assert self.is_text_present(
            'Note: This facility has been marked closed')
