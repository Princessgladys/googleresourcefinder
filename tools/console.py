#!/usr/bin/python2.5
# Copyright 2009-2010 by Ka-Ping Yee
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import code
import getpass
import logging
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(PROJECT_DIR, 'app')
sys.path.append(APP_DIR)

for dir in [
    os.environ.get('APPENGINE_DIR', ''),
    '/usr/lib/google_appengine',
    '/usr/local/lib/google_appengine',
    '/usr/local/google_appengine'
]:
    if os.path.isdir(dir):
        APPENGINE_DIR = dir
        break
else:
    raise SystemExit('Could not find google_appengine directory. '
                     'Please set APPENGINE_DIR.')

sys.path.append(APPENGINE_DIR)
sys.path.append(APPENGINE_DIR + '/lib/django')
sys.path.append(APPENGINE_DIR + '/lib/webob')
sys.path.append(APPENGINE_DIR + '/lib/yaml/lib')

from google.appengine.ext.remote_api import remote_api_stub
from google.appengine.ext import db

from access import *
from model import *

def init(app_id, host, username=None, password=None):
    print 'App Engine server at %s' % host
    if not username:
        username = raw_input('Username: ')
    else:
        print 'Username: %s' % username
    if not password:
        password = getpass.getpass('Password: ')
    remote_api_stub.ConfigureRemoteDatastore(
        app_id, '/remote_api', lambda: (username, password), host)

    db.Query().get()
    return host

if __name__ == '__main__':
    if len(sys.argv[1:]) < 2:
        raise SystemExit('Usage: %s <app_id> <hostname>' % sys.argv[0])
    init(*sys.argv[1:])
    logging.basicConfig(file=sys.stderr, level=logging.INFO)
    code.interact('', None, locals())
