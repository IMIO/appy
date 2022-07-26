'''Extracts statistics from an ODF document (meta.xml)'''

# ------------------------------------------------------------------------------
from appy.shared.zip import unzip
from appy.shared.utils import getOsTempFolder
from appy.shared.xml_parser import XmlUnmarshaller

# ------------------------------------------------------------------------------
class OdfMetadata:
    '''Represents metadata about an ODF document'''
    def __init__(self, metadata):
        '''Initialises instance attributes based on m_metadata that contains the
           unmarshalled content of some ODF file's meta.xml.'''
        # Store document statistics
        stats = metadata.get('document-statistic')
        for name, value in stats.__dict__.iteritems():
            # Value should be integer
            try:
                value = int(value)
            except ValueError:
                pass
            # Attribute names can contain dashes
            setattr(self, name.replace('-', ''), value)

# ------------------------------------------------------------------------------
class MetadataReader:
    metaTagTypes = {'meta:document-statistic': 'object'}

    def __init__(self, fileName):
        self.fileName = fileName

    def run(self):
        '''Extracts metadata and statistics from the ODF file whose name is in
           self.fileName and returns an OdfMetadata instance.'''
        # Unzip the ODF file into a temp folder
        tempFolder = getOsTempFolder(sub=True)
        metaXml = unzip(self.fileName, tempFolder, odf=True)['meta.xml']
        parser = XmlUnmarshaller(tagTypes=self.metaTagTypes)
        return OdfMetadata(parser.unmarshall(metaXml).meta)
# ------------------------------------------------------------------------------
