# Copyright 2009-2010 by Phil Fritzsche
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

from google.appengine.api import mail
from google.appengine.api import users

from google.appengine.ext import db
from google.appengine.ext import webapp

from utils import _

import datetime
import email
import logging
import model
import utils

def send_updates():
	""" Sends out updates to users based on what facilities they are
		subscribed to and which ones have been updated.
	"""
	(users, locale) = get_users_to_email()
	if not users: return
	
	for email, facilities in users.iteritems():
		send_update(email, facilities, locale[email])
	
def get_users_to_email():
	""" Gathers a list of the facilities that users are subscribed to
		and checks if it is time to e-mail them yet.
	""" 
	users = {}
	locale = {}
	
	for alert in model.Alert.all(): # compile list of facility names per user
		fac = model.db.Model.get(alert.facility_id)
		(updated, values) = has_update(alert, fac)
		if updated:
			locale[alert.user_email] = alert.locale
			if alert.user_email not in users.keys():
				users[alert.user_email] = {}
			if fac.get_value('title') not in users[alert.user_email].keys():
				users[alert.user_email][fac.get_value('title')] = values
			else:
				# make better way to handle facilities with same name
				users[alert.user_email][fac.get_value('title')+' (dup)'] = values
		else:
			continue

	return users, locale
	
def send_update(email, facilities, locale):
	""" Sends an update to a specific user. """
	django.utils.translation.activate(locale)
	
	body = ''
	for key in facilities.keys():
		# will work with jeromy to fix UI; for testing purposes:
		body += key.upper() + '\n'
		for attr, value in facilities[key].iteritems():
			body += attr + ": " + str(value) + '\n'
		body += '\n'
		
	message = mail.EmailMessage()
	message.sender = 'updates@resource-finder.appspotmail.com'
	message.to = email
	message.subject = _('Resource Finder Facility Updates')
	message.body = body

	message.send()	
	
def has_update(alert, facility):
	""" Determines if a facility has been updated after the users last
		update e-mail was sent and returns which values have been updated.
	""" 
	updated_attrs = {}
	updated = False
	facility_type = model.FacilityType.get_by_key_name(facility.type)
	
	for attr in facility_type.attribute_names:
		value = facility.get_value(attr)
		if not value: continue
		
		last_facility_update = facility.get_observed(attr)
		
		# if last update was before the user was last updated, move to next attr
		if last_facility_update < alert.last_sent: continue
			
		# convert frequency to timedelta
		if alert.frequency == '1/min':
			next_update_time = alert.last_sent
		elif alert.frequency == '1/day':
			next_update_time = alert.last_sent + datetime.timedelta(1)
		elif alert.frequency == '1/week':
			next_update_time = alert.last_sent + datetime.timedelta(7)
		else:
			next_update_time = alert.last_sent + datetime.timedelta(30)
		
		# check and see if frequency period is up	
		# if so, add value to list of values to send
		if datetime.datetime.now() > next_update_time \
				and last_facility_update > alert.last_sent:
			updated_attrs[attr] = value
			updated = True
		
	if updated:
		alert.last_sent = datetime.datetime.now()
		db.put(alert)

	return updated, updated_attrs

if __name__ == '__main__':
	send_updates()
