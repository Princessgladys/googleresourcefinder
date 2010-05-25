from resource_mapper_test_case import ResourceMapperTestCase
import unittest

# "name" attributes of the checkboxes for available services in the edit form.
SERVICES = [
    'general_surgery',
    'orthopedics',
    'neurosurgery',
    'vascular_surgery',
    'general_medicine',
    'cardiology',
    'infectious_disease',
    'pediatrics',
    'postoperative_care',
    'obstetrics_gynecology',
    'dialysis',
    'lab',
    'x_ray',
    'ct_scan',
    'blood_bank',
    'corpse_removal',
]

# "name" attributes of the string input fields in the edit form.
STR_FIELDS = [
    'contact_name',
    'phone',
    'email',
    'departemen',
    'district',
    'commune',
    'address',
    'organization',
    'damage',
    'comments',
]

class EditTests(ResourceMapperTestCase):
    def test_edit_link(self):
        """Confirms that the "Edit this record" link in the detail bubble
        goes to the edit form."""
        self.login('/')
        self.s.click('id=facility-1')
        # For some reason, this wait doesn't always work unless we do it twice.
        self.wait_until(self.s.is_element_present, 'link=Edit this record')
        self.wait_until(self.s.is_element_present, 'link=Edit this record')
        self.s.click('link=Edit this record')
        self.wait_for_load()
        self.assertTrue('/edit?' in self.s.get_location())

    def test_edit_page(self):
        """Confirms that all the fields in the edit form save the entered
        values, and these values appear pre-filled when the form is loaded."""
        # Go to the edit page
        self.login('/edit?facility_name=mspphaiti.org..11136')
        self.assertTrue(self.s.get_text('//h1').startswith('Edit'))

        # First-time edit should show nickname and affiliation fields
        self.assert_element('//input[@name="auth_nickname"]')
        self.assert_element('//input[@name="auth_affiliation"]')

        # Test javascript error checking
        text_fields = {}
        text_fields['auth_nickname'] = '   '
        text_fields['auth_affiliation'] = '\t'
        text_fields['available_beds'] = 'available'
        text_fields['total_beds'] = 'total'
        text_fields['location.lat'] = '91'
        text_fields['location.lon'] = '-181'
        self.fill_fields(text_fields, {}, {})
        self.s.click('//input[@name="save"]')
        self.verify_errors(text_fields)

        # Fill in the form
        text_fields = dict((name, name + '_foo') for name in STR_FIELDS)
        text_fields['auth_nickname'] = 'Test'
        text_fields['auth_affiliation'] = 'Test'
        text_fields['available_beds'] = '   1'
        text_fields['total_beds'] = '2\t  '
        text_fields['location.lat'] = '18.537207 '
        text_fields['location.lon'] = '\t-72.349663'
        checkbox_fields = dict(('services.' + name, True) for name in SERVICES)
        select_fields = {'facility_type': 'COM', 'category': 'C/S',
                         'construction': 'Adobe', 'reachable_by_road': 'TRUE',
                         'can_pick_up_patients': 'FALSE',
                         'operational_status': 'No surgical capacity'}
        self.fill_fields(text_fields, checkbox_fields, select_fields)

        # Submit the form
        self.s.click('//input[@name="save"]')
        self.wait_for_load()

        # Check that we got back to the main map
        self.assertEquals(
            self.environment['base_url'] + '/', self.s.get_location())

        # Return to the edit page
        self.open_path('/edit?facility_name=mspphaiti.org..11136')
        self.assertTrue(self.s.get_text('//h1').startswith('Edit'))

        # Nickname and affiliation fields should not be shown this time
        self.assert_no_element('//input[@name="auth_nickname"]')
        self.assert_no_element('//input[@name="auth_affiliation"]')
        del text_fields['auth_nickname']
        del text_fields['auth_affiliation']

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
        select_fields = {'facility_type': '', 'category': '',
                         'construction': '', 'reachable_by_road': '',
                         'can_pick_up_patients': '', 'operational_status': ''}
        self.fill_fields(text_fields, checkbox_fields, select_fields)

        # Submit the form
        self.s.click('//input[@name="save"]')
        self.wait_for_load()

        # Return to the edit page
        self.open_path('/edit?facility_name=mspphaiti.org..11136')
        self.assertTrue(self.s.get_text('//h1').startswith('Edit'))

        # Check that everything is now empty or deselected
        self.verify_fields(text_fields, checkbox_fields, select_fields)

        # Set the integer fields to zero
        self.s.type('//input[@name="available_beds"]', '  0')
        self.s.type('//input[@name="total_beds"]', '0  ')

        # Submit the form
        self.s.click('//input[@name="save"]')
        self.wait_for_load()

        # Return to the edit page
        self.open_path('/edit?facility_name=mspphaiti.org..11136')
        self.assertTrue(self.s.get_text('//h1').startswith('Edit'))

        # Check that the integer fields are actually zero, not empty
        text_fields['available_beds'] = '0'
        text_fields['total_beds'] = '0'
        self.verify_fields(text_fields, checkbox_fields, select_fields)


    def fill_fields(self, text_fields, checkbox_fields, select_fields):
        """Fills in text fields, selects or deselects checkboxes, and
        makes drop-down selections.  Each of the arguments should be a
        dictionary of field names to values."""
        for name, value in text_fields.items():
            input_xpath = '//input[@name="%s"]' % name
            self.s.type(input_xpath, value)
        for name, value in checkbox_fields.items():
            checkbox_xpath = '//input[@name="%s"]' % name
            (value and self.s.check or self.s.uncheck)(checkbox_xpath)
        for name, value in select_fields.items():
            select_xpath = '//select[@name="%s"]' % name
            self.s.select(select_xpath, 'value=' + value)

    def verify_fields(self, text_fields, checkbox_fields, select_fields):
        """Checks the values of text fields, state of checkboxes, and
        selection state of options.  Each of the arguments should be a
        dictionary of field names to values."""
        for name, value in text_fields.items():
            input_xpath = '//input[@name="%s"]' % name
            self.assertEquals(value, self.s.get_value(input_xpath))
        for name, value in checkbox_fields.items():
            checkbox_xpath = '//input[@name="%s"]' % name
            self.assertEquals(value, self.s.is_checked(checkbox_xpath))
        for name, value in select_fields.items():
            select_xpath = '//select[@name="%s"]' % name
            self.assertEquals([value], self.s.get_selected_values(select_xpath))

    def verify_errors(self, text_fields):
        """Checks that each text field has an error associated with it.
        Argument should be a dictionary of field names to values"""
        for name, value in text_fields.items():
            error_xpath = '//div[@id="%s_errormsg"]' % name.split('.')[0]
            self.assertTrue(self.s.is_visible(error_xpath))

if __name__ == '__main__':
    unittest.main()
