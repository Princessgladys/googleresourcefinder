from model import *

def make_version(cc, country_name):
    """Creates a new version for the given country."""
    country = Country.get_by_key_name(cc)
    if not country:
        country = Country(key_name=cc, name=country_name)
        country.put()
    version = Version(country)
    version.put()
    return version

def setup_version(version):
    """Sets up the attributes and facility types."""
    def attr(type, key, name, abbr=None, values=[]):
        return Attribute(version, key_name=key, type=type, name=name,
                         abbreviation=abbr or name, values=values)

    str_attr = lambda key, name, abbr=None: attr('str', key, name, abbr)
    text_attr = lambda key, name, abbr=None: attr('text', key, name, abbr)
    contact_attr = lambda key, name, abbr=None: attr('contact', key, name, abbr)
    date_attr = lambda key, name, abbr=None: attr('date', key, name, abbr)
    int_attr = lambda key, name, abbr=None: attr('int', key, name, abbr)
    multi_attr = (lambda key, name, abbr, values:
                  attr('multi', key, name, abbr, values))

    attributes = [
        contact_attr('contact', 'Contact'),
        str_attr('hours_of_operation', 'Hours'),
        date_attr('closing_date', 'Date site will close'),
        int_attr('patient_count', 'Current number of patients', 'Patients'),
        int_attr('patient_capacity', 'Patient capacity', 'Capacity'),
        int_attr('doctor_count', 'Current number of doctors', 'Doctors'),
        multi_attr('specialty_care', 'Specialty care', 'Specialty care',
                   ['obstetrics', 'orthopedic_surgery', 'physical_therapy']),
        multi_attr('medical_equipment', 'Medical equipment available',
                   'Equipment', ['x_ray', 'ultrasound']),
        text_attr('comment', 'Comment')
    ]

    hospital = FacilityType(version, key_name='hospital',
                            name='Hospital', abbreviation='H',
                            attributes=[a.key().name() for a in attributes])

    def message(namespace, id, **langs):
        return Message(namespace=namespace, id=id, **langs)
    name_message = lambda id, **langs: message('attribute_name', id, **langs)
    value_message = lambda id, **langs: message('attribute_value', id, **langs)

    messages = [
        name_message('contact', en='Contact'),
        name_message('hours_of_operation', en='Hours'),
        name_message('closing_date', en='Date site will close'),
        name_message('patient_count', en='Current number of patients'),
        name_message('patient_capacity', en='Patient capacity'),
        name_message('doctor_count', en='Current number of doctors'),
        name_message('specialty_care', en='Specialty care'),
        name_message('medical_equipment', en='Medical equipment available'),
        name_message('comment', en='Comment'),
        value_message('obstetrics', en='Obstetrics'),
        value_message('orthopedic_surgery', en='Orthopedic surgery'),
        value_message('physical_therapy', en='Physical therapy'),
        value_message('x_ray', en='X-ray'),
        value_message('ultrasound', en='Ultrasound'),
    ]

    db.put(attributes)
    db.put(hospital)
    db.put(messages)

def setup_new_version(cc='ht', country_name='Haiti'):
    version = make_version(cc, country_name)
    setup_version(version)
    return version
