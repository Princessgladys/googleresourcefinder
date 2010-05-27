#!/usr/bin/python2.5
# Copyright 2010 Google Inc.
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

"""
Extracts translations to a .po file using django's makemessages script
and additional custom support for js- and python-formatted strings.
Also supports message descriptions and meanings provided by
specially-formatted comments directly above a message to be translated.

In javascript, comments look like:
    // Some other comment, must not separate i18n comments from the code
    //i18n: Label for an administrative division of a country
    messages.DEPARTMENT = 'Department';

In python:
    # Some other comment, must not separate i18n comments from the code
    #i18n: Label for an administrative division of a country
    dept = _('Department')

And in a Django template:
    {% comment %}
    #Some other comment, must not separate i18n comments from the code
    #i18n: Label for an administrative division of a country
    {% endcomment %}
    <span>{% trans "Department" %}</span>

Warning: This code technically also supports an i18n_meaning tag to create
msgctxt lines in the .po file, but these are not supported by the current
django version used by appengine (if msgctxt lines appear, not only are they
ignored, but they prevent the correct translation from being returned),
so they are not used.

Instead of running this script directly, use the 'extract_messages' shell
script, which sets up the PYTHONPATH and other necessary environment variables.

Example:
    ../tools/extract_messages ../tools/setup.py static/locale.js
"""

import codecs
import os
import re
import sys

