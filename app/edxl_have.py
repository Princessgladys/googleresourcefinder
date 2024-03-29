"""XML conversion for EDXL-HAVE."""

from feedlib import time_formats, xml_utils


EDXL_HAVE_NS = 'urn:oasis:names:tc:emergency:EDXL:HAVE:1.0'
GML_NS = 'http://opengis.net/gml'
URI_PREFIXES = {
    EDXL_HAVE_NS: 'have',
    GML_NS: 'gml'
}


class HospitalStatus(xml_utils.Converter):
    __metaclass__ = xml_utils.Singleton
    NS = EDXL_HAVE_NS

    def from_element(self, element):
        return [Hospital.from_element(hospital)
                for hospital in element.find(self.qualify('Hospital'))]

    def to_element(self, name, value):
        return self.element(name,
            [Hospital.to_element('Hospital', hospital) for hospital in value])


class Hospital(xml_utils.Converter):
    __metaclass__ = xml_utils.Singleton
    NS = EDXL_HAVE_NS

    def from_element(self, element):
        value = {}
        org_info = element.find(self.qualify('OrganizationInformation'))
        if org_info is not None:
            value.update(Text.struct_from_children(org_info,
                'OrganizationID',
                'OrganizationIDProviderName',
                'OrganizationName',
                'OrganizationTypeText',
                'CommentText'
            ))
        value.update(GeoLocation.struct_from_children(element,
            'OrganizationGeoLocation',
        ))
        value.update(DateTime.struct_from_children(element, 'LastUpdateTime'))
        return value

    def to_element(self, name, value):
        return self.element(name,
            self.element('OrganizationInformation',
                Text.struct_to_elements(value,
                    'OrganizationID',
                    'OrganizationIDProviderName',
                    'OrganizationName',
                    'OrganizationTypeText',
                    'CommentText',
                ),
            ),
            GeoLocation.struct_to_elements(value, 'OrganizationGeoLocation'),
            DateTime.struct_to_elements(value, 'LastUpdateTime')
        )


class Text(xml_utils.Converter):
    __metaclass__ = xml_utils.Singleton
    NS = EDXL_HAVE_NS

    def from_element(self, element):
        return element.text.strip()

    def to_element(self, name, value):
        return xml_utils.element(self.qualify(name), value)


class DateTime(xml_utils.Converter):
    __metaclass__ = xml_utils.Singleton
    NS = EDXL_HAVE_NS

    def from_element(self, element):
        return time_formats.from_rfc3339(element.text.strip())

    def to_element(self, name, value):
        return xml_utils.element(
            self.qualify(name), time_formats.to_rfc3339(value))


class GeoLocation(xml_utils.Converter):
    __metaclass__ = xml_utils.Singleton
    NS = EDXL_HAVE_NS

    def from_element(self, element):
        point = element.find(xml_utils.qualify(GML_NS, 'Point'))
        if point is not None:
            pos = point.find(xml_utils.qualify(GML_NS, 'pos'))
            if pos is not None:
                latitude, longitude = map(float, pos.text.split())
                return (latitude, longitude)

    def to_element(self, name, value):
        return self.element(name,
            xml_utils.element(xml_utils.qualify(GML_NS, 'Point'),
                xml_utils.element(xml_utils.qualify(GML_NS, 'pos'),
                    '%g %g' % (latitude, longitude)
                )
            )
        )


def read(file):
    """Parses EDXL-HAVE <Hospital> elements and returns a list of records."""
    hospitals = xml_utils.read(file).findall('.//{%s}Hospital' % EDXL_HAVE_NS)
    return map(Hospital.from_element, hospitals)

def write(file, hospitals):
    """Writes a list of hospital elements as an EDXL-HAVE document."""
    xml_utils.write(file, serialize(hospitals), URI_PREFIXES)
