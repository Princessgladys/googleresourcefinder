from selenium_test_case import SeleniumTestCase


class LoginTest(SeleniumTestCase):
    def test_map_loaded(self):
        assert self.login('/?subdomain=haiti')
        self.assert_element('map')
