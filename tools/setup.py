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

from access import *
from extract_messages import parse_message, PATTERNS
from feeds import crypto
from model import *
from utils import *

def setup_facility_types():
    """Sets up the attributes and facility types."""
    def attr(type, name, values=[], edit_action=None):
        return Attribute(
            key_name=name, type=type, edit_action=edit_action, values=values)

    # NB: Attributes are kept in a specific order defined by zeiger
    # Be careful when changing them, as you will change the order
    # of appearance in the map info window. Also, order here should
    # be kept roughly in sync with CSV column order defined in app/export.py
    attributes = [
        attr('str', 'title', edit_action='advanced_edit'),
        attr('str', 'alt_title', edit_action='advanced_edit'),
        attr('int', 'healthc_id', edit_action='advanced_edit'),
        attr('int', 'pcode', edit_action='advanced_edit'),
        attr('int', 'available_beds'),
        attr('int', 'total_beds'),
        attr('multi', 'services',
             ['GENERAL_SURGERY', 'ORTHOPEDICS', 'NEUROSURGERY',
              'VASCULAR_SURGERY', 'INTERNAL_MEDICINE', 'CARDIOLOGY',
              'INFECTIOUS_DISEASE', 'PEDIATRICS', 'POSTOPERATIVE_CARE',
              'REHABILITATION', 'OBSTETRICS_GYNECOLOGY', 'MENTAL_HEALTH',
              'DIALYSIS', 'LAB', 'X_RAY', 'CT_SCAN', 'BLOOD_BANK',
              'CORPSE_REMOVAL']),
        attr('str', 'contact_name'),
        attr('str', 'phone'),
        attr('str', 'email'),
        attr('str', 'department'),
        attr('str', 'district'),
        attr('str', 'commune'),
        attr('str', 'address'),
        attr('geopt', 'location'),
        attr('str', 'accuracy'),
        attr('str', 'organization'),
        attr('choice', 'organization_type',
             ['PUBLIC', 'FOR_PROFIT', 'UNIVERSITY', 'COMMUNITY',
              'NGO', 'FAITH_BASED', 'MILITARY', 'MIXED']),
        attr('choice', 'category',
             ['HOSPITAL', 'CLINIC', 'MOBILE_CLINIC', 'DISPENSARY']),
        attr('choice', 'construction',
             ['REINFORCED_CONCRETE', 'UNREINFORCED_MASONRY', 'WOOD_FRAME',
              'ADOBE']),
        attr('str', 'damage'),
        attr('choice', 'operational_status',
             ['OPERATIONAL', 'NO_SURGICAL_CAPACITY', 'FIELD_HOSPITAL',
              'FIELD_WITH_HOSPITAL', 'CLOSED_OR_CLOSING']),
        attr('text', 'comments'),
        attr('bool', 'reachable_by_road'),
        attr('bool', 'can_pick_up_patients'),
        attr('str', 'region_id', edit_action='advanced_edit'),
        attr('str', 'district_id', edit_action='advanced_edit'),
        attr('str', 'commune_id', edit_action='advanced_edit'),
        attr('str', 'commune_code', edit_action='advanced_edit'),
        attr('str', 'sante_id', edit_action='advanced_edit'),
    ]

    db.put(attributes)

    hospital = FacilityType(
        key_name='hospital',
        attribute_names=[a.key().name() for a in attributes],
        minimal_attribute_names=['title', 'pcode', 'healthc_id',
                                 'available_beds', 'total_beds', 'services',
                                 'contact_name', 'phone', 'address',
                                 'location', 'operational_status'])
    db.put(hospital)


