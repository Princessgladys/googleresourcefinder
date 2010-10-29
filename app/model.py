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
modifications to a subject's attributes, add a new Report for that Subject.

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

import datetime

from google.appengine.ext import db

MAX_DATE = datetime.datetime(datetime.MAXYEAR, 1, 1)

class Subdomain(db.Model):
    """A separate grouping of Subjects and SubjectTypes.  Top-level entity,
    with no parent.  Key name: unique subdomain name.  In the UI, each
    subdomain appears to be an independent instance of the application.  The
    permitted actions of Accounts and key_names of Subjects and SubjectTypes
    are namespaced by prefixing them with the subdomain name and a colon.  All
    other entities are shared across all subdomains."""
    pass  # No properties for now; only the key_name is significant.


def filter_by_prefix(query, key_name_prefix, root_kind=None):
    """Filters a query for key_names that have the given prefix.  If root_kind
    is specified, filters the query for children of any entities that are of
    that kind with the given prefix; otherwise, the results are assumed to be
    top-level entities of the kind being queried."""
    root_kind = root_kind or query._model_class.__name__
    min_key = db.Key.from_path(root_kind, key_name_prefix)
    max_key = db.Key.from_path(root_kind, key_name_prefix + u'\uffff')
    return query.filter('__key__ >=', min_key).filter('__key__ <=', max_key)

def value_or_none(value):
    """Converts any false value other than 0 or 0.0 to None."""
    if value or value == 0:
        return value
    return None

def get_name(name_or_entity):
    """If given an entity, returns its name (without subdomain); if given a
    string, returns the string itself."""
    if isinstance(name_or_entity, (Subject, SubjectType)):
        return name_or_entity.name
    elif isinstance(name_or_entity, db.Model):
        return name_or_entity.key().name()
    else:
        return name_or_entity


class SubdomainMixin:
    """A mix-in class providing common methods for entities whose key names
    begin with a subdomain and a colon."""
    @classmethod
    def get(cls, subdomain, name):
        """Gets an entity by its subdomain and name.  This method overrides
        the default get() method, which takes a db.Key."""
        return cls.get_by_key_name(subdomain + ':' + name)

    @classmethod
    def all_in_subdomain(cls, subdomain):
        """Gets a query for all entities with the given subdomain."""
        root_kind = getattr(cls, 'ROOT_KIND', None)
        return filter_by_prefix(cls.all(), subdomain + ':', root_kind)

    def get_subdomain(self):
        """Gets the entity's subdomain."""
        return self.key().name().split(':', 1)[0]
    subdomain = property(get_subdomain)

    def get_name(self):
        """Gets the entity's name (without the subdomain)."""
        return self.key().name().split(':', 1)[1]
    name = property(get_name)


class Subject(SubdomainMixin, db.Expando):
    """A thing whose attributes are tracked by this application.  Top-level
    entity, has no parent.  Key name: subdomain + ':' + subject name.
    A subject name is a globally unique ID that starts with a domain name and
    a slash.  In the 'haiti' subdomain, Subjects are health facilities with a
    government or internationally established health facility ID."""
    timestamp = db.DateTimeProperty(auto_now_add=True)  # creation time
    type = db.StringProperty(required=True)  # key_name of a SubjectType,
                                             # without the subdomain prefix
    author = db.UserProperty()  # who created this Subject
    # additional properties for the current value of each attribute
    # (named by Attribute's key_name).  This denormalization is for read speed.
    # Consider an attribute named 'foo'. We will store 6 values here:
    # foo__                    various types, the attribute value
    # foo__observed            datetime, timestamp when the value was valid
    # foo__author              users.User, the user who provided the change
    # foo__author_nickname     string, source of the change
    # foo__author_affiliation  string, affiliation of the source
    # foo__comment             string, a comment about the change
    # These properties will exist with the following invariants:
    # 1. If subject.foo__ is not present, that means attribute "foo" has never
    #    existed on this subject at any point in the past.
    # 2. If subject.foo__ is None, that means some user actually set the
    #    attribute to "(unspecified)".
    # 3. All six fields are always written together at the same time, and are
    #    never removed.  (Hence either all are present or none are present.)

    @staticmethod
    def create(subdomain, subject_type_or_type_name, subject_name, author):
        """Creates a Subject with a given subdomain, type, name, and author."""
        return Subject(key_name='%s:%s' % (subdomain, subject_name),
                       type=get_name(subject_type_or_type_name), author=author)

    @staticmethod
    def generate_name(host, subject_type_or_type_name):
        """Makes a new unique subject_name for an original subject (originally
        created in this repository, not cloned from an external repository)."""
        id = UniqueId.create_id()
        return '%s/%s.%d' % (host, get_name(subject_type_or_type_name), id)

    @staticmethod
    def get_stored_name(attribute_name):
        return '%s__' % attribute_name

    @classmethod
    def delete_complete(cls, subject): 
        if subject:
            minimal_subject = MinimalSubject.get_by_subject(subject)
            db.delete([subject, minimal_subject])

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


