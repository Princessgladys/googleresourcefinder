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

from extract_messages import parse_message, PATTERNS
from model import *
from utils import *

def make_version(country_code, title):
    """Creates a new version for the given country."""
    country = Country.get_by_key_name(country_code)
    if not country:
        country = Country(key_name=country_code, title=title)
        country.put()
    version = Version(country)
    version.put()
    return version

def setup_version(version):
    """Sets up a new version."""
    setup_facility_types(version)
    setup_messages(version)

def setup_facility_types(version):
    """Sets up the attributes and facility types."""
    def attr(type, name, values=[], editable=True):
        return Attribute(
            version, key_name=name, type=type, editable=editable, values=values)

    # NB: Attributes are kept in a specific order defined by zeiger
    # Be careful when changing them, as you will change the order
    # of appearance in the map info window. Also, order here should
    # be kept roughly in sync with CSV column order defined in app/export.py
    attributes = [
        attr('int', 'healthc_id', editable=False),
        attr('int', 'available_beds'),
        attr('int', 'total_beds'),
        attr('multi', 'services',
             ['general_surgery', 'orthopedics', 'neurosurgery',
              'vascular_surgery', 'general_medicine', 'cardiology',
              'infectious_disease', 'pediatrics', 'postoperative_care',
              'obstetrics_gynecology', 'dialysis', 'lab',
              'x_ray', 'ct_scan', 'blood_bank', 'corpse_removal']),
        attr('str', 'contact_name'),
        attr('str', 'phone'),
        attr('str', 'email'),
        attr('str', 'departemen'),
        attr('str', 'district'),
        attr('str', 'commune'),
        attr('str', 'address'),
        attr('str', 'organization'),
        attr('choice', 'type',
             ['COM', 'MIL', 'MIX', 'NGO', 'PRI', 'PUB', 'UNI']),
        attr('choice', 'category',
             ['C/S', 'C/S Temp', 'CAL', 'CSL', 'DISP', 'F Hospital',
              'HOP', 'HOP Temp', 'HOP Spec', 'MOB', 'MOB Temp',
              'Other', 'Unknown']),
        attr('choice', 'construction',
             ['Reinforced concrete', 'Unreinforced masonry', 'Wood frame',
              'Adobe']),
        attr('str', 'damage'),
        attr('str', 'comments'),
        attr('bool', 'reachable_by_road'),
        attr('bool', 'can_pick_up_patients'),
        attr('str', 'region_id', editable=False),
        attr('str', 'district_id', editable=False),
        attr('str', 'commune_id', editable=False),
        attr('str', 'commune_code', editable=False),
        attr('str', 'sante_id', editable=False),
    ]

    hospital = FacilityType(
        version, key_name='hospital',
        attribute_names=[a.key().name() for a in attributes])

    db.put(attributes)
    db.put(hospital)


