from model import Account, Subject, db
from selenium_test_case import Regex, SeleniumTestCase
import datetime
import scrape

# "name" attributes of the checkboxes for available services in the edit form.
SERVICES = [
    'GENERAL_SURGERY',
    'ORTHOPEDICS',
    'NEUROSURGERY',
    'VASCULAR_SURGERY',
    'INTERNAL_MEDICINE',
    'CARDIOLOGY',
    'INFECTIOUS_DISEASE',
    'PEDIATRICS',
    'POSTOPERATIVE_CARE',
    'REHABILITATION',
    'OBSTETRICS_GYNECOLOGY',
    'MENTAL_HEALTH',
    'DIALYSIS',
    'LAB',
    'X_RAY',
    'CT_SCAN',
    'BLOOD_BANK',
    'MORTUARY_SERVICES',
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

EDIT_PATH = '/edit?subdomain=haiti&subject_name=example.org/123'
ADD_PATH = '/edit?subdomain=haiti&add_new=yes&subject_type=hospital'


class EditTest(SeleniumTestCase):
    def setUp(self):
        SeleniumTestCase.setUp(self)
        self.put_subject(
            'haiti', 'example.org/123',
            title='title_foo', location=db.GeoPt(51.5, 0))
        self.put_account(actions=['*:view', '*:edit', '*:add'])  # allow edits
        self.set_default_permissions(actions=['*:view']) # allow view by default
        self.s = scrape.Session()

    def tearDown(self):
        for subject in Subject.all_in_subdomain('haiti'):
            self.delete_subject('haiti', subject.name)
        self.delete_account()
        self.delete_default_account()
        SeleniumTestCase.tearDown(self)

    def test_edit_link(self):
        """Confirms that the "Edit this record" link in the detail bubble
        goes to the edit form."""
        self.edit(login=True)

    def test_edit_page(self):
        """Separate-page edit: Confirms that all the fields in the edit form
        save the entered values, and these values appear pre-filled when the
        form is loaded."""
        def login(self):
            self.login_to_edit_page()

        def save(self):
            self.click('//input[@name="save"]')
            self.wait_for_load()
            # Check that we got back to the main map
            assert (self.get_location() ==
                    self.config.base_url + '/?subdomain=haiti')

        def edit(self):
            self.open_edit_page()

        # Check that feed is empty
        feed = self.s.go('http://localhost:8081/feeds/delta')
        assert feed.first('atom:feed')
        assert feed.first('atom:feed').all('atom:entry') == []

        self.run_edit(login, save, edit)

        # TODO(kpy): This feature is disabled until we can debug it.
        # Re-enable this test when the delta feed is working properly.
        # Check that feed is not empty now
        # feed = self.s.go('http://localhost:8081/feeds/delta')
        # assert feed.first('atom:feed')
        # assert feed.first('atom:feed').first('atom:entry')

    def test_edit_permissions(self):
        """Ensure that the edit page can't be used without edit permission."""
        self.login('/edit')

        self.delete_account()
        self.put_account(actions=['*:view'])  # view only
        assert self.get_status_code(EDIT_PATH) == 403
        assert self.get_status_code(ADD_PATH) == 403

        self.delete_account()
        self.put_account(actions=['*:edit'])  # edit but not add
        assert self.get_status_code(EDIT_PATH) == 200
        assert self.get_status_code(ADD_PATH) == 403

        self.delete_account()
        self.put_account(actions=['*:add'])  # add but not edit
        assert self.get_status_code(EDIT_PATH) == 403
        assert self.get_status_code(ADD_PATH) == 200

        self.delete_account()
        self.put_account(actions=['*:edit', '*:add'])  # both add and edit
        assert self.get_status_code(EDIT_PATH) == 200
        assert self.get_status_code(ADD_PATH) == 200

    def test_add_page(self):
        """Confirms that a new subject can be created on the stand-alone
        edit page, and its values appear pre-filled when the form is
        subsequently loaded to edit the newly created subject."""
        names_before = [s.name for s in Subject.all_in_subdomain('haiti')]

        def login(self):
            self.login(ADD_PATH)
            self.assert_text(Regex('Add a new.*'), '//h1')

        def save(self):
            self.click('//input[@name="save"]')
            self.wait_for_load()

        def edit(self):
            # Look for the newly created subject.
            names_after = [s.name for s in Subject.all_in_subdomain('haiti')]
            extra_names = list(set(names_after) - set(names_before))
            assert len(extra_names) == 1

            # Open it in the edit page to confirm that its values are set.
            self.open_path(
                '/edit?subdomain=haiti&subject_name=%s' % extra_names[0])

        self.run_edit(login, save, edit)

    def test_inplace_edit(self):
        """In-place edit: Confirms that all the fields in the in-place edit
        form save the entered values, and these values appear pre-filled when
        the form is loaded."""
        def login(self):
            self.edit(login=True)

        def save(self):
            self.click('//input[@name="save"]')
            self.wait_until(self.is_visible, 'data')

        def edit(self):
            self.edit()

        self.run_edit(login, save, edit)

    def run_edit(self, login_func, save_func, edit_func):
        """Runs the edit flow, for use in both inplace and separate page
        editing."""

        login_func(self)

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
        text_fields['total_beds__comment'] = 'comment1'
        text_fields['location.lat'] = '18.537207 '
        text_fields['location.lon'] = '\t-72.349663'
        text_fields['location__comment'] = 'comment2'
        checkbox_fields = dict(('services.' + name, True) for name in SERVICES)
        select_fields = {'organization_type': 'NGO', 'category': 'CLINIC',
                         'construction': 'ADOBE', 'reachable_by_road': 'TRUE',
                         'can_pick_up_patients': 'FALSE',
                         'operational_status': 'NO_SURGICAL_CAPACITY'}
        self.fill_fields(text_fields, checkbox_fields, select_fields)

        # Submit the form
        save_func(self)

        # Check that the facility list is updated
        regex = Regex('.*1 / 2.*General Surgery.*')
        self.wait_until(lambda: regex.match(self.get_text('id=subject-1')))

        edit_func(self)

        # Nickname and affiliation fields should not be shown this time
        self.assert_no_element('//input[@name="account_nickname"]')
        self.assert_no_element('//input[@name="account_affiliation"]')
        del text_fields['account_nickname']
        del text_fields['account_affiliation']

        # Check that the new values were saved, and are pre-filled in the form
        # except for comments which should remain empty.
        text_fields['available_beds'] = '1'  # whitespace should be gone
        text_fields['total_beds'] = '2'  # whitespace should be gone
        text_fields['location.lat'] = '18.537207'  # whitespace should be gone
        text_fields['location.lon'] = '-72.349663'  # whitespace should be gone
        text_fields['total_beds__comment'] = ''
        text_fields['location__comment'] = ''
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
        save_func(self)

        # Check that the facility list is updated to reflect the emptying
        # Note the en-dash \u2013 implies "no value"
        regex = Regex(u'.*\u2013 / \u2013')
        self.wait_until(lambda: regex.match(self.get_text('id=subject-1')))

        edit_func(self)

        # Check that everything is now empty or deselected
        self.verify_fields(text_fields, checkbox_fields, select_fields)

        # Set the integer fields to zero
        self.type('//input[@name="available_beds"]', '  0')
        self.type('//input[@name="total_beds"]', '0  ')

        # Submit the form
        self.click('//input[@name="save"]')

        save_func(self)

        # Check that the facility list is updated to show the zeros
        regex = Regex('.*0 / 0')
        self.wait_until(lambda: regex.match(self.get_text('id=subject-1')))

        edit_func(self)

        # Check that the integer fields are actually zero, not empty
        text_fields['available_beds'] = '0'
        text_fields['total_beds'] = '0'
        self.verify_fields(text_fields, checkbox_fields, select_fields)

    def test_edit_comments(self):
        """Tests comments and bubble reload during in-place edit."""
        def login(self):
            self.login_to_edit_page()

        def save(self):
            self.save_and_load_bubble()

        def edit(self):
            self.open_edit_page()

        self.run_edit_comments(login, save, edit)

    def test_inplace_edit_comments(self):
        """Tests comments and bubble reload during in-place edit."""
        def login(self):
            self.edit(login=True)

        def save(self):
            self.click('//input[@name="save"]')
            self.wait_until(self.is_visible, 'data')

        def edit(self):
            self.edit()

        self.run_edit_comments(login, save, edit)

    def run_edit_comments(self, login_func, save_func, edit_func):
        text_fields = {}

        # Fill comment, but not available beds field ----------------------- #

        login_func(self)

        # Fill in the form. Change available beds comment.
        text_fields['account_nickname'] = 'Test'
        text_fields['account_affiliation'] = 'Test'
        text_fields['total_beds'] = ''
        text_fields['total_beds__comment'] = 'comment_foo!'
        text_fields['location.lat'] = '18.537207 '
        text_fields['location.lon'] = '-72.349663'
        checkbox_fields = {}
        select_fields = {}
        self.fill_fields(text_fields, checkbox_fields, select_fields)

        # Reload bubble, go to change details page, and confirm changes
        save_func(self)

        self.click('link=Change details')
        assert self.is_text_present(u'Total beds: \u2013')
        assert self.is_text_present('comment_foo!')

        # Fill available beds, but not comment field ----------------------- #

        # Nickname and affiliation fields should not be shown this time
        del text_fields['account_nickname']
        del text_fields['account_affiliation']

        # Return to the edit form
        edit_func(self)

        # Change beds but without comment
        text_fields['total_beds'] = '37'
        text_fields['total_beds__comment'] = ''
        self.fill_fields(text_fields, checkbox_fields, select_fields)

        save_func(self)

        # Go to change details page, and confirm changes
        self.click('link=Change details')
        assert self.is_text_present('Total beds: 37')
        assert not self.is_text_present('comment_foo!')

        # Fill available beds and comment fields --------------------------- #

        # Return to the edit form
        edit_func(self)

        # Change total beds and comment fields.
        text_fields['total_beds'] = '99'
        text_fields['total_beds__comment'] = 'comment_bar!'
        self.fill_fields(text_fields, checkbox_fields, select_fields)

        # Reload bubble, go to change details page, and confirm changes
        save_func(self)

        # Go to change details page, and confirm changes
        self.wait_for_element('link=Change details')
        self.click('link=Change details')
        self.wait_until(self.is_text_present, 'Total beds: 99')
        self.wait_until(self.is_text_present, 'comment_bar!')

        # Delete both available beds and comment fields -------------------- #

        # Return to the edit form
        edit_func(self)

        # Fill fields
        text_fields['total_beds'] = ''
        text_fields['total_beds__comment'] = ''
        self.fill_fields(text_fields, checkbox_fields, select_fields)

        # Reload bubble and go to change details page
        save_func(self)

        # Go to change details page, and confirm changes
        self.click('link=Change details')
        assert self.is_text_present(u'Total beds: \u2013')
        assert not self.is_text_present('comment_bar!')

    def test_inplace_edit_signed_out(self):
        """In-place edit starting from signed out:"""
        self.open_path('/')

        # Open a bubble
        self.click('id=subject-1')
        self.wait_for_element('link=Sign in to edit')

        # Click Sign in to edit
        self.click_and_wait('link=Sign in to edit')

        # Login in at the login screen
        self.login()

        # Wait for the edit form to appear
        self.wait_until(self.is_visible, 'edit-data')
        self.assert_element('//input[@name="account_nickname"]')

    def test_inplace_edit_no_location_facility(self):
        self.delete_subject('haiti', 'example.org/123')
        self.put_subject('haiti', 'example.org/123', title='title_foo')

        self.open_path('/')
        self.click_and_wait('link=Sign in')
        self.login()

        # Facility list click for a no-facility location opens the edit form
        # directly
        self.click('id=subject-1')
        self.wait_until(self.is_visible, 'edit-data')
        self.assert_element('//input[@name="account_nickname"]')

    def test_no_location_facility_edit_signed_out(self):
        """In-place edit starting from signed out with a no location subject:"""
        self.delete_subject('haiti', 'example.org/123')
        self.put_subject('haiti', 'example.org/123', title='title_foo')

        self.open_path('/')

        # Try to open a bubble, look for the sign in link
        self.click('id=subject-1')
        self.wait_for_element('id=status-sign-in')

        # Click Sign in
        self.click_and_wait('id=status-sign-in')

        # Login in at the login screen
        self.login()

        # Wait for the edit form to appear
        self.wait_until(self.is_visible, 'edit-data')
        self.assert_element('//input[@name="account_nickname"]')

    def edit(self, login=False):
        """Goes to edit form for subject 1"""
        if login:
            self.open_path('/')
            self.click_and_wait('link=Sign in')
            self.login()
        self.click('id=subject-1')
        self.wait_for_element('link=Edit this record')
        self.click('link=Edit this record')
        self.wait_until(self.is_visible, 'edit-data')

    def save_and_load_bubble(self):
        # Submit the form
        self.click('//input[@name="save"]')
        self.wait_for_load()

        # Check that we got back to the main map
        assert self.get_location() == self.config.base_url + '/?subdomain=haiti'

        # Test bubble change history comments
        self.click('id=subject-1')
        self.wait_for_element('link=Change details')

    def open_edit_page(self):
        self.open_path(EDIT_PATH)
        self.assert_text(Regex('Edit.*'), '//h1')

    def login_to_edit_page(self):
        self.login(EDIT_PATH)
        self.assert_text(Regex('Edit.*'), '//h1')

    def fill_fields(self, text_fields, checkbox_fields, select_fields):
        """Fills in text fields, selects or deselects checkboxes, and
        makes drop-down selections.  Each of the arguments should be a
        dictionary of field names to values."""
        for name, value in text_fields.items():
            self.type('//*[@name=%r]' % name, value)
        for name, value in checkbox_fields.items():
            (value and self.check or self.uncheck)('//*[@name=%r]' % name)
        for name, value in select_fields.items():
            self.select('//*[@name=%r]' % name, 'value=' + value)

    def verify_fields(self, text_fields, checkbox_fields, select_fields):
        """Checks the values of text fields, state of checkboxes, and
        selection state of options.  Each of the arguments should be a
        dictionary of field names to values."""
        for name, value in text_fields.items():
            self.assert_value(value, '//*[@name=%r]' % name)
        for name, value in checkbox_fields.items():
            assert value == self.is_checked('//*[@name=%r]' % name)
        for name, value in select_fields.items():
            assert [value] == self.get_selected_values('//*[@name=%r]' % name)

    def verify_errors(self, text_fields):
        """Checks that all the given text fields have visible error messages.
        Argument should be a dictionary of field names to values."""
        for name, value in text_fields.items():
            error_xpath = '//div[@id="%s_errormsg"]' % name.split('.')[0]
            self.assertTrue(self.is_visible(error_xpath))
