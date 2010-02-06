#!/usr/bin/python2.5

from model import *
import re
import scrape
import unicodedata

BR_RE = re.compile(r'<br */?>')

def make_key(text):
    text = re.sub(r'[ -]+', '_', text.strip())
    decomposed = unicodedata.normalize('NFD', text)
    return ''.join(ch for ch in decomposed if re.match(r'\w', ch)).lower()

def get_hospitals(url='http://wiki.openstreetmap.org/wiki/WikiProject_Haiti/Status/Hospitals/OldHospitalReport'):
    doc = scrape.Session().go(url)
    hospitals = []
    division_map = {}
    for row in doc.first('table').all('tr'):
        cells = row.all('td')
        if len(cells) != 7:
            continue
        name = cells[1].text.strip()
        location = cells[2].text.strip()
        try:
            latitude, longitude = map(float, location.split(','))
            location = (latitude, longitude)
        except:
            location = None
        divisions = cells[3].split(BR_RE)
        arrondissement = None
        for division in divisions:
            if ':' in division.text:
                label, value = division.text.split(':', 1)
                if label.strip().lower() == 'state district':
                    arrondissement = value.strip()
        if arrondissement and location:
            division_key = make_key(arrondissement)
            division_map[division_key] = arrondissement
            hospitals.append({
                'name': name,
                'location': location,
                'division': division_key
            })
    return hospitals, division_map

def load_hospitals(hospitals, division_map, cc='ht'):
    country = Country.get_by_key_name(cc)
    version = Version(country)
    supplies = [
        Supply(key_name='doctor', name='Doctors', abbreviation='D'),
        Supply(key_name='bed', name='Beds', abbreviation='B'),
        Supply(key_name='patient', name='Patients', abbreviation='P')
    ]
    db.put(supplies)
    version.supplies = [supply.key() for supply in supplies]
    version.put()

    arrondissement = DivisionType(
        version, key_name='arrondissement',
        singular='arrondissement', plural='arrondissements')
    db.put(arrondissement)
    divisions = {}
    for key in sorted(division_map.keys(), key=lambda d: division_map[d]):
        divisions[key] = Division(
            version, id=key, type=arrondissement, name=division_map[key])
    db.put(divisions.values())

    facilities = {}
    for hospital in hospitals:
        facility = Facility(
            version, id=make_key(hospital['name']),
            name=hospital['name'],
            location=db.GeoPt(*hospital['location']),
            division=divisions[hospital['division']],
            divisions=[divisions[hospital['division']].key()]
        )
        facilities[facility.id] = facility
    db.put(facilities.values())


