"""Tests for app/feeds_delta.py.

If you want to test with a real live pubsubhubbub instance, here's how
to do it.  You'll be running your own pubsubhubbub instance locally,
since pubsubhubbub needs to make web requests to your app (which is
running on localhost:8080).

1.  Download and run pubsubhubbub with these commands (see also
    http://code.google.com/p/pubsubhubbub/wiki/DeveloperGettingStartedGuide):

    svn checkout http://pubsubhubbub.googlecode.com/svn/trunk/ pshb
    dev_appserver.py --port 8888 --datastore_path=/tmp/pshb.ds pshb/hub

    TODO(kpy): configure the hub url in the app
    TODO(kpy): create dummy data to edit in the app

2.  In another shell, start resourcefinder:

    tools/gae run app --datastore_path=/tmp/rf.ds

3.  In yet another shell, start feeddrop:

    tools/gae run feeddrop --port 8081 --datastore_path=/tmp/feeddrop.ds

4.  Using your browser, subscribe resourcefinder to a feeddrop feed:

    a.  Navigate to: http://localhost:8080/pubsub?subdomain=haiti
        (Make sure you are logged in as an administrator.)

    b.  Enter the URL http://localhost:8081/feeds/test and click "Subscribe".

        "Asked hub to subscribe" should appear in the resourcefinder log.

    c.  Then navigate to: http://localhost:8888/_ah/admin/queues

    d.  Run all tasks that are pending there until no more tasks are pending.

        "Added subscription" should appear in the resourcefinder log.

5.  Post an entry to the feeddrop feed:

    a.  Execute this command:

        curl --data-binary @docs/sms_edit.xml http://localhost:8081/feeds/test

        "Stored entry" should appear in the feeddrop log.

    b.  Run all pending tasks at http://localhost:8081/_ah/admin/queues

    c.  Run all pending tasks at http://localhost:8888/_ah/admin/queues

        "Edit applied" should appear in the resourcefinder log.

6.  Using your browser, verify that the posted report has been stored:

    http://localhost:8080/_ah/admin/datastore?kind=ReportEntry

7.  Using your browser, verify that the Subject was edited:

    http://localhost:8080/_ah/admin/datastore?kind=Subject
"""

import datetime
import urllib

from feedlib.report_feeds import ReportEntry
from scrape_test_case import ScrapeTestCase

# An actual POST request body from pubsubhubbub.
# Note that PSHB currently requires the Atom namespace to be the default
# XML namespace (e.g. it recognizes <entry> but not <atom:entry>).  Brett
# is working on fixing this.
DATA = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns:have="urn:oasis:names:tc:emergency:EDXL:HAVE:1.0" xmlns:report="http://schemas.google.com/report/2010" xmlns="http://www.w3.org/2005/Atom" xmlns:gml="http://opengis.net/gml" xmlns:xnl="urn:oasis:names:tc:ciq:xnl:3">
  <id>http://example.com/feeds/delta</id>

<entry>
    <author>
      <email>foo@example.com</email>
    </author>
    <id>http://example.com/feeds/delta/122</id>
    <title/>
    <updated>2010-03-16T09:13:48.224281Z</updated>
    <report:subject>paho.org/HealthC_ID/1115006</report:subject>
    <report:observed>2010-03-12T12:12:12Z</report:observed>
    <report:content type="{urn:oasis:names:tc:emergency:EDXL:HAVE:1.0}Hospital">
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
    </report:content>
  </entry>
</feed>
"""


class DeltaTest(ScrapeTestCase):
    URL = 'http://localhost:8081/feeds/delta?subdomain=haiti'
    TOPIC = 'http://localhost:8081/static/sample_feed.xml'
    TOKEN = 'mytoken'

    def setUp(self):
        ScrapeTestCase.setUp(self)
        for entry in ReportEntry.all():
            entry.delete()

    def tearDown(self):
        for entry in ReportEntry.all():
            entry.delete()
        ScrapeTestCase.tearDown(self)

    def test_empty_feed(self):
        doc = self.s.go('http://localhost:8081/feeds/delta?subdomain=haiti')
        assert doc.first('atom:feed')

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

        doc = self.s.go(self.URL, data=DATA)
        assert self.s.status == 200
        assert doc.content == ''

        # Now a Record should have been written to the datastore.
        assert ReportEntry.all().count() == 1

        entry = ReportEntry.all().get()
        assert entry.external_entry_id == 'http://example.com/feeds/delta/122'
        assert entry.external_feed_id == 'http://example.com/feeds/delta'
        assert (entry.type_name ==
                '{urn:oasis:names:tc:emergency:EDXL:HAVE:1.0}Hospital')
        assert entry.subject_id == 'paho.org/HealthC_ID/1115006'
        assert entry.title is None
        assert entry.author_uri == 'mailto:foo@example.com'
        assert entry.observed == datetime.datetime(2010, 3, 12, 12, 12, 12)
        # Not checking: arrived (dynamic), content (large)
