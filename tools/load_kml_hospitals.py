from model import *
from setup import *
import datetime
import datetime
import kml
import re
import unicodedata
import utils

BEDS_RE = re.compile(r'(\d+) *[bB]eds')

def load_hospitals(version, records):
    """Loads a list of hospital records into the given version."""
    arrondissement = DivisionType(
        version, key_name='arrondissement',
        singular='arrondissement', plural='arrondissements')
    db.put(arrondissement)
    unknown = Division(
        version, key_name='unknown', type='arrondissement', title='Unknown')
    db.put(unknown)

    facilities = []
    reports = []
    for record in records:
        location = record['location']
        facility_name = utils.make_name(record['title'])
        facilities.append(Facility(
            version,
            key_name=facility_name,
            type='hospital',
            title=record['title'],
            location=db.GeoPt(location[1], location[0]),
            division_name='unknown',
            division_names=['unknown']
        ))
        if record.get('comment', ''):
            comment = record['comment']
            report = Report(
                version,
                facility_name=facility_name,
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
