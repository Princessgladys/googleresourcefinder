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

get_frequency(alert, facility): returns a text frequency as a timedelta
is_time_to_send(alert, frequency): returns if enough time has passed to require
    an update for a particular facility
form_body(values): forms the e-mail body for an update e-mail
EmailData: used as a structure to store useful information for an update
MailUpdateSystem(utils.Handler): handler class to send e-mail updates
"""

__author__ = 'pfritzsche@google.com (Phil Fritzsche)'

import datetime
import email
import logging
import time

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.api import users

from google.appengine.ext import db
from google.appengine.ext import webapp

import django.utils.translation

import model
import utils

from utils import _

DAYS_SECS = 60 * 60 * 24
ADMIN_TIMEOUT_ALERT_TIME_SECS = 60


FREQUENCY_TO_DATETIME = {
    'immediate': datetime.timedelta(0),
    '1/day': datetime.timedelta(1),
    '1/week': datetime.timedelta(7),
    '1/month': datetime.timedelta(30)
}


def get_frequency_as_time_delta(alert, frequency):
    """Given a text frequency, converts it to a timedelta."""
    if frequency == 'default':
        return FREQUENCY_TO_DATETIME[alert.default_frequency]
    return FREQUENCY_TO_DATETIME[frequency]


def is_time_to_send(alert, frequency):
    """Given an alert and a facility, determines if it is time to send an
    e-mail to the user about that particular facility. Returns True/False."""
    delta = datetime.datetime.now() - alert.last_sent
    return frequency <= delta


def form_body(values):
    """Forms the body text for an e-mail. """
    body = ''
    for facility_name in values.keys():
        facility_title = values[facility_name].keys()[0]
        updates = values[facility_name][facility_title]
        body += facility_title.upper() + '\n'
        for attr, update in updates.iteritems():
            body += attr + ": " + str(update) + '\n'
        body += '\n'
    return body


class EmailData():
    """Helper class; used as a structure to store useful information for an
    e-mail update.
    
    Attributes:
        locale: the locale to send this e-mail in
        to: the user to send the e-mail to
        updated_params: the updated facilities and attributes to be used for
            the update e-mail
    """
    def __init__(self, locale, to, updated_params):
        self.locale = locale
        self.to = to
        self.updated_params = updated_params


class MailUpdateSystem(utils.Handler):
    """Handler class; on POST request, sends out e-mail updates to users
    subscribed to various facilities. Can send alerts to users subscribed to
    a specific facility, or perform a general purpose update to all users if no
    particular facility is supplied.
    
    Functions:
        init(): initializes necessary variables
        get(): responds to HTTP GET requests; does nothing
        post(): responds to HTTP POST requests; responds to the HTTP request
        send_immediate_updates(): sends an e-mail to all users subscribed to a
            particular facility status == 'immediate'
        send_email_to_all_users(): gathers a list of users and their locales
            and sends them an e-mail as appropriate
        fetch_updates(alert, facility, facilities): gathers a list of updates 
            for the given facility and the given alert
        send_admin_timeout_email(time): sends an alert to admins about the
            length of time this script to run
    """
    def init(self):
        """Initializes appropriate variables for later use."""
        self.time_start = time.time()
        self.facility_name = self.params.facility_name or ''
    
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
            num_alerts = self.send_immediate_updates()
        else:
            # performed during daily email subscription routine; sends emails
            # to all users subscribed to any facility, if there are any new
            # updates and their frequency requires an update
            num_alerts = self.send_email_to_all_users()
            
        time_delta = time.time() - self.time_start
        if (time_delta >= ADMIN_TIMEOUT_ALERT_TIME_SECS and
            memcache.get('last_alert_email_sent') is None):
            send_admin_timeout_email(time_delta, num_alerts)
            memcache.set('last_alert_email_sent', 'sent', time=DAYS_SECS)

    def send_immediate_updates(self):
        """Gathers a list of immediate update subscribers for the given
        facility and sends updates to them.
        
        Returns the number of alerts processed."""
        num_alerts = 0
        alerts = model.Alert.all().filter(
            'facility_names =', self.facility_name)
        if not alerts:
            return 0
        
        facility = model.Facility.get_by_key_name(self.facility_name)
        updated_vals = {}
        for arg in self.request.arguments():
            if arg == 'facility_name':
                continue
            updated_vals[arg] = facility.get_value(arg)
                
        body = form_body({self.facility_name: { 
            facility.get_value('title') : updated_vals}})
        
        for alert in alerts:
            freqs = dict(zip(alert.facility_names, alert.frequencies))
            if freqs[self.facility_name] == 'immediate':
                num_alerts += 1
                account = db.GqlQuery('SELECT * FROM Account WHERE email = :1',
                                      alert.user_email).get()
                self.send_email(account.locale, alert.user_email, body)
        
        return num_alerts

    def send_email_to_all_users(self):
        """Gathers a list of users and their locales and sends them updates.
        
        Accesses the database to create a dictionary of all users, the
        facilities they are subscribed to, and the users' locales. It then
        renders the body of an update e-mail and sends it to each user.
        
        Returns:
            The number of alerts processed.
        """
        num_alerts = 0
        for alert in model.Alert.all(): # compile list of facilities per user
            freqs = dict(zip(alert.facility_names, alert.frequencies))
            updated = False
            facilities = {}
            for i in range(len(alert.facility_names)):
                freq = get_frequency_as_time_delta(alert,
                                                   alert.frequencies[i])
                if not is_time_to_send(alert, freq):
                    continue
                fac = model.Facility.get_by_key_name(alert.facility_names[i])
                values = self.fetch_updates(alert, fac, freq)
                if values:
                    updated = True
                    facilities[fac.key().name()] = {fac.get_value('title'):
                        values}
            
            if updated:
                account = db.GqlQuery('SELECT * FROM Account WHERE email = :1',
                      alert.user_email).get()
                self.send_email(account.locale, alert.user_email,
                    form_body(facilities))
                alert.last_sent = datetime.datetime.now()
                db.put(alert)
                num_alerts += 1

        return num_alerts
    
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
            if not value and value != 0:
                continue
            last_facility_update = facility.get_observed(attr)
            if last_facility_update < alert.last_sent:
                continue
            next_update_time = alert.last_sent + frequency
            if (datetime.datetime.now() > next_update_time and
                last_facility_update > alert.last_sent):
                updated_attrs[attr] = value
        
        return updated_attrs
    
    def send_email(self, locale, to, body):
        """Sends a single e-mail update.
        
        Args:
            locale: the locale whose language to use for the email
            to: the user to send the update to
            body: the text to use as the body of the e-mail
        """
        
        # Will not alter the active locale for the website, given that it is
        # running in a separate thread, disconnected from any user interaction.
        django.utils.translation.activate(locale)
        
        message = mail.EmailMessage()
        message.sender = 'updates@resource-finder.appspotmail.com'
        message.to = to
        message.subject = utils.to_unicode(
            _('Resource Finder Facility Updates'))
        message.body = body
        
        message.send()
    
    def send_admin_timeout_email(self, time, num_alerts):
        """Sends an alert to admins about this file's time to run, if it has
        taken too long.
        
        Args:
            time: amount of time taken to run the script
            num_alerts: the number of alerts processed during this time
        """
        message = mail.EmailMessage()
        message.sender = 'alerts@resource-finder.appspotmail.com'
        message.to = 'resourcefinder-alerts@google.com'
        message.subject = '[ALERT] Resource Finder Cron Job is Running Slowly'
        message.body = ('A recent e-mail subscription cron job ran with ' +
            'total time: %s. During this time, %d alerts were sent.'
            % (str(time), num_alerts))

        message.send()

if __name__ == '__main__':
    utils.run([('/send_mail_updates', MailUpdateSystem)], debug=True)
