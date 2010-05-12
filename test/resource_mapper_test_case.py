from selenium import selenium
import unittest, os

class ResourceMapperTestCase(unittest.TestCase):         
    def setUp(self):
        self.initEnvironment()
        self.verificationErrors = []
        self.selenium = selenium("localhost", 4444, "*chrome", "https://www.google.com/")
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)
    
    def login(self):
        sel = self.selenium
        sel.open(self.environment["login_url"])
        sel.type(self.environment["email_element_id"], self.environment["user_name"])
        if not self.environment["is_local"]:
            sel.type("Passwd", self.environment["password"])
        
        sel.click(self.environment["login_element_id"])
        sel.wait_for_page_to_load("30000")
        
    def initEnvironment(self):
        envType = os.environ["env"]
        env = {}
        env["local"] = {
                      "is_local" : True, 
                      "login_url" : 'http://localhost:8080/_ah/login?continue=http%3A//localhost%3A8080/',
                      "user_name" : "testuser@gmail.com",
                      "email_element_id" : "email",
                      "login_element_id" : "submit-login" }
        env["dev"] = {
                      "is_local" : False, 
                      "login_url" : "/accounts/ServiceLogin?service=ah&continue=http://resourcemapper.appspot.com/_ah/login%3Fcontinue%3Dhttp://resourcemapper.appspot.com/&ltmpl=gm&ahname=Resource+Mapper&sig=c61af07a6645f768377488e2f88b61cd",
                      "user_name" : "testuser@gmail.com",
                      "password" : "",
                      "email_element_id" : "Email",
                      "login_element_id" : "signIn" }
        if envType == None:
            envType = "local"
        if env[envType] == None: 
            raise Exception("Environment" + envType + " is not defined. Allowed environments are: local, dev, demo")
        self.environment = env[envType]
        
