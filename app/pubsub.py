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

from feedlib import crypto, report_feeds
from utils import ErrorMessage, Handler, db, run, urlencode


class PshbSubscription(db.Model):
    """Represents a currently active subscription to an external feed."""
    subdomain = db.StringProperty()
    topic = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)

    @staticmethod
    def subscribe(subdomain, topic):
        PshbSubscription(key_name=subdomain + ':' + topic,
                         subdomain=subdomain, topic=topic).put()

    @staticmethod
    def unsubscribe(subdomain, topic):
        sub = PshbSubscription.get_by_key_name(subdomain + ':' + topic)
        if sub:
            sub.delete()


class Pubsub(Handler):
    """Handler for the PSHB subscription administration page."""

    def get(self):
        if not self.subdomain:
            raise ErrorMessage(400, 'No subdomain specified.')

        # Show the list of subscriptions and the form for adding a new one.
        self.render(
            'templates/pubsub.html', subdomain=self.subdomain, subscriptions=(
                PshbSubscription.all().filter('subdomain =', self.subdomain)))
    
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
            'hub.verify': 'async',
            'hub.secret': crypto.get_key('hub_secret'),
            # Give the hub up to 10 minutes to call us back.
            'hub.verify_token': crypto.sign('hub_verify', topic, 600)
        }
        urlfetch.fetch(report_feeds.HUB, urlencode(params), urlfetch.POST,
                       {'Content-Type': 'application/x-www-form-urlencoded'})
        logging.info('Asked hub to %s: %s', mode, topic)

        # Wait a moment for the hub to call back and verify the subscription.
        url = self.request.host_url + self.get_url('/pubsub')
        self.write('<meta http-equiv="refresh" content="2;url=%s">...' % url)

if __name__ == '__main__':
    run([('/pubsub', Pubsub)], debug=True)