class MinimalSubject(SubdomainMixin, db.Expando):
    """Minimal version of Subject that loads fast from the datastore and
    contains just the information needed to populate the initial list and map.
    Parent: Subject.  Key name: same as its parent Subject.  Wouldn't be
    necessary if we could select columns from the datastore."""
    type = db.StringProperty(required=True)  # key_name of a SubjectType,
                                             # without the subdomain prefix
    # More properties for the current values of ONLY the most critically
    # important attributes of Subject (named by Attribute's key_name).
    # An attribute named foo will be stored as 'foo__' to match Subject.

    ROOT_KIND = 'Subject'  # filter_by_prefix uses this to filter keys properly

    @staticmethod
    def create(subject):
        return MinimalSubject(
            subject, key_name=subject.key().name(), type=subject.type)

    @staticmethod
    def get_by_subject(subject):
        """Gets the MinimalSubject entity for the given Subject."""
        return MinimalSubject.all().ancestor(subject).get()

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


class UniqueId(db.Model):
    """This entity is used just to generate unique numeric IDs."""
    @staticmethod
    def create_id():
        """Gets a numeric ID that is guaranteed to be different from any ID
        previously returned by this static method."""
        unique_id = UniqueId()
        unique_id.put()
        return unique_id.key().id()


class SubjectType(SubdomainMixin, db.Model):
    """A type of Subject, e.g. hospital, warehouse, charity, camp.  Top-level
    entity, has no parent.  Key name: subdomain + ':' + type name.  A type name
    is an identifier used as the value of Subject.type."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    attribute_names = db.StringListProperty()  # key_names of Attribute entities
    minimal_attribute_names = db.StringListProperty()  # key_names of
        # Attribute entities whose values should be copied into MinimalSubject

    @staticmethod
    def create(subdomain, subject_type_name):
        return SubjectType(key_name=subdomain + ':' + subject_type_name)


class Attribute(db.Model):
    """An attribute of a subject, e.g. services available, # of
    patients. Top-level entity, has no parent.  Key name: name of a property
    in a Report, and also the name of the Message providing the
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
    edit_action = db.StringProperty() # What Account action can edit?
    values = db.StringListProperty()  # allowed value names for choice or multi

class Report(db.Expando):
    """A report on the attributes and resources of a Subject.
    Parent: Subject.  A Report may represent a partial update of the
    attributes of the subject."""
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

class Account(db.Model):
    """User account. Top-level entity, has no parent.  Users without Account
    entities can use the application; for such users, their permissions are
    determined by the special Account object with key_name='default'.  Users
    get their own Account entities when editing a Subject, requesting
    permissions, being granted permissions, or subscribing to alerts."""
    timestamp = db.DateTimeProperty(auto_now_add=True)  # creation time
    description = db.StringProperty()  # full name or description
    email = db.StringProperty()  # e-mail address of the account
    user_id = db.StringProperty()  # users.User.id() of the account
    nickname = db.StringProperty()  # nickname for display in the UI; may
                                    # differ from users.User.nickname()
    affiliation = db.StringProperty()  # company or organization, etc.
    token = db.StringProperty()  # secret token for looking up an Account with
                                 # no e-mail address (so we can have Account
                                 # entities for nonexistent Google Accounts)
    actions = db.StringListProperty()  # actions allowed for this user (items
                                       # have the form subdomain + ':' + verb;
                                       # '*' is a wildcard subdomain or verb)
    requested_actions = db.StringListProperty()  # permissions requested but
                                                 # not yet granted
    locale = db.StringProperty() # user chosen locale
    # default frequency for updates
    default_frequency = db.StringProperty(default='instant')
    # preferred format to receive e-mail in
    email_format = db.StringProperty(choices=['plain', 'html'], default='plain')

    # For explanation of default settings for the next alert times, see
    # mail_alerts.py's send_digests function.
    # next time to send a daily update
    next_daily_alert = db.DateTimeProperty(default=MAX_DATE)
    # next time to send a weekly update to the user
    next_weekly_alert = db.DateTimeProperty(default=MAX_DATE)
    # next time to send a monthly update to the user
    next_monthly_alert = db.DateTimeProperty(default=MAX_DATE)

class Message(db.Expando):
    """Internationalized strings for value identifiers.  Top-level entity,
    has no parent."""
    # Formerly namespace, renamed to work around bug in GAE 1.3.5 (b/2811890);
    # Can change back after 1.3.6, which contains the fix
    ns = db.StringProperty(required=True, choices=[
      'english',  # name is an English string
      'attribute_name',  # name is an Attribute's key_name
      'attribute_value', # name is a value name in a choice or multi attribute
      'subject_type' # name is a SubjectType's key_name (including subdomain)
    ])
    name = db.StringProperty()
    # additional properties for each language (named by locale code)

