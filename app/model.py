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

class Facility(db.Expando):
    """A Facility whose attributes are tracked. Top-level entity, has no parent.
    Key name: government or internationally established facility ID."""
    timestamp = db.DateTimeProperty(auto_now_add=True) # creation time
    type = db.StringProperty(required=True)  # key_name of a FacilityType
    user = db.UserProperty() # who created this facility
    # additional properties for the current value of each attribute
    # (named by Attribute's key_name).  This denormalization is for read speed.
    # Consider an attribute named 'foo'. We will store 6 values here:
    # foo              various, the attribute value
    # foo__timestamp   db.DateTimeProperty, observation timestamp when the
    #                                       value was valid
    # foo__user        db.UserProperty, the user who changed the value
    # foo__nickname    db.StringProperty, nickname of the user
    # foo__affiliation db.StringProperty, affiliation of the user
    # foo__comment     db.StringProperty, a comment left by the user making the
    #                                     change

class FacilityType(db.Model):
    """A type of Facility, e.g. hospital, warehouse, charity, camp.
    Top-level entity, has no parent.
    Key name: an identifier used as the value of Facility.type."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    attributes = db.ListProperty(db.Key)  # keys of Attribute entities

class Attribute(db.Model):
    """An attribute of a facility or resource, e.g. services available, # of
    patients. Top-level entity, has no parent.  Key name: name of a property
    in a FacilityReport,and also the name of the Message providing the
    UI-displayable attribute name."""
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
        'multi',  # value is a list of strings (which are elements of 'values')
        'geopt', # value is a db.GeoPt with latitude and longitude
    ])
    edit_role = db.StringProperty() # What Authorization role can edit?
    values = db.StringListProperty()  # allowed value names for choice or multi

class FacilityReport(db.Expando):
    """A report on the attributes and resources of a Facility.
    Parent: Facility."""
    arrival_timestamp = db.DateTimeProperty(auto_now_add=True) # date we
                                                               # received report
    user = db.UserProperty()
    observation_timestamp = db.DateTimeProperty()  # date that report contents
                                                   # were valid
    # additional properties for each Attribute (named by Attribute's key_name)
    # Consider an attribute named 'foo'. We will store 2 values here:
    # foo           various, the attribute value
    # foo__comment   db.StringProperty, a comment from user making the change

class Message(db.Expando):
    """Internationalized strings for value identifiers.  Top-level entity,
    has no parent."""
    namespace = db.StringProperty(required=True, choices=[
      'english',  # name is an English string
      'attribute_name',  # name is an Attribute's key_name
      'attribute_value', # name is a value name in a choice or multi attribute
      'facility_type' # name is a FacilityType's key name
    ])
    name = db.StringProperty()
    # additional properties for each language (named by language code)

class Dump(db.Model):
    """A record of the data received from a data source in its native format,
    before it was converted and loaded into the datastore.  Top-level entity,
    has no parent."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    base = db.SelfReference()  # if present, this dump is a clone of base
    source = db.StringProperty()  # URL identifying the source
    data = db.BlobProperty()  # received raw data