def setup_messages():
    """Sets up messages, pulling translations from the django .po files."""
    def message(namespace, name, **kw):
        return Message(namespace=namespace, name=name, **kw)
    name_message = lambda name, **kw: message('attribute_name', name, **kw)
    value_message = lambda name, **kw: message('attribute_value', name, **kw)
    fac_type_message = lambda name, **kw: message('facility_type', name, **kw)

    messages = [
        #i18n: Name of a facility
        name_message('title', en='Facility name'),
        #i18n: Alternate name of a facility
        name_message('alt_title', en='Alternate facility name'),
        #i18n: Proper name of an ID for a healthcare facility defined by the
        #i18n: Pan-American Health Organization, no translation necessary.
        name_message('pcode', en='PCode'),
        #i18n: Proper name of an ID for a healthcare facility, no translation
        #i18n: necessary.
        name_message('healthc_id', en='HealthC ID'),
        #i18n: Total number of unoccupied beds at a hospital.
        name_message('available_beds', en='Available beds'),
        #i18n: Total number of beds at a hospital
        name_message('total_beds', en='Total beds'),
        #i18n: work done by someone that benefits another
        name_message('services', en='Services'),
        #i18n: Name of a person to contact for more information.
        name_message('contact_name', en='Contact name'),
        #i18n: telephone number
        name_message('phone', en='Phone'),
        #i18n: E-mail address
        name_message('email', en='E-mail'),
        #i18n: Meaning: administrative division
        name_message('department', en='Department'),
        #i18n: Meaning: administrative division
        name_message('district', en='District'),
        #i18n: Meaning: low-level administrative division
        name_message('commune', en='Commune'),
        #i18n: street address
        name_message('address', en='Address'),
        #i18n: latitude, longitude location
        name_message('location', en='Location'),
        #i18n: Accuracy of latitude, longitude coordinates
        name_message('accuracy', en='Accuracy'),
        #i18n: Meaning: referring to the name of an organization
        name_message('organization', en='Organization name'),
        #i18n: Type of organization (public, private, military, NGO, etc.)
        name_message('organization_type', en='Organization type'),
        #i18n: Category of facility (hospital, clinic, field team, etc.)
        name_message('category', en='Category'),
        #i18n: Materials making up a building
        name_message('construction', en='Construction'),
        #i18n: Level of destruction
        name_message('damage', en='Damage'),
        #i18n: Whether or not a facility is fully operational.
        name_message('operational_status', en='Operational status'),
        #i18n: remarks
        name_message('comments', en='Comments'),
        #i18n: Whether or not a facility can be accessed by a road.
        name_message('reachable_by_road', en='Reachable by road'),
        #i18n: Whether or not a facility can send a vehicle to pick up
        #i18n: patients
        name_message('can_pick_up_patients', en='Can pick up patients'),

        # organization_type

        #i18n: Type of organization: Local community organization
        value_message('COMMUNITY', en='Community'),
        #i18n: Type of organization: Faith-based organization
        value_message('FAITH_BASED', en='Faith-based'),
        #i18n: Type of organization: For-profit organization
        value_message('FOR_PROFIT', en='For-profit'),
        #i18n: Type of organization: Organization associated with armed forces
        value_message('MILITARY', en='Military'),
        #i18n: Type of organization: Organization with mixed function
        value_message('MIXED', en='Mixed'),
        #i18n: Type of organization: Non-governmental organization
        value_message('NGO', en='NGO'),
        #i18n: Type of organization: Public (government) organization
        value_message('PUBLIC', en='Public'),
        #i18n: Type of organization: Organization associated with a university
        value_message('UNIVERSITY', en='University'),

        # category

        #i18n: Category of facility: Clinic
        value_message('CLINIC', en='Clinic'),
        #i18n: Category of facility: A dispensary where medicine and medical
        #i18n: supplies are given out.
        value_message('DISPENSARY', en='Dispensary'),
        #i18n: Category of facility: Hospital.
        value_message('HOSPITAL', en='Hospital'),
        #i18n: Category of facility: A mobile clinic.
        value_message('MOBILE_CLINIC', en='Mobile clinic',),

        # construction

        #i18n: Type of facility construction: concrete with metal and/or mesh
        #i18n: added to provide extra support against stresses
        value_message('REINFORCED_CONCRETE', en='Reinforced concrete'),
        #i18n: Type of facility construction: walls constructed of clay brick
        #i18n: or concrete block
        value_message('UNREINFORCED_MASONRY', en='Unreinforced masonry'),
        #i18n: Type of facility construction: timber jointed together with nails
        value_message('WOOD_FRAME', en='Wood frame'),
        #i18n: Type of facility construction: sun-dried clay bricks
        value_message('ADOBE', en='Adobe'),

        # operational_status

        #i18n: Facility operational status: in working order
        value_message('OPERATIONAL', en='Operational'),
        #i18n: Facility operational status: cannot perform surgeries
        value_message('NO_SURGICAL_CAPACITY', en='No surgical capacity'),
        #i18n: Facility operational status: as functional as a field hospital
        value_message('FIELD_HOSPITAL', en='Field hospital'),
        #i18n: Facility operational status: as functional as a field hospital
        #i18n: next to a hospital
        value_message('FIELD_WITH_HOSPITAL',
                      en='Field hospital co-located with hospital'),
        #i18n: Facility operational status: closed or in the process of closing
        value_message('CLOSED_OR_CLOSING', en='Closed or closing'),

        # services

        #i18n: Service provided by a health facility (use Title Case).
        #i18n: Meaning: surgical specialty that focuses on abdominal organs
        value_message('GENERAL_SURGERY', en='General Surgery'),
        #i18n: Service provided by a health facility (use Title Case).
        #i18n: Meaning: treats diseases and injury to bones, muscles, joints and
        #i18n: Meaning: tendons
        value_message('ORTHOPEDICS', en='Orthopedics'),
        #i18n: service provided by a health facility (use Title Case).
        #i18n: Meaning: surgery that involves the nervous system
        value_message('NEUROSURGERY', en='Neurosurgery'),
        #i18n: Service provided by a health facility (use Title Case).
        #i18n: Meaning: surgical specialty that focuses on arteries and veins
        value_message('VASCULAR_SURGERY', en='Vascular Surgery'),
        #i18n: Service provided by a health facility (use Title Case).
        #i18n: Meaning: deals with diagnosis and (non-surgical) treatment of
        #i18n: Meaning: diseases of the internal organs
        value_message('INTERNAL_MEDICINE', en='Internal Medicine'),
        #i18n: Service provided by a health facility (use Title Case).
        #i18n: Meaning: branch of medicine dealing with the heart
        value_message('CARDIOLOGY', en='Cardiology'),
        #i18n: Service provided by a health facility (use Title Case).
        #i18n: Meaning: specializing in treating communicable diseases
        value_message('INFECTIOUS_DISEASE', en='Infectious Disease'),
        #i18n: Service provided by a health facility (use Title Case).
        #i18n: Meaning: branch of medicine dealing with infants and children
        value_message('PEDIATRICS', en='Pediatrics'),
        #i18n: Service provided by a health facility (use Title Case).
        #i18n: care given after surgery until patient is discharged
        value_message('POSTOPERATIVE_CARE', en='Postoperative Care'),
        #i18n: Service provided by a health facility (use Title Case).
        #i18n: Meaning: care given to improve and recover lost function after
        #i18n: an illness or injury that has caused functional limitations
        value_message('REHABILITATION', en='Rehabilitation'),
        #i18n: Service provided by a health facility (use Title Case).
        #i18n: Meaning: Obstetrics deals with childbirth and care of the mother.
        #i18n: Meaning: Gynecology deals with diseases and hygiene of women
        value_message('OBSTETRICS_GYNECOLOGY', en='Obstetrics and Gynecology'),
        #i18n: Service provided by a health facility (use Title Case).
        #i18n: Meaning: Care for cognitive and emotional well-being.
        value_message('MENTAL_HEALTH', en='Mental Health'),
        #i18n: Service provided by a health facility (use Title Case).
        #i18n: Meaning: Artificial replacement for lost kidney function.
        value_message('DIALYSIS', en='Dialysis'),
        #i18n: Service provided by a health facility (use Title Case).
        value_message('LAB', en='Lab'),
        #i18n: Service provided by a health facility (use Title Case).
        value_message('X_RAY', en='X-Ray'),
        #i18n: Service provided by a health facility (use Title Case).
        value_message('CT_SCAN', en='CT Scan'),
        #i18n: Service provided by a health facility (use Title Case).
        value_message('BLOOD_BANK', en='Blood Bank'),
        #i18n: Service provided by a health facility (use Title Case).
        value_message('CORPSE_REMOVAL', en='Corpse Removal'),
    ]

    for locale in os.listdir(settings.LOCALE_PATHS[0]):
        django.utils.translation.activate(locale)
        for message in messages:
            try:
                text = django.utils.translation.gettext_lazy(
                    message.en).decode('utf-8')
            except KeyError:
                logging.warning('en and %s messages are the same: %r' %
                                (locale, message.en))
                text = message.en
            setattr(message, locale, text)

    existing = list(m for m in Message.all(keys_only=True))
    db.put(messages)
    # Clean up obsolete existing messages
    while existing:
        batch, existing = existing[:200], existing[200:]
        db.delete(batch)

