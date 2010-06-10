from google.appengine.api import users
from model import Facility, MinimalFacility
from selenium_test_case import Regex, SeleniumTestCase
import datetime
import scrape

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
            'Corpse Removal']

class MainTestCase(SeleniumTestCase):
    def setUp(self):
        SeleniumTestCase.setUp(self)
        f = Facility(key_name='example.org/1000', type='hospital')
        f.set_attribute('title', 'title_foo1', datetime.datetime.now(),
                        users.User('test@example.com'),
                        'nickname_foo', 'affiliation_foo', 'comment_foo')
        f.set_attribute('location', db.GeoPt(51.5, 0), datetime.datetime.now(),
                        users.User('test@example.com'),
                        'nickname_foo', 'affiliation_foo', 'comment_foo')
        f.put()
        mf = MinimalFacility(f, type='hospital')
        mf.set_attribute('title', 'title_foo1')
        mf.set_attribute('location', db.GeoPt(51.5, 0))
        mf.put()

        f = Facility(key_name='example.org/1001', type='hospital')
        f.set_attribute('title', 'title_foo2', datetime.datetime.now(),
                        users.User('test@example.com'),
                        'nickname_foo', 'affiliation_foo', 'comment_foo')
        f.set_attribute('location', db.GeoPt(50.5, 1), datetime.datetime.now(),
                        users.User('test@example.com'),
                        'nickname_foo', 'affiliation_foo', 'comment_foo')
        f.put()
        mf = MinimalFacility(f, type='hospital')
        mf.set_attribute('title', 'title_foo2')
        mf.set_attribute('location', db.GeoPt(51.5, 1))
        mf.put()
        self.s = scrape.Session()

    def tearDown(self):
        f = Facility.get_by_key_name('example.org/1000')
        mf = MinimalFacility.all().ancestor(f).get()
        mf.delete()
        f.delete()
        
        f = Facility.get_by_key_name('example.org/1001')
        mf = MinimalFacility.all().ancestor(f).get()
        mf.delete()
        f.delete()

        SeleniumTestCase.tearDown(self)

    def test_elements_present(self):
        """Confirms that listbox and maps with elements are present and
        interaction between a list and a map works."""    
        self.login('/')
 
        # Check list column names        
        self.failUnless(self.is_text_present("Facility"))
        self.failUnless(self.is_text_present("Services"))
        self.failUnless(self.is_text_present("Total Beds"))

        # Check that all services are listed in the drop down
        for service in SERVICES:
            self.assert_element("//select[option='" + service + "']" )

        # Make sure facilities are visible    
        self.failUnless(self.is_visible("//tr[@id='facility-1']"))
        self.failUnless(self.is_visible("//tr[@id='facility-2']"))

        # Check map is present with zoom elements
        self.failUnless(self.is_element_present('map'), 'map is not present')
        self.failUnless(self.is_element_present("//div[@title='Zoom in']"))
        self.failUnless(self.is_element_present("//div[@title='Zoom out']"))
 
        # Click on facility name and make sure it results in a bubble 
        # with correct name
        facility_xpath = "//tr[@id='facility-1']"
        facility_name = self.get_text(facility_xpath + '/td')
        bubble_xpath = "//div[@class='bubble']/span/span[@class='title']"
        self.click(facility_xpath)
        self.wait_for_element(bubble_xpath)
        self.assert_text(facility_name, bubble_xpath)
