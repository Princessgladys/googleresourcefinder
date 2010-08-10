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

import logging

from google.appengine.ext import db

import cache
from model import Account

# Actions that are permitted/forbidden according to the 'actions' property:
#     'view': view the UI (unnecessary if default is 'anyone can view')
#     'edit': edit basic fields (unnecessary if default is
#         'any signed in user can make edits')
#     'advanced_edit': edit all fields
#     'add': add new subjects
#     'remove': remove subjects from the UI (not delete them entirely)
#     'grant': grant access to other users
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
        if user.email():
            return check_email(user.email())
        if user.user_id():
            return check_user_id(user.user_id())

def get_default_permissions():
    """Returns the list of default permissions granted to all users,
    which resides in the special Account with key_name='default'."""
    account = cache.DEFAULT_ACCOUNT.get()
    return account and account.actions or []

def check_action_permitted(account, subdomain, action):
    """Returns True if the account is allowed to perform the given action
    in the given subdomain."""
    # Items in the Account.actions list have the form subdomain + ':' + verb,
    # where '*' can be used a wildcard for the subdomain or the verb.
    actions = get_default_permissions() + (account and account.actions or [])
    return ('%s:%s' % (subdomain, action) in actions or
            '%s:*' % subdomain in actions or
            '*:%s' % action in actions or
            '*:*' in actions)

def check_and_log(request, user):
    account = check_request(request, user)
    logging.info(
        'access.py: ' + (account and 'authorized %s' % account.description
                         or 'not authorized') +
        ' (access_token=%r, user=%r)'
        % (request.get('access_token'), user and user.email()))
    if not account and user:
        # Create an account for this user with no actions, but don't save it.
        account = Account(description=user.nickname(), email=user.email())
    return account