def setup_js_messages():
    """Writes translated messages into app/static/locale_XX.js."""
    js_path = os.path.join(ROOT, 'static')
    js_template = open(os.path.join(js_path, 'locale.js')).readlines()
    patterns = PATTERNS['js']
    strcat_pattern = (
        patterns['string'] + '(\s*\+\s*' + patterns['string'] + ')*')
    locales = os.listdir(settings.LOCALE_PATHS[0])
    locales.remove('en')

    for locale in locales:
        django.utils.translation.activate(locale)
        output_file = os.path.join(js_path, 'locale_%s.js'
                                   % django.utils.translation.get_language())
        print >>sys.stderr, 'Writing ' + output_file
        output = open(output_file, 'w')
        current_msg = ''
        current_msg_line = ''
        for line in js_template:
            line = line.replace('\n', '')
            output_line = True
            match = re.match(patterns['start'], line)
            if match or current_msg_line:
                current_msg_line += line
                current_msg += parse_message(patterns['string'], line)

            if current_msg_line and re.search(patterns['end'], line):
                trans = django.utils.translation.gettext_lazy(
                    current_msg).decode('utf-8')
                if current_msg == trans:
                    logging.warning('en and %s messages are the same: %r' %
                                    (locale, current_msg))
                line = re.sub(strcat_pattern, to_js_string(trans),
                              current_msg_line, count=1)
                line = re.sub('\s*=\s*', ' = ', line, count=1)
                current_msg = ''
                current_msg_line = ''
            elif current_msg_line:
                output_line = False

            if output_line:
                print >>output, line

        output.close()

