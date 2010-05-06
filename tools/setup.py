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
    def attr(type, name, values=[], editable=True):
        return Attribute(
            version, key_name=name, type=type, editable=editable, values=values)

    attributes = [
        attr('int', 'healthc_id', editable=False),
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
        #i18n: Proper name of an ID for a healthcare facility, no translation
        #i18n: necessary.
        name_message('healthc_id', en='HealthC ID', es='HealthC ID', fr='HealthC ID'),
        #i18n_meaning: referring to the name of an organization
        name_message('organization',
                     en='Organization name', es=u'Nombre de la organizaci\xf3n',
                     fr='Nom de l\'organisation'),
        #i18n_meaning: administrative division
        name_message('departemen', en='Department', es='Departamento',
                     fr='Departement'),
        #i18n_meaning: administrative division
        name_message('district', en='District', es='Distrito', fr='District'),
        #i18n_meaning: low-level administrative division
        name_message('commune', en='Commune', es='Comuna', fr='Commune'),
        #i18n: street address
        name_message('address', en='Address', es=u'Direcci\xf3n', fr='Adresse'),
        #i18n: telephone number
        name_message('phone', en='Phone', es=u'Tel\xe9fono',
                     fr=u'T\xe9l\xe9phone'),
        #i18n: E-mail address
        name_message('email', en='E-mail', es='E-mail', fr='E-mail'),
        #i18n: genre, subdivision of a particular kind of thing
        name_message('type', en='Type', es='Tipo', fr='Genre'),
        #i18n: collection of things sharing a common attribute
        name_message('category', en='Category', es='Categoria',
                     fr=u'Cat\xe9gorie'),
        #i18n: destruction
        name_message('damage', en='Damage', es=u'Da\xf1o', fr='Dommage'),
        #i18n: remarks
        name_message('comments', en='Comments', es='Comentarios',
                     fr='Commentaires'),
        #i18n: Name of a person to contact for more information.
        name_message('contact_name', en='Contact name', es='Nombre de contacto',
                     fr='Nom du contact'),
        #i18n: Total number of beds at a hospital
        name_message('total_beds', en='Total beds',
                     es='Cantidad total de camas', fr='Lits en total'),
        #i18n: Total number of unoccupied beds at a hospital.
        name_message('available_beds', en='Available beds',
                     es='Camas disponibles', fr='Lits disponibles'),
        #i18n: work done by someone that benefits another
        name_message('services', en='Services', es='Servicios', fr='Services'),
        #i18n: Whether or not a facility can be accessed by a road.
        name_message('reachable_by_road', en='Reachable by road',
                     es=u'Acceso a trav\xe9s de carretera',
                     fr='Accessible par la route'),
        #i18n: Whether or not a facility can send a vehicle to pick up
        #i18n: patients
        name_message('can_pick_up_patients',
                     en='Can pick up patients',
                     es='Puedes pasar a buscar pacientes',
                     fr='Peut ramasser les patients'),

        # type

        #i18n: Type of a facility working with a residential district
        value_message('COM', en='Community', es='Comunidad',
                      fr='Communautaire'),
        #i18n: Type of a facility associated with armed forces
        value_message('MIL', en='Military', es='Militar', fr='Militaire'),
        #i18n: Type of a facility with mixed function
        value_message('MIX', en='Mixed', es='Variada', fr='Mixte'),
        #i18n: Type of a facility: non-governmental organization
        value_message('NGO', en='NGO', es='ONG', fr='ONG'),
        #i18n: Type of a facility confined to particular persons
        value_message('PRI', en='Private', es='Privado', fr=u'Priv\xe9'),
        #i18n: Type of a facility open to the public
        value_message('PUB', en='Public', es='Publico', fr='Publique'),
        #i18n: Type of a facility: establishment of higher learning
        value_message('UNI', en='University', es='Universidad',
                      fr='Universitaire'),
        #i18n: Type of a facility committed to improving the health of
        #i18n: a community
        value_message('C/S', en='Health center', es='Centro de salud',
                      fr=u'Centre de sant\xe9'),
        #i18n: Type of a facility: a health center that exists for a
        #i18n: finite period of time.
        value_message('C/S Temp',
                      en='Temporary health center',
                      es='Centro de salud transitorio',
                      fr=u'Centre de sant\xe9 temporaire'),
        #i18n: Type of a facility: a health center with available beds,
        #i18n: as a hospital has.
        value_message('CAL',
                      en='Health center with beds',
                      es='Centro de salud con camas',
                      fr=u'Centre de sant\xe9 avec lits'),
        #i18n: Type of a facility: a health center without beds.
        value_message('CSL',
                      en='Health center without beds',
                      es='Centro de salud sin camas',
                      fr=u'Centre de sant\xe9 sans lits'),

        # category

        #i18n: Category of a health facility where medicine and medical
        #i18n: supplies are given out.
        value_message('DISP', en='Dispensary', es='Dispensario',
                      fr='Dispensaire'),
        #i18n: Category of a mobile self-sufficient health care facility.
        value_message('F Hospital', en='Field hospital',
                      es='Hospital de campo', fr=u'H\xf4pital de campagne'),
        #i18n: Category of a health facility where patients receive
        #i18n: treatment.
        value_message('HOP', en='Hospital', es='Hospital', fr=u'H\xf4pital'),
        #i18n: Category of a health facility, existing for a finite
        #i18n: period of time.
        value_message('HOP Temp', en='Temporary hospital',
                      es='Hospital transitorio',
                      fr=u'H\xf4pital temporaire'),
        #i18n: Category of a health facility with a particular specialty.
        value_message('HOP Spec',
                      en='Specialized hospital',
                      es='Hospital especializado',
                      fr=u'H\xf4pital sp\xe9cialis\xe9'),
        #i18n: Category of a moveable unit that provides a service.
        value_message('MOB', en='Mobile facility',
                      es=u'Instalaci\xf3n m\xf3vil',
                      fr=u'Facilit\xe9 mobile'),
        #i18n: Category of a moveable unit that provides a particular
        #i18n: service for a finite period of time
        value_message('MOB Temp',
                      en='Temporary mobile facility',
                      es=u'Instalaci\xf3n transitoria m\xf3vil',
                      fr=u'Facilit\xe9 mobile temporaire'),
        #i18n: Category of a facility.
        value_message('Other', en='Other', es='Otro', fr='Autre'),
        #i18n: Category of a facility.
        value_message('Unknown', en='Unknown', es='Desconocido', fr='Inconnu'),

        # services

        #i18n: Service provided by a health facility.
        #i18n_meaning: surgical specialty that focuses on abdominal organs
        value_message('general_surgery', en='General surgery',
                      es=u'Cirug\xeda general', fr=u'Chirurgie g\xe9n\xe9rale'),
        #i18n: Service provided by a health facility
        #i18n_meaning: treats diseases and injury to bones, muscles, joints and
        #i18n_meaning: tendons
        value_message('orthopedics', en='Orthopedics', es='Ortopedia',
                      fr=u'Orthop\xe9die'),
        #i18n: service provided by a health facility
        #i18n_meaning: surgery that involves the nervous system
        value_message('neurosurgery', en='Neurosurgery', es=u'Neurocirug\xeda',
                      fr='Neurochirurgie'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: surgical specialty that focuses on arteries and veins
        value_message('vascular_surgery', en='Vascular surgery',
                      es=u'Cirug\xeda vascular',
                      fr='Chirurgie vasculaire'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: deals with diagnosis and (non-surgical) treatment of
        #i18n_meaning: diseases of the internal organs
        value_message('general_medicine', en='General medicine',
                      es='Medicina general', fr=u'M\xe9decine g\xe9n\xe9rale'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: branch of medicine dealing with the heart and its diseases
        value_message('cardiology', en='Cardiology', es=u'Cardiolog\xeda',
                      fr='Cardiologie'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: specializing in treating communicable diseases
        value_message('infectious_disease', en='Infectious disease',
                      es='Enfermedad infecciosa',
                      fr='Maladies infectieuses'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: branch of medicine dealing with infants and children
        value_message('pediatrics', en='Pediatrics',
                      es=u'Pediatr\xeda', fr=u'P\xe9diatrie'),
        #i18n: Service provided by a health facility.
        #i18n: care given after surgery until patient is discharged
        value_message('postoperative_care', en='Postoperative care',
                      es=u'Cuidados postoperatorios',
                      fr=u'Soins postop\xe9ratoires'),
        #i18n: services provided by a health facility
        #i18n_meaning: Obstetrics deals with childbirth and care of the mother.
        #i18n_meaning: Gynecology deals with diseases and hygiene of women
        value_message('obstetrics_gynecology',
                      en='Obstetrics and gynecology',
                      es=u'Obstetricia y ginecolog\xeda',
                      fr=u'Obst\xe9trique et gyn\xe9cologie'),
        #i18n: Service provided by a health facility.
        value_message('dialysis', en='Dialysis', es=u'Di\xe1lisis',
                      fr='Dialyse'),
        #i18n: Service provided by a health facility.
        value_message('lab', en='Lab', es='Laboratorio', fr='Laboratoire'),
        #i18n: Service provided by a health facility.
        value_message('x_ray', en='X-ray', es='Rayos X', fr='Rayon X'),
        #i18n: Service provided by a health facility.
        value_message('ct_scan', en='CT scan', es=u'Tomograf\xeda computada',
                      fr='CT scan'),
        #i18n: Service provided by a health facility.
        value_message('blood_bank', en='Blood bank', es='Banco de sangre',
                      fr='Banque du sang'),
        #i18n: Service provided by a health facility.
        value_message('corpse_removal', en='Corpse removal',
                      es=u'Retiro de cad\xe1ver',
                      fr=u'Enl\xe8vement des cadavres'),
    ]

    db.put(attributes)
    db.put(hospital)
    db.put(messages)

def setup_new_version(country_code='ht', title='Haiti'):
    version = make_version(country_code, title)
    setup_version(version)
    return version
