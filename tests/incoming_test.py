"""Tests for app/feed_receiver.py.

If you want to test with a real live pubsubhubbub instance, here's how
to do it.  You'll be running your own pubsubhubbub instance locally,
since pubsubhubbub needs to make web requests to your app (which is
running on localhost:8080).

For steps 1-3 see also:
http://code.google.com/p/pubsubhubbub/wiki/DeveloperGettingStartedGuide

1. Dowload the pubsubhubbub source code from:
   http://code.google.com/p/pubsubhubbub/source/checkout

2. Run the pubsubhubbub server code (in the hub subdirectory) using:
   dev_appserver.py --port 8888 --datastore_path=/tmp/hub.datastore hub

3. Check that it works by pointing your browser to:
   http://localhost:8888
   (Don't click on any links -- they don't work because they're https.)

4. In another shell, run your resourcefinder instance in the usual way:
   tools/gae run app

5. Drop a copy of docs/sample_feed.xml into the app/static directory:
   cp docs/sample_feed.xml app/static

6. Check that this worked by pointing your browser to:
   http://localhost:8080/static/sample_feed.xml

7. Using your browser, send a subscription request to pubsubhubbub:

   a. Point your browser to http://localhost:8888/subscribe

   b. Fill out the top form as follows:

      - Callback: http://localhost:8080/incoming/mytoken
      - Topic: http://localhost:8080/static/sample_feed.xml
      - Leave everything else default

   c. Submit the form.

   d. Navigate to http://localhost:8888/_ah/admin/queues

   e. Run all tasks that are pending there until no more tasks are pending

   If successful, the form submission returns a 204 status which looks
   like nothing happened in your browser.  In the resourcefinder logs
   you should see two requests:

   - "GET /static/sample_feed.xml HTTP/1.1" 200
   - "GET /incoming/mytoken HTTP/1.1" 200

8. Using your browser, send a publish request to pubsubhubbub:

   a. Point your browser to http://localhost:8888/publish

   b. Fill out the top form as follows:

      - Topic: http://localhost:8080/static/sample_feed.xml

   c. Submit the form.

   d. Navigate to http://localhost:8888/_ah/admin/queues

   e. Run all tasks that are pending there until no more tasks are pending

   Again, if successul, nothing appears to happen in the browser.  The
   resourcefinder logs should show one request (and some other
   messages):

   - "POST /incoming/mytoken HTTP/1.1" 200

   (The body of this POST request should be similar to DATA below,
   except it contains two records.)

9. Using your browser, verify that two records corresponding to the
   contents of docs/sample_feed.xml have been added to the datastore:
   http://localhost:8080/_ah/admin/datastore?kind=Record

TODO: Once this part is implemented, verify that the corresponding
Report, Subject and MinimalSubject records have been created/updated.
"""

import datetime
import urllib

from feeds import records
from scrape_test_case import ScrapeTestCase

# An actual POST request body from pubsubhubbub.
# Note that PSHB currently requires the Atom namespace to be the default
# XML namespace (e.g. it recognizes <entry> but not <atom:entry>).  Brett
# is working on fixing this.
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

        # Erase all records from the datastore.
        for rec in records.Record.all():
            rec.delete()
        
        doc = self.s.go(self.URL, data=DATA)
        print doc.content
        assert self.s.status == 200
        assert doc.content == ''

        # Now a Record should have been written to the datastore.
        assert records.Record.all().count() == 1

        record = records.Record.all().get()
        assert record.feed_id == 'http://example.com/feeds/delta'
        assert (record.type_name ==
                '{urn:oasis:names:tc:emergency:EDXL:HAVE:1.0}Hospital')
        assert record.subject_id == 'paho.org/HealthC_ID/1115006'
        assert record.title is None
        assert record.author_email == 'foo@example.com'
        assert record.observed == datetime.datetime(2010, 3, 12, 12, 12, 12)
        # Not checking: arrived (dynamic), content (large)
