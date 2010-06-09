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

"""Renders and populates a settings page for the logged in user.

Accesses the Account and Alert data structures to retrieve any information
pertaining to the logged in user that said user has control over changing.

make_frequency_plain(frequency): returns a datastore friendly version of the
    user friendly frequency text
create_choice_input(facility, frequency): creates html output as a dropdown
    box with the facilities frequency pre-selected
Settings(utils.handler): renders the page; handles GET and POST requests
"""

__author__ = 'pfritzsche@google.com (Phil Fritzsche)'

import logging
import model
import utils

from feeds.crypto import sign, verify
from utils import ErrorMessage, Redirect
from utils import db, html_escape, users, _

XSRF_KEY_NAME = 'resource-finder-settings'
DAY_SECS = 24 * 60 * 60

FREQUENCY_UF_TO_PLAIN = {
    'Never Update': '',
    'Immediate Updates': '1/min',
    'Once per Day': '1/day',
    'Once per Week': '1/week',
    'Once per Month': '1/month'
}


FREQUENCY_PLAIN_TO_UF = {
    '': 'Never Update',
    '1/min': 'Immediate Updates',
    '1/day': 'Once per Day',
    '1/week': 'Once per Week',
    '1/month': 'Once per Month'
}


def make_frequency_plain(frequency):
    """Returns datastore-friendly version of the plain text frequency updates.
    
    The format this information is stored in the datastore is not user-
    friendly. This is a convenience function to switch between them.
    
    Args:
        frequency: a human readable frequency string
    
    Returns:
        A datastore-friendly frequency string.
    """
    return FREQUENCY_UF_TO_PLAIN[frequency]
    
    
def make_frequency_readable(frequency):
    """Returns datastore-friendly version of the plain text frequency updates.
    
    The format this information is stored in the datastore is not user-
    friendly. This is a convenience function to switch between them.
    
    Args:
        frequency: a human readable frequency string
    
    Returns:
        A datastore-friendly frequency string.
    """
    return FREQUENCY_PLAIN_TO_UF[frequency]


def create_choice_box(choices, preselect = '', name = '', extra_lines=0):
    """Creates HTML output for a particular facility's frequency.
    
    Creates a dropdown box with the options available in 'FREQUENCY_CHOICES'
    above, where the current frequency for the facility is pre-selected.
    
    Args:
        choices: the choices for the dropdown box
        preselct: the choice to preselect, if any
        name: the name for the select field, if any
        extra_lines: number of lines after this box, if any
            
    Returns:
        A string containing the necessary HTML output for a dropdown box with
        the appropriate box preselected for the user.
    """
    spacing = '<br />' * extra_lines
    if name:
        output = '<select name="%s">' % html_escape(name)
    else:
        output = '<select>'
    options = []
    for i in range(len(choices)):
        if choices[i] == preselect:
            options.append('<option selected>%s</option>' % choices[i])
        else:
            options.append('<option>%s</option>' % choices[i])
    return output + '%s</select>%s' % (''.join(options), spacing)


class Settings(utils.Handler):
    """Handler for calls to /settings. Creates / displays a user settings page.
    
    Attributes:
        email: logged in user's email
        account: current user's Account object from datastore [see model.py]
        alert: current user's Alert object from datastore [see model.py]
        frequencies: dictionary of frequencies for each facility the user is
            subscribed to
    """
    
    def init(self):
        """Checks for logged-in user and gathers necessary information."""

        self.require_logged_in_user()
        self.email = self.user.email()
        self.account = db.GqlQuery('SELECT * FROM Account WHERE email = :1',
                                   self.email).get()
        if not self.account:
            #i18n: Error message for request missing facility name.
            raise ErrorMessage(404, _('Invalid or missing account e-mail.'))
        self.alert = db.GqlQuery('SELECT * FROM Alert WHERE user_email = :1',
                                 self.email).get()
        if self.alert:
            self.frequencies = []
            for i in range(len(self.alert.facility_keys)):
                #use tuples to maintain order
                self.frequencies.append((self.alert.facility_keys[i],
                                         self.alert.frequencies[i]))

    def get(self):
        """Responds to HTTP GET requests to /settings.
        
        Will populate the screen with a list of the user's subscribed 
        facilities and their respective selected frequencies."""
        
        self.init()
        fields = []
        alert_ctrl_fields = []
        
        choices = [_('Never Update'), _('Immediate Updates'),
                   _('Once per Day'), _('Once per Week'), _('Once per Month')]
        plain_choices = [make_frequency_plain(choice) for choice in choices]
        
        fields.append({
            'title': 'Default Frequency',
            'input': create_choice_box(choices, 
                make_frequency_readable(self.alert.default_frequency),
                'df', 2)
        })
        
        if self.alert.frequencies:
            fac_keys, freqs = zip(*self.frequencies)
            for i in range(len(fac_keys)):
                facility = model.Facility.get_by_key_name(fac_keys[i])
                title = facility.get_value('title')
                fields.append({
                    'title': title,
                    'input': create_choice_box(choices,
                        make_frequency_readable(freqs[i]), title)
                })
            
        token = sign(XSRF_KEY_NAME, self.user.user_id(), DAY_SECS)

        self.render('templates/settings.html',
                    token=token, user_email=self.email,
                    fields=fields, account=self.account,
                    params=self.params, logout_url=users.create_logout_url('/'),
                    instance=self.request.host.split('.')[0])

    def post(self):
        """Responds to HTTP POST requests to /settings.
        
        If the user selected cancel, redirect to main RF page. If the user
        selected save, it updates the datastore with the newly selected 
        frequencies, as selected / changed by the user."""
        
        self.init()

        if self.request.get('cancel'):
            raise Redirect('/')

        if not verify(XSRF_KEY_NAME, self.user.user_id(),
            self.request.get('token')):
            raise ErrorMessage(403, 'Unable to submit data for %s'
                               % self.user.email())

        logging.info("updating user subscriptions: %s" % self.user)
        
        #TODO(pfritzsche): better way to pull out only facilities?
        ignore = ['cc', 'facility_name', 'editable.', 'token', 'embed', 'save']
        new_frequencies = []
        facilities = self.request.arguments()
        facilities.sort()
                
        for facility in facilities:
            if facility == 'df':
                default_frequency = make_frequency_plain(
                    self.request.get('df'))
            elif facility not in ignore:
                new_frequencies.append(make_frequency_plain(
                    self.request.get(facility)))

        def update(alert, frequencies, default_frequency):
            """Helper function; updates the facility alert frequencies."""
            
            if not frequencies:
                return
            logging.info(frequencies)
            logging.info(alert.frequencies)
            for i in range(len(frequencies) - 1, -1, -1):
                if not frequencies[i]:
                    del alert.frequencies[i]
                    del alert.facility_keys[i]
                else:
                    alert.frequencies[i] = frequencies[i]
            alert.default_frequency = default_frequency
            
            db.put(alert)

        db.run_in_transaction(update, self.alert, new_frequencies,
            default_frequency)
        
        if self.params.embed:
            #i18n: Record updated successfully.
            self.write(_('Record updated.'))
        else:
            raise Redirect('/')

if __name__ == '__main__':
    utils.run([('/settings', Settings)], debug=True)
