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

"""Handler for feed posting requests."""

import logging

from edxl_have import Hospital
from feeds.report_feeds import handle_feed_post
from model import Report
from utils import Handler, run


class Incoming(Handler):

    def get(self, token=None):
        """Subscription verification from hub."""

        # TODO(guido): Check other hub parameters.

        # Reference:
        # pubsubhubbub.googlecode.com/svn/trunk/pubsubhubbub-core-0.3.html
        challenge = self.request.GET['hub.challenge']
        self.response.out.write(challenge)

    def post(self, token):
        """Feed update notification from hub."""

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
        reports = handle_feed_post(self.request, self.response, 'delta')

        for report in reports:
            # TODO: Now parse these records and apply the edits to Report,
            # Subject, and MinimalSubject.
            pass


if __name__ == '__main__':
    run([('/incoming/([^/]+)', Incoming)], debug=True)
