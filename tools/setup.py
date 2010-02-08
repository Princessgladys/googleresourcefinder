def make_new_version(cc, country_name):
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
    int_attr = lambda key, name, abbr=None: attr('int', key, name, abbr)
    multi_attr = (lambda key, name, abbr, values:
                  attr('multi', key, name, abbr, values))

    attributes = [
        str_attr('contact_name', 'Contact name'),
        str_attr('contact_phone', 'Contact phone'),
        str_attr('contact_email', 'Contact email'),
        str_attr('hours_of_operation', 'Hours of operation'),
        str_attr('end_date', 'Service end date'),
        int_attr('doctor_count', 'Current number of doctors', 'Doc'),
        int_attr('patient_count', 'Current number of patients', 'Pat'),
        int_attr('patient_capacity', 'Patient capacity', 'Cap'),
        multi_attr('doctor_specialties', 'Doctor specialties available',
                   'Specialties', ['obstetrics', 'orthopedic surgery',
                                   'physical therapy']),
        multi_attr('medical_equipment', 'Medical equipment available',
                   'Equipment', ['x-ray', 'ultrasound']),
        str_attr('comments', 'Comments')
    ]

    hospital = FacilityType(version, key_name='hospital',
                            name='Hospital', abbreviation='H',
                            attributes=[a.key().name() for a in attributes])

    db.put(attributes)
    db.put(hospital)
