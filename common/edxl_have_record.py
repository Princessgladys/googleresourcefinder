import records
import time_formats

EDXL_HAVE_NS = 'urn:oasis:names:tc:emergency:EDXL:HAVE:1.0'

class EdxlHaveHospitalType(records.RecordType):
    def get_subject_id(self, element):
        return element.find('.//{%s}OrganizationID' % EDXL_HAVE_NS).text.strip()

    def get_observed(self, element):
        time_element = element.find('.//{%s}LastUpdateTime' % EDXL_HAVE_NS)
        return time_formats.from_rfc3339(time_element.text.strip())

records.register_type('{%s}Hospital' % EDXL_HAVE_NS, EdxlHaveHospitalType())
