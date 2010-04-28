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

from google.appengine.ext import db
import logging

ROLES = ['user', 'editor', 'superuser']

class Authorization(db.Model):
    timestamp = db.DateTimeProperty(auto_now_add=True)
    description = db.StringProperty(required=True)
    email = db.StringProperty()
    user_id = db.StringProperty()
    token = db.StringProperty()
    # user roles are in the format: country_code:role
    # where role is one of ROLES
    # an empty country_code means the user has the role for
    # all countries
    user_roles = db.StringListProperty()
    requested_roles = db.StringListProperty()

def check_token(token):
    return Authorization.all().filter('token =', token).get()

def check_email(email):
    return Authorization.all().filter('email =', email).get()

def check_user_id(user_id):
    return Authorization.all().filter('user_id =', user_id).get()

def check_request(request, user):
    if request.get('token'):
        return check_token(request.get('token'))
    if user:
        return check_email(user.email()) or check_user_id(user.user_id())

def check_user_role(auth, role, cc):
    """Return True if the auth user has the given role for the given country"""
    return auth and ("%s:%s" % (cc or '',role) in auth.user_roles or
                     ":%s" % role in auth.user_roles)

def check_and_log(request, user):
    auth = check_request(request, user)
    logging.info(
        'access.py: ' +
        (auth and 'authorized %s' % auth.description or 'not authorized') +
        ' (token=%r, user=%r)' % (request.get('token'), user and user.email()))
    if not auth and user:
        # we create an auth for a login user with no roles and don't save it
        auth = Authorization(description=user.nickname(),
                             email=user.email())
    return auth
