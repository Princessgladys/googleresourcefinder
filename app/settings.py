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

import datetime
import logging
import model
import re
import urlparse
import utils
import wsgiref

from access import check_action_permitted
from feed_provider import schedule_add_record
from feeds.crypto import sign, verify
from main import USE_WHITELISTS
from rendering import clean_json, json_encode
from utils import DateTime, ErrorMessage, HIDDEN_ATTRIBUTE_NAMES, Redirect
from utils import db, get_message, html_escape, simplejson
from utils import to_unicode, users, _

XSRF_KEY_NAME = 'resource-finder-settings'
DAY_SECS = 24 * 60 * 60

def create_input(facility, frequency):
    output = '<select name="%s">' % html_escape(facility.get_value('title'))
    options = []
    choices = [_('Immediate Updates'), _('Once per Day'), _('Once per Week'),
        _('Once per Month')]
    choices_plain = ['1/min', '1/day', '1/week', '1/month']
    for i in range(len(choices)):
        if choices_plain[i] == frequency:
            options.append('<option selected>%s</option>' % choices[i])
        else:
            options.append('<option>%s</option>' % choices[i])
    return output + '%s</select>' % ''.join(options)

class Settings(utils.Handler):
    def init(self):
        """Checks for logged-in user and sets up the page, based on the user's
        settings."""

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
            self.frequencies = {}
            for i in range(len(self.alert.facility_keys)):
                self.frequencies[self.alert.facility_keys[i]] = \
                    self.alert.frequencies[i]

    def get(self):
        self.init()
        fields = []
        
        if self.alert:
            for facility_key in self.frequencies:
                facility = model.Facility.get_by_key_name(facility_key)
                fields.append({
                    'title': facility.get_value('title'),
                    'input': create_input(facility,
                                          self.frequencies[facility_key])
                })
            
        token = sign(XSRF_KEY_NAME, self.user.user_id(), DAY_SECS)

        self.render('templates/settings.html',
                    token=token, user_email=self.email,
                    fields=fields, account=self.account,
                    params=self.params, logout_url=users.create_logout_url('/'),
                    instance=self.request.host.split('.')[0])

    def post(self):
        self.init()

        if self.request.get('cancel'):
            raise Redirect('/')

        if not verify(XSRF_KEY_NAME, self.user.user_id(),
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

        logging.info("record by user: %s" % self.user)

        def update(key, facility_type, attributes, request, user, account):
            facility = db.get(key)
            minimal_facility = model.MinimalFacility.all().ancestor(
                facility).get()
            utcnow = datetime.datetime.utcnow().replace(microsecond=0)
            report = model.Report(
                facility,
                arrived=utcnow,
                source=get_source_url(request),
                author=user,
                observed=utcnow)
            change_metadata = ChangeMetadata(
                utcnow, user, account.nickname, account.affiliation)
            has_changes = False
            changed_attributes_dict = {}

            for name in facility_type.attribute_names:
                attribute = attributes[name]
                # To change an attribute, it has to have been marked editable
                # at the time the page was rendered, the new value has to be
                # different than the one in the facility at the time the page
                # rendered, and the user has to have permission to edit it now.
                if (is_editable(request, attribute) and
                    has_changed(facility, request, attribute)):
                    if not can_edit(account, attribute):
                        raise ErrorMessage(
                            403, _(
                            #i18n: Error message for lacking edit permissions
                            '%(user)s does not have permission to edit %(a)s')
                            % {'user': user.email(),
                               'a': get_message('attribute_name',
                                                attribute.key().name())})
                    has_changes = True
                    apply_change(facility, minimal_facility, report,
                                 facility_type, request, attribute,
                                 change_metadata)
                    changed_attributes_dict[name] = attribute

            if has_changes:
                # Schedule a task to add a feed record.
                # We can't really do this inside this transaction, since
                # feed records are not part of the entity group.
                # Transactional tasks is the closest we can get.
                schedule_add_record(self.request, user,
                    facility, changed_attributes_dict, utcnow)
                db.put([report, facility, minimal_facility])

        db.run_in_transaction(update, self.facility.key(), self.facility_type,
                              self.attributes, self.request,
                              self.user, self.account)
        if self.params.embed:
            #i18n: Record updated successfully.
            self.write(_('Record updated.'))
        else:
            raise Redirect('/')

if __name__ == '__main__':
    utils.run([('/settings', Settings)], debug=True)
