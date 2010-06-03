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

import datetime
import logging
import model
import re
import urlparse
import utils
import wsgiref
from access import check_action_permitted
from main import USE_WHITELISTS, USER_LOCATION_XSRF_KEY_NAME, DAY_SECS
from rendering import clean_json, json_encode
from utils import DateTime, ErrorMessage, HIDDEN_ATTRIBUTE_NAMES, Redirect
from utils import db, get_message, html_escape, simplejson, to_unicode, users, _
from feeds.crypto import sign, verify

# TODO(shakusa) Add per-attribute comment fields


def get_suggested_nickname(user):
    """Returns the suggested Account.nickname based on a user.nickname"""
    return re.sub('@.*', '', user and user.nickname() or '')

def display_location_text(location_text):
    if not location_text:
        return ''
    else:
        return location_text
    
def display_geopt(value):
    lat = value and value.lat or ''
    lon = value and value.lon or ''
    return '%s, %s' % (lat, lon)
     
def parse_geopt(value):
    components = value.split(',')
    try:
        lat = float(components[0])
        lon = float(components[1])
    except ValueError:
        return None
    return db.GeoPt(lat, lon)

class UserLocation(utils.Handler):
    def get(self):
        self.require_logged_in_user()

        token = sign(USER_LOCATION_XSRF_KEY_NAME, self.user.user_id(), DAY_SECS)
        fields = [{'name': 'location_text',
                       'type': 'text',
                       'input': 'location text',
                       'json': display_location_text(self.account.location_text)},
                      {'name': 'location',
                       'type': 'geopt',
                       'input': 'location',
                       'json': display_geopt(self.account.location)},
                     ]                     

        self.render('templates/user_location.html',
            token=token, account=self.account, fields=fields,
            suggested_nickname=get_suggested_nickname(self.user),
            logout_url=users.create_logout_url('/'),
            instance=self.request.host.split('.')[0])

    def post(self):
        self.require_logged_in_user()

        if self.request.get('cancel'):
            raise Redirect('/')
        
        if not verify(USER_LOCATION_XSRF_KEY_NAME, self.user.user_id(),
            self.request.get('token')):
            raise ErrorMessage(403, 'Unable to submit data for %s'
                               % self.user.email())

        if not self.account.nickname:
            nickname = self.request.get('account_nickname', None)
            if not nickname:
                logging.error("Missing editor nickname")
                #i18n: Error message for request missing nickname
                raise ErrorMessage(400, 'Missing editor nickname.')
            self.account.nickname = nickname.strip()

            affiliation = self.request.get('account_affiliation', None)
            if not affiliation:
                logging.error("Missing editor affiliation")
                #i18n: Error message for request missing affiliation
                raise ErrorMessage(400, 'Missing editor affiliation.')
            self.account.affiliation = affiliation.strip()
            self.account.actions.append('edit')
            self.account.put()
            logging.info('Assigning nickname "%s" and affiliation "%s" to %s'
                         % (nickname, affiliation, self.account.email))

        logging.info('updating %s' % self.user)
        location_text = self.request.get('location_text', None)
        if location_text:
            self.account.location_text = location_text
        elif location_text == '':
            # This was explicitly set to empty.
            self.account.location_text = ''
        location = self.request.get('location', None)
        if location:
            self.account.location = parse_geopt(location)
        elif location == '':
            # This was explicitly set to empty.
            self.account.location = None
        else:
            lat = self.request.get('lat', None)
            lon = self.request.get('lon', None)
            if lat and lon:
                self.account.location = db.GeoPt(float(lat), float(lon))
        logging.error('HERE')
        self.account.put()
        self.redirect('/user_location')
       
if __name__ == '__main__':
    utils.run([('/user_location', UserLocation)], debug=True)
