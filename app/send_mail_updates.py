# Copyright 2009-2010 by Google Inc.
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

"""Sends facility updates to users per their subscriptions.

Accesses the Account data structure to retrieve facility updates for each user,
then sends out information to each user per their subscription settings.

send_updates(): main function; gathers a list of users and sends updates
get_users_to_email(): gathers a list of users and their locales
send_update(email, locale, facilities): sends a specific e-mail to a user
fetch_updates(email, facilities): gathers a list of updates for each user
send_speed_alert_email(time): sends an alert to admins about file's time to run
"""

__author__ = 'pfritzsche@google.com'

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.api import users

from google.appengine.ext import db
from google.appengine.ext import webapp

from utils import _

import django.utils.translation

import datetime
import email
import logging
import model
import utils

def send_updates():
    """Main function of the script; sends updates to all users.

    Gathers a list of all users, then iterates through each user to send them
    an e-mail with the appropriate information. If this process takes more than
    two minutes, e-mail the administrators of the code to let them know the cron
    job may need more time than anticipated.
    """
    time_start = datetime.datetime.now()
    
    users = get_users_to_email()
    if not users:
        return
    
    for email, values in users.iteritems():
        send_update(email, values)
        
    time_delta = datetime.datetime.now().minute - time_start.minute
    if abs(time_delta) >= 2 and memcache.get('last_alert_email_sent') is None:
        send_speed_alert_email(time_delta)
        memcache.set('last_alert_email_sent', 'sent', time=86400)

def get_users_to_email():
    """Gathers a list of users and their locales.
    
    Accesses the database to create a dictionary of all users, the facilities
    they are subscribed to, and the users' locales.
    
    Returns:
        A dictionary mapping the users e-mails to the facilities they are
        subscribed to as well as the locales of each user. Example:
        
        {'pfritzsche@google.com' : {
            'locale' : 'en',
            'facility_foo' : {'attr1' : 'new_value'},
            'facility_bar' : {'attr2' : 'new_value'} },
         'shakusa@google.com' : {
            'locale' : 'en',
            'facility_zoo' : {'attr1' : 'new_value', 'attr2' : 'new_value'} },
        }
    """ 
    users = {}
    
    for alert in model.Alert.all(): # compile list of facility names per user
        for i in range(len(alert.facility_keys)):
            fac = model.db.Model.get(alert.facility_keys[i])
            freq = alert.frequencies[i]
            values = fetch_updates(alert, fac, freq)
            if values:
                if alert.user_email not in users:
                    users[alert.user_email] = {}
                users[alert.user_email]['locale'] = alert.locale
                users[alert.user_email][fac.key().name()] = values

    return users
    
def send_update(email, values):
    """Sends an update to a specific user. """
    
    # Will not alter the active locale for the website, given that it is
    # running in a separate thread, disconnected from any user interaction.
    django.utils.translation.activate(values['locale'])
    
    body = ''
    for key in values.keys():
        if key == 'locale':
            continue
            
        # TODO(pfritzsche): work with Jeromy to improve e-mail UI
        body += key.upper() + '\n'
        for attr, value in values[key].iteritems():
            body += attr + ": " + str(value) + '\n'
        body += '\n'
        
    message = mail.EmailMessage()
    message.sender = 'updates@resource-finder.appspotmail.com'
    message.to = email
    # TODO(pfritzsche): make sure unicode chars render properly in the e-mail
    message.subject = utils.to_unicode(_('Resource Finder Facility Updatés'))
    message.body = body

    message.send()    
    
def fetch_updates(alert, facility, frequency):
    """Finds updated attributes of the facility for a given alert.
    
    Determines if a facility has been updated after the users last
    update e-mail was sent. If it has been, it creates a dictionary of
    the specific facility attributes that have been updated.
    
    Returns:
        Dictionary containing a list of any updated attributes. Example:
        
        { 'attr1' : 'new_value', 'attr2' : 'new_value' , ... }
    """ 
    updated_attrs = {}
    facility_type = model.FacilityType.get_by_key_name(facility.type)
    
    for attr in facility_type.attribute_names:
        value = facility.get_value(attr)
        if not value and value != 0: continue
        
        last_facility_update = facility.get_observed(attr)
        
        # if last update was before the user was last updated, move to next attr
        if last_facility_update < alert.last_sent:
            continue
            
        # convert frequency to timedelta
        if frequency == '1/min':
            next_update_time = alert.last_sent
        elif frequency == '1/day':
            next_update_time = alert.last_sent + datetime.timedelta(1)
        elif frequency == '1/week':
            next_update_time = alert.last_sent + datetime.timedelta(7)
        else:
            next_update_time = alert.last_sent + datetime.timedelta(30)
        
        # check and see if frequency period is up    
        # if so, add value to list of values to send
        if (datetime.datetime.now() > next_update_time and
            last_facility_update > alert.last_sent):
            updated_attrs[attr] = value
        
    if updated_attrs:
        alert.last_sent = datetime.datetime.now()
        db.put(alert)

    return updated_attrs
    
def send_speed_alert_email(time):
    """Sends an alert to admins about file's time to run.
    
    If the file is taking too long to run, alerts the admins.
    
    Args:
        time: amount of time taken to run the script.
    """
    message = mail.EmailMessage()
    message.sender = 'alerts@resource-finder.appspotmail.com'
    message.to = ['pfritzsche@google.com',
                  'shakusa@google.com',
                  'kpy@google.com']
    message.subject = '[ALERT] Resource Finder Cron Job is Running Slowly'
    message.body = ('A recent e-mail subscription cron job ran with total ' +
        'time: %s' % str(time))

    message.send() 

if __name__ == '__main__':
    send_updates()
