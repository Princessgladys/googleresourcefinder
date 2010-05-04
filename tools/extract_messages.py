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
   and additional custom support for js- and python-formatted strings.
   Also supports message descriptions and meanings provided by
   specially-formatted comments directly above a message to be translated.

   In javascript, comments look like:

   // Some other comment, must not separate i18n comments from the code
   //i18n: Label for an administrative division of a country
   //i18n_meaning: Adminstrative division in France
   messages.DEPARTMENT = 'Department';

   In python:
   # Some other comment, must not separate i18n comments from the code
   #i18n: Label for an administrative division of a country
   #i18n_meaning: Adminstrative division in France
   dept = _('Department')

   And in a Django template:
   {% comment %}
   #Some other comment, must not separate i18n comments from the code
   #i18n: Label for an administrative division of a country
   #i18n_meaning: Adminstrative division in France
   {% endcomment %}
   <span>{% trans "Department" %}</span>

   Must be run from the app/ directory for makemessages to work.
   Example:
   ../tools/extract_messages.py ../tools/setup.py static/locale.js
"""

import os
import re
import sys

DJANGO_EN_PO = 'locale/en/LC_MESSAGES/django.po'
DJANGO_END_COMMENT_PATTERN = '{\% endcomment \%}'
STRING_LITERAL_PATTERN = r'''\s*(["'])((\\.|[^\\])*?)\1'''

PATTERNS = {
    'js' : {
        'start': r'\s*(messages\.[A-Z_1-9]+)\s*=',
        'string': STRING_LITERAL_PATTERN,
        'end': r';\s*$',
        'description': r'^\s*//i18n:\s*(.*)',
        'meaning': r'\s*//i18n_meaning:\s*(.*)'
    },
    'py' : {
        'start': r'\s*[a-z]+_message\(',
        'string': r'en\s*=' + STRING_LITERAL_PATTERN,
        'end': r'\),?\s*$',
        'description': r'^\s*#i18n:\s*(.*)',
        'meaning': r'^\s*#i18n_meaning:\s*(.*)'
    }
}

class Message:
    """ Describes a message, with optional description and meaning"""

    def __init__(self, msgid, description='', meaning=''):
        self.msgid = msgid
        self.description = description
        self.meaning = meaning

    def __eq__(self, other):
        """Only message and meaning factor into equality and hash."""
        if not isinstance(other, type(self)):
            return False
        return self.msgid == other.msgid and self.meaning == other.meaning

    def __hash__(self):
        """Only message and meaning factor into equality and hash."""
        return hash(self.msgid) ^ hash(self.meaning)

    def __cmp__(self, other):
        """Compare based on msgid."""
        if type(other) is not type(self):
            return NotImplemented
        return cmp(self.msgid, other.msgid)

def django_makemessages():
    """Run django's makemessages routine to extract messages from python and
       html files. Return the header from the django-generated .po file
       and a dict from Message to a list of file:line_num references where that
       Message was extracted."""
    cmd = ('/home/build/google3/third_party/py/django/v1_1/bin/django-admin.py '
        + 'makemessages -a')
    (stdin, stdout, stderr) = os.popen3(cmd, 't')
    errors = stderr.read()
    if errors:
        raise SystemExit(errors)

    # Holds the header at the top of the django po file
    header = ''
    # A sentinel to know when to stop considering lines part of the header
    header_done = False
    # The return dict of Message to code ref 'file:line_num'
    message_to_ref = {}
    # The current file:line_num ref, which occurs on a previous line to it's
    # corresponding message
    current_ref = ''
    # The current msgid, it can span multiple lines
    current_msgid = None
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
            current_msgid = re.match(
                '''msgid ['"](.*)['"]\s*$''', line).group(1)
        elif line.startswith('msgstr'):
            refs = current_ref.split(' ')
            (description, meaning) = find_description_meaning(refs)
            message_to_ref[Message(current_msgid, description, meaning)] = refs
            current_ref = ''
            current_msgid = None
        elif current_msgid is not None:
            current_msgid += re.match('''['"](.*)['"]\s*$''', line).group(1)
    return (header, message_to_ref)

def find_description_meaning(refs):
    """Horribly inefficient search for description and meaning strings,
       required because django makemessages doesn't parse them out for us"""
    patterns = PATTERNS['py']
    for ref in refs:
        (file, line_num) = ref.split(':')
        line_num = int(line_num)
        # django makemessages hacks in support for html files by appending .py
        # to the end and treating them like py files.  Remove that hack here
        file = file.replace('.html.py', '.html')

        # Hold the description and meaning, if we find them
        current_description = []
        current_meaning = []

        lines = open(file).readlines()
        for line in reversed(lines[:line_num - 1]):
            match = re.match(patterns['description'], line)
            if match:
                current_description.insert(0, match.group(1))
                continue
            match = re.match(patterns['meaning'], line)
            if match:
                current_meaning.insert(0, match.group(1))
                continue
            # For html files, need to skip over the django end comment marker
            # to get to the meaning lines
            if re.search(DJANGO_END_COMMENT_PATTERN, line):
                continue
            # The line was not part of a message description or meaning comment,
            # so it must not exist
            break
        if current_description or current_meaning:
            return (' '.join(current_description), ' '.join(current_meaning))

    return ('', '')