DJANGO_END_COMMENT_PATTERN = '{\% endcomment \%}'
DJANGO_STRING_PATTERN = '''['"](.*)['"]\s*$'''
STRING_LITERAL_PATTERN = r'''\s*(["'])((\\.|[^\\])*?)\1'''
DJANGO_BIN = os.environ['APPENGINE_DIR'] + '/lib/django/django/bin'

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

    def __init__(self, msgid, description='', meaning='', msgstr=''):
        self.msgid = msgid
        self.description = description
        self.meaning = meaning
        self.msgstr = msgstr

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
       html files."""
    cwd = os.getcwd()
    os.chdir(os.environ['APP_DIR'])
    (stdin, stdout, stderr) = os.popen3(
        os.path.join(DJANGO_BIN, 'make-messages.py') + ' -a', 't')
    errors = stderr.read()
    if errors:
        raise SystemExit(errors)
    os.chdir(cwd)

def parse_django_po(po_filename):
    """Return the header from the django-generated .po file
       and a dict from Message to a list of file:line_num references where that
       Message was extracted"""
    # Holds the header at the top of the django po file
    header = ''
    # A sentinel to know when to stop considering lines part of the header
    header_done = False
    # The return dict of Message to code ref 'file:line_num'
    message_to_ref = {}
    # The current file:line_num ref, which occurs on a previous line to it's
    # corresponding message
    current_ref = ''
    # The current Message
    current_msg = Message(None, None, None, None)

    for line in codecs.open(po_filename, encoding='utf-8'):
        if line.startswith('#:'):
            header_done = True
        if not header_done:
            header += line
            continue
        line = line.strip()
        if not line.strip() and current_msg.msgid:
            refs = current_ref.split(' ')
            if not current_msg.description and not current_msg.meaning:
                (desc, meaning) = find_description_meaning(refs)
                current_msg.description = desc
                current_msg.meaning = meaning
            if not current_msg.description:
                current_msg.description = ''
            if not current_msg.meaning:
                current_msg.meaning = ''
            message_to_ref[current_msg] = refs
            current_ref = ''
            current_msg = Message(None, None, None, None)
        elif line.startswith('#:'):
            current_ref = line[3:]
        elif line.startswith('#.'):
            current_msg.description = line[3:]
        elif line.startswith('msgstr'):
            current_msg.msgstr = parse_po_tagline(line, 'msgstr')
        elif current_msg.msgstr is not None:
            current_msg.msgstr += parse_po_tagline(line)
        elif line.startswith('msgid'):
            current_msg.msgid = parse_po_tagline(line, 'msgid')
        elif current_msg.msgid is not None:
            current_msg.msgid += parse_po_tagline(line)
        elif line.startswith('msgctxt'):
            current_msg.meaning = parse_po_tagline(line, 'msgctxt')
        elif current_msg.meaning is not None:
            current_msg.meaning += parse_po_tagline(line)

    if current_msg.msgid:
        refs = current_ref.split(' ')
        if not current_msg.description and not current_msg.meaning:
            (desc, meaning) = find_description_meaning(refs)
            current_msg.description = desc
            current_msg.meaning = meaning
        if not current_msg.description:
            current_msg.description = ''
        if not current_msg.meaning:
            current_msg.meaning = ''
        message_to_ref[current_msg] = refs

    return (header, message_to_ref)

def parse_po_tagline(line, tag=''):
    """Parse a tag line from a po file."""
    match = re.match((tag and (tag + ' ') or '') + DJANGO_STRING_PATTERN, line)
    return len(match.groups()) > 0 and match.group(1) or ''

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

        lines = open(os.path.join(os.environ['APP_DIR'], file)).readlines()
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
            current_message += parse_message(patterns['string'], line)
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

def parse_message(pattern, line):
    match = re.search(pattern, line)
    msg_part = ''
    if match:
        # Unescape the type of quote (single or double) that surrounded
        # the message, then escape double-quotes, which we use to
        # surround the message in the .po file
        quote = match.group(1)
        msg_part = match.group(2).replace('\\' + quote, quote).replace(
            '"', '\\"')
    return msg_part

def merge(msg_to_ref, ref_msg_pairs):
    """ Merge ref_msg_pairs into msg_to_ref """
    for (ref, msg) in ref_msg_pairs:
        msg_to_ref.setdefault(msg, []).append(ref)

def output_po_file(output_filename, header, msg_to_ref):
    """Write a po file to output from the given header and dict from message
       to list of file:line_num references where the message appears."""
    output = codecs.open(output_filename, 'w', 'utf-8')
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
        print >>output, 'msgstr "%s"\n' % message.msgstr
    output.close()

def has_sh_placeholders(message):
    """Returns true if the message has placeholders."""
    return re.search(r'\$\{(\w+)\}', message) is not None

def has_python_placeholders(message):
    """Returns true if the message has placeholders."""
    return re.search(r'%\(\w+\)s', message) is not None

if __name__ == '__main__':
    po_filenames = [
        os.path.join(os.environ['APP_DIR'], 'locale', locale,
                     'LC_MESSAGES', 'django.po')
        for locale in os.listdir(os.path.join(os.environ['APP_DIR'], 'locale'))]

    # Parse input files
    print 'Parsing input files'
    en_ref_msg_pairs = []
    for input_filename in sys.argv[1:]:
        en_ref_msg_pairs.extend(parse_file(input_filename))

    # For each language, grab translations for existing messages
    # (descriptions and meanings get blown away by makemessages)
    ref_msg_pairs = {}
    for po_filename in po_filenames:
        (header, message_to_ref) = parse_django_po(po_filename)
        msgs = message_to_ref.keys()
        ref_msg_pairs[po_filename] = []
        for (ref, msg) in en_ref_msg_pairs:
            msgstr = (msg in msgs) and msgs[msgs.index(msg)].msgstr or ''
            ref_msg_pairs[po_filename].append(
                (ref, Message(msg.msgid, msg.description, msg.meaning, msgstr)))

    # Run Django's makemessages
    print 'Running django makemessages'
    django_makemessages()

    # For each language, overwrite the django makemessages output with ours
    for po_filename in po_filenames:
        print 'Writing %s' % po_filename
        (header, message_to_ref) = parse_django_po(po_filename)
        merge(message_to_ref, ref_msg_pairs[po_filename])
        output_po_file(po_filename, header, message_to_ref)
