"""XML parsing and serialization framework.

This framework helps you parse XML documents, which may have many levels
of nested elements, into flatter Python structures.  To use it, define
subclasses of Converter.  Each Converter describes how to convert a subtree
of an XML document to or from a Python value.  The type and structure of
the Python value is up to the Converter.
"""

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

def qualify(ns, name):
    """Makes a namespace-qualified name."""
    return '{%s}%s' % (ns, name)


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

class Converter:
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

    def create_element(self, name, *child_args):
        """Creates an element containing the given child elements.  The
        arguments can be children or lists of children, and are allowed to
        include None, which is ignored."""
        element = etree.Element(self.qualify(name))
        for arg in child_args:
            for child in isinstance(arg, list) and arg or [arg]:
                if child is not None:
                    element.append(child)
        return element
