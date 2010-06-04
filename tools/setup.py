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
              'VASCULAR_SURGERY', 'GENERAL_MEDICINE', 'CARDIOLOGY',
              'INFECTIOUS_DISEASE', 'PEDIATRICS', 'POSTOPERATIVE_CARE',
              'OBSTETRICS_GYNECOLOGY', 'DIALYSIS', 'LAB',
              'X_RAY', 'CT_SCAN', 'BLOOD_BANK', 'CORPSE_REMOVAL']),
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
             ['COM', 'MIL', 'MIX', 'NGO', 'PRI', 'PUB', 'UNI']),
        attr('choice', 'category',
             ['C/S', 'C/S Temp', 'CAL', 'CSL', 'DISP', 'F Hospital',
              'HOP', 'HOP Temp', 'HOP Spec', 'MOB', 'MOB Temp',
              'Other', 'Unknown']),
        attr('choice', 'construction',
             ['REINFORCED_CONCRETE', 'UNREINFORCED_MASONRY', 'WOOD_FRAME',
              'ADOBE']),
        attr('str', 'damage'),
        attr('choice', 'operational_status',
             ['OPERATIONAL', 'NO_SURGICAL_CAPACITY', 'FIELD_HOSPITAL',
              'FIELD_WITH_HOSPITAL', 'CLOSED_OR_CLOSING']),
        attr('str', 'comments'),
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
                                 'location'])
    db.put(hospital)
    
    attributes = [
        attr('str', 'title', edit_action='advanced_edit'),
        attr('str', 'Provider_Number', edit_action='advanced_edit'),
        attr('str', 'Hospital_Type'),
        attr('bool', 'Emergency_Services'),
        attr('str', 'Contact_Name'),
        attr('str', 'Phone_Number'),
        attr('str', 'Email'),
        attr('str', 'Address'),
        attr('str', 'City'),
        attr('str', 'State'),
        attr('int', 'ZIP_Code'),
        attr('geopt', 'location'),
        attr('float', 'Heart_Attack_30-Day_Mortality'),
        attr('float', 'Heart_Failure_30-Day_Mortality'),
        attr('float', 'Pneumonia_30-Day_Mortality'),
        attr('float', 'Heart_Attack_30-Day_Readmission'),
        attr('float', 'Heart_Failure_30-Day_Readmission'),
        attr('float', 'Pneumonia_30-Day_Readmission'),
        attr('float', 'Aspirin_on_Heart_Attack_Arrival'),
        attr('float', 'Aspirin_on_Heart Attack_Discharge'),
        attr('float', 'ACE_or_ARB_for_Heart_Attack_and_LVSD'),
        attr('float', 'Beta_Blocker_on_Heart_Attack_Discharge'),
        attr('float', 'Smoking_Cessation_Heart_Attack'),
        attr('float', 'Fibrinolytic_Within_30_Minutes_Heart_Attack_Arrival'),
        attr('float', 'PCI_Within_90_Minutes_Heart_Attack_Arrival'),
        attr('float', 'LV_Systolic_Eval_for_Heart_Failure'),
        attr('float', 'ACE_or_ARB_for_Heart_Failure_and_LVSD'),
        attr('float', 'Discharge_Instructions_Heart_Failure'),
        attr('float', 'Smoking_Cessation_Heart_Failure'),
        attr('float', 'Pneumococcal_Vaccine_for_Pneumonia'),
        attr('float', 'Antibiotics_within_6_Hours_for_Pneumonia'),
        attr('float', 'Blood_Culture_Before_Antibiotics_for_Pneumonia'),
        # TODO(?) figure out why there are duplicate columns w/ different data
        attr('float', 'Smoking_Cessation_Heart_Failure_2'),
        attr('float', 'Most_Appropriate_Antibiotic_for_Pneumonia'),
        attr('float', 'Flu_Vaccine_for_Pneumonia'),
        attr('float', 'Antibiotics_Within_1_Hour_Before_Surgery'),
        attr('float', 'Antibiotics_Stopped_Within_24_hours_After_Surgery'),
        attr('float', 'Appropriate_Antibiotics_for_Surgery'),
        attr('float',
            'Blood_Clot_Prevention_Within_24_hours_Before_or_After_Surgery'),
        attr('float', 'Blood_Clot_Prevention_After_Certain_Surgeries'),
        attr('float', 'Sugar_Control_after_Heart_Surgery'),
        attr('float', 'Safer_Hair_Removal_for_Surgery'),
        attr('float', 'Beta_Blockers_Maintained_for_Surgery'),
        attr('float', 'Pain_Relief_Children_Asthma_Admission'),
        attr('float', 'Corticosteroid_Children_Asthma_Admission'),
        attr('float', 'Caregiver_Plan_Children_Asthma_Admission'),
        attr('float', 'Nurses_"Always"_Communicated_Well'),
        attr('float', 'Doctors_"Always"_Communicated Well'),
        attr('float', 'Patients_"Always"_Received Help When Wanted'),
        attr('float', 'Pain_"Always"_Well_Controlled'),
        attr('float', 'Medicines_"Always"_Explained Before Administered'),
        attr('float', 'Room_and_Bathroom_"Always"_Clean'),
        attr('float', 'Room_"Always"_Quiet_at_Night'),
        attr('float', 'Home_Recovery_Instructions_Given'),
        attr('float', 'Patient_Rating_of_9-10'),
        attr('float', 'Patient_Recommended_Hospital')
    ]
    
    db.put(attributes)

    us_hospital = FacilityType(
        key_name='us_hospital',
        attribute_names=[a.key().name() for a in attributes],
        minimal_attribute_names=['title', 'Provider_Number', 'Hospital_Type',
                                 'Emergency_Services', 'Contact_Name',
                                 'Phone_Number', 'Address', 'location'])
    db.put(us_hospital)

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
        value_message('COM', en='Community'),
        #i18n: Type of organization: Organization associated with armed forces
        value_message('MIL', en='Military'),
        #i18n: Type of organization: Organization with mixed function
        value_message('MIX', en='Mixed'),
        #i18n: Type of organization: Non-governmental organization
        value_message('NGO', en='NGO'),
        #i18n: Type of organization: Private organization
        value_message('PRI', en='Private'),
        #i18n: Type of organization: Public (government) organization
        value_message('PUB', en='Public'),
        #i18n: Type of organization: Organization associated with a university
        value_message('UNI', en='University'),

        # category

        #i18n: Category of facility: Health center
        value_message('C/S', en='Health center'),
        #i18n: Category of facility: health center that exists for a
        #i18n: finite period of time.
        value_message('C/S Temp', en='Temporary health center'),
        #i18n: Category of facility: a health center with available beds,
        #i18n: as a hospital has.
        value_message('CAL', en='Health center with beds'),
        #i18n: Category of facility: a health center without beds.
        value_message('CSL', en='Health center without beds'),
        #i18n: Category of facility: a dispensary where medicine and medical
        #i18n: supplies are given out.
        value_message('DISP', en='Dispensary'),
        #i18n: Category of facility: A mobile self-sufficient health facility.
        value_message('F Hospital', en='Field hospital'),
        #i18n: Category of facility: Hospital
        value_message('HOP', en='Hospital'),
        #i18n: Category of facility: Hospital existing for a finite
        #i18n: period of time.
        value_message('HOP Temp', en='Temporary hospital'),
        #i18n: Category of facility: A hospital with a particular specialty.
        value_message('HOP Spec', en='Specialized hospital'),
        #i18n: Category of facility: A moveable unit that provides a service.
        value_message('MOB', en='Mobile facility',),
        #i18n: Category of facility: A moveable unit that provides a particular
        #i18n: service for a finite period of time.
        value_message('MOB Temp', en='Temporary mobile facility'),
        #i18n: Category of facility: Other.
        value_message('Other', en='Other'),
        #i18n: Category of facility: Unknown.
        value_message('Unknown', en='Unknown'),

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

        #i18n: Service provided by a health facility. 
        #i18n: Meaning: surgical specialty that focuses on abdominal organs
        value_message('GENERAL_SURGERY', en='General surgery'),
        #i18n: Service provided by a health facility 
        #i18n: Meaning: treats diseases and injury to bones, muscles, joints and
        #i18n: Meaning: tendons
        value_message('ORTHOPEDICS', en='Orthopedics'),
        #i18n: service provided by a health facility 
        #i18n: Meaning: surgery that involves the nervous system
        value_message('NEUROSURGERY', en='Neurosurgery'),
        #i18n: Service provided by a health facility. 
        #i18n: Meaning: surgical specialty that focuses on arteries and veins
        value_message('VASCULAR_SURGERY', en='Vascular surgery'),
        #i18n: Service provided by a health facility. 
        #i18n: Meaning: deals with diagnosis and (non-surgical) treatment of
        #i18n: Meaning: diseases of the internal organs
        value_message('GENERAL_MEDICINE', en='General medicine'),
        #i18n: Service provided by a health facility. 
        #i18n: Meaning: branch of medicine dealing with the heart
        value_message('CARDIOLOGY', en='Cardiology'),
        #i18n: Service provided by a health facility. 
        #i18n: Meaning: specializing in treating communicable diseases
        value_message('INFECTIOUS_DISEASE', en='Infectious disease'),
        #i18n: Service provided by a health facility. 
        #i18n: Meaning: branch of medicine dealing with infants and children
        value_message('PEDIATRICS', en='Pediatrics'),
        #i18n: Service provided by a health facility. 
        #i18n: care given after surgery until patient is discharged
        value_message('POSTOPERATIVE_CARE', en='Postoperative care'),
        #i18n: services provided by a health facility 
        #i18n: Meaning: Obstetrics deals with childbirth and care of the mother.
        #i18n: Meaning: Gynecology deals with diseases and hygiene of women
        value_message('OBSTETRICS_GYNECOLOGY', en='Obstetrics and gynecology'),
        #i18n: Service provided by a health facility.
        value_message('DIALYSIS', en='Dialysis'),
        #i18n: Service provided by a health facility.
        value_message('LAB', en='Lab'),
        #i18n: Service provided by a health facility.
        value_message('X_RAY', en='X-ray'),
        #i18n: Service provided by a health facility.
        value_message('CT_SCAN', en='CT scan'),
        #i18n: Service provided by a health facility.
        value_message('BLOOD_BANK', en='Blood bank'),
        #i18n: Service provided by a health facility.
        value_message('CORPSE_REMOVAL', en='Corpse removal'),
    ]

    for locale in os.listdir(settings.LOCALE_PATHS[0]):
        django.utils.translation.activate(locale)
        for message in messages:
            try:
                text = django.utils.translation.gettext_lazy(
                    message.en).decode('utf-8')
            except KeyError:
                logging.warning('Translation for "%s" same as "en" for "%s"'
                                % (locale, message.en))
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

def setup_new_datastore():
    """Sets up a new datastore with facility types and translations."""
    setup_facility_types()
    setup_messages()

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
    setup_new_datastore()

def add_account(email='test@example.com', description='Test',
                nickname='Test', affiliation='Test',
                actions=[':view', ':edit']):
    """Adds an Account entity to the datastore."""
    Account(email=email, description=description, nickname=nickname,
            affiliation=affiliation, actions=actions).put()
