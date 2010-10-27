"""Tests for app/feeds_delta.py.

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

from feedlib import crypto
from feedlib.report_feeds import ReportEntry
from model import MinimalSubject, Subject
from scrape_test_case import ScrapeTestCase

# An actual POST request body from pubsubhubbub.
POST_DATA = '''<?xml version="1.0" encoding="utf-8"?>
<atom:feed xmlns:atom="http://www.w3.org/2005/Atom" xmlns:report="http://schemas.google.com/report/2010" xmlns:gs="http://schemas.google.com/spreadsheets/2006">
  <atom:id>http://feeddrop.appspot.com/feeds/kpy_sms</atom:id>
  <atom:title>http://feeddrop.appspot.com/feeds/kpy_sms</atom:title>
  <atom:updated>2010-10-26T23:18:28.722198Z</atom:updated>
  <atom:link href="https://pubsubhubbub.appspot.com" rel="hub"/>

<atom:entry>
    <atom:id>http://feeddrop.appspot.com/feeds/kpy_sms/31001</atom:id>
    <atom:title/>
    <atom:updated>2010-10-26T23:18:28.722198Z</atom:updated>
    <atom:author>
      <atom:uri>mailto:test@example.com</atom:uri>
      <atom:email>test@example.com</atom:email>
    </atom:author>
    <report:subject>paho.org/HealthC_ID/1115010</report:subject>
    <report:observed>2010-10-20T17:06:18Z</report:observed>
    <report:content type="{http://schemas.google.com/report/2010}row">
      <report:row>
        <gs:field name="available_beds">123</gs:field>
        <gs:field name="total_beds">234</gs:field>
        <gs:field name="operational_status">FIELD_HOSPITAL</gs:field>
      </report:row>
    </report:content>
  </atom:entry>
</atom:feed>'''


class DeltaTest(ScrapeTestCase):
    URL = 'http://localhost:8081/feeds/delta?subdomain=haiti'
    TOPIC = u'http://localhost:8081/static/sample_feed.xml'

    def setUp(self):
        ScrapeTestCase.setUp(self)
        self.hub_secret = crypto.get_key('hub_secret')

    def tearDown(self):
        for subject in Subject.all():
            subject.delete()
        for entry in ReportEntry.all():
            entry.delete()
        ScrapeTestCase.tearDown(self)

    def test_empty_feed(self):
        doc = self.s.go('http://localhost:8081/feeds/delta?subdomain=haiti')
        assert doc.first('atom:feed')

    def test_subscription_verification(self):
        # Test GET request from the hub to verify subscription.
        challenge = 'mychallenge'
        query = {'hub.mode': 'subscribe',
                 'hub.topic': self.TOPIC,
                 'hub.verify_token': crypto.sign('hub_verify', self.TOPIC),
                 'hub.challenge': challenge,
                 'hub.lease_seconds': '2592000'}
        doc = self.s.go(self.URL + '&' + urllib.urlencode(query))
        assert self.s.status == 200
        assert doc.content == challenge

    def test_feed_update_notification(self):
        # Set up a Subject that will be updated.
        subject = Subject.create(
            'haiti', 'hospital', 'paho.org/HealthC_ID/1115010', None)

        # The incoming edit's effective time (see POST_DATA) is on 2010-10-20.
        BEFORE_EDIT = datetime.datetime(2010, 10, 1)
        AFTER_EDIT = datetime.datetime(2010, 11, 1)
        subject.set_attribute(
            'available_beds', 100, BEFORE_EDIT, None, None, None, '')
        subject.set_attribute(
            'total_beds', 200, AFTER_EDIT, None, None, None, '')
        subject.put()
        MinimalSubject.create(subject).put()

        # Test POST request from the hub to announce feed update.
        signature = 'sha1=' + crypto.sha1_hmac(self.hub_secret, POST_DATA)
        doc = self.s.go(self.URL, data=POST_DATA,
                        headers={'X-Hub-Signature': signature})
        assert self.s.status == 200
        assert doc.content == ''

        # Now a Record should have been written to the datastore.
        assert ReportEntry.all().count() == 1

        entry = ReportEntry.all().get()
        assert entry.external_entry_id == \
            'http://feeddrop.appspot.com/feeds/kpy_sms/31001'
        assert entry.external_feed_id == \
            'http://feeddrop.appspot.com/feeds/kpy_sms'
        assert entry.type_name == '{http://schemas.google.com/report/2010}row'
        assert entry.subject_id == 'paho.org/HealthC_ID/1115010'
        assert entry.title is None
        assert entry.author_uri == 'mailto:test@example.com'
        assert entry.observed == datetime.datetime(2010, 10, 20, 17, 6, 18)
        # Not checking: arrived (dynamic), content (large)

        # The corresponding Subject should have been edited as a result.
        subject = Subject.get('haiti', 'paho.org/HealthC_ID/1115010')
        # The newer edit should take effect, but not the older edit.
        assert subject.get_value('available_beds') == 123
        assert subject.get_value('total_beds') == 200
        # A new attribute should be created.
        assert subject.get_value('operational_status') == 'FIELD_HOSPITAL'

    def test_feed_update_bad_signature(self):
        # Test a POST with an invalid signature.
        doc = self.s.go(self.URL, data=POST_DATA,
                        headers={'X-Hub-Signature': 'sha1=foo'})
        assert self.s.status == 200  # PSHB spec section 7.4
        assert ReportEntry.all().count() == 0
