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
Manages per-user permissions.

There is also a token system for allowing access to anonymous users by passing
them a url.
"""

from google.appengine.ext import db
import logging
from model import Account

# Actions explained:
# 'view' user can view the UI (unnecessary if default is 'anyone can view')
# 'edit' user can edit basic fields of facilities (unnecessary if default is
#          'any signed in user can make edits')
# 'advanced_edit' user can edit all fields of facilities
# 'add' user can add new facilities
# 'remove' user can remove facilities from the UI (not delete them entirely)
# 'grant' user can grant access to other users
ACTIONS = ['view', 'add', 'remove', 'edit', 'advanced_edit', 'grant']

def check_token(token):
    return Account.all().filter('token =', token).get()

def check_email(email):
    return Account.all().filter('email =', email).get()

def check_user_id(user_id):
    return Account.all().filter('user_id =', user_id).get()

def check_request(request, user):
    if request.get('access_token'):
        return check_token(request.get('access_token'))
    if user:
        return check_email(user.email()) or check_user_id(user.user_id())

def check_action_permitted(account, action):
    """Return True if the account is allowed to perform the given action"""
    logging.info(account)
    logging.info(action)
    logging.info(account.actions)
    return account and (action in account.actions
                        or ":%s" % action in account.actions)

def check_and_log(request, user):
    account = check_request(request, user)
    logging.info(
        'access.py: ' + (account and 'authorized %s' % account.description
                         or 'not authorized') +
        ' (access_token=%r, user=%r)'
        % (request.get('access_token'), user and user.email()))
    if not account and user:
        # we create an account for a logged-in user with no actions
        # but don't save it
        account = Account(description=user.nickname(), email=user.email())
    return account
