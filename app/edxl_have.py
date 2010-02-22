"""XML conversion for EDXL-HAVE."""

from xmlutils import Converter, etree, indent


EDXL_HAVE_NS = 'urn:oasis:names:tc:emergency:EDXL:HAVE:1.0'
GEO_OASIS_NS = 'http://www.opengis.net/gml/geo-oasis/10'
GML_NS = 'http://opengis.net/gml'


class HospitalStatus(Converter):
    NS = EDXL_HAVE_NS

    def from_element(self, element):
        return [Hospital.from_element(hospital)
                for hospital in element.find(self.qualify('Hospital'))]

    def to_element(self, name, value):
        return self.create_element(name,
            [Hospital.to_element('Hospital', hospital) for hospital in value])

HospitalStatus = HospitalStatus()  # singleton


class Hospital(Converter):
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
            org_loc = org_info.find(self.qualify('OrganizationLocation'))
            if org_loc is not None:
                value.update(Text.struct_from_children(org_loc,
                    'StreetFullText',
                    'LocationCityName',
                    'LocationCountyName',
                    'LocationStateName',
                    'LocationPostalCodeID',
                    'LocationCountryName',
                ))
                value.update(GeoLocation.struct_from_children(org_loc,
                    'OrganizationGeoLocation',
                ))
        return value

    def to_element(self, name, value):
        return self.create_element(name,
            self.create_element('OrganizationInformation',
                Text.struct_to_elements(value,
                    'OrganizationID',
                    'OrganizationIDProviderName',
                    'OrganizationName',
                    'OrganizationTypeText',
                    'CommentText',
                ),
                self.create_element('OrganizationLocation',
                    Text.struct_to_elements(value,
                        'StreetFullText',
                        'LocationCityName',
                        'LocationCountyName',
                        'LocationStateName',
                        'LocationPostalCodeID',
                        'LocationCountryName',
                    ),
                    GeoLocation.struct_to_elements(value,
                        'OrganizationGeoLocation',
                    )
                ),
            ),
        )

Hospital = Hospital()  # singleton


def create_text_element(tag, text):
    element = etree.Element(tag)
    element.text = text
    return element


class Text(Converter):
    NS = EDXL_HAVE_NS

    def from_element(self, element):
        return element.text.strip()

    def to_element(self, name, value):
        return create_text_element(self.qualify(name), value)

Text = Text()  # singleton


class GeoLocation(Converter):
    NS = GEO_OASIS_NS

    def from_element(self, element):
        where = element.find(self.qualify('where'))
        if where is not None:
            point = where.find(qualify(GML_NS, 'Point'))
            if point is not None:
                latitude, longitude = map(float, point.text.split())
                return (latitude, longitude)

    def to_element(self, name, value):
        return self.create_element(name,
            self.create_element('where',
                create_text_element(qualify(GML_NS, 'Point'),
                    '%g %g' % (latitude, longitude)
                )
            )
        )

GeoLocation = GeoLocation()  # singleton


def parse_file(file):
    """Parses EDXL-HAVE <Hospital> elements and returns a list of records."""
    hospitals = etree.parse(file).findall('.//{%s}Hospital' % EDXL_HAVE_NS)
    return map(Hospital.from_element, hospitals)

def register_namespaces():
    """Sets the namespace prefixes for the namespaces we use."""
    import xml.etree.ElementTree
    xml.etree.ElementTree._namespace_map[EDXL_HAVE_NS] = 'have'
    xml.etree.ElementTree._namespace_map[GEO_OASIS_NS] = 'geo-oasis'
    xml.etree.ElementTree._namespace_map[GML_NS] = 'gml'

def write_file(file, hospitals):
    """Writes a list of hospital elements as an EDXL-HAVE document."""
    register_namespaces()
    root = HospitalStatus.to_element('HospitalStatus', hospitals)
    indent(root)
    file.write('<?xml version="1.0"?>\n')
    etree.ElementTree(root).write(file, encoding='utf-8')
