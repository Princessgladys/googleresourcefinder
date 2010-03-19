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

    hospital = FacilityType(
        version, key_name='hospital',
        attribute_names=[a.key().name() for a in attributes])

    def message(namespace, name, **kw):
        return Message(version, namespace=namespace, name=name, **kw)
    name_message = lambda name, **kw: message('attribute_name', name, **kw)
    value_message = lambda name, **kw: message('attribute_value', name, **kw)

    messages = [
        name_message('contact_transfers',
                     en='Contact for patient transfers',
                     fr='Contact pour transfert des patients'),
        name_message('contact_general',
                     en='Contact for general info',
                     fr='Contact pour informations generales'),
        name_message('hours_of_operation',
                     en='Hours', fr='Horaires d\'ouverture'),
        name_message('closing_date', 
                     en='Date site will close',
                     fr='Date de cloture du site'),
        name_message('patient_count', 
                     en='Current number of patients',
                     fr='Nombre de patients actuellement'),
        name_message('patient_capacity', 
                     en='Patient capacity',
                     fr='Capacit\u00e9 en patients'),
        name_message('doctor_count', 
                     en='Current number of doctors',
                     fr='Nombre de m\u00e9decins actuellement'),
        name_message('specialty_care',
                     en='Specialty care', fr='Sp\u00e9cialit\u00e9s'),
        name_message('medical_equipment', 
                     en='Medical equipment available',
                     fr='\u00c9quipement m\u00e9dical'),
        name_message('comment', en='Comment', fr='Commentaires'),
        value_message('obstetrics', en='Obstetrics', fr='Obstetrique'),
        value_message('orthopedic_surgery', 
                      en='Orthopedic surgery', fr='Chirurgie orthopedique'),
        value_message('physical_therapy', 
                      en='Physical therapy', fr='Th\u00e9rapie physique'),
        value_message('x_ray', en=u'X\u2011ray', fr='Radiologie'),
        value_message('ultrasound', en='Ultrasound', fr='\u00c9chographie'),
    ]

    db.put(attributes)
    db.put(hospital)
    db.put(messages)

def setup_new_version(country_code='ht', title='Haiti'):
    version = make_version(country_code, title)
    setup_version(version)
    return version