def setup_messages(version):
    """Sets up messages, pulling translatioons from the django .po files."""
    def message(namespace, name, **kw):
        return Message(version, namespace=namespace, name=name, **kw)
    name_message = lambda name, **kw: message('attribute_name', name, **kw)
    value_message = lambda name, **kw: message('attribute_value', name, **kw)

    messages = [
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
        #i18n_meaning: administrative division
        name_message('departemen', en='Department'),
        #i18n_meaning: administrative division
        name_message('district', en='District'),
        #i18n_meaning: low-level administrative division
        name_message('commune', en='Commune'),
        #i18n: street address
        name_message('address', en='Address'),
        #i18n_meaning: referring to the name of an organization
        name_message('organization', en='Organization name'),
        #i18n: genre, subdivision of a particular kind of thing
        name_message('type', en='Type'),
        #i18n: collection of things sharing a common attribute
        name_message('category', en='Category'),
        #i18n: the materials making up a building
        name_message('construction', en='Construction'),
        #i18n: destruction
        name_message('damage', en='Damage'),
        #i18n: remarks
        name_message('comments', en='Comments'),
        #i18n: Whether or not a facility can be accessed by a road.
        name_message('reachable_by_road', en='Reachable by road'),
        #i18n: Whether or not a facility can send a vehicle to pick up
        #i18n: patients
        name_message('can_pick_up_patients', en='Can pick up patients'),

        # type

        #i18n: Type of a facility working with a residential district
        value_message('COM', en='Community'),
        #i18n: Type of a facility associated with armed forces
        value_message('MIL', en='Military'),
        #i18n: Type of a facility with mixed function
        value_message('MIX', en='Mixed'),
        #i18n: Type of a facility: non-governmental organization
        value_message('NGO', en='NGO'),
        #i18n: Type of a facility confined to particular persons
        value_message('PRI', en='Private'),
        #i18n: Type of a facility open to the public
        value_message('PUB', en='Public'),
        #i18n: Type of a facility: establishment of higher learning
        value_message('UNI', en='University'),
        #i18n: Type of a facility committed to improving the health of
        #i18n: a community
        value_message('C/S', en='Health center'),
        #i18n: Type of a facility: a health center that exists for a
        #i18n: finite period of time.
        value_message('C/S Temp', en='Temporary health center'),
        #i18n: Type of a facility: a health center with available beds,
        #i18n: as a hospital has.
        value_message('CAL', en='Health center with beds'),
        #i18n: Type of a facility: a health center without beds.
        value_message('CSL', en='Health center without beds'),
        #i18n: Type of facility construction: concrete with metal and/or mesh
        #i18n: added to provide extra support against stresses
        value_message('Reinforced concrete', en='Reinforced concrete'),
        #i18n: Type of facility construction: walls constructed of clay brick
        #i18n: or concrete block
        value_message('Unreinforced masonry', en='Unreinforced masonry'),
        #i18n: Type of facility construction: timber jointed together with nails
        value_message('Wood frame', en='Wood frame'),
        #i18n: Type of facility construction: sun-dried clay bricks
        value_message('Adobe', en='Adobe'),

        # category

        #i18n: Category of a health facility where medicine and medical
        #i18n: supplies are given out.
        value_message('DISP', en='Dispensary'),
        #i18n: Category of a mobile self-sufficient health care facility.
        value_message('F Hospital', en='Field hospital'),
        #i18n: Category of a health facility where patients receive
        #i18n: treatment.
        value_message('HOP', en='Hospital'),
        #i18n: Category of a health facility, existing for a finite
        #i18n: period of time.
        value_message('HOP Temp', en='Temporary hospital'),
        #i18n: Category of a health facility with a particular specialty.
        value_message('HOP Spec', en='Specialized hospital'),
        #i18n: Category of a moveable unit that provides a service.
        value_message('MOB', en='Mobile facility',),
        #i18n: Category of a moveable unit that provides a particular
        #i18n: service for a finite period of time
        value_message('MOB Temp', en='Temporary mobile facility'),
        #i18n: Category of a facility.
        value_message('Other', en='Other'),
        #i18n: Category of a facility.
        value_message('Unknown', en='Unknown'),

        # services

        #i18n: Service provided by a health facility.
        #i18n_meaning: surgical specialty that focuses on abdominal organs
        value_message('general_surgery', en='General surgery'),
        #i18n: Service provided by a health facility
        #i18n_meaning: treats diseases and injury to bones, muscles, joints and
        #i18n_meaning: tendons
        value_message('orthopedics', en='Orthopedics'),
        #i18n: service provided by a health facility
        #i18n_meaning: surgery that involves the nervous system
        value_message('neurosurgery', en='Neurosurgery'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: surgical specialty that focuses on arteries and veins
        value_message('vascular_surgery', en='Vascular surgery'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: deals with diagnosis and (non-surgical) treatment of
        #i18n_meaning: diseases of the internal organs
        value_message('general_medicine', en='General medicine'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: branch of medicine dealing with the heart and its diseases
        value_message('cardiology', en='Cardiology'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: specializing in treating communicable diseases
        value_message('infectious_disease', en='Infectious disease'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: branch of medicine dealing with infants and children
        value_message('pediatrics', en='Pediatrics'),
        #i18n: Service provided by a health facility.
        #i18n: care given after surgery until patient is discharged
        value_message('postoperative_care', en='Postoperative care'),
        #i18n: services provided by a health facility
        #i18n_meaning: Obstetrics deals with childbirth and care of the mother.
        #i18n_meaning: Gynecology deals with diseases and hygiene of women
        value_message('obstetrics_gynecology', en='Obstetrics and gynecology'),
        #i18n: Service provided by a health facility.
        value_message('dialysis', en='Dialysis'),
        #i18n: Service provided by a health facility.
        value_message('lab', en='Lab'),
        #i18n: Service provided by a health facility.
        value_message('x_ray', en='X-ray'),
        #i18n: Service provided by a health facility.
        value_message('ct_scan', en='CT scan'),
        #i18n: Service provided by a health facility.
        value_message('blood_bank', en='Blood bank'),
        #i18n: Service provided by a health facility.
        value_message('corpse_removal', en='Corpse removal'),
    ]

    for locale in os.listdir(settings.LOCALE_PATHS[0]):
        django.utils.translation.activate(locale)
        for message in messages:
            setattr(message, locale,
                    django.utils.translation.gettext_lazy(message.en))

    db.put(messages)

def setup_js_messages():
    """Sets up translated versions of app/static/locale.js"""
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
                    logging.warning('Translation for "%s "same as "en" for "%s"'
                                    % (locale, current_msg))
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

def setup_new_version(country_code='ht', title='Haiti'):
    """The public interface to this module."""
    version = make_version(country_code, title)
    setup_version(version)
    setup_js_messages()
    return version
