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

"""An interactive Python console connected to an app's datastore.

Instead of running this script directly, use the 'console' shell script,
which sets up the PYTHONPATH and other necessary environment variables."""

import code
import getpass
import logging
import os
import sys

from google.appengine.ext.remote_api import remote_api_stub
from google.appengine.ext import db

from access import *
from model import *

# Set up more useful representations, handy for interactive data manipulation
# and debugging.  Unfortunately, the App Engine runtime relies on the specific
# output of repr(), so this isn't safe in production, only debugging.

def key_repr(key):
    levels = []
    while key:
        levels.insert(0, '%s %s' % (key.kind(), key.id() or repr(key.name())))
        key = key.parent()
    return '<Key: %s>' % '/'.join(levels)
db.Key.__repr__ = key_repr

def model_repr(model):
    if model.is_saved():
        key = model.key()
        return '<%s: %s>' % (key.kind(), key.id() or repr(key.name()))
    else:
        return '<%s: unsaved>' % model.kind()
db.Model.__repr__ = model_repr

def init(app_id, host=None, username=None, password=None):
    if not host:
        host = app_id + '.appspot.com'
    print 'App Engine server at %s' % host
    if not username:
        username = raw_input('Username: ')
    else:
        print 'Username: %s' % username
    # Sets up users.get_current_user() inside of the console
    os.environ['USER_EMAIL'] = username
    if not password:
        password = getpass.getpass('Password: ')
    remote_api_stub.ConfigureRemoteDatastore(
        app_id, '/remote_api', lambda: (username, password), host)

    db.Query().count()
    return host

if __name__ == '__main__':
    if len(sys.argv[1:]) < 1:
        raise SystemExit('Usage: %s <app_id> <hostname>' % sys.argv[0])
    logging.basicConfig(file=sys.stderr, level=logging.INFO)
    init(*sys.argv[1:])
    code.interact('', None, locals())