def parse_file(input_filename):
    """Parses the given file, extracting messages. Returns a list of tuples
       of 'input_filename:line_number' to a tuple of
       (message string, description, meaning)."""
    # Patterns for the given input file
    patterns = PATTERNS[input_filename.split('.')[-1]]
    # The return list of pairs of ref 'file:line_num' to message
    ref_msg_pairs = []
    # Description lines for the current message
    current_description = []
    # Meaning lines for the current message
    current_meaning = []
    # The current message being parsed.  This is a local var as the msg
    # can span multiple lines.
    current_message = ''
    # The line number to assign to the current message, usually the first line
    # of the statement containing the message.
    current_message_line_num = -1
    # Current line number in the input file
    line_num = 0

    for line in file(input_filename):
        line_num += 1
        match = re.match(patterns['description'], line)
        if match:
            current_description.append(match.group(1))
            continue
        match = re.match(patterns['meaning'], line)
        if match:
            current_meaning.append(match.group(1))
            continue

        if re.match(patterns['start'], line):
            # Remember that we've started a message for multi-line messages
            current_message_line_num = line_num

        if current_message_line_num != -1:
            match = re.search(patterns['string'], line)
            if match:
                current_message += match.group(2)

            if re.search(patterns['end'], line):
                # End of the current message
                ref = input_filename + ':' + str(current_message_line_num)
                ref_msg_pairs.append(
                    (ref, Message(current_message,
                                  ' '.join(current_description),
                                  ' '.join(current_meaning))))
                current_message_line_num = -1
                current_message = ''
                current_description = []
                current_meaning = []
    return ref_msg_pairs

def merge(msg_to_ref, ref_msg_pairs):
    """ Merge ref_msg_pairs into msg_to_ref """
    for (ref, msg) in ref_msg_pairs:
        msg_to_ref.setdefault(msg, []).append(ref)

def output_po_file(output, header, msg_to_ref):
    """Write a po file to output from the given header and dict from message
       to list of file:line_num references where the message appears."""
    output.write(header)

    for message, refs in sorted(msg_to_ref.items()):
        msgid = message.msgid
        description = message.description
        meaning = message.meaning
        if not description and not meaning:
            description = 'TODO: Message description and/or meaning'
        print >>output, '#. %s' % description
        print >>output, '#: %s' % ' '.join(refs)
        if has_sh_placeholders(msgid):
            print >>output, '#, sh-format'
        elif has_python_placeholders(msgid):
            print >>output, '#, python-format'
        if meaning:
            print >>output, 'msgctxt "%s"' % meaning
        print >>output, 'msgid "%s"' % msgid
        print >>output, 'msgstr ""\n'
    output.flush()

def has_sh_placeholders(message):
    """Returns true if the message has placeholders."""
    return re.search(r'\$\{(\w+)\}', message) is not None

def has_python_placeholders(message):
    """Returns true if the message has placeholders."""
    return re.search(r'%\(\w+\)s', message) is not None

if __name__ == '__main__':
    if not os.getcwd().endswith('app'):
        raise SystemExit('Please run from the app/ diretory')

    (header, msg_to_ref) = django_makemessages()
    for input_filename in sys.argv[1:]:
        ref_msg_pairs = parse_file(input_filename)
        merge(msg_to_ref, ref_msg_pairs)

    output = sys.stdout
    output_po_file(output, header, msg_to_ref)
