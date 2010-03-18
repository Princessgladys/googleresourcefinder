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
import time

def set_dump(version):
    if not version.dump:
        version.dump = version.dumps[0]
        version.put()
        logging.info('collapse.py: set dump for %r to %r' %
                     (version, version.dump))

def collapse_duplicate(earlier, later):
    if ((earlier.dump.source, earlier.dump.data) ==
        (later.dump.source, later.dump.data)):
        logging.info('collapse.py: collapsing %r' % later)
        later.base = earlier
        later.put()
        delete_descendants(later)
        return True

def delete_descendants(version):
    if version.dump:
        db.delete(version.dump.key())
    else:
        db.delete(version.dumps)
    version.dump = None
    version.dumps = []
    version.put()
    family = list(db.Query(keys_only=True).ancestor(version))
    kids = filter(lambda k: k != version.key(), family)
    logging.info('collapse.py: %r has %d descendant%s' %
                 (version, len(kids), plural(kids)))
    if kids:
        for i in range(0, len(kids), 100):
            db.delete(kids[i:i + 100])
        logging.info('collapse.py: deleted %d descendant%s' %
                     (len(kids), plural(kids)))

def check_time(start_time, time_limit):
    elapsed_time = time.time() - start_time
    if elapsed_time > time_limit:
        logging.info('collapse.py: elapsed time is %.2f' % elapsed_time)
        return True

def collapse_all(skip=0, time_limit=10):
    start_time = time.time()
    versions = list(Version.all().order('timestamp'))
    i = skip
    while i < len(versions):
        if check_time(start_time, time_limit):
            return i
        if versions[i].base:
            logging.info('collapse.py: %d %r already collapsed to %r' %
                         (i, versions[i], versions[i].base))
            delete_descendants(versions[i])
            i += 1
            continue
        logging.info('collapse.py: reference is %d %r' % (i, versions[i]))
        set_dump(versions[i])
        j = i + 1
        while j < len(versions):
            if check_time(start_time, time_limit):
                return i
            if versions[j].base:
                logging.info('collapse.py: %d %r already collapsed to %r' %
                             (j, versions[j], versions[j].base))
                delete_descendants(versions[j])
                j += 1
                continue
            set_dump(versions[j])
            logging.info('collapse.py: comparing %d %r to reference' %
                         (j, versions[j]))
            collapsed = db.run_in_transaction(
                collapse_duplicate, versions[i], versions[j])
            if collapsed:
                j += 1
                continue
            break
        i = j

class Collapse(Handler):
    def get(self):
        skip = int(self.request.get('skip', 0))
        self.write('<p>' + _('skip') + ' = ' + skip)
        next = collapse_all(skip, 15)
        if next is None:
            self.write('<p>' + _('done!'))
        else:
            self.write('<p>' + _('next') + ' = ' + next)
            url = 'collapse?skip=%d' % next
            self.write('<meta http-equiv="refresh" content="45;url=%s">' % url)

if __name__ == '__main__':
    run([('/collapse', Collapse)], debug=True)
