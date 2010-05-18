# Copyright 2009-2010, Ka-Ping Yee
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

"""
Manages per-user permissions.  Three types of access are defined
- user = User can view the app
- editor = User can make changes
- superuser = User can grant access to other users

There is also a token system for allowing access to anonymous users by passing
them a url.
"""

from google.appengine.ext import db
import logging

# Roles explained:
# 'viewer' user can view the UI (unnecessary if default is 'anyone can view')
# 'editor' user can edit basic fields of facilities (unnecessary if default is
#          'any signed in user can make edits')
# 'supereditor' user can edit all fields of facilities
# 'adder' user can add new facilities
# 'remover' user can remove facilities from the UI (not delete them entirely)
# 'superuser' user can grant access to other users (but still needs the other
#             roles to add, remove, edit, etc)
ROLES = ['viewer', 'adder', 'remover', 'editor', 'supereditor', 'superuser']

class Authorization(db.Model):
    timestamp = db.DateTimeProperty(auto_now_add=True)
    description = db.StringProperty(required=True)
    email = db.StringProperty()
    user_id = db.StringProperty()
    nickname = db.StringProperty()
    affiliation = db.StringProperty()
    token = db.StringProperty()
    # user_role is of the form type:role
    # type is either 'f' or '' for now, role is one of ROLES,
    user_roles = db.StringListProperty()
    requested_roles = db.StringListProperty()

def check_token(token):
    return Authorization.all().filter('token =', token).get()

def check_email(email):
    return Authorization.all().filter('email =', email).get()

def check_user_id(user_id):
    return Authorization.all().filter('user_id =', user_id).get()

def check_request(request, user):
    if request.get('access_token'):
        return check_token(request.get('access_token'))
    if user:
        return check_email(user.email()) or check_user_id(user.user_id())

def check_user_role(auth, role, type='f'):
    """Return True if the auth user has the given role"""
    return auth and ("%s:%s" % (type, role) in auth.user_roles or
                     ":%s" % role in auth.user_roles)

def check_and_log(request, user):
    auth = check_request(request, user)
    logging.info(
        'access.py: ' +
        (auth and 'authorized %s' % auth.description or 'not authorized') +
        ' (access_token=%r, user=%r)'
        % (request.get('access_token'), user and user.email()))
    if not auth and user:
        # we create an auth for a login user with no roles and don't save it
        auth = Authorization(description=user.nickname(),
                             email=user.email())
    return auth
