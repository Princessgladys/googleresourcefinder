from model import *

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
    """Sets up the attributes and facility types."""
    def attr(type, name, values=[]):
        return Attribute(version, key_name=name, type=type, values=values)

    attributes = [
        attr('contact', 'contact_transfers'),
        attr('contact', 'contact_general'),
        attr('str', 'hours_of_operation'),
        attr('date', 'closing_date'),
        attr('int', 'patient_count'),
        attr('int', 'patient_capacity'),
        attr('int', 'doctor_count'),
        attr('multi', 'specialty_care',
             ['obstetrics', 'orthopedic_surgery', 'physical_therapy']),
        attr('multi', 'medical_equipment', ['x_ray', 'ultrasound']),
        attr('text', 'comment')
    ]

    hospital = FacilityType(version, key_name='hospital',
                            attributes=[a.key().name() for a in attributes])

    def message(namespace, name, **kw):
        return Message(version, namespace=namespace, name=name, **kw)
    name_message = lambda name, **kw: message('attribute_name', name, **kw)
    value_message = lambda name, **kw: message('attribute_value', name, **kw)

    messages = [
        name_message('contact_transfers', en='Contact for patient transfers'),
        name_message('contact_general', en='Contact for general info'),
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

def setup_new_version(country_code='ht', title='Haiti'):
    version = make_version(country_code, title)
    setup_version(version)
    return version
