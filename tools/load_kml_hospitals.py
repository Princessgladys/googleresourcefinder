from model import *
from setup import *
import datetime
import datetime
import kml
import re
import unicodedata

BEDS_RE = re.compile(r'(\d+) *[bB]eds')

def make_key(text):
    text = re.sub(r'[ -]+', '_', text.strip())
    decomposed = unicodedata.normalize('NFD', text)
    return ''.join(ch for ch in decomposed if re.match(r'\w', ch)).lower()

def load_hospitals(version, records):
    """Loads a list of hospital records into the given version."""
    arrondissement = DivisionType(
        version, key_name='arrondissement',
        singular='arrondissement', plural='arrondissements')
    db.put(arrondissement)
    unknown = Division(
        version, id='unknown', type='arrondissement', name='Unknown')
    db.put(unknown)

    facilities = []
    reports = []
    for record in records:
        location = record['location']
        facility_id = make_key(record['name'])
        facilities.append(Facility(
            version,
            type='hospital',
            id=facility_id,
            name=record['name'],
            location=db.GeoPt(location[1], location[0]),
            division_id='unknown',
            division_ids=['unknown']
        ))
        if record.get('comment', ''):
            comment = record['comment']
            report = Report(
                version,
                facility_id=facility_id,
                date=datetime.date.today(),
                comment=db.Text(comment))
            match = BEDS_RE.search(comment)
            if match:
                report.patient_capacity = int(match.group(1))
            reports.append(report)
    db.put(facilities)
    db.put(reports)

def load_kml_file(version, filename):
    load_hospitals(version, kml.parse_file(open(filename)))
