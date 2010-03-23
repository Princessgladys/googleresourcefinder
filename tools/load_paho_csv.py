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
        print record
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
            title=record['Fac_NameFr'] or record['NomInstitu'],
            location=db.GeoPt(latitude, longitude),
            division_name=record['Departemen'].strip()
        ))
        reports.append(Report(
            version,
            facility_name=facility_name,
            date=datetime.date.today(),
            organization=record['Oorganisat'],
            departemen=record['Departemen'],
            district=record['DistrictNom'],
            commune=record['Commune'],
            address=record['Address'],
            phone=record['Telephone'],
            email=record['email'],
            type=record['Type'],
            category=record['Categorie'],
            damage=record['Damage'],
            comment=record['OperationalStatus']
        ))
    db.put(facilities)
    db.put(reports)

