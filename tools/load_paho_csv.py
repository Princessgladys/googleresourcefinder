from model import *
from setup import *
import csv
import datetime

def load_paho_csv(version, filename):
    """Loads the PAHO master list as a CSV file into the given version."""
    departemen = DivisionType(
        version, key_name='departemen',
        singular='department', plural='departments')
    db.put(departemen)

    divisions = {}
    for dept in ['ARTIBONITE', 'CENTRE', 'GRANDE ANSE', 'NIPPES', 'NORD',
                 'NORD EST', 'NORD OUEST', 'OUEST', 'SUD', 'SUD EST']:
        divisions[dept] = Division(
            version, key_name=dept, type='departemen', title=dept.capitalize())
    db.put(divisions.values())

    facilities = []
    reports = []
    for record in csv.DictReader(open(filename)):
        for key in record:
            record[key] = record[key].decode('utf-8')
        facility_name = 'mspphaiti.org..' + record['PCode']
        try:
            latitude = float(record['X_DDS'])
            longitude = float(record['Y_DDS'])
        except ValueError:
            continue
        facilities.append(Facility(
            version,
            key_name=facility_name,
            type='hospital',
            title=record['Fac_NameFr'].strip() or record['NomInstitu'],
            location=db.GeoPt(latitude, longitude),
            division_name=record['Departemen'].strip()
        ))
        reports.append(Report(
            version,
            facility_name=facility_name,
            date=datetime.date.today(),
            healthc_id=record['HealthC_ID'].strip() or None,
            organization=record['Oorganisat'].strip() or None,
            departemen=record['Departemen'].strip() or None,
            district=record['DistrictNom'].strip() or None,
            commune=record['Commune'].strip() or None,
            address=record['Address'].strip() or None,
            phone=record['Telephone'].strip() or None,
            email=record['email'].strip(),
            type=record['Type'].strip() or None,
            category=record['Categorie'].strip() or None,
            damage=record['Damage'].strip() or None,
            comment=record['OperationalStatus'].strip() or None,
            region_id=record['RegionId'].strip() or None,
            district_id=record['DistrictId'].strip() or None,
            commune_id=record['CommuneId'].strip() or None,
            code_commune=record['CodeCommun'].strip() or None,
            sante_id=record['SanteID'].strip() or None,
        ))

    put_batches(facilities + reports)

def put_batches(entities):
    """Works around annoying limitations of App Engine's datastore."""
    while entities:
        batch, entities = entities[:200], entities[200:]
        db.put(batch)
