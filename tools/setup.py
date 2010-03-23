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
        name_message('organization',
                     en='Organization name',
                     fr='Nom de l\'organisation'),
        name_message('departemen', en='Departement', fr='Departement'),
        name_message('district', en='District', fr='District'),
        name_message('commune', en='Commune', fr='Commune'),
        name_message('address', en='Address', fr='Adresse'),
        name_message('phone', en='Phone', fr=u'T\xe9l\xe9phone'),
        name_message('email', en='E-mail', fr='E-mail'),
        name_message('type', en='Type', fr='Genre'),
        name_message('category', en='Category', fr=u'Cat\xe9gorie'),
        name_message('damage', en='Damage', fr='Dommage'),
        name_message('comments', en='Comments', fr='Commentaires'),
        name_message('contact_name', en='Contact name', fr='Nom du contact'),
        name_message('total_beds',
                     en='Total beds', fr='Lits en total'),
        name_message('available_beds',
                     en='Available beds', fr='Lits disponibles'),
        name_message('services', en='Services', fr='Services'),
        name_message('reachable_by_road',
                     en='Reachable by road', fr='Accessible par la route'),
        name_message('can_pick_up_patients',
                     en='Can pick up patients',
                     fr='Peut ramasser les patients'),

        # type
        value_message('COM', en='Community', fr='Communautaire'),
        value_message('MIL', en='Military', fr='Militaire'),
        value_message('MIX', en='Mixed', fr='Mixte'),
        value_message('NGO', en='NGO', fr='ONG'),
        value_message('PRI', en='Private', fr=u'Priv\xe9'),
        value_message('PUB', en='Public', fr='Publique'),
        value_message('UNI', en='University', fr='Universitaire'),
        value_message('C/S', en='Health center', fr=u'Centre de sant\xe9'),
        value_message('C/S Temp',
                      en='Temporary health center',
                      fr=u'Centre de sant\xe9 temporaire'),
        value_message('CAL',
                      en='Health center with beds',
                      fr=u'Centre de sant\xe9 avec lits'),
        value_message('CSL',
                      en='Health center without beds',
                      fr=u'Centre de sant\xe9 sans lits'),

        # category
        value_message('DISP', en='Dispensary', fr='Dispensaire'),
        value_message('F Hospital',
                      en='Field hospital', fr=u'H\xf4pital de campagne'),
        value_message('HOP', en='Hospital', fr=u'H\xf4pital'),
        value_message('HOP Temp',
                      en='Temporary hospital', fr=u'H\xf4pital temporaire'),
        value_message('HOP Spec',
                      en='Specialized hospital',
                      fr=u'H\xf4pital sp\xe9cialis\xe9'),
        value_message('MOB', en='Mobile facility', fr=u'Facilit\xe9 mobile'),
        value_message('MOB Temp',
                      en='Temporary mobile facility',
                      fr=u'Facilit\xe9 mobile temporaire'),
        value_message('Other', en='Other', fr='Autre'), 
        value_message('Unknown', en='Unknown', fr='Inconnu'), 

        # services
        value_message('general_surgery',
                      en='General surgery', fr=u'Chirurgie g\xe9n\xe9rale'),
        value_message('orthopedics', en='Orthopedics', fr=u'Orthop\xe9die'),
        value_message('neurosurgery', en='Neurosurgery', fr='Neurochirurgie'),
        value_message('vascular_surgery',
                      en='Vascular surgery', fr='Chirurgie vasculaire'),
        value_message('general_medicine',
                      en='General medicine', fr=u'M\xe9decine g\xe9n\xe9rale'),
        value_message('cardiology', en='Cardiology', fr='Cardiologie'),
        value_message('infectious_disease',
                      en='Infectious disease', fr='Maladies infectieuses'),
        value_message('pediatrics', en='Pediatrics', fr=u'P\xe9diatrie'),
        value_message('postoperative_care',
                      en='Postoperative care', fr=u'Soins postop\xe9ratoires'),
        value_message('obstetrics_gynecology',
                      en='Obstetrics and gynecology',
                      fr=u'Obst\xe9trique et gyn\xe9cologie'),
        value_message('dialysis', en='Dialysis', fr='Dialyse'),
        value_message('lab', en='Lab', fr='Laboratoire'),
        value_message('x_ray', en='X-ray', fr='Rayon X'),
        value_message('ct_scan', en='CT scan', fr='CT scan'),
        value_message('blood_bank', en='Blood bank', fr='Banque du sang'),
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
