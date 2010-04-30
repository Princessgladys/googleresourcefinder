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
        attr('str', 'organization'),
        attr('str', 'departemen'),
        attr('str', 'district'),
        attr('str', 'commune'),
        attr('str', 'address'),
        attr('str', 'phone'),
        attr('str', 'email'),
        attr('choice', 'type',
             ['COM', 'MIL', 'MIX', 'NGO', 'PRI', 'PUB', 'UNI']),
        attr('choice', 'category',
             ['C/S', 'C/S Temp', 'CAL', 'CSL', 'DISP', 'F Hospital',
              'HOP', 'HOP Temp', 'HOP Spec', 'MOB', 'MOB Temp',
              'Other', 'Unknown']),
        attr('str', 'damage'),
        attr('str', 'comments'),
        attr('str', 'contact_name'),
        attr('int', 'total_beds'),
        attr('int', 'available_beds'),
        attr('multi', 'services',
             ['general_surgery', 'orthopedics', 'neurosurgery',
              'vascular_surgery', 'general_medicine', 'cardiology',
              'infectious_disease', 'pediatrics', 'postoperative_care',
              'obstetrics_gynecology', 'dialysis', 'lab',
              'x_ray', 'ct_scan', 'blood_bank', 'corpse_removal']),
        attr('bool', 'reachable_by_road'),
        attr('bool', 'can_pick_up_patients'),
    ]

    hospital = FacilityType(
        version, key_name='hospital',
        attribute_names=[a.key().name() for a in attributes])

    def message(namespace, name, **kw):
        return Message(version, namespace=namespace, name=name, **kw)
    name_message = lambda name, **kw: message('attribute_name', name, **kw)
    value_message = lambda name, **kw: message('attribute_value', name, **kw)

    messages = [
        #i18n_meaning: referring to the name of an organization
        name_message('organization',
                     en='Organization name',
                     fr='Nom de l\'organisation'),
        #i18n_meaning: administrative division
        name_message('departemen', en='Department', fr='Departement'),
        #i18n_meaning: administrative division
        name_message('district', en='District', fr='District'),
        #i18n_meaning: low-level administrative division
        name_message('commune', en='Commune', fr='Commune'),
        #i18n: street address
        name_message('address', en='Address', fr='Adresse'),
        #i18n: telephone number
        name_message('phone', en='Phone', fr=u'T\xe9l\xe9phone'),
        #i18n: E-mail address
        name_message('email', en='E-mail', fr='E-mail'),
        #i18n: genre, subdivision of a particular kind of thing
        name_message('type', en='Type', fr='Genre'),
        #i18n: collection of things sharing a common attribute
        name_message('category', en='Category', fr=u'Cat\xe9gorie'),
        #i18n: destruction
        name_message('damage', en='Damage', fr='Dommage'),
        #i18n: remarks
        name_message('comments', en='Comments', fr='Commentaires'),
        #i18n: Name of a person to contact for more information.
        name_message('contact_name', en='Contact name', fr='Nom du contact'),
        #i18n: Total number of beds at a hospital
        name_message('total_beds',
                     en='Total beds', fr='Lits en total'),
        #i18n: Total number of unoccupied beds at a hospital.
        name_message('available_beds',
                     en='Available beds', fr='Lits disponibles'),
        #i18n: work done by someone that benefits another
        name_message('services', en='Services', fr='Services'),
        #i18n: Whether or not a facility can be accessed by a road.
        name_message('reachable_by_road',
                     en='Reachable by road', fr='Accessible par la route'),
        #i18n: Whether or not a facility can send a vehicle to pick up
        #i18n: patients
        name_message('can_pick_up_patients',
                     en='Can pick up patients',
                     fr='Peut ramasser les patients'),

        # type

        #i18n: Type of a facility working with a residential district
        value_message('COM', en='Community', fr='Communautaire'),
        #i18n: Type of a facility associated with armed forces
        value_message('MIL', en='Military', fr='Militaire'),
        #i18n: Type of a facility with mixed function
        value_message('MIX', en='Mixed', fr='Mixte'),
        #i18n: Type of a facility: non-governmental organization
        value_message('NGO', en='NGO', fr='ONG'),
        #i18n: Type of a facility confined to particular persons
        value_message('PRI', en='Private', fr=u'Priv\xe9'),
        #i18n: Type of a facility open to the public
        value_message('PUB', en='Public', fr='Publique'),
        #i18n: Type of a facility: establishment of higher learning
        value_message('UNI', en='University', fr='Universitaire'),
        #i18n: Type of a facility committed to improving the health of
        #i18n: a community
        value_message('C/S', en='Health center', fr=u'Centre de sant\xe9'),
        #i18n: Type of a facility: a health center that exists for a
        #i18n: finite period of time.
        value_message('C/S Temp',
                      en='Temporary health center',
                      fr=u'Centre de sant\xe9 temporaire'),
        #i18n: Type of a facility: a health center with available beds,
        #i18n: as a hospital has.
        value_message('CAL',
                      en='Health center with beds',
                      fr=u'Centre de sant\xe9 avec lits'),
        #i18n: Type of a facility: a health center without beds.
        value_message('CSL',
                      en='Health center without beds',
                      fr=u'Centre de sant\xe9 sans lits'),

        # category

        #i18n: Category of a health facility where medicine and medical
        #i18n: supplies are given out.
        value_message('DISP', en='Dispensary', fr='Dispensaire'),
        #i18n: Category of a mobile self-sufficient health care facility.
        value_message('F Hospital',
                      en='Field hospital', fr=u'H\xf4pital de campagne'),
        #i18n: Category of a health facility where patients receive
        #i18n: treatment.
        value_message('HOP', en='Hospital', fr=u'H\xf4pital'),
        #i18n: Category of a health facility, existing for a finite
        #i18n: period of time.
        value_message('HOP Temp',
                      en='Temporary hospital', fr=u'H\xf4pital temporaire'),
        #i18n: Category of a health facility with a particular specialty.
        value_message('HOP Spec',
                      en='Specialized hospital',
                      fr=u'H\xf4pital sp\xe9cialis\xe9'),
        #i18n: Category of a moveable unit that provides a service.
        value_message('MOB', en='Mobile facility', fr=u'Facilit\xe9 mobile'),
        #i18n: Category of a moveable unit that provides a particular
        #i18n: service for a finite period of time
        value_message('MOB Temp',
                      en='Temporary mobile facility',
                      fr=u'Facilit\xe9 mobile temporaire'),
        #i18n: Category of a facility.
        value_message('Other', en='Other', fr='Autre'),
        #i18n: Category of a facility.
        value_message('Unknown', en='Unknown', fr='Inconnu'),

        # services

        #i18n: Service provided by a health facility.
        #i18n_meaning: surgical specialty that focuses on abdominal organs
        value_message('general_surgery',
                      en='General surgery', fr=u'Chirurgie g\xe9n\xe9rale'),
        #i18n: Service provided by a health facility
        #i18n_meaning: treats diseases and injury to bones, muscles, joints and
        #i18n_meaning: tendons
        value_message('orthopedics', en='Orthopedics', fr=u'Orthop\xe9die'),
        #i18n: service provided by a health facility
        #i18n_meaning: surgery that involves the nervous system
        value_message('neurosurgery', en='Neurosurgery', fr='Neurochirurgie'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: surgical specialty that focuses on arteries and veins
        value_message('vascular_surgery',
                      en='Vascular surgery', fr='Chirurgie vasculaire'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: deals with diagnosis and (non-surgical) treatment of
        #i18n_meaning: diseases of the internal organs
        value_message('general_medicine',
                      en='General medicine', fr=u'M\xe9decine g\xe9n\xe9rale'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: branch of medicine dealing with the heart and its diseases
        value_message('cardiology', en='Cardiology', fr='Cardiologie'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: specializing in treating communicable diseases
        value_message('infectious_disease',
                      en='Infectious disease', fr='Maladies infectieuses'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: branch of medicine dealing with infants and children
        value_message('pediatrics', en='Pediatrics', fr=u'P\xe9diatrie'),
        #i18n: Service provided by a health facility.
        #i18n: care given after surgery until patient is discharged
        value_message('postoperative_care',
                      en='Postoperative care', fr=u'Soins postop\xe9ratoires'),
        #i18n: services provided by a health facility
        #i18n_meaning: Obstetrics deals with childbirth and care of the mother.
        #i18n_meaning: Gynecology deals with diseases and hygiene of women
        value_message('obstetrics_gynecology',
                      en='Obstetrics and gynecology',
                      fr=u'Obst\xe9trique et gyn\xe9cologie'),
        #i18n: Service provided by a health facility.
        value_message('dialysis', en='Dialysis', fr='Dialyse')
        #i18n: Service provided by a health facility.
        value_message('lab', en='Lab', fr='Laboratoire'),
        #i18n: Service provided by a health facility.
        value_message('x_ray', en='X-ray', fr='Rayon X'),
        #i18n: Service provided by a health facility.
        value_message('ct_scan', en='CT scan', fr='CT scan'),
        #i18n: Service provided by a health facility.
        value_message('blood_bank', en='Blood bank', fr='Banque du sang'),
        #i18n: Service provided by a health facility.
        value_message('corpse_removal',
                      en='Corpse removal', fr=u'Enl\xe8vement des cadavres'),
    ]

    db.put(attributes)
    db.put(hospital)
    db.put(messages)

def setup_new_version(country_code='ht', title='Haiti'):
    version = make_version(country_code, title)
    setup_version(version)
    return version
