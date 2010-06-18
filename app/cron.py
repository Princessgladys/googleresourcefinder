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

from utils import *
from google.appengine.api.labs import taskqueue

class Job(db.Model):
    """A periodically running job."""
    description = db.StringProperty()
    url = db.StringProperty()  # URL to access
    payload = db.StringProperty()  # payload to POST
    method = db.StringProperty(choices=['GET', 'POST'], required=True)
    months = db.ListProperty(int)  # list of months, or [] for all
    days_of_month = db.ListProperty(int)  # list of days, or [] for all
    weekdays = db.ListProperty(int)  # list of weekdays (Sun=0), or [] for all
    hours_of_day = db.ListProperty(int)  # list of hours, or [] for all
    minutes_of_hour = db.ListProperty(int)  # list of minutes, or [] for all

class Timestamp(db.Model):
    timestamp = db.DateTimeProperty(required=True)

def truncate_to_minute(datetime):
    return DateTime(datetime.year, datetime.month, datetime.day,
                    datetime.hour, datetime.minute)

def get_datetimes():
    """Get a list of DateTime objects for each minute since the last run.
    The presence of a Timestamp with key name 'cron' and timestamp t means
    that cron.py has been run for every minute up to and including t."""
    now = truncate_to_minute(DateTime.utcnow())
    last_run = Timestamp.get_by_key_name('cron')
    if last_run is None:
        logging.debug('cron.py: initializing timestamp to %s' % to_isotime(now))
        last = now
    else:
        last = truncate_to_minute(last_run.timestamp)
    Timestamp(key_name='cron', timestamp=now).put()

    next_posix = to_posixtime(last) + 60
    now_posix = to_posixtime(now)

    datetimes = []
    while next_posix <= now_posix:
        datetimes.append(to_datetime(next_posix))
        next_posix += 60
    return datetimes

def job_should_run(job, datetime):
    return ((datetime.month in job.months or not job.months) and
            (datetime.day in job.days_of_month or not job.days_of_month) and
            (datetime.isoweekday() % 7 in job.weekdays or not job.weekdays) and
            (datetime.hour in job.hours_of_day or not job.hours_of_day) and
            (datetime.minute in job.minutes_of_hour or not job.minutes_of_hour))

def make_task_name(text):
    return re.sub('[^a-zA-Z0-9-]', '-', ' '.join(text.split()))

class Cron(Handler):
    def get(self):
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
        for datetime in db.run_in_transaction(get_datetimes):
            logging.debug('cron.py: checking %s' % to_isotime(datetime))
            for job in Job.all():
                if job_should_run(job, datetime):
                    name = make_task_name('cron-%s--%s' % (
                        to_isotime(datetime), job.description))
                    taskqueue.add(name=name, url=job.url, payload=job.payload,
                                  method=job.method, headers=headers)
                    logging.info('cron.py: queued %s' % name)

if __name__ == '__main__':
    run([('/cron', Cron)], debug=True)
