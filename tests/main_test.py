from model import db
from selenium_test_case import Regex, SeleniumTestCase
import datetime
import model

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
            'Mortuary Services',
            'Outpatient Care',
            'Emergency Services',
            'Cholera Treatment Center',
            'Other']

class MainTestCase(SeleniumTestCase):
    def setUp(self):
        SeleniumTestCase.setUp(self)
        self.put_account(actions=['*:view'])
        self.put_subject(
            'haiti', 'example.org/1000',
            title='title_foo1', location=db.GeoPt(51.5, 0))
        self.put_subject(
            'haiti', 'example.org/1001',
            title='title_foo2', location=db.GeoPt(50.5, 1),
            operational_status='CLOSED_OR_CLOSING')
        self.put_subject(
            'haiti', 'example.org/1002',
            title='title_foo3', location=db.GeoPt(49.5, 2),
            alert_status='alert_status_foo')
        self.put_subject(
            'pakistan', 'example.org/1003',
            title='title_foo4', location=db.GeoPt(48.6, 3),
            alert_status='alert_status_foo')
        self.bubble_xpath = "//div[@class='bubble']/span/span[@class='title']"

    def tearDown(self):
        self.delete_account()
        self.delete_default_account()
        if model.Subject.get('haiti', 'example.org/1000'):
            self.delete_subject('haiti', 'example.org/1000')
        self.delete_subject('haiti', 'example.org/1001')
        self.delete_subject('haiti', 'example.org/1002')
        self.delete_subject('pakistan', 'example.org/1003')
        SeleniumTestCase.tearDown(self)

    def test_default_permissions(self):
        """Confirms that when the default account has 'view' permission,
        login is not required."""
        # No default permission; should redirect to login page.
        self.open_path('/?subdomain=haiti')
        self.wait_for_element(self.config.login_form)

        # 'view' permission provided by default; should go straight to map.
        self.set_default_permissions(['*:view'])
        self.open_path('/?subdomain=haiti&flush=yes')
        self.wait_for_element('map')

        # Even with 'edit' granted by default, editing should still need login.
        self.set_default_permissions(['*:view', '*:edit'])
        self.open_path(
            '/edit?subdomain=haiti&subject_name=example.org/1000&flush=yes')
        self.wait_for_element(self.config.login_form)

        # After login, editing should be allowed.
        self.login(
            '/edit?subdomain=haiti&subject_name=example.org/1000&flush=yes')
        self.assert_text(Regex('Edit.*'), '//h1')

    def test_elements_present(self):
        """Confirms that listbox and maps with elements are present and
        interaction between a list and a map works."""
        self.login('/?subdomain=haiti')
        
        # Should have automatically redirected to subdomain 'haiti'.
        assert 'subdomain=haiti' in self.get_location()
 
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
        self.click(subject_xpath)
        self.wait_for_element(self.bubble_xpath)
        self.assert_text(subject_title, self.bubble_xpath)

        # Check a few links
        assert self.is_visible('link=Help')
        assert self.is_visible('link=Export CSV')
        assert self.is_visible('link=View Master List archive')

        # Check pop out button not here
        assert not self.is_text_present('New window')

        # Re-open page with iframe param set to yes and check again
        self.open_path('/?subdomain=haiti&iframe=yes')
        assert self.is_text_present('New window')

        # Check the add facility button
        map_control = '//div[@class="new-subject-map-control-ui"]'
        assert not self.is_element_present(map_control)

        # Remove permissions from account and add to default. Make sure button
        # is still there.
        self.set_default_permissions(['*:view', '*:add'])
        self.open_path('/?subdomain=haiti&flush=yes')
        self.wait_for_element(map_control)

        # Add permissions to account and remove from default permissions,
        # then make sure add facility button loads
        self.set_default_permissions(['*:view'])
        self.delete_account()
        self.put_account(actions=['*:view', '*:add'])
        self.open_path('/?subdomain=haiti&flush=yes')
        self.wait_for_element(map_control)

    def test_closed_facilities(self):
        """Confirms that closed facilities appear grey in the facility list
        and have a warning message in their info bubble."""
        self.login_and_check_first_facility()

        # Facility 1001 is closed (grey in list and 'closed' message in bubble).
        assert 'disabled' in self.get_attribute('//tr[@id="subject-2"]/@class')
        self.click('id=subject-2')
        self.wait_for_element(self.bubble_xpath)
        assert self.is_text_present(
            'Note: This facility has been marked closed')

        # Make sure the message appears in other languages, too.
        self.open_path('/?subdomain=haiti&lang=fr')
        self.wait_for_element('subject-2')
        self.click('id=subject-2')
        self.wait_for_element(self.bubble_xpath)
        assert self.is_text_present(
            u'Note: Cet \xe9tablissement a \xe9t\xe9 marqu\xe9e ferm\xe9e.')

        # Change facility 1000 to closed.
        self.put_subject(
            'haiti', 'example.org/1000',
            title='title_foo1', location=db.GeoPt(51.5, 0),
            operational_status='CLOSED_OR_CLOSING')

        # Reload and flush the cache so we see the changes.
        # Also switch back from French to English.
        self.open_path('/?subdomain=haiti&flush=yes&lang=en')

        # Facility 1000 should now be grey and have a 'closed' message.
        assert 'disabled' in self.get_attribute('//tr[@id="subject-1"]/@class')
        self.click('id=subject-1')
        self.wait_for_element(self.bubble_xpath)
        assert self.is_text_present(
            'Note: This facility has been marked closed')

    def test_facilities_on_alert(self):
        """Confirms that facilities on alert appear red in the facility list and
        have an alert message in their info bubble."""
        self.login_and_check_first_facility()

        # Facility 1002 is on alert (red in list and alert message in bubble).
        assert 'on-alert' in self.get_attribute('//tr[@id="subject-3"]/@class')
        self.click('id=subject-3')
        self.wait_for_element(self.bubble_xpath)
        assert self.is_text_present('Alert: alert_status_foo')

        # Add alert status to facility 1000
        self.put_subject(
            'haiti', 'example.org/1000',
            title='title_foo1', location=db.GeoPt(51.5, 0),
            alert_status='alert_status_bar')

        # Reload and flush the cache so we see the changes.
        self.open_path('/?subdomain=haiti&flush=yes')

        # Facility 1000 should now be red and have an alert message.
        assert 'on-alert' in self.get_attribute('//tr[@id="subject-1"]/@class')
        self.click('id=subject-1')
        self.wait_for_element(self.bubble_xpath)
        assert self.is_text_present('Alert: alert_status_bar')

        # Remove alert status from facility 1000
        self.put_subject(
            'haiti', 'example.org/1000',
            title='title_foo1', location=db.GeoPt(51.5, 0),
            alert_status='')

        # Reload and flush the cache so we see the changes.
        self.open_path('/?subdomain=haiti&flush=yes')

        # Facility 1000 should now be red and have an alert message.
        assert 'on-alert' not in self.get_attribute(
            '//tr[@id="subject-1"]/@class')
        self.click('id=subject-1')
        self.wait_for_element(self.bubble_xpath)
        assert not self.is_text_present('Alert: alert_status_bar')

    def test_choose_subdomain_page(self):
        """Confirms choose subdomain page works as expected"""
        self.open_path('/')
        self.wait_for_element('link=haiti')
        assert self.is_visible('link=haiti')
        assert self.is_visible('link=pakistan')
        self.click('link=pakistan')
        self.wait_for_element(self.config.login_form)
        self.login()
        self.wait_for_element('subject-1')
        self.assert_no_element('link=View Master List archive')

    def test_viewport_filter(self):
      """Confirms the 'in map view' checkbox correctly filters by viewport"""
      self.login('/?subdomain=haiti')

      # Start with 3 subjects visible in the subject list
      assert self.is_visible('subject-1')
      assert self.is_visible('subject-2')
      assert self.is_visible('subject-3')

      # Click 'in map view', no change
      self.click('id=viewport-filter')
      self.wait_until(self.is_visible, 'subject-1')
      assert self.is_visible('subject-2')
      assert self.is_visible('subject-3')

      # Zoom into the second subject, subjects 1 and 3 disappear from the list
      self.run_script('map.setZoom(map.getZoom() + 5)')
      self.wait_until(self.is_not_visible, 'subject-1')
      assert self.is_visible('subject-2')
      assert self.is_not_visible('subject-3')

      # Pan to the first subject, subjects 2 and 3 disappear from the list
      self.run_script('map.panTo(new google.maps.LatLng(51.5, 0))')
      self.wait_until(self.is_visible, 'subject-1')
      assert self.is_not_visible('subject-2')
      assert self.is_not_visible('subject-3')

      # Turn off 'in map view', all subjects visible again in the list
      self.click('id=viewport-filter')
      self.wait_until(self.is_visible, 'subject-2')
      assert self.is_visible('subject-1')
      assert self.is_visible('subject-3')

      # Turn on 'in map view' again, only subject 1 is visible in the list
      self.click('id=viewport-filter')
      self.wait_until(self.is_not_visible, 'subject-2')
      assert self.is_visible('subject-1')
      assert self.is_not_visible('subject-3')

    def login_and_check_first_facility(self):
        """Helper function. Logs into the haiti subdomain, waits for the list to
        load, then checks to make sure that facility 1000 is open."""
        self.login('/?subdomain=haiti')

        # Wait for the facility list to populate.
        self.wait_for_element('subject-3')

        # Facility 1000 is open (black in list and no 'closed' message).
        assert 'disabled' not in self.get_attribute(
            '//tr[@id="subject-1"]/@class')
        self.click('id=subject-1')
        self.wait_for_element(self.bubble_xpath)
        assert not self.is_text_present(
            'Note: This facility has been marked closed')

    def test_embed_link(self):
        # Login and wait for page to load
        self.login('/?subdomain=haiti')
        self.wait_for_element('subject-3')

        # Make sure that embed link is present
        assert self.is_text_present('Embed on your site')
        self.click_and_wait_for_new_window('embed-rf')

        # Verify that this looks like the embed window
        params = self.get_location().split('/')[-1]
        location = params.split('?')[0]
        assert location == 'embed'
        assert self.is_text_present('Embedding the Application')

    def test_purge_delete(self):
        model.Subscription(key_name='haiti:example.org/1000:test@example.com',
                           user_email='test@example.com',
                           subject_name='haiti:example.org/1000',
                           frequency='daily').put()
        model.PendingAlert(
            key_name='daily:test@example.com:haiti:example.org/1000',
            user_email='test@example.com', frequency='daily', type='hospital',
            subject_name='haiti:example.org/1000').put()

        # Login to main page
        self.set_default_permissions(['*:view'])
        self.delete_account()
        self.open_path('/?subdomain=haiti')
        self.wait_for_element('//tr[@id="subject-1"]')

        # Open facility bubble. Default permissions do not contain purge. Make
        # sure the delete link is not present in the bubble.
        self.click('id=subject-1')
        self.wait_for_element(self.bubble_xpath)
        assert not self.is_text_present('Delete Permanently')

        # Login with account, that does not have permissions. Link should still
        # not be present in the bubble.
        self.put_account(actions=['*:purge'])
        self.click_and_wait('link=Sign in')
        self.login()
        self.click('id=subject-1')
        self.wait_for_element(self.bubble_xpath)
        assert self.is_text_present('Delete Permanently')

        # Click delete button. Make sure facility is actually gone.
        self.click('id=purge-delete')
        assert len(model.Subject.all().fetch(4)) == 3
        assert not model.Subscription.all().get()
        assert not model.PendingAlert.all().get()
