from selenium_test_case import SeleniumTestCase
import unittest

class LoginTestCase(SeleniumTestCase):
    def test_map_loaded(self):
        self.assertTrue(self.login('/'))
        self.assertTrue(self.is_element_present('map'))

if __name__ == "__main__":
    unittest.main()
