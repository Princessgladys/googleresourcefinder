from selenium import selenium
import os
import unittest

ENV_OPTIONS = {
    'local': {
        'is_local': True, 
        'login_url': 'http://localhost:8080/_ah/login?'
             'continue=http%3A//localhost%3A8080/',
        'user_name': 'testuser@gmail.com',
        'email_element_id': 'email',
        'login_element_id': 'submit-login'
    }, 
    'dev': {
        'is_local': False, 
        'login_url': '/accounts/ServiceLogin?'
             'service=ah&continue=http://resourcemapper.appspot.com/'
             '_ah/login%3Fcontinue%3Dhttp://resourcemapper.appspot.com/&'
             'ltmpl=gm&ahname=Resource+Mapper&'
             'sig=c61af07a6645f768377488e2f88b61cd',
        'user_name': 'testuser@gmail.com',
        'password': '',
        'email_element_id': 'Email',
        'login_element_id': 'signIn'
    } 
} 

class ResourceMapperTestCase(unittest.TestCase):         
    def setUp(self):
        self.initEnvironment()
        self.verificationErrors = []
        self.s = selenium('localhost', 4444, '*chrome', 
                          'https://www.google.com/')
        self.s.start()

    def tearDown(self):
        self.s.stop()
        self.assertEqual([], self.verificationErrors)
    
    def login(self):
        self.s.open(self.environment['login_url'])
        self.s.type(self.environment['email_element_id'],
                    self.environment['user_name'])
        if not self.environment['is_local']:
            self.s.type('Passwd', self.environment['password'])
        
        self.s.click(self.environment['login_element_id'])
        self.s.wait_for_page_to_load('30000')

    def initEnvironment(self):
        if not os.environ.has_key('env'):
            raise Exception('Please specify environment env = {local, dev}')
        envType = os.environ['env']
        self.environment = ENV_OPTIONS[envType]
