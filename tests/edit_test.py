from google.appengine.api import users
from model import *
from selenium_test_case import Regex, SeleniumTestCase
import datetime
import scrape

# "name" attributes of the checkboxes for available services in the edit form.
SERVICES = [
    'GENERAL_SURGERY',
    'ORTHOPEDICS',
    'NEUROSURGERY',
    'VASCULAR_SURGERY',
    'GENERAL_MEDICINE',
    'CARDIOLOGY',
    'INFECTIOUS_DISEASE',
    'PEDIATRICS',
    'POSTOPERATIVE_CARE',
    'OBSTETRICS_GYNECOLOGY',
    'DIALYSIS',
    'LAB',
    'X_RAY',
    'CT_SCAN',
    'BLOOD_BANK',
    'CORPSE_REMOVAL',
]

# "name" attributes of the string input fields in the edit form.
STR_FIELDS = [
    'contact_name',
    'phone',
    'email',
    'department',
    'district',
    'commune',
    'address',
    'organization',
    'damage',
    'comments',
]


class EditTest(SeleniumTestCase):
    def setUp(self):
        SeleniumTestCase.setUp(self)
        f = Facility(key_name='example.org/123', type='hospital')
        f.set_attribute('title', 'title_foo', datetime.datetime.now(),
                        users.User('test@example.com'),
                        'nickname_foo', 'affiliation_foo', 'comment_foo')
        f.set_attribute('location', db.GeoPt(51.5, 0), datetime.datetime.now(),
                        users.User('test@example.com'),
                        'nickname_foo', 'affiliation_foo', 'comment_foo')
        f.put()
        self.mf = MinimalFacility(f, type='hospital')
        self.mf.set_attribute('title', 'title_foo')
        self.mf.set_attribute('location', db.GeoPt(51.5, 0))
        self.mf.put()
        self.s = scrape.Session()

    def tearDown(self):
        Facility.get_by_key_name('example.org/123').delete()
        self.mf.delete()
        # Reset account to initial (no nickname, affiliation) state
        a = Account.all().fetch(1)[0]
        a.nickname = ''
        a.affiliation = ''
        a.put()
        SeleniumTestCase.tearDown(self)

    def edit(self):
        """Goes to edit form for facility 1"""
        self.login('/')
        self.click('id=facility-1')
        # For some reason, this wait doesn't always work unless we do it twice.
        self.wait_for_element('link=Edit this record')
        self.wait_for_element('link=Edit this record')
        self.click('link=Edit this record')
        self.wait_until(self.is_visible, 'edit-data')

    def test_edit_link(self):
        """Confirms that the "Edit this record" link in the detail bubble
        goes to the edit form."""
        self.edit()

    def test_edit_page_new(self):
        """Confirms that all the fields in the edit form save the entered
        values, and these values appear pre-filled when the form is loaded
        (using the new edit approach)."""
        self.edit()

        # First-time edit should show nickname and affiliation fields
        self.assert_element('//input[@name="account_nickname"]')
        self.assert_element('//input[@name="account_affiliation"]')

        # Test javascript error checking
        text_fields = {}
        text_fields['account_nickname'] = '   '
        text_fields['account_affiliation'] = '\t'
        text_fields['available_beds'] = 'available'
        text_fields['total_beds'] = 'total'
        text_fields['location.lat'] = '91'
        text_fields['location.lon'] = '-181'
        self.fill_fields(text_fields, {}, {})
        self.click('//input[@name="save"]')
        self.verify_errors(text_fields)

        # Fill in the form
        text_fields = dict((name, name + '_foo') for name in STR_FIELDS)
        text_fields['account_nickname'] = 'Test'
        text_fields['account_affiliation'] = 'Test'
        text_fields['available_beds'] = '   1'
        text_fields['total_beds'] = '2\t  '
        text_fields['location.lat'] = '18.537207 '
        text_fields['location.lon'] = '\t-72.349663'
        checkbox_fields = dict(('services.' + name, True) for name in SERVICES)
        select_fields = {'organization_type': 'COM', 'category': 'C/S',
                         'construction': 'ADOBE', 'reachable_by_road': 'TRUE',
                         'can_pick_up_patients': 'FALSE',
                         'operational_status': 'NO_SURGICAL_CAPACITY'}
        self.fill_fields(text_fields, checkbox_fields, select_fields)

        # Submit the form
        self.click('//input[@name="save"]')
        self.wait_until(self.is_visible, 'data')

        # Return to the edit page
        self.edit()

        # Nickname and affiliation fields should not be shown this time
        self.assert_no_element('//input[@name="account_nickname"]')
        self.assert_no_element('//input[@name="account_affiliation"]')
        del text_fields['account_nickname']
        del text_fields['account_affiliation']

        # Check that the new values were saved, and are pre-filled in the form
        text_fields['available_beds'] = '1'  # whitespace should be gone
        text_fields['total_beds'] = '2'  # whitespace should be gone
        text_fields['location.lat'] = '18.537207'  # whitespace should be gone
        text_fields['location.lon'] = '-72.349663'  # whitespace should be gone
        self.verify_fields(text_fields, checkbox_fields, select_fields)

        # Now empty everything
        text_fields = dict((name, '') for name in STR_FIELDS)
        text_fields['available_beds'] = ''
        text_fields['total_beds'] = ''
        checkbox_fields = dict(('services.' + name, False) for name in SERVICES)
        select_fields = {'organization_type': '', 'category': '',
                         'construction': '', 'reachable_by_road': '',
                         'can_pick_up_patients': '', 'operational_status': ''}
        self.fill_fields(text_fields, checkbox_fields, select_fields)

        # Submit the form
        self.click('//input[@name="save"]')
        self.wait_until(self.is_visible, 'data')

        # Return to the edit page
        self.edit()

        # Check that everything is now empty or deselected
        self.verify_fields(text_fields, checkbox_fields, select_fields)

        # Set the integer fields to zero
        self.type('//input[@name="available_beds"]', '  0')
        self.type('//input[@name="total_beds"]', '0  ')

        # Submit the form
        self.click('//input[@name="save"]')
        self.wait_until(self.is_visible, 'data')

        # Return to the edit page
        self.edit()

        # Check that the integer fields are actually zero, not empty
        text_fields['available_beds'] = '0'
        text_fields['total_beds'] = '0'
        self.verify_fields(text_fields, checkbox_fields, select_fields)

    def test_edit_page(self):
        """Confirms that all the fields in the edit form save the entered
        values, and these values appear pre-filled when the form is loaded."""

        # Check that feed is empty
        feed = self.s.go('http://localhost:8081/feeds/delta')
        assert feed.first('atom:feed')
        assert feed.first('atom:feed').all('atom:entry') == []

        # Go to the edit page
        self.login('/edit?facility_name=example.org/123')
        self.assert_text(Regex('Edit.*'), '//h1')

        # First-time edit should show nickname and affiliation fields
        self.assert_element('//input[@name="account_nickname"]')
        self.assert_element('//input[@name="account_affiliation"]')

        # Test javascript error checking
        text_fields = {}
        text_fields['account_nickname'] = '   '
        text_fields['account_affiliation'] = '\t'
        text_fields['available_beds'] = 'available'
        text_fields['total_beds'] = 'total'
        text_fields['location.lat'] = '91'
        text_fields['location.lon'] = '-181'
        self.fill_fields(text_fields, {}, {})
        self.click('//input[@name="save"]')
        self.verify_errors(text_fields)

        # Fill in the form
        text_fields = dict((name, name + '_foo') for name in STR_FIELDS)
        text_fields['account_nickname'] = 'Test'
        text_fields['account_affiliation'] = 'Test'
        text_fields['available_beds'] = '   1'
        text_fields['total_beds'] = '2\t  '
        text_fields['location.lat'] = '18.537207 '
        text_fields['location.lon'] = '\t-72.349663'
        checkbox_fields = dict(('services.' + name, True) for name in SERVICES)
        select_fields = {'organization_type': 'COM', 'category': 'C/S',
                         'construction': 'ADOBE', 'reachable_by_road': 'TRUE',
                         'can_pick_up_patients': 'FALSE',
                         'operational_status': 'NO_SURGICAL_CAPACITY'}
        self.fill_fields(text_fields, checkbox_fields, select_fields)

        # Submit the form
        self.click('//input[@name="save"]')
        self.wait_for_load()

        # Check that we got back to the main map
        self.assertEquals(self.config.base_url + '/', self.get_location())

        # Return to the edit page
        self.open_path('/edit?facility_name=example.org/123')
        self.assert_text(Regex('Edit.*'), '//h1')

        # Nickname and affiliation fields should not be shown this time
        self.assert_no_element('//input[@name="account_nickname"]')
        self.assert_no_element('//input[@name="account_affiliation"]')
        del text_fields['account_nickname']
        del text_fields['account_affiliation']

        # Check that the new values were saved, and are pre-filled in the form
        text_fields['available_beds'] = '1'  # whitespace should be gone
        text_fields['total_beds'] = '2'  # whitespace should be gone
        text_fields['location.lat'] = '18.537207'  # whitespace should be gone
        text_fields['location.lon'] = '-72.349663'  # whitespace should be gone
        self.verify_fields(text_fields, checkbox_fields, select_fields)

        # Now empty everything
        text_fields = dict((name, '') for name in STR_FIELDS)
        text_fields['available_beds'] = ''
        text_fields['total_beds'] = ''
        checkbox_fields = dict(('services.' + name, False) for name in SERVICES)
        select_fields = {'organization_type': '', 'category': '',
                         'construction': '', 'reachable_by_road': '',
                         'can_pick_up_patients': '', 'operational_status': ''}
        self.fill_fields(text_fields, checkbox_fields, select_fields)

        # Submit the form
        self.click('//input[@name="save"]')
        self.wait_for_load()

        # Return to the edit page
        self.open_path('/edit?facility_name=example.org/123')
        self.assert_text(Regex('Edit.*'), '//h1')

        # Check that everything is now empty or deselected
        self.verify_fields(text_fields, checkbox_fields, select_fields)

        # Set the integer fields to zero
        self.type('//input[@name="available_beds"]', '  0')
        self.type('//input[@name="total_beds"]', '0  ')

        # Submit the form
        self.click('//input[@name="save"]')
        self.wait_for_load()

        # Return to the edit page
        self.open_path('/edit?facility_name=example.org/123')
        self.assert_text(Regex('Edit.*'), '//h1')

        # Check that the integer fields are actually zero, not empty
        text_fields['available_beds'] = '0'
        text_fields['total_beds'] = '0'
        self.verify_fields(text_fields, checkbox_fields, select_fields)

        # Check that feed is not empty now
        feed = self.s.go('http://localhost:8081/feeds/delta')
        assert feed.first('atom:feed')
        assert feed.first('atom:feed').first('atom:entry')


    def fill_fields(self, text_fields, checkbox_fields, select_fields):
        """Fills in text fields, selects or deselects checkboxes, and
        makes drop-down selections.  Each of the arguments should be a
        dictionary of field names to values."""
        for name, value in text_fields.items():
            input_xpath = '//input[@name="%s"]' % name
            self.type(input_xpath, value)
        for name, value in checkbox_fields.items():
            checkbox_xpath = '//input[@name="%s"]' % name
            (value and self.check or self.uncheck)(checkbox_xpath)
        for name, value in select_fields.items():
            select_xpath = '//select[@name="%s"]' % name
            self.select(select_xpath, 'value=' + value)

    def verify_fields(self, text_fields, checkbox_fields, select_fields):
        """Checks the values of text fields, state of checkboxes, and
        selection state of options.  Each of the arguments should be a
        dictionary of field names to values."""
        for name, value in text_fields.items():
            input_xpath = '//input[@name="%s"]' % name
            self.assert_value(value, input_xpath)
        for name, value in checkbox_fields.items():
            checkbox_xpath = '//input[@name="%s"]' % name
            self.assertEquals(value, self.is_checked(checkbox_xpath))
        for name, value in select_fields.items():
            select_xpath = '//select[@name="%s"]' % name
            self.assertEquals([value], self.get_selected_values(select_xpath))

    def verify_errors(self, text_fields):
        """Checks that all the given text fields have visible error messages.
        Argument should be a dictionary of field names to values."""
        for name, value in text_fields.items():
            error_xpath = '//div[@id="%s_errormsg"]' % name.split('.')[0]
            self.assertTrue(self.is_visible(error_xpath), "element xpath is %s" % error_xpath)
