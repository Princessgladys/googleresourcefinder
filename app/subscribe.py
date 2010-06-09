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

Settings(utils.handler): renders the page; handles GET and POST requests
"""

__author__ = 'pfritzsche@google.com (Phil Fritzsche)'

import logging
import model

from utils import Handler
from utils import db, run

class Subscribe(Handler):
    """Handler for /subscribe. Adds facility to user subscription list.
    
    Attributes:
        email: logged in user's email
        account: current user's Account object from datastore [see model.py]
        alert: current user's Alert object from datastore [see model.py]
        frequencies: dictionary of frequencies for each facility the user is
            subscribed to
            
    Functions:
        get(): responds to HTTP GET requests; do nothing
        post(): responds to HTTP POST requests; add facility to subscription
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
                #TODO(pfritzsche): better way to get titles?
                f = model.Facility.get_by_key_name(self.alert.facility_keys[i])
                #use tuples to maintain order
                self.frequencies.append((f.get_value('title'),
                                         self.alert.facility_keys[i],
                                         self.alert.frequencies[i]))

    def get(self):
        """Responds to HTTP GET requests to /subscribe."""
        pass

    def post(self):
        """Responds to HTTP POST requests to /subscribe."""
        self.init()

        def update(request, alert, frequencies):
            """Helper function; updates the facility alert list."""

            if frequencies:
                titles, keys, freqs = zip(*frequencies)
            
            if frequencies and request.get('facility') in keys:
                    # remove facility from list
                    keys = list(keys)
                    freqs = list(freqs)
                    index = keys.index(request.get('facility'))
                    del keys[index]
                    del freqs[index]
                    alert.facility_keys = keys
                    alert.frequencies = freqs
            else:
                # add facility to list
                frequencies.append((request.get('title'),
                                    request.get('facility'),
                                    alert.default_frequency))
                frequencies.sort()
                new_titles, new_keys, new_frequencies = zip(*frequencies)
                alert.facility_keys = list(new_keys)
                alert.frequencies = list(new_frequencies)
            
            db.put(alert)

        db.run_in_transaction(update, self.request, self.alert,
            self.frequencies)

if __name__ == '__main__':
    run([('/subscribe', Subscribe)], debug=True)
