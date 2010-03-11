import xmlutils

ATOM_NS = 'http://www.w3.org/2005/Atom'

def write_feed(file, records, uri_prefixes={}):
    """Writes an Atom feed containing the given records to the given file."""
    root = xmlutils.element('{%s}feed' % ATOM_NS, *[
        xmlutils.element('{%s}entry' % ATOM_NS,
            xmlutils.element('{%s}author' % ATOM_NS,
                xmlutils.element('{%s}email' % ATOM_NS, record.author_email)),
            xmlutils.element('{%s}id' % ATOM_NS, record.atom_id),
            xmlutils.element('{%s}title' % ATOM_NS, record.title),
            xmlutils.element('{%s}updated' % ATOM_NS, record.arrival_time),
            xmlutils.fromstring(record.content)
        ) for record in records])
    xmlutils.write(file, root, dict((ATOM_NS, 'atom'), **uri_prefixes))
