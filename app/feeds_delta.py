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

from feedlib import errors, report_feeds, xml_utils
from google.appengine.ext import db
from utils import DateTime, Handler, Struct, run
import cache
import model
import row_utils


def update_subject(subdomain, subject_name, observed, account, source_url,
                   values, comments={}, arrived=None):
    """Applies a set of changes to a single subject with a single author,
    producing one new Report and updating one Subject and one MinimalSubject.
    'account' can be any object with 'user', 'nickname', and 'affiliation'
    attributes.  'values' and 'comments' should both be dictionaries with
    attribute names as their keys."""

    # The SubjectType is in a different entity group, so we have to obtain
    # it outside of the transaction to get at the minimal_attribute_names.
    subject = model.Subject.get(subdomain, subject_name)
    subject_type = model.SubjectType.get(subdomain, subject.type)
    minimal_attribute_names = subject_type.minimal_attribute_names

    # We'll use these to fill in the metadata on the subject. 
    user = account.get('user')
    nickname = account.get('nickname')
    affiliation = account.get('affiliation')

    # The real work happens here.
    def work():
        # We want to transactionally update the Report, Subject, and
        # MinimalSubject, so reload the Subject inside the transaction.
        subject = model.Subject.get(subdomain, subject_name)
        minimal_subject = model.MinimalSubject.get_by_subject(subject)

        # Create an empty Report.
        report = model.Report(
            subject,
            observed=observed,
            author=account.user,
            source=source_url,
            arrived=arrived or DateTime.utcnow())

        # Fill in the new values on the Report and update the Subject.
        subject_changed = False
        for name in values:
            report.set_attribute(name, values[name], comments.get(name))
            last_observed = subject.get_observed(name)
            # Only update the Subject if the incoming value is newer.
            if last_observed is None or last_observed < observed:
                subject_changed = True
                subject.set_attribute(name, values[name], observed, user,
                                      nickname, affiliation, comments.get(name))
                if name in minimal_attribute_names:
                    minimal_subject.set_attribute(name, values[name])

        # Store the new Report.
        db.put(report)

        # If the Subject has been modified, store it and flush the cache.
        if subject_changed:
            db.put([subject, minimal_subject])
            cache.MINIMAL_SUBJECTS[subdomain].flush()
            cache.JSON[subdomain].flush()

    db.run_in_transaction(work)


class Feed(Handler):
    def get(self):
        """Emits entries in the delta feed; also handles subscription checks."""
        if not self.subdomain:
            raise errors.ErrorMessage(404, 'Not found')
        challenge = self.request.get('hub.challenge')
        if challenge:
            # A hub is verifying a subscription request.  Confirm it.
            # TODO(guido): Check other hub parameters.
            # Reference:
            # pubsubhubbub.googlecode.com/svn/trunk/pubsubhubbub-core-0.3.html
            self.response.out.write(challenge)

        else:
            report_feeds.handle_feed_get(
                self.request, self.response, self.subdomain + '/delta')

    def post(self):
        """Feed update notification from hub."""
        if not self.subdomain:
            raise errors.ErrorMessage(404, 'Not found')

        # TODO(kpy): Remove this when it's been fully tested.
        logging.info("POST headers:\n%s", self.request.headers)
        logging.info("POST body:\n%s", self.request.body)

        # TODO(guido): Check hub signature.

        # TODO(shakusa) Implement an authorization token scheme
        # This involves changes to the data model so that we can store
        # the token along with the (maybe different) email associated with
        # each record

        # TODO(shakusa) Do we need to enforce read-only fields
        # subject name (id), healthc_id, subject title ?

        # Store the incoming reports on the 'delta' feed.
        entries = report_feeds.handle_feed_post(
            self.request, self.response, self.subdomain + '/delta')

        # Store each report as a report entity and apply its changes.
        for entry in entries:
            account = Struct(user=None, nickname=entry.author_uri)
            row = xml_utils.parse(entry.content)
            values, comments = row_utils.parse_from_elements(row)
            update_subject(self.subdomain, entry.subject_id, entry.observed,
                           account, entry.external_feed_id, values, comments)


class Entry(Handler):
    def get(self):
        report_feeds.handle_entry_get(
            self.request, self.response, self.subdomain + '/delta')


if __name__ == '__main__':
    run([('/feeds/delta', Feed),
         ('/feeds/delta/\d+', Entry)], debug=True)
