#!/usr/bin/python2.5
# Copyright 2010 by Steve Hakusa
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

"""Extracts translations to a .po file using django's makemessages script
   and additional custom support for js- and python-formatted strings
   Must be run from the app/ directory for makemessages to work.
   Example:
   ../tools/extract_messages.py ../tools/setup.py static/locale.js
"""

import os
import re
import sys

DJANGO_EN_PO = 'locale/en/LC_MESSAGES/django.po'

PATTERNS = {
    'js' : {
        'start': r'\s*messages\.[A-Z_]+\s*=',
        'array': r'\s*[\'"](.*)[\'"]\.split\([\'"](.*)[\'"]\)',
        'string': r'\s*[\'"](.*)[\'"]',
        'end': r';\s*$'
    },
    'py' : {
        'start': r'\s*[a-z]+_message\(',
        'array': None,
        'string': r'en\s*=\s*[\'"](\w+)[\'"]',
        'end': r'\),?\s*$'
    }
}

def django_makemessages():
    """ Run django's makemessages routine to extract messages from python and
        html files
    """
    cmd = ('/home/build/google3/third_party/py/django/v1_1/bin/django-admin.py '
        + 'makemessages -a')
    (stdin, stdout, stderr) = os.popen3(cmd, 't')
    errors = stderr.read()
    if errors:
        raise SystemExit(errors)
    header = ''
    header_done = False
    msgid_to_ref = {}
    current_ref = ''
    for line in open(DJANGO_EN_PO):
        if line.startswith('#:'):
            header_done = True
        if not header_done:
            header += line
            continue
        line = line.strip()
        if line.startswith('#:'):
            current_ref = line[3:]
        elif line.startswith('msgid'):
            msgid = re.match('msgid [\'"](.*)[\'"]\s*$', line).group(1)
            msgid_to_ref[msgid] = current_ref
            current_ref = ''
    return (header, msgid_to_ref)

def parse_file(input_filename):
    """ Parses the given file, extracting messages. Returns a dictionary
        of 'input_filename:line_number' to the message string."""
    patterns = PATTERNS[input_filename[-2:]]
    ref_msgid_pairs = []
    current_msgids = []
    current_msgids_line_num = -1
    line_num = 0

    for line in file(input_filename):
        line_num += 1
        if re.match(patterns['start'], line):
            # Remember that we've started a message for multi-line messages
            current_msgids_line_num = line_num
            current_msgids = parse_messages(patterns, line, current_msgids)
        elif current_msgids_line_num is not -1:
            # Multi-line message support
            current_msgids = parse_messages(patterns, line, current_msgids)

        if re.search(patterns['end'], line):
            # End of the current message
            for msg in current_msgids:
                ref_msgid_pairs.append(
                    (input_filename + ':' + str(current_msgids_line_num), msg))
            current_msgids_line_num = -1
            current_msgids = []
    return ref_msgid_pairs

def parse_messages(patterns, line, current_msgids):
    """ Parses a part of a message on a line. Also handles arrays of messages
        of the form 'message1 message2 message3'.split(' '); """
    # Grab the part of the message from previous lines, if necessary
    current = len(current_msgids) == 1 and current_msgids[0] or ''

    # First try the array pattern
    match = patterns['array'] and re.search(patterns['array'], line) or None
    if match:
        arr_str = current + match.group(1)
        split = match.group(2)
        return arr_str.split(split)

    # If that fails, try the string pattern
    match = re.search(patterns['string'], line)
    if match:
        return [current + match.group(1)]

    # Everything failed, return what was passed in
    return current_msgids

def merge(msgid_to_ref, ref_msgid_pairs):
    """ Merge ref_msgid_pairs into msgid_to_ref """
    for (ref, msgid) in ref_msgid_pairs:
        if msgid in msgid_to_ref:
            msgid_to_ref[msgid] = msgid_to_ref[msgid] + ' ' + ref
        else:
            msgid_to_ref[msgid] = ref

def output_po_file(header, msgid_to_ref, input_filename, output):
    """ Format messages and output to output_file """
    output.write(header)

    sorted = msgid_to_ref.items()
    sorted.sort()
    for msgid, refs in sorted:
        print >>output, '#. TODO: Message description and meaning'
        print >>output, '#: %s' % refs
        if has_sh_placeholders(msgid):
            print >>output, '#, sh-format'
        elif has_python_placeholders(msgid):
            print >>output, '#, python-format'
        print >>output, 'msgid "%s"' % msgid
        print >>output, 'msgstr ""\n'

def has_sh_placeholders(message):
    """ Returns true if the message has placeholders """
    return re.search(r'\$\{([a-zA-Z_]+)\}', message) is not None

def has_python_placeholders(message):
    """ Returns true if the message has placeholders """
    return re.search(r'%\([a-zA-Z_]+\)s', message) is not None

if __name__ == '__main__':
    if len(sys.argv[1:]) < 1:
        raise SystemExit('Usage: %s <special_input1> ... <special_inputN>'
                         % sys.argv[0])

    if not os.getcwd().endswith('app'):
        raise SystemExit('Please run from app/ diretory')

    (header, msgid_to_ref) = django_makemessages()
    for input_filename in sys.argv[1:]:
        ref_msgid_pairs = parse_file(input_filename)
        merge(msgid_to_ref, ref_msgid_pairs)

    output = sys.stdout
    output_po_file(header, msgid_to_ref, input_filename, output)
