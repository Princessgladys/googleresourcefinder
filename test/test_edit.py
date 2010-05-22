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
        self.wait_until(self.s.is_element_present, 'link=Edit this record')
        self.s.click('link=Edit this record')
        self.wait_for_load()
        self.assertTrue('/edit?' in self.s.get_location())

    def test_edit_page(self):
        """Confirms that all the fields in the edit form save the entered
        values, and these values appear pre-filled when the form is loaded."""
        # Go to the edit page
        self.login('/edit?cc=ht&facility_name=mspphaiti.org..95644')
        self.assertTrue(self.s.get_text('//h1').startswith('Edit'))

        # Fill in the form
        text_fields = dict((name, name + '_foo') for name in STR_FIELDS)
        text_fields['available_beds'] = '1'
        text_fields['total_beds'] = '2'
        checkbox_fields = dict(('services.' + name, True) for name in SERVICES)
        select_fields = {'type': 'COM', 'category': 'C/S',
                         'construction': 'Adobe', 'reachable_by_road': 'TRUE',
                         'can_pick_up_patients': 'FALSE'}
        self.fill_fields(text_fields, checkbox_fields, select_fields)

        # Submit the form
        self.s.click('//input[@name="save"]')
        self.wait_for_load()

        # Return to the edit page
        self.open_path('/edit?cc=ht&facility_name=mspphaiti.org..95644')
        self.assertTrue(self.s.get_text('//h1').startswith('Edit'))

        # Check that the new values were saved, and are pre-filled in the form
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

if __name__ == '__main__':
    unittest.main()
