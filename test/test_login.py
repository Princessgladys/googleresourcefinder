from resource_mapper_test_case import ResourceMapperTestCase
import unittest

class LoginTestCase(ResourceMapperTestCase):
         
    def test_map_loaded(self):
        self.login()
        try: self.failUnless(self.selenium.is_element_present("map"), "login failed")
        except AssertionError, e: self.verificationErrors.append(str(e))
        

if __name__ == "__main__":
    unittest.main()