def to_js_string(string):
    """Escapes quotes and escapes unicode characters to \uXXXX notation"""
    return simplejson.dumps(string).replace("'", "\'")

def setup_datastore():
    """Sets up the facility types and translations in a datastore.  (Existing
    the facility types and messages will be updated; existing Facility or
    Report information will not be changed or deleted.)"""
    setup_facility_types()
    setup_messages()
    memcache.flush_all()  # flush any cached messages

def wipe_datastore(*kinds):
    """Deletes everything in the datastore except Accounts and Secrets.
    If 'kinds' is given, deletes only those kinds of entities."""
    for kind in kinds or [Attribute, FacilityType, Message, Dump,
                          MinimalFacility, Facility, Report]:
        keys = kind.all(keys_only=True).fetch(200)
        while keys:
            logging.info('%s: deleting %d...' % (kind.kind(), len(keys)))
            db.delete(keys)
            keys = kind.all(keys_only=True).fetch(200)

def reset_datastore():
    """Wipes everything in the datastore except Accounts and Secrets,
    then sets up the datastore for new data."""
    wipe_datastore()
    setup_datastore()

def add_account(email='test@example.com', description=None,
                nickname=None, affiliation=None, actions=[':view', ':edit']):
    """Adds an Account entity to the datastore."""
    Account(email=email, description=description or email,
            nickname=nickname or email.split('@')[0],
            affiliation=affiliation or email.split('@')[1],
            actions=actions).put()
