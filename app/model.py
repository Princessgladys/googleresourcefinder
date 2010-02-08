# Copyright 2009-2010 by Ka-Ping Yee
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The SMS for Life data model.  All entities and fields are add-only and
are never deleted or overwritten.  To represent modifications to a country's
data, create a new Version under the appropriate Country."""

from google.appengine.ext import db

class Country(db.Model):
    """Root entity for a country.  Key name: ISO 3166 two-letter lowercase
    country code."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    name = db.StringProperty(required=True)  # UI text

class Dump(db.Model):
    """A record of the data received from a data source in its native format,
    before it was converted and loaded into the datastore.  Parent: Country."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    base = db.SelfReference()  # if present, this dump is a clone of base
    source = db.StringProperty()  # URL identifying the source
    data = db.BlobProperty()  # received raw data

class Version(db.Model):
    """The parent entity for a complete snapshot of a single country's data.
    All entities below have a Version as their parent.  All changes to a
    country's data, except for the addition of new Reports, require the
    creation of a new Version.  Parent: Country."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    base = db.SelfReference()  # if present, this version is a clone of base
    dump = db.Reference(Dump)  # dump used to make this snapshot
    dumps = db.ListProperty(db.Key)  # list of dumps (deprecated)

class DivisionType(db.Model):
    """Descriptor for a type of administrative division within a country.
    Usually each DivisionType corresponds to a level of granularity (e.g.
    province, state, zone, region, district, ward).  Parent: Version.
    Key name: an identifier used as the value of Division.type."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    singular = db.StringProperty(required=True)  # UI text, singular form
    plural = db.StringProperty(required=True)  # UI text, plural form

class Division(db.Model):
    """An administrative division within a country.  Parent: Version."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    id = db.StringProperty(required=True)  # government ID
    type = db.StringProperty(required=True)  # key_name of a DivisionType
    superdivision = db.SelfReference(collection_name='subdivisions')
    name = db.StringProperty(required=True)  # UI text
    location = db.GeoPtProperty()  # approximate center, for labelling

class Attribute(db.Model):
    """An attribute of a facility, e.g. services available, number of patients.
    Parent: Version.  Key name: name of a property in a Report."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    name = db.StringProperty(required=True)  # UI text
    abbreviation = db.StringProperty()  # UI text
    type = db.StringProperty(required=True, choices=[
        'str',  # value is a single-line string (Python unicode)
        'text',  # value is a string, shown as long text (Python unicode)
        'int',  # value is an integer (64-bit long)
        'float',  # value is a float (Python float, i.e. double)
        'choice',  # value is a string (one of the elements in 'values')  
        'multi'  # value is a list of strings (which are elements of 'values')
    ])
    values = db.StringListProperty()  # for choice or multi

class FacilityType(db.Model):
    """A type of facility, e.g. hospital, warehouse.  Parent: Version.
    Key name: an identifier used as the value of Facility.type."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    name = db.StringProperty(required=True)  # UI text
    abbreviation = db.StringProperty(required=True)  # UI text
    attributes = db.StringListProperty()  # key_names of Attribute entities

class Facility(db.Model):
    """A facility whose attributes are tracked.  Parent: Version."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    type = db.StringProperty(required=True)  # key_name of a FacilityType
    id = db.StringProperty(required=True)  # government ID
    name = db.StringProperty(required=True)  # UI text
    division = db.Reference(Division)  # lowest-level division assigned
    divisions = db.ListProperty(db.Key)  # all levels of containing divisions
    location = db.GeoPtProperty()  # for plotting the facility on a map

class Report(db.Expando):
    """A report on the attributes of a facility.  Parent: Version."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    facility = db.Reference(Facility)
    date = db.DateProperty()  # date that report contents were valid
    # additional properties for each Attribute (named by Attribute's key_name)
