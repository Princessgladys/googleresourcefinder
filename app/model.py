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

"""The Resource Mapper data model.  All entities and fields are add-only and
are never deleted or overwritten.  To represent modifications to a country's
data, create a new Version under the appropriate Country.  To represent
modifications to a facility's attributes, add a new Report for that Facility.

This project uses the following naming conventions in variables and properties:

    "key":
        An App Engine entity key.

    "name":
        A unique identifier for an entity, used as the entity's key_name.
        Fields ending in "_name" contain the key_names of other entities.

        Names should be C-style identifiers (thus usable as HTML element IDs,
        form element names, and CSS classes) and are usually not displayed in
        the UI directly.  For each name, there should be a corresponding
        Message entity that provides the localized text.

    "title":
        A non-localizable, UI-displayable text label for an entity.
"""

from google.appengine.ext import db

class Country(db.Model):
    """Root entity for a country.  Key name: ISO 3166 two-letter lowercase
    country code."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    title = db.StringProperty(required=True)  # UI text

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
    """An administrative division within a country.  Parent: Version.
    Key name: government or internationally established division ID."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    type = db.StringProperty(required=True)  # key_name of a DivisionType
    superdivision_name = db.StringProperty()  # a Division's key_name
    title = db.StringProperty(required=True)  # UI text
    location = db.GeoPtProperty()  # approximate center, for labelling

class Attribute(db.Model):
    """An attribute of a facility, e.g. services available, number of patients.
    Parent: Version.  Key name: name of a property in a Report, and also the
    name of the Message providing the UI-displayable attribute name."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    type = db.StringProperty(required=True, choices=[
        'str',  # value is a single-line string (Python unicode)
        'text',  # value is a string, shown as long text (Python unicode)
        'contact',  # value is a 3-line string (name, phone, e-mail address)
        'date',  # value is a date (Python datetime with time 00:00:00)
        'int',  # value is an integer (64-bit long)
        'float',  # value is a float (Python float, i.e. double)
        'bool',  # value is a boolean
        'choice',  # value is a string (one of the elements in 'values')  
        'multi'  # value is a list of strings (which are elements of 'values')
    ])
    values = db.StringListProperty()  # allowed value names for choice or multi

class FacilityType(db.Model):
    """A type of facility, e.g. hospital, warehouse.  Parent: Version.
    Key name: an identifier used as the value of Facility.type."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    attribute_names = db.StringListProperty()  # key_names of Attribute entities

class Facility(db.Model):
    """A facility whose attributes are tracked.  Parent: Version.
    Key name: government or internationally established facility ID."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    type = db.StringProperty(required=True)  # key_name of a FacilityType
    title = db.StringProperty(required=True)  # UI text
    division_name = db.StringProperty(required=True)  # a Division's key_name
    division_names = db.StringListProperty()  # all levels of Divisions
    location = db.GeoPtProperty()  # for plotting the facility on a map

class Report(db.Expando):
    """A report on the attributes of a facility.  Parent: Version."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    facility_name = db.StringProperty()  # a Facility's key_name
    date = db.DateProperty()  # date that report contents were valid
    user = db.UserProperty()
    # additional properties for each Attribute (named by Attribute's key_name)

class Message(db.Expando):
    """Internationalized strings for value identifiers.  Parent: Version."""
    namespace = db.StringProperty(required=True, choices=[
      'english',  # name is an English string
      'attribute_name',  # name is an Attribute's key_name
      'attribute_value'  # name is a value name in a choice or multi attribute
    ])
    name = db.StringProperty()
    # additional properties for each language (named by language code)
