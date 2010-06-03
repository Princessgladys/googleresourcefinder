"""Tests for app/feed_receiver.py."""

import urllib

from feeds import records
from scrape_test_case import ScrapeTestCase

# An actual POST request body from pubsubhubbub.
DATA = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns:have="urn:oasis:names:tc:emergency:EDXL:HAVE:1.0" xmlns:status="http://schemas.google.com/2010/status" xmlns="http://www.w3.org/2005/Atom" xmlns:gml="http://opengis.net/gml" xmlns:xnl="urn:oasis:names:tc:ciq:xnl:3">
  <id>http://example.com/feeds/delta</id>

<entry>
    <author>
      <email>foo@example.com</email>
    </author>
    <id>http://example.com/feeds/delta/122</id>
    <title/>
    <updated>2010-03-16T09:13:48.224281Z</updated>
    <status:subject>paho.org/HealthC_ID/1115006</status:subject>
    <status:observed>2010-03-12T12:12:12Z</status:observed>
    <status:report type="{urn:oasis:names:tc:emergency:EDXL:HAVE:1.0}Hospital">
      <have:Hospital>
        <have:OrganizationInformation>
          <xnl:OrganisationName>
            <xnl:NameElement>Foo Hospital</xnl:NameElement>
          </xnl:OrganisationName>
        </have:OrganizationInformation>
        <have:OrganizationGeoLocation>
          <gml:Point>
            <gml:pos>45.256 -71.92</gml:pos>
          </gml:Point>
        </have:OrganizationGeoLocation>
        <have:LastUpdateTime>2010-03-12T12:12:12Z</have:LastUpdateTime>
      </have:Hospital>
    </status:report>
  </entry>
</feed>
"""


class IncomingTest(ScrapeTestCase):

    TOKEN = 'mytoken'
    URL = 'http://localhost:8081/incoming/' + TOKEN
    TOPIC = 'http://localhost:8081/static/sample_feed.xml'

    def test_subscription_verification(self):
        # Test GET request from the hub to verify subscription.
        challenge = 'mychallenge'
        query = {'hub.verify_token': self.TOKEN,
                 'hub.challenge': challenge,
                 'hub.topic': self.TOPIC,
                 'hub.mode': 'subscribe',
                 'hub.lease_seconds': '2592000'}
        qs = urllib.urlencode(query)
        url = '%s?%s' % (self.URL, qs)
        doc = self.s.go(url)
        assert self.s.status == 200
        assert doc.content == challenge

    def test_feed_update_notification(self):
        # Test POST request from the hub to announce feed update.

        # Initially, there are no records.
        assert records.Record.all().count() == 0
        
        doc = self.s.go(self.URL, data=DATA)
        assert self.s.status == 200
        assert doc.content == ''

        # Now a Report record should have been written to the datastore.
        assert records.Record.all().count() == 1
