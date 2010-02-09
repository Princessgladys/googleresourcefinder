The application won't work unless you populate it with a little data.

To get started:

    hg clone https://resourcemapper.googlecode.com/hg/ resourcemapper 


Then start the server:

    dev_appserver.py app

You ned to create a user to user the app, even locally
In the admin console:
Authorization(email='test@example.com', description='Test').put()

Now connect to the server like this:

    tools/console.py resourcemapper localhost:8080

Log in with any username and password.

At the Python prompt:

    Country(key_name='ht', name='Haiti').put()
    execfile('tools/setup.py')

Dump of a conversation with Ka-Ping who created the app, about the data model:
----
The entity hierarchy in the datastore is
Country -> Version -> everything

Ka-Ping: good!
I noticed that there is a list of hospitals at
http://wiki.openstreetmap.org/wiki/WikiProject_Haiti/Status/Hospital/Report		

Ka-Ping: Division is intended to represent a division at any level (e.g. department, arrondissement, city); divisions can be arranged in a hierarchy.  The facility is attached to the lowest-level division containing it.

Ka-Ping: The five arrondissements that are currently in setup.py are the subdivisions of the Ouest Department, which is the department containing Port-au-Prince.
I don't know how many of the other departments will be relevant to us.

Ka-Ping: The association between reports and supplies is a shortcut (a bit of a hack): the reports are expandable models, with property names that match the key_names of the supplies.
Ka-Ping: I did this so I wouldn't have to issue datastore queries on each supply.
Ka-Ping: The major weakness of the design is that it currently assumes that ALL the data can be dumped into JSON and delivered with the map.  (Then JS can slice & dice it on the client side.)
There is no AJAX querying of data.  The client does any data filtering in memory.
This is fine (and fast) if the data is small enough.  It might become a problem if we get to thousands of facilities.
me: yes
so you query the whole db everytime?
Ka-Ping: Yes.  Well, the DB stores versions, so we query an entire version every time.
This ought to be optimized of course.

Ka-Ping: The SMS for Life app was designed to work with a separate datastore.
The reports come in by SMS, so the phone company has their own database of stock level reports.
Periodically, the load.py task pulls in a copy of the phone company's database into the local datastore.
Each time that happens, it creates a new Version, and all the entities are stored under that Version.  All the old Versions are kept around just in case.
The entity hierarchy in the datastore is
Country -> Version -> everything else
