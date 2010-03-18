"""XML parsing and serialization framework.

This framework helps you parse XML documents, which may have many levels
of nested elements, into flatter Python structures.  To use it, define
subclasses of Converter.  Each Converter describes how to convert a subtree
of an XML document to or from a Python value.  The type and structure of
the Python value is up to the Converter.
"""

import copy
try:
    import xml.etree.cElementTree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree

def qualify(ns, name):
    """Makes a namespace-qualified name."""
    return '{%s}%s' % (ns, name)

def element(tag, *attributes_and_text_and_children):
    """Creates an Element with the given tag and contents.  The arguments may
    include dictionaries of attributes, child elements, lists of child elements,
    and text content for the element."""
    element = ElementTree.Element(tag)
    for arg in attributes_and_text_and_children:
        if isinstance(arg, dict):  # attributes
            for key, value in attributes:
                element.set(key, value)
        elif not isinstance(arg, list):
            arg = [arg]
        for child in arg:  # text or child elements
            if isinstance(child, basestring):
                element.text = (element.text or '') + child
            else:
                element.append(child)
    return element

def indent(element, level=0):
    """Adds indentation to an element subtree."""
    indentation = '\n' + level*'  '
    if len(element):
        if not element.text or not element.text.strip():
            element.text = indentation + '  '
        if not element.tail or not element.tail.strip():
            element.tail = indentation
        for child in element:
            indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indentation
    elif level:
        if not element.tail or not element.tail.strip():
            element.tail = indentation

def fix_name(name, uri_prefixes):
    """Converts a Clark qualified name into a name with a namespace prefix."""
    if name[0] == '{':
        uri, tag = name[1:].split('}')
        if uri in uri_prefixes:
            return uri_prefixes[uri] + ':' + tag
    return name

def set_prefixes(root, uri_prefixes):
    """Replaces Clark qualified element names with specific given prefixes."""
    for uri, prefix in uri_prefixes.items():
        root.set('xmlns:' + prefix, uri)

    for element in root.getiterator():
        element.tag = fix_name(element.tag, uri_prefixes)

def parse(string):
    """Parses XML from a string."""
    return ElementTree.fromstring(string)

def serialize(root):
    """Serializes XML to a string."""
    return ElementTree.tostring(root)

def read(file):
    """Reads an XML tree from a file."""
    return ElementTree.parse(file)

def write(file, root, uri_prefixes={}, pretty_print=True):
    """Writes an XML tree to a file, using the given map of namespace URIs to
    prefixes, and adding nice indentation."""
    root_copy = copy.deepcopy(root)
    set_prefixes(root_copy, uri_prefixes)
    if pretty_print:
        indent(root_copy)
    # Setting encoding to 'UTF-8' makes ElementTree write the XML declaration
    # because 'UTF-8' differs from ElementTree's default, 'utf-8'.  According
    # to the XML 1.0 specification, 'UTF-8' is also the recommended spelling.
    ElementTree.ElementTree(root_copy).write(file, encoding='UTF-8')


# ==== Record types ========================================================

class Struct(dict):
    """A dictionary whose values can also be accessed as attributes."""
    def __init__(self, **kwargs):
        self.update(kwargs)

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


# ==== Converter base class ================================================

def Singleton(name, bases, dict):
    """Use this metaclass on Converter subclasses to create a instance."""
    return type(name, bases, dict)()


class Converter(object):
    """Abstract base class for subtree converters, which convert subtrees
    of XML to/from Python values."""

    # Concrete subclasses should declare their XML namespace URL.
    NS = None

    # Concrete subclasses should implement these two methods.
    def from_element(self, element):
        """Converts an Element of this kind to a Python value."""
        raise NotImplementedError

    def to_element(self, tag, value):
        """Converts a Python value of this kind to an Element."""
        raise NotImplementedError

    # The rest are utility methods, which should not need to be overridden.
    def qualify(self, name):
        return qualify(self.NS, name)

    def struct_from_children(self, element, *names):
        """Converts several immediate child Elements of the given Element,
        all of this kind, to a Struct containing their Python values."""
        record = Struct()
        for name in names:
            child = element.find(self.qualify(name))
            if child is not None:
                record[name] = self.from_element(child)
        return record

    def struct_to_elements(self, struct, *names):
        """Converts a selected set of the values in the given Struct, all
        of this kind, to a list of Elements."""
        elements = []
        for name in names:
            if name in struct:
                elements.append(self.to_element(name, struct[name]))
        return elements

    def element(self, name, *attributes_and_text_and_children):
        """Creates an element with the given name, qualified in this
        Converter's default namespace.  See xmlutils.element."""
        tag = self.qualify(name)
        return element(tag, *attributes_and_text_and_children)
