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
        date_attr('close_date', 'Date site will close'),
        int_attr('patient_count', 'Current number of patients', 'Pat'),
        int_attr('patient_capacity', 'Patient capacity', 'Cap'),
        int_attr('doctor_count', 'Current number of doctors', 'Doc'),
        multi_attr('specialty_care', 'Specialty care', 'Specialty care',
                   ['Obstetrics', 'Orthopedic surgery', 'Physical therapy']),
        multi_attr('medical_equipment', 'Medical equipment available',
                   'Equipment', ['X-ray', 'Ultrasound']),
        text_attr('comment', 'Comment')
    ]

    hospital = FacilityType(version, key_name='hospital',
                            name='Hospital', abbreviation='H',
                            attributes=[a.key().name() for a in attributes])

    db.put(attributes)
    db.put(hospital)

def setup_new_version(cc='ht', country_name='Haiti'):
    version = make_version(cc, country_name)
    setup_version(version)
    return version
