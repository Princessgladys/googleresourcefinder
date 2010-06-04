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
    author = db.UserProperty() # who created this facility
    # additional properties for the current value of each attribute
    # (named by Attribute's key_name).  This denormalization is for read speed.
    # Consider an attribute named 'foo'. We will store 6 values here:
    # foo__                various, the attribute value
    # foo__observed           db.DateTimeProperty, observation timestamp when
    #                                              the value was valid
    # foo__author             db.UserProperty, the user who provided the change
    # foo__author_nickname    db.StringProperty, source of the change
    # foo__author_affiliation db.StringProperty, affiliation of the source
    # foo__comment            db.StringProperty, a comment about the change
    # These properties will exist with the following invariants:
    # 1. If facility.foo__ is not present, that means attribute "foo" has never
    # existed on this facility at any point in the past.
    # 2. If facility.foo__ is None, that means some user actually set the
    # attribute to "(unspecified)".
    # 3. All six fields are always written together at the same time, and
    # are never removed.  (Hence either all are present or none are present.)

    @staticmethod
    def get_stored_name(attribute_name):
        return '%s__' % attribute_name

    def has_value(self, attribute_name):
        """Returns the value of the Attribute with the given key_name,
           or default if it does not exist."""
        return hasattr(self, '%s__' % attribute_name)

    def get_value(self, attribute_name, default=None):
        """Returns the value of the Attribute with the given key_name,
           or default if it does not exist."""
        return getattr(self, '%s__' % attribute_name, default)

    def get_observed(self, attribute_name, default=None):
        """Returns the timestamp when the Attribute with the given key_name
           was valid, or default if it does not exist."""
        return getattr(self, '%s__observed' % attribute_name, default)

    def get_author(self, attribute_name, default=None):
        """Returns the author of the Attribute value with the given key_name,
           or default if it does not exist."""
        return getattr(self, '%s__author' % attribute_name, default)

    def get_author_nickname(self, attribute_name, default=None):
        """Returns the author nickname of the Attribute value with the given
           key_name, or default if it does not exist."""
        return getattr(self, '%s__author_nickname' % attribute_name, default)

    def get_author_affiliation(self, attribute_name, default=None):
        """Returns the affiliation of the author of the Attribute value
           with the given key_name, or default if it does not exist."""
        return getattr(self, '%s__author_affiliation' % attribute_name, default)

    def get_comment(self, attribute_name, default=None):
        """Returns the author's comment about the Attribute value with the
           given key_name, or default if it does not exist."""
        return getattr(self, '%s__comment' % attribute_name, default)

    def set_attribute(self, name, value, observed, author, author_nickname,
                      author_affiliation, comment):
        """Sets the value for the Attribute with the given key_name."""
        setattr(self, '%s__' % name, value_or_none(value))
        setattr(self, '%s__observed' % name, value_or_none(observed))
        setattr(self, '%s__author' % name, value_or_none(author))
        setattr(self, '%s__author_nickname' % name,
                value_or_none(author_nickname))
        setattr(self, '%s__author_affiliation' % name,
                value_or_none(author_affiliation))
        setattr(self, '%s__comment' % name, value_or_none(comment))

class MinimalFacility(db.Expando):
    """Minimal version of Facility that loads fast from the datastore.
    Parent: Facility. Wouldn't be necessary if we could select columns
    from the datastore."""
    type = db.StringProperty(required=True)  # key_name of a FacilityType
    # properties for the current value of ONLY the most critically important
    # attributes of Facility (named by Attribute's key_name).
    # An attribute named foo will be stored as 'foo__' to match Facility.

    @staticmethod
    def get_stored_name(attribute_name):
        return '%s__' % attribute_name

    def has_value(self, attribute_name):
        """Returns the value of the Attribute with the given key_name,
           or default if it does not exist."""
        return hasattr(self, '%s__' % attribute_name)

    def get_value(self, attribute_name, default=None):
        """Returns the value of the Attribute with the given key_name,
           or default if it does not exist."""
        return getattr(self, '%s__' % attribute_name, default)

    def set_attribute(self, name, value):
        """Sets the value for the Attribute with the given key_name."""
        setattr(self, '%s__' % name, value_or_none(value))

