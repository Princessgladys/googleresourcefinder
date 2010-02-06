
import datetime

c = Country.get_by_key_name('ht')
v = Version(c)

supplies = [
    Supply(key_name='doctor', name='Doctors', abbreviation='D'),
    Supply(key_name='bed', name='Beds', abbreviation='B'),
    Supply(key_name='patient', name='Patients', abbreviation='P')
]
db.put(supplies)

v.supplies = [supply.key() for supply in supplies]
v.put()

arr = DivisionType(v, key_name='arrondissement', singular='arrondissement', plural='arrondissements')
arr.put()

pap = Division(v, id='portauprince', type=arr, name='Port-au-Prince')
arrs = [
    Division(v, id='arcahaie', type=arr, name='Arcahaie'),
    Division(v, id='croixdesbouquets', type=arr, name='Croix-des-Bouquets'),
    Division(v, id='lagonave', type=arr, name='La Gonave'),
    Division(v, id='leogane', type=arr, name=u'L\u00e9og\u00e2ne'),
    pap
]
db.put(arrs)

cv = Facility(v, id='christianville', name='Christianville Mission',
        division=pap, divisions=[pap.key()],
        location=db.GeoPt(18.5239655, -72.5560404))
blanchard = Facility(v, id='blanchard', name='Blanchard PHC',
        division=pap, divisions=[pap.key()],
        location=db.GeoPt(18.5952691, -72.314784))
choscal = Facility(v, id='choscal', name='Choscal Hospital (MSF)',
        division=pap, divisions=[pap.key()],
        location=db.GeoPt(18.5779178, -72.3368166))
comfort = Facility(v, id='comfort', name='USNS Comfort',
        division=pap, divisions=[pap.key()],
        location=db.GeoPt(18.5541404, -72.3501696))
facs = [cv, blanchard, choscal, comfort]

db.put(facs)

reps = [
    Report(v, facility=blanchard, date=datetime.date(2010, 2, 2),
        doctor=3, bed=11, patient=23),
    Report(v, facility=cv, date=datetime.date(2010, 2, 2),
        doctor=0, bed=5, patient=51),
    Report(v, facility=choscal, date=datetime.date(2010, 2, 2),
        doctor=12, bed=200, patient=207)
]

db.put(reps)
