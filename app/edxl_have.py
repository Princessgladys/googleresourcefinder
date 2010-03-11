"""XML conversion for EDXL-HAVE."""

import xmlutils


EDXL_HAVE_NS = 'urn:oasis:names:tc:emergency:EDXL:HAVE:1.0'
GEO_OASIS_NS = 'http://www.opengis.net/gml/geo-oasis/10'
GML_NS = 'http://opengis.net/gml'
URI_PREFIXES = {
    EDXL_HAVE_NS: 'have',
    GEO_OASIS_NS: 'geo-oasis',
    GML_NS: 'gml'
}

class HospitalStatus(xmlutils.Converter):
    __metaclass__ = xmlutils.Singleton
    NS = EDXL_HAVE_NS

    def from_element(self, element):
        return [Hospital.from_element(hospital)
                for hospital in element.find(self.qualify('Hospital'))]

    def to_element(self, name, value):
        return self.element(name,
            [Hospital.to_element('Hospital', hospital) for hospital in value])


class Hospital(xmlutils.Converter):
    __metaclass__ = xmlutils.Singleton
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
        return self.element(name,
            self.element('OrganizationInformation',
                Text.struct_to_elements(value,
                    'OrganizationID',
                    'OrganizationIDProviderName',
                    'OrganizationName',
                    'OrganizationTypeText',
                    'CommentText',
                ),
                self.element('OrganizationLocation',
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


class Text(xmlutils.Converter):
    __metaclass__ = xmlutils.Singleton
    NS = EDXL_HAVE_NS

    def from_element(self, element):
        return element.text.strip()

    def to_element(self, name, value):
        return xmlutils.element(self.qualify(name), value)


class GeoLocation(xmlutils.Converter):
    __metaclass__ = xmlutils.Singleton
    NS = GEO_OASIS_NS

    def from_element(self, element):
        where = element.find(self.qualify('where'))
        if where is not None:
            point = where.find(qualify(GML_NS, 'Point'))
            if point is not None:
                latitude, longitude = map(float, point.text.split())
                return (latitude, longitude)

    def to_element(self, name, value):
        return self.element(name,
            self.element('where',
                xmlutils.element(qualify(GML_NS, 'Point'),
                    '%g %g' % (latitude, longitude)
                )
            )
        )


def read(file):
    """Parses EDXL-HAVE <Hospital> elements and returns a list of records."""
    hospitals = xmlutils.read(file).findall('.//{%s}Hospital' % EDXL_HAVE_NS)
    return map(Hospital.from_element, hospitals)

def write(file, hospitals):
    """Writes a list of hospital elements as an EDXL-HAVE document."""
    root = HospitalStatus.to_element('HospitalStatus', hospitals)
    xmlutils.write(file, root, URI_PREFIXES)
