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

"""Handler for the delta feed, which accepts external edits and publishes
both internal and external edits."""

import logging

from google.appengine.ext import db

import cache
import config
from feedlib import crypto, errors, report_feeds, xml_utils
import model
import pubsub
import row_utils
from utils import DateTime, Handler, Struct, run


def update_subject(subject, observed, account, source_url, values, comments={},
                   arrived=None):
    """Applies a set of changes to a single subject with a single author,
    producing one new Report and updating one Subject and one MinimalSubject.
    'account' can be any object with 'user', 'nickname', and 'affiliation'
    attributes.  'values' and 'comments' should both be dictionaries with
    attribute names as their keys."""

    # SubjectType and Attribute entities are in separate entity groups from
    # the Subject, so we have to obtain them outside of the transaction.
    subject_type = cache.SUBJECT_TYPES[subject.subdomain][subject.type]
    minimal_attribute_names = subject_type.minimal_attribute_names
    editable_attributes = []
    for name in subject_type.attribute_names:
        if not cache.ATTRIBUTES[name].edit_action:
            # Don't allow feeds to edit attributes that have an edit_action.
            editable_attributes.append(name)

    # We'll use these to fill in the metadata on the subject. 
    user = account.user
    nickname = account.nickname
    affiliation = account.affiliation

    # The real work happens here.
    def work(key):
        # We want to transactionally update the Report, Subject, and
        # MinimalSubject, so reload the Subject inside the transaction.
        subject = db.get(key)
        minimal_subject = model.MinimalSubject.get_by_subject(subject)

        # Create an empty Report.
        report = model.Report(
            subject,
            observed=observed,
            author=user,
            source=source_url,
            arrived=arrived or DateTime.utcnow())

        # Fill in the new values on the Report and update the Subject.
        subject_changed = False
        for name in values:
            if name in editable_attributes:
                report.set_attribute(name, values[name], comments.get(name))
                last_observed = subject.get_observed(name)
                # Only update the Subject if the incoming value is newer.
                if last_observed is None or last_observed < observed:
                    subject_changed = True
                    subject.set_attribute(
                        name, values[name], observed, user, nickname,
                        affiliation, comments.get(name))
                    if name in minimal_attribute_names:
                        minimal_subject.set_attribute(name, values[name])

        # Store the new Report.
        db.put(report)

        # If the Subject has been modified, store it and flush the cache.
        if subject_changed:
            db.put([subject, minimal_subject])
            cache.MINIMAL_SUBJECTS[subject.subdomain].flush()
            cache.JSON[subject.subdomain].flush()

    db.run_in_transaction(work, subject.key())


class Feed(Handler):
    def get(self):
        """Emits entries in the delta feed; also handles subscription checks."""
        if not self.subdomain:
            raise errors.ErrorMessage(400, 'No subdomain specified.')

        if self.request.get('hub.mode') in ['subscribe', 'unsubscribe']:
            # Handle a subscription verification request.  Reference:
            # pubsubhubbub.googlecode.com/svn/trunk/pubsubhubbub-core-0.3.html
            topic = self.request.get('hub.topic')
            signature = self.request.get('hub.verify_token')
            if not crypto.verify('hub_verify', topic, signature):
                # Section 6.2.1 of the PSHB spec says to return 404.
                raise errors.ErrorMessage(404, 'Invalid signature.')

            # The request came from us.  Confirm it.
            if self.request.get('hub.mode') == 'subscribe':
                pubsub.PshbSubscription.subscribe(self.subdomain, topic)
                logging.info('Added subscription: ' + topic)
            else:
                pubsub.PshbSubscription.unsubscribe(self.subdomain, topic)
                logging.info('Removed subscription: ' + topic)
            self.response.out.write(self.request.get('hub.challenge'))

        else:
            report_feeds.handle_feed_get(
                self.request, self.response, self.subdomain + '/delta',
                hub=config.get('hub_url'))

    def post(self):
        """Feed update notification from hub."""
        if not self.subdomain:
            raise errors.ErrorMessage(404, 'Not found')

        # Check the signature on the request, to verify that this came from
        # a hub that we subscribed to (and gave our hub_secret to).
        hmac = crypto.sha1_hmac(crypto.get_key('hub_secret'), self.request.body)
        if self.request.headers.get('X-Hub-Signature', '') != 'sha1=' + hmac:
            # Section 7.4 of the PSHB spec says to return 200 (oddly).
            raise errors.ErrorMessage(200, 'Invalid signature.')

        # Store the incoming reports on the 'delta' feed.
        entries = report_feeds.handle_feed_post(
            self.request, self.response, self.subdomain + '/delta',
            hub=config.get('hub_url'))

        # Store each report as a report entity and apply its changes.
        for entry in entries:
            # TODO(kpy): Handle identity for incoming edits better.
            account = Struct(
                user=None, affiliation='', nickname=entry.author_uri)
            row = xml_utils.parse(entry.content)
            values, comments = row_utils.parse_from_elements(row)
            subject = model.Subject.get(self.subdomain, entry.subject_id)
            if subject:
                try:
                    update_subject(subject, entry.observed, account,
                                   entry.external_feed_id, values, comments,
                                   entry.arrived)
                    logging.info('Edit applied: %s -> %s' %
                                 (entry.external_entry_id, entry.subject_id))
                except:
                    logging.exception('Edit failed: ' + entry.external_entry_id)
            else:
                logging.info('Entry %s had unknown subject %s' %
                             (entry.external_entry_id, entry.subject_id))


class Entry(Handler):
    def get(self):
        report_feeds.handle_entry_get(
            self.request, self.response, self.subdomain + '/delta')


if __name__ == '__main__':
    run([('/feeds/delta', Feed),
         ('/feeds/delta/\d+', Entry)], debug=True)
