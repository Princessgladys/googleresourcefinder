from resource_mapper_test_case import ResourceMapperTestCase
import unittest

class LoginTestCase(ResourceMapperTestCase):
    def test_map_loaded(self):
        self.login()
        self.failUnless(self.s.is_element_present('map'), 'login failed')        

if __name__ == "__main__":
    unittest.main()