class FacilityType(db.Model):
    """A type of Facility, e.g. hospital, warehouse, charity, camp.
    Top-level entity, has no parent.
    Key name: an identifier used as the value of Facility.type."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    attribute_names = db.StringListProperty()  # key_names of Attribute entities
    minimal_attribute_names = db.StringListProperty() # key_names of Attribute
                                                      # entities for
                                                      # MinimalFacility

class Attribute(db.Model):
    """An attribute of a facility, e.g. services available, # of
    patients. Top-level entity, has no parent.  Key name: name of a property
    in a Report,and also the name of the Message providing the
    UI-displayable attribute name."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    type = db.StringProperty(required=True, choices=[
        'str',     # value is a single-line string (Python unicode)
        'text',    # value is a string, shown as long text (Python unicode)
        'contact', # value is a 3-line string (name, phone, e-mail address)
        'date',    # value is a date (Python datetime with time 00:00:00)
        'int',     # value is an integer (64-bit long)
        'float',   # value is a float (Python float, i.e. double)
        'bool',    # value is a boolean
        'choice',  # value is a string (one of the elements in 'values')
        'multi',   # value is a list of strings (which are elements of 'values')
        'geopt',   # value is a db.GeoPt with latitude and longitude
    ])
    edit_role = db.StringProperty() # What Authorization role can edit?
    values = db.StringListProperty()  # allowed value names for choice or multi

class Report(db.Expando):
    """A report on the attributes and resources of a Facility.
    Parent: Facility. A Report may represent a partial update of the
    attributes of the facility."""
    arrived = db.DateTimeProperty(auto_now_add=True) # date we received report
    source = db.StringProperty() # a URL, the source of the report
    author = db.UserProperty() # author of the report
    observed = db.DateTimeProperty()  # date that report contents were valid
    # additional properties for each Attribute (named by Attribute's key_name)
    # Consider an attribute named 'foo'. We will store 2 values here:
    # foo__          various, the attribute value
    # foo__comment   db.StringProperty, a comment from user making the change
    # These properties will exist with the following invariants:
    # 1. If report.foo__ is not present, that means attribute "foo" should
    # not change its value from the previous report.
    # 2. If report.foo__ is None, that means some user actually set the
    # attribute to "(unspecified)".
    # 3. Both fields are always written together at the same time, and
    # are never removed.  (Hence either all are present or none are present.)

    def get_value(self, attribute_name, default=None):
        """Returns the value of the Attribute with the given key_name,
           or default if it does not exist."""
        return getattr(self, '%s__' % attribute_name, default)

    def get_comment(self, attribute_name, default=None):
        """Returns the author's comment about the Attribute value with the
           given key_name, or default if it does not exist."""
        return getattr(self, '%s__comment' % attribute_name, default)

    def set_attribute(self, name, value, comment):
        """Sets the value for the Attribute with the given key_name."""
        setattr(self, '%s__' % name, value_or_none(value))
        setattr(self, '%s__comment' % name, value_or_none(comment))

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
    
class Alert(db.Model):
    """A subscription by a user to receive notification when details for a
    facility change. Top-level entity, has no parent."""
    user_email = db.StringProperty(required=True) # user to alert
    locale = db.StringProperty(required=True) # user locale
    facility_keys = db.StringListProperty(required=True) # key of facility
    last_sent = db.DateTimeProperty(required=True, auto_now_add=True)
    # time of previous update
    frequencies = db.StringListProperty(required=True) # frequency at which
                                                       # to send updates

def value_or_none(value):
    """Converts any false value other than 0 or 0.0 to None."""
    if value or value == 0:
        return value
    return None
