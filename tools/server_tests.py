#!/usr/bin/python2.5
# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Starts up an appserver and runs end-to-end tests against it.

Instead of running this script directly, use the 'server_tests' shell script,
which sets up the PYTHONPATH and other necessary environment variables."""

import code
import os
import re
import signal
import subprocess
import sys
import threading
import time
import traceback
import unittest

import access
import console
import model
import optparse
import scrape
import setup


class ProcessRunner(threading.Thread):
    """A thread that starts a subprocess, collects its output, and stops it."""

    READY_RE = re.compile('')  # this output means the process is ready
    OMIT_RE = re.compile('INFO ')  # omit these lines from the displayed output
    ERROR_RE = re.compile('ERROR|CRITICAL')  # this output indicates failure

    def __init__(self, name, args):
        threading.Thread.__init__(self)
        self.name = name
        self.args = args
        self.process = None  # subprocess.Popen instance
        self.ready = False  # process is running and ready
        self.failed = False  # process emitted an error message in its output
        self.output = []

    def run(self):
        """Starts the subprocess and collects its output while it runs."""
        self.process = subprocess.Popen(
            self.args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            close_fds=True)

        # Each subprocess needs a thread to be watching it and absorbing its
        # output; otherwise it will block when its stdout pipe buffer fills.
        while self.process.poll() is None:
            line = self.process.stdout.readline()
            if not line:  # process finished
                return
            if self.READY_RE.search(line):
                self.ready = True
            if self.OMIT_RE.search(line):  # filter out these lines
                continue
            if self.ERROR_RE.search(line):  # something went wrong
                self.failed = True
            if line.strip():
                self.output.append(line.strip())

    def stop(self):
        """Terminates the subprocess and returns its status code."""
        if self.process:  # started
            if self.isAlive():  # still running
                os.kill(self.process.pid, signal.SIGKILL)
            else:
                self.failed = self.process.returncode != 0
        self.clean_up()
        if self.failed:
            self.flush_output()
            print >>sys.stderr, '%s failed (status %s).\n' % (
                self.name, self.process.returncode)
        else:
            print >>sys.stderr, '%s stopped.' % self.name

    def flush_output(self):
        """Flushes the buffered output from this subprocess to stderr."""
        self.output, lines_to_print = [], self.output
        if lines_to_print:
            print >>sys.stderr
        for line in lines_to_print:
            print >>sys.stderr, self.name + ': ' + line

    def wait_until_ready(self, timeout=10):
        """Waits until the subprocess has logged that it is ready."""
        fail_time = time.time() + timeout
        while self.isAlive() and not self.ready and time.time() < fail_time:
            for jiffy in range(10):  # wait one second, aborting early if ready
                if not self.ready:
                    time.sleep(0.1)
            if not self.ready:
                self.flush_output()  # after each second, show output
        if self.ready:
            print >>sys.stderr, '%s started.' % self.name
        else:
            raise RuntimeError('%s failed to start.' % self.name)

    def clean_up(self):
        pass


class AppServerRunner(ProcessRunner):
    """Manages a dev_appserver subprocess."""

    READY_RE = re.compile('Running application ' + console.get_app_id())

    def __init__(self, port):
        self.datastore_path = '/tmp/dev_appserver.datastore.%d' % os.getpid()
        ProcessRunner.__init__(self, 'appserver', [
            os.environ['PYTHON'],
            os.path.join(os.environ['APPENGINE_DIR'], 'dev_appserver.py'),
            os.environ['APP_DIR'],
            '--port=%s' % port,
            '--clear_datastore',
            '--datastore_path=%s' % self.datastore_path,
            '--require_indexes'
        ])

    def clean_up(self):
        if os.path.exists(self.datastore_path):
            os.unlink(self.datastore_path)


class SeleniumRunner(ProcessRunner):
    """Manages a Selenium server subprocess."""

    READY_RE = re.compile('Started org.openqa.jetty.jetty.Server')
    ERROR_RE = re.compile(r'ERROR|CRITICAL|Exception')

    def __init__(self):
        ProcessRunner.__init__(
            self, 'selenium', ['java', '-jar', os.environ['SELENIUM_JAR']])


def main():
    parser = optparse.OptionParser()
    parser.add_option('-a', '--address', help='appserver hostname')
    parser.add_option('-p', '--port', type='int', help='appserver port number')
    parser.set_defaults(address='localhost', port=8081, verbose=False)
    options, args = parser.parse_args()

    runners = []
    success = False
    original_interact = code.interact
    try:
        if options.address == 'localhost':
            # Start up a clean new appserver for testing.
            runners.append(AppServerRunner(options.port))
            # TODO(kpy): Find a cleaner way to pass settings through to
            # the SeleniumTestCase.
            os.environ['TEST_CONFIG'] = 'local'
        else:
            # TODO(kpy): Pass options.address and options.port through to
            # the SeleniumTestCase.
            os.environ['TEST_CONFIG'] = 'dev'
        runners.append(SeleniumRunner())
        for runner in runners:
            runner.start()
        for runner in runners:
            runner.wait_until_ready()

        # Initialize the datastore.
        console.connect(
            '%s:%d' % (options.address, options.port), None, 'test', 'test')
        setup.setup_datastore()

        # Gather the selected tests, or all the tests if none were specified.
        loader = unittest.defaultTestLoader
        suites = []
        for filename in os.listdir(os.environ['TESTS_DIR']):
            if filename.endswith('_test.py'):
                module = filename[:-3]
                if args:
                    for pattern in args:
                        if re.match(pattern, filename):
                            suites.append(loader.loadTestsFromName(module))
                            break
                else:        
                    suites.append(loader.loadTestsFromName(module))

        # Patch code.interact() to flush log output before proceeding.
        def flush_interact(*args):
            for runner in runners:
                runner.flush_output()
            original_interact(*args)
        code.interact = flush_interact

        # Run the tests.
        print
        result = unittest.TextTestRunner().run(unittest.TestSuite(suites))
        if result.wasSuccessful():
            success = True
        print
    except:
        # Something went wrong in this script.
        traceback.print_exc()
        raise SystemExit
    finally:
        # Clean up all the subprocesses, no matter what happened.
        for runner in runners:
            if not success:
                runner.flush_output()  # show logs if anything failed
            runner.stop()
        print '\nTests %s.' % (success and 'passed' or 'failed')
        code.interact = original_interact


if __name__ == '__main__':
    main()