class Dump(db.Model):
    """A record of the data received from a data source in its native format,
    before it was converted and loaded into the datastore.  Top-level entity,
    has no parent."""
    timestamp = db.DateTimeProperty(auto_now_add=True)
    base = db.SelfReference()  # if present, this dump is a clone of base
    source = db.StringProperty()  # URL identifying the source
    data = db.BlobProperty()  # received raw data

# TODO(kpy): Clean up the inconsistent use of the term "subject_name".
# In Subscription, subject_name is the entire Subject key including the
# subdomain; elsewhere it is just the part after the subdomain.
class Subscription(db.Model):
    """A subscription by a user to receive notification when details for a
    facility change. Top-level entity, has no parent.
    Key name: follows the format subject_name:user_email"""
    user_email = db.StringProperty(required=True) # user to alert
    subject_name = db.StringProperty(required=True) # key_name of subject
    frequency = db.StringProperty(required=True, choices=[
        'instant', # send an alert whenever the facility is updated
        'daily', # send during a daily digest e-mail
        'weekly', # send during a weekly digest e-mail
        'monthly' # send during a monthly digest e-mail on the 1st of the month
    ]) # frequency of updates for this subject
    
    @staticmethod
    def get(subject_name, user_email):
        """Gets a Subscription entity by its subject_name and e-mail."""
        return Subscription.get_by_key_name(subject_name + ':' + user_email)
    
    @staticmethod
    def get_by_subject(subject_name):
        """Gets a query for all PendingAlert with the given subject name."""
        return filter_by_prefix(Subscription.all(), subject_name + ':')

class PendingAlert(MinimalSubject):
    """A pending notification for a user; waiting to be sent on a daily/weekly/
    monthly basis, pending the frequency of the particular alert. Top-level
    entity, has no parent.
    Key name: follows the format frequency:user_email:subject_name"""
    user_email = db.StringProperty(required=True) # user to alert
    subject_name = db.StringProperty(required=True) # key_name of subject
    timestamp = db.DateTimeProperty() # creation time of the pending alert
    frequency = db.StringProperty(required=True, choices=[
        'instant', # send an alert whenever the subject is updated
        'daily', # send during a daily digest e-mail
        'weekly', # send during a weekly digest e-mail
        'monthly' # send during a monthly digest e-mail on the 1st of the month
    ]) # frequency of updates for this subject

    @staticmethod
    def get(frequency, user_email, subject_name):
        """Gets a PendingAlert entity by its frequency, e-mail, and 
        subject name."""
        return PendingAlert.get_by_key_name(frequency + ':' + user_email +
                                            ':' + subject_name)
    
    @staticmethod
    def get_by_frequency(frequency, user_email):
        """Gets a query for all PendingAlert with the given frequency and
        associated user e-mail."""
        return filter_by_prefix(PendingAlert.all(), frequency + ':' +
                                user_email + ':')

class MailUpdateText(db.Expando):
    """A map from attribute names and values to alternate values accepted
    in the mail editing system. They are strings that users can type into
    e-mails to refer to attribute names or values. Key name: follows the
    format namespace:name.
    
    This table should at all times contain the following special cases for
    general-use attribute values: true, false, and none. Accepted values are:
        true: ['Yes', 'y', 'true']
        false: ['No', 'n', 'false']
        none: ['*none']
    by default. In total, the number of entities in the table should be equal
    to the number of attribute entities, plus the unique values across all
    multi and choice attributes, plus the 3 general values defined above."""
    # name is an attribute name or attribute value; see below
    name = db.StringProperty(required=True)
    ns = db.StringProperty(required=True, choices=[
        'attribute_name', # name is an attribute's key_name
        'attribute_value' # name is a value name in a choice or multi attribute
    ])
    # Expando values should be initialized on a per-language basis as a list
    # of accepted input strings for this particular map, in that language.
    # Use the same naming format as in the Message table [en for English,
    # fr for French, etc.]. The first value in each list should match the
    # corresponding Message, to make mail editing behavior resilient to
    # changes in translations. For comparison purposes, each item in the
    # list will be treated as case-insensitive. Spaces should be used in
    # favor of underscores.

    @classmethod
    def get(cls, ns, name):
        """Gets an entity by its namespace and name."""
        key_name = '%s:%s' % (ns, name)
        return cls.get_by_key_name(key_name)

    @classmethod
    def create(cls, ns, name, **kwargs):
        """Creates an entity with the specified namespace and name."""
        key_name = '%s:%s' % (ns, name)
        return cls(key_name=key_name, ns=ns, name=name, **kwargs)

    @classmethod
    def all_in_namespace(cls, ns):
        """Gets a query for all entities with the given namespace."""
        return filter_by_prefix(cls.all(), ns + ':')
