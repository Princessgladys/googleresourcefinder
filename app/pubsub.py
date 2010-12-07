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

"""A simple administration page for adding or removing PSHB subscriptions."""

import logging

from google.appengine.api import urlfetch

import config
from feedlib import crypto, report_feeds
from model import filter_by_prefix
from utils import ErrorMessage, Handler, db, run, urlencode


class PshbSubscription(db.Model):
    """Represents a currently active subscription to an external feed.
    Key name: subdomain + ':' + topic URL.  "Topic" is PSHB terminology."""
    topic = db.StringProperty()  # feed URL that we are subscribed to
    created = db.DateTimeProperty(auto_now_add=True)  # subscription start time

    @staticmethod
    def get(subdomain, topic):
        """Gets a PshbSubscription entity by its subdomain and topic URL."""
        return PshbSubscription.get_by_key_name(subdomain + ':' + topic)

    @staticmethod
    def all_in_subdomain(subdomain):
        """Gets a query for all PshbSubscriptions in the given subdomain."""
        return filter_by_prefix(PshbSubscription.all(), subdomain + ':')

    @staticmethod
    def subscribe(subdomain, topic):
        """Adds a PshbSubscription for the given subdomain and topic."""
        PshbSubscription(key_name=subdomain + ':' + topic,
                         subdomain=subdomain, topic=topic).put()

    @staticmethod
    def unsubscribe(subdomain, topic):
        """Removes the specified PshbSubscription, if it exists."""
        sub = PshbSubscription.get(subdomain, topic)
        if sub:
            sub.delete()


class Pubsub(Handler):
    """Handler for the PSHB subscription administration page."""
    https_required = True  # must match https_required in feeds_delta.py

    def get(self):
        if not self.subdomain:
            raise ErrorMessage(400, 'No subdomain specified.')

        # Show the list of subscriptions and the form for adding a new one.
        self.render(
            'templates/pubsub.html', subdomain=self.subdomain, subscriptions=(
                PshbSubscription.all_in_subdomain(self.subdomain)))
    
    def post(self):
        if not self.subdomain:
            raise ErrorMessage(400, 'No subdomain specified.')

        topic = self.request.get('topic')
        mode = self.request.get('mode')
        if mode not in ['subscribe', 'unsubscribe']:
            raise ErrorMessage(400, 'Invalid mode.')

        callback = self.request.host_url + self.get_url('/feeds/delta')

        # Send the hub a subscription request.  Reference:
        # pubsubhubbub.googlecode.com/svn/trunk/pubsubhubbub-core-0.3.html
        params = {
            'hub.callback': callback,
            'hub.mode': mode,
            'hub.topic': topic,
            # Should be 'async', but http://pubsubhubbub.appspot.com/ has a bug
            # so only 'sync' currently works. See https://groups.google.com/
            # group/pubsubhubbub/browse_thread/thread/bc4d01f8b9961ae7
            'hub.verify': 'sync',
            'hub.secret': crypto.get_key('hub_secret'),
            # Give the hub up to 10 minutes to call us back.
            'hub.verify_token': crypto.sign('hub_verify', topic, 600)
        }
        urlfetch.fetch(config.get('hub_url'), urlencode(params), urlfetch.POST,
                       {'Content-Type': 'application/x-www-form-urlencoded'})
        logging.info('Asked hub to %s: %s', mode, topic)

        # Wait a moment for the hub to call back and verify the subscription.
        url = self.request.host_url + self.get_url('/pubsub')
        self.write('<meta http-equiv="refresh" content="2;url=%s">...' % url)

if __name__ == '__main__':
    run([('/pubsub', Pubsub)], debug=True)
