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

    def message(namespace, name, **kw):
        return Message(version, namespace=namespace, name=name, **kw)
    name_message = lambda name, **kw: message('attribute_name', name, **kw)
    value_message = lambda name, **kw: message('attribute_value', name, **kw)

    messages = [
        #i18n: Proper name of an ID for a healthcare facility, no translation
        #i18n: necessary.
        name_message('healthc_id', en='HealthC ID', es_419='HealthC ID',
                     fr='HealthC ID'),
        #i18n: Total number of unoccupied beds at a hospital.
        name_message('available_beds', en='Available beds',
                     es_419='Camas disponibles', fr='Lits disponibles'),
        #i18n: Total number of beds at a hospital
        name_message('total_beds', en='Total beds',
                     es_419='Cantidad total de camas', fr='Lits en total'),
        #i18n: work done by someone that benefits another
        name_message('services', en='Services', es_419='Servicios',
                     fr='Services'),
        #i18n: Name of a person to contact for more information.
        name_message('contact_name', en='Contact name',
                     es_419='Nombre de contacto', fr='Nom du contact'),
        #i18n: telephone number
        name_message('phone', en='Phone', es_419=u'Tel\xe9fono',
                     fr=u'T\xe9l\xe9phone'),
        #i18n: E-mail address
        name_message('email', en='E-mail', es_419='E-mail', fr='E-mail'),
        #i18n_meaning: administrative division
        name_message('departemen', en='Department', es_419='Departamento',
                     fr='Departement'),
        #i18n_meaning: administrative division
        name_message('district', en='District', es_419='Distrito',
                     fr='District'),
        #i18n_meaning: low-level administrative division
        name_message('commune', en='Commune', es_419='Comuna', fr='Commune'),
        #i18n: street address
        name_message('address', en='Address', es_419=u'Direcci\xf3n',
                     fr='Adresse'),
        #i18n_meaning: referring to the name of an organization
        name_message('organization',
                     en='Organization name',
                     es_419=u'Nombre de la organizaci\xf3n',
                     fr='Nom de l\'organisation'),
        #i18n: genre, subdivision of a particular kind of thing
        name_message('type', en='Type', es_419='Tipo', fr='Genre'),
        #i18n: collection of things sharing a common attribute
        name_message('category', en='Category', es_419='Categoria',
                     fr=u'Cat\xe9gorie'),
        #i18n: the materials making up a building
        name_message('construction', en='Construction',
                     es_419=u'Construcci\xf3n', fr='Construction'),
        #i18n: destruction
        name_message('damage', en='Damage', es_419=u'Da\xf1o', fr='Dommage'),
        #i18n: remarks
        name_message('comments', en='Comments', es_419='Comentarios',
                     fr='Commentaires'),
        #i18n: Whether or not a facility can be accessed by a road.
        name_message('reachable_by_road', en='Reachable by road',
                     es_419=u'Acceso a trav\xe9s de carretera',
                     fr='Accessible par la route'),
        #i18n: Whether or not a facility can send a vehicle to pick up
        #i18n: patients
        name_message('can_pick_up_patients',
                     en='Can pick up patients',
                     es_419='Puedes pasar a buscar pacientes',
                     fr='Peut ramasser les patients'),

        # type

        #i18n: Type of a facility working with a residential district
        value_message('COM', en='Community', es_419='Comunidad',
                      fr='Communautaire'),
        #i18n: Type of a facility associated with armed forces
        value_message('MIL', en='Military', es_419='Militar', fr='Militaire'),
        #i18n: Type of a facility with mixed function
        value_message('MIX', en='Mixed', es_419='Variada', fr='Mixte'),
        #i18n: Type of a facility: non-governmental organization
        value_message('NGO', en='NGO', es_419='ONG', fr='ONG'),
        #i18n: Type of a facility confined to particular persons
        value_message('PRI', en='Private', es_419='Privado', fr=u'Priv\xe9'),
        #i18n: Type of a facility open to the public
        value_message('PUB', en='Public', es_419='Publico', fr='Publique'),
        #i18n: Type of a facility: establishment of higher learning
        value_message('UNI', en='University', es_419='Universidad',
                      fr='Universitaire'),
        #i18n: Type of a facility committed to improving the health of
        #i18n: a community
        value_message('C/S', en='Health center', es_419='Centro de salud',
                      fr=u'Centre de sant\xe9'),
        #i18n: Type of a facility: a health center that exists for a
        #i18n: finite period of time.
        value_message('C/S Temp',
                      en='Temporary health center',
                      es_419='Centro de salud transitorio',
                      fr=u'Centre de sant\xe9 temporaire'),
        #i18n: Type of a facility: a health center with available beds,
        #i18n: as a hospital has.
        value_message('CAL',
                      en='Health center with beds',
                      es_419='Centro de salud con camas',
                      fr=u'Centre de sant\xe9 avec lits'),
        #i18n: Type of a facility: a health center without beds.
        value_message('CSL',
                      en='Health center without beds',
                      es_419='Centro de salud sin camas',
                      fr=u'Centre de sant\xe9 sans lits'),
        #i18n: Type of facility construction: concrete with metal and/or mesh
        #i18n: added to provide extra support against stresses
        value_message('Reinforced concrete',
                      en='Reinforced concrete',
                      es_419=u'De hormig\xf3n armado',
                      fr=u'Le b\xe9ton arm\xe9'),
        #i18n: Type of facility construction: walls constructed of clay brick
        #i18n: or concrete block
        value_message('Unreinforced masonry',
                      en='Unreinforced masonry',
                      es_419=u'Mamposter\xeda no reforzada',
                      fr=u'Ma\xe7onnerie non arm\xe9e'),
        #i18n: Type of facility construction: timber jointed together with nails
        value_message('Wood frame',
                      en='Wood frame',
                      es_419='Marcos de madera',
                      fr=u'\xc0 ossature de bois'),
        #i18n: Type of facility construction: sun-dried clay bricks
        value_message('Adobe',
                      en='Adobe',
                      es_419='Adobe',
                      fr=u'Adobe'),

        # category

        #i18n: Category of a health facility where medicine and medical
        #i18n: supplies are given out.
        value_message('DISP', en='Dispensary', es_419='Dispensario',
                      fr='Dispensaire'),
        #i18n: Category of a mobile self-sufficient health care facility.
        value_message('F Hospital', en='Field hospital',
                      es_419='Hospital de campo', fr=u'H\xf4pital de campagne'),
        #i18n: Category of a health facility where patients receive
        #i18n: treatment.
        value_message('HOP', en='Hospital', es_419='Hospital', fr=u'H\xf4pital'),
        #i18n: Category of a health facility, existing for a finite
        #i18n: period of time.
        value_message('HOP Temp', en='Temporary hospital',
                      es_419='Hospital transitorio',
                      fr=u'H\xf4pital temporaire'),
        #i18n: Category of a health facility with a particular specialty.
        value_message('HOP Spec',
                      en='Specialized hospital',
                      es_419='Hospital especializado',
                      fr=u'H\xf4pital sp\xe9cialis\xe9'),
        #i18n: Category of a moveable unit that provides a service.
        value_message('MOB', en='Mobile facility',
                      es_419=u'Instalaci\xf3n m\xf3vil',
                      fr=u'Facilit\xe9 mobile'),
        #i18n: Category of a moveable unit that provides a particular
        #i18n: service for a finite period of time
        value_message('MOB Temp',
                      en='Temporary mobile facility',
                      es_419=u'Instalaci\xf3n transitoria m\xf3vil',
                      fr=u'Facilit\xe9 mobile temporaire'),
        #i18n: Category of a facility.
        value_message('Other', en='Other', es_419='Otro', fr='Autre'),
        #i18n: Category of a facility.
        value_message('Unknown', en='Unknown', es_419='Desconocido', fr='Inconnu'),

        # services

        #i18n: Service provided by a health facility.
        #i18n_meaning: surgical specialty that focuses on abdominal organs
        value_message('general_surgery', en='General surgery',
                      es_419=u'Cirug\xeda general', fr=u'Chirurgie g\xe9n\xe9rale'),
        #i18n: Service provided by a health facility
        #i18n_meaning: treats diseases and injury to bones, muscles, joints and
        #i18n_meaning: tendons
        value_message('orthopedics', en='Orthopedics', es_419='Ortopedia',
                      fr=u'Orthop\xe9die'),
        #i18n: service provided by a health facility
        #i18n_meaning: surgery that involves the nervous system
        value_message('neurosurgery', en='Neurosurgery', es_419=u'Neurocirug\xeda',
                      fr='Neurochirurgie'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: surgical specialty that focuses on arteries and veins
        value_message('vascular_surgery', en='Vascular surgery',
                      es_419=u'Cirug\xeda vascular',
                      fr='Chirurgie vasculaire'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: deals with diagnosis and (non-surgical) treatment of
        #i18n_meaning: diseases of the internal organs
        value_message('general_medicine', en='General medicine',
                      es_419='Medicina general', fr=u'M\xe9decine g\xe9n\xe9rale'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: branch of medicine dealing with the heart and its diseases
        value_message('cardiology', en='Cardiology', es_419=u'Cardiolog\xeda',
                      fr='Cardiologie'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: specializing in treating communicable diseases
        value_message('infectious_disease', en='Infectious disease',
                      es_419='Enfermedad infecciosa',
                      fr='Maladies infectieuses'),
        #i18n: Service provided by a health facility.
        #i18n_meaning: branch of medicine dealing with infants and children
        value_message('pediatrics', en='Pediatrics',
                      es_419=u'Pediatr\xeda', fr=u'P\xe9diatrie'),
        #i18n: Service provided by a health facility.
        #i18n: care given after surgery until patient is discharged
        value_message('postoperative_care', en='Postoperative care',
                      es_419=u'Cuidados postoperatorios',
                      fr=u'Soins postop\xe9ratoires'),
        #i18n: services provided by a health facility
        #i18n_meaning: Obstetrics deals with childbirth and care of the mother.
        #i18n_meaning: Gynecology deals with diseases and hygiene of women
        value_message('obstetrics_gynecology',
                      en='Obstetrics and gynecology',
                      es_419=u'Obstetricia y ginecolog\xeda',
                      fr=u'Obst\xe9trique et gyn\xe9cologie'),
        #i18n: Service provided by a health facility.
        value_message('dialysis', en='Dialysis', es_419=u'Di\xe1lisis',
                      fr='Dialyse'),
        #i18n: Service provided by a health facility.
        value_message('lab', en='Lab', es_419='Laboratorio', fr='Laboratoire'),
        #i18n: Service provided by a health facility.
        value_message('x_ray', en='X-ray', es_419='Rayos X', fr='Rayon X'),
        #i18n: Service provided by a health facility.
        value_message('ct_scan', en='CT scan', es_419=u'Tomograf\xeda computada',
                      fr='CT scan'),
        #i18n: Service provided by a health facility.
        value_message('blood_bank', en='Blood bank', es_419='Banco de sangre',
                      fr='Banque du sang'),
        #i18n: Service provided by a health facility.
        value_message('corpse_removal', en='Corpse removal',
                      es_419=u'Retiro de cad\xe1ver',
                      fr=u'Enl\xe8vement des cadavres'),
    ]

    db.put(attributes)
    db.put(hospital)
    db.put(messages)

def setup_new_version(country_code='ht', title='Haiti'):
    version = make_version(country_code, title)
    setup_version(version)
    return version
