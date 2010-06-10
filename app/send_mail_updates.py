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

get_frequency(alert, facility): returns frequency for a particular facility
MailUpdateSystem(utils.Handler): handler class to send e-mail updates
"""

__author__ = 'pfritzsche@google.com (Phil Fritzsche)'

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

DAYS_SECS = 60 * 60 * 24
ADMIN_TIMEOUT_ALERT_TIME = 2

FREQUENCY_CONVERSTION = {
    'immediate': datetime.timedelta(0),
    '1/day': datetime.timedelta(1),
    '1/week': datetime.timedelta(7),
    '1/month': datetime.timedelta(30)
}

def get_frequency(alert, facility):
    """Given an alert and a facility, returns the frequency of subscription
    for that alert and facility."""
    for i in range(len(alert.frequencies)):
        if alert.facility_names[i] == facility:
            return alert.frequencies[i]
            
def is_time_to_send(alert, frequency):
    delta = datetime.datetime.now() - alert.last_sent
    
    if frequency == 'default':
        f_delta = FREQUENCY_CONVERSTION[alert.default_frequency]
    else:
        f_delta = FREQUENCY_CONVERSTION[frequency]
        
    return f_delta < delta

class MailUpdateSystem(utils.Handler):
    """Handler class; on POST request, sends out e-mail updates to users
    subscribed to various facilities. Can send alerts to users subscribed to
    a specific facility, or perform a general purpose update to all users if no
    particular facility is supplied.
    
    Functions:
        init(): initializes necessary variables
        get(): responds to HTTP GET requests; does nothing
        post(): responds to HTTP POST requests; determines how to respond
            properly
        send_immediate_updates(): gathers a list of immediate update
            subscribers for the given facility and sends updates
        send_immediate_email(email, locale, value): sends e-mail for one
            facility; assumes it is an immediate update
        send_non_immediate_updates(): gathers a list of all users and sends out
            e-mails accordingly, pending user subscription frequency
        get_users_to_email(): gathers a list of users and their locales
        send_list_updates(email, locale, facilities): sends a specific e-mail
            to a user, for all subscribed facilities as necessary
        fetch_updates(email, facilities): gathers a list of updates for each
            user
        send_admin_timeout_email(time): sends an alert to admins about the
            length of time this script to run
    """
    def init(self):
        """Initializes appropriate variables for later use."""
        self.ignore_args = ['facility_name']
        self.time_start = datetime.datetime.now()
        self.facility_name = self.request.get('facility_name') or ''
        if self.facility_name:
            self.facility = model.Facility.get_by_key_name(self.facility_name)
            self.facility_title = self.facility.get_value('title')
            
            self.updated_vals = []
            for arg in self.request.arguments():
                if arg == 'facility_name':
                    continue
                self.updated_vals.append((arg, self.facility.get_value(arg)))
    
    def get(self):
        """Default method; do nothing."""
        pass
    
    def post(self):
        """Handles HTTP POST requests.
        
        Determines if it is responding to an update request for a single 
        facility or if it is sending out an all purpose e-mail update to
        all users whose subscriptions require updating at this time. Also
        performs a check to see how long this script runs; if it takes too
        long, it alerts the administrators to the problem.
        """
        self.init()
        
        if self.facility_name:
            # performed when a facility is updated; sends emails to all users
            # subscribed to that facility
            self.send_immediate_updates()
        else:
            # performed during daily email subscription routine; sends emails
            # to all users subscribed to any facility, if there are any new
            # updates and their frequency requires an update
            self.send_non_immediate_updates()
            
        time_delta = datetime.datetime.now().minute - self.time_start.minute
        if (abs(time_delta) >= ADMIN_TIMEOUT_ALERT_TIME and
            memcache.get('last_alert_email_sent') is None):
            send_admin_timeout_email(time_delta)
            memcache.set('last_alert_email_sent', 'sent', time=DAYS_SECS)
            
    def send_immediate_updates(self):
        """Gathers a list of immediate update subscribers for the given
        facility and sends updates to them."""
        alerts = model.Alert.all().filter(
            'facility_names =', self.facility_name)
        if not alerts:
            return
        for alert in alerts:
            if get_frequency(alert, self.facility_name) == 'immediate':
                account = db.GqlQuery('SELECT * FROM Account WHERE email = :1',
                                      alert.user_email).get()
                locale = account.locale
                self.send_immediate_email(alert.user_email, locale)
            
    def send_immediate_email(self, email, locale):
        """Sends an update to a specific user for one facility. """
        
        # Will not alter the active locale for the website, given that it is
        # running in a separate thread, disconnected from any user interaction.
        django.utils.translation.activate(locale)
        
        body = self.facility.get_value('title').upper() + '\n' # facility_name
        # TODO(pfritzsche): work with Jeromy to improve e-mail UI
        for attr, value in self.updated_vals:
            body += attr + ": " + str(value) + '\n'

        message = mail.EmailMessage()
        message.sender = 'updates@resource-finder.appspotmail.com'
        message.to = email
        # TODO(pfritzsche): make sure unicode chars render properly in the e-mail
        message.subject = utils.to_unicode(_('Resource Finder Facility Updates'))
        message.body = body

        message.send()
        
    def send_non_immediate_updates(self):
        """Gathers a list of all users, then iterates through each user to send them
        an e-mail with the appropriate information. If this process takes more than
        two minutes, e-mail the administrators of the code to let them know the cron
        job may need more time than anticipated.
        """
        users = self.get_users_to_email()
        if not users:
            return
        
        for email, values in users.iteritems():
            self.send_list_updates(email, values)

    def get_users_to_email(self):
        """Gathers a list of users and their locales.
        
        Accesses the database to create a dictionary of all users, the
        facilities they are subscribed to, and the users' locales.
        
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
        updated = False
        for alert in model.Alert.all(): # compile list of facilities per user
            account = db.GqlQuery('SELECT * FROM Account WHERE email = :1',
                                  alert.user_email).get()
            for i in range(len(alert.facility_names)):
                if not is_time_to_send(alert,
                    get_frequency(alert, alert.facility_names[i])):
                    continue
                fac = model.Facility.get_by_key_name(alert.facility_names[i])
                freq = alert.frequencies[i]
                values = self.fetch_updates(alert, fac, freq)
                if values:
                    updated = True
                    if alert.user_email not in users:
                        users[alert.user_email] = {}
                    users[alert.user_email]['locale'] = account.locale
                    users[alert.user_email][fac.key().name()] = values
            if updated:
                alert.last_sent = datetime.datetime.now()
                db.put(alert)
                updated = False

        return users
        
    def send_list_updates(self, email, values):
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
        message.subject = utils.to_unicode(_('Resource Finder Facility Updates'))
        message.body = body

        message.send()
        
    def fetch_updates(self, alert, facility, frequency):
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
            if frequency == 'immediate':
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

        return updated_attrs
        
    def send_admin_timeout_email(self, time):
        """Sends an alert to admins about file's time to run.
        
        If the file is taking too long to run, alerts the admins.
        
        Args:
            time: amount of time taken to run the script.
        """
        message = mail.EmailMessage()
        message.sender = 'alerts@resource-finder.appspotmail.com'
        message.to = 'resourcefinder-alerts@google.com'
        message.subject = '[ALERT] Resource Finder Cron Job is Running Slowly'
        message.body = ('A recent e-mail subscription cron job ran with ' +
            'total time: %s' % str(time))

        message.send() 

if __name__ == '__main__':
    utils.run([('/send_mail_updates', MailUpdateSystem)], debug=True)
