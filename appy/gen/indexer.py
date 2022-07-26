'''This file defines code for extracting, from field values, the text to be
   indexed.'''

# ------------------------------------------------------------------------------
from appy.gen.utils import splitIntoWords
from appy.shared.xml_parser import XmlParser
from appy.shared.utils import normalizeText

# ------------------------------------------------------------------------------
class ValidValue:
    '''Ensures that a field value, ready to be stored in an index, is valid'''
    # Indeed, some values may not be acceptable for the catalog: if it it an
    # empty list, string, None or an empty tuple, for example, instead of using
    # it, the catalog will keep the previously catalogued value! For such cases,
    # this class produces an "empty" value that will really overwrite the
    # previous one.

    @classmethod
    def forRef(klass, field, value):
        '''p_value is the new value we want to index in the catalog, for a Ref
           p_field.'''
        # The index does not like persistent lists
        if value: return list(value)
        # Ugly catalog: if I return an empty list, the previous value is kept
        return [field.emptyIndexValue]

    @classmethod
    def forString(klass, value, forSearch):
        '''p_value is the new value we want to index in the catalog, for a
           String field.'''
        # Ugly catalog: if I give an empty tuple as index value, it keeps the
        # previous value. If I give him a tuple containing an empty string, it
        # is ok.
        if isinstance(value, tuple) and not value:
            value = forSearch and ' ' or ('',)
        # Ugly catalog: if value is an empty string or None, it keeps the
        # previous index value.
        elif value in (None, ''): return ' '
        return value

# Default Appy indexes ---------------------------------------------------------
defaultIndexes = {
    'State': 'ListIndex', 'UID': 'FieldIndex', 'Title': 'TextIndex',
    'SortableTitle': 'FieldIndex', 'SearchableText': 'TextIndex',
    'Creator': 'FieldIndex', 'Created': 'DateIndex', 'Modified': 'DateIndex',
    'ClassName': 'FieldIndex', 'Allowed': 'KeywordIndex',
    'Container': 'FieldIndex'}

# Stuff for creating or updating the indexes -----------------------------------
class TextIndexInfo:
    '''Parameters for a text ZCTextIndex'''
    lexicon_id = "text_lexicon"
    index_type = 'Okapi BM25 Rank'

class XhtmlIndexInfo:
    '''Parameters for a html ZCTextIndex'''
    lexicon_id = "xhtml_lexicon"
    index_type = 'Okapi BM25 Rank'

class ListIndexInfo:
    '''Parameters for a list ZCTextIndex'''
    lexicon_id = "list_lexicon"
    index_type = 'Okapi BM25 Rank'

def updateIndexes(installer, indexInfo):
    '''This function updates the indexes defined in the catalog'''
    catalog = installer.app.catalog
    logger = installer.logger
    for indexName, indexType in indexInfo.iteritems():
        indexRealType = indexType
        if indexType in ('XhtmlIndex', 'TextIndex', 'ListIndex'):
            indexRealType = 'ZCTextIndex'
        # If this index already exists but with a different type (or with a
        # deprecated lexicon), remove it.
        if indexName in catalog.indexes():
            indexObject = catalog.Indexes[indexName]
            oldType = indexObject.__class__.__name__
            toDelete = False
            if (oldType != indexRealType):
                toDelete = True
                info = indexRealType
            elif (oldType == 'ZCTextIndex') and \
                 (indexObject.lexicon_id == 'lexicon'):
                toDelete = True
                info = '%s (%s)' % (oldType, indexType)
            if toDelete:
                catalog.delIndex(indexName)
                logger.info('Index %s (%s) to replace as %s.' % \
                            (indexName, oldType, info))
        if indexName not in catalog.indexes():
            # We need to (re-)create this index
            if indexType == 'TextIndex':
                catalog.addIndex(indexName, indexRealType, extra=TextIndexInfo)
            elif indexType == 'XhtmlIndex':
                catalog.addIndex(indexName, indexRealType, extra=XhtmlIndexInfo)
            elif indexType == 'ListIndex':
                catalog.addIndex(indexName, indexRealType, extra=ListIndexInfo)
            else:
                catalog.addIndex(indexName, indexType)
            # Indexing database content based on this index
            logger.info('Reindexing %s (%s)...' % (indexName, indexType))
            catalog.reindexIndex(indexName, installer.app.REQUEST)
            logger.info('Done.')

# ------------------------------------------------------------------------------
class XhtmlTextExtractor(XmlParser):
    '''Extracts text from XHTML'''
    def __init__(self, lower=True, dash=False, raiseOnError=False):
        XmlParser.__init__(self, raiseOnError=raiseOnError)
        # Must be lowerise text ?
        self.lower = lower
        # Must we keep dashes ?
        self.dash = dash

    def startDocument(self):
        XmlParser.startDocument(self)
        self.res = []

    def endDocument(self):
        self.res = ' '.join(self.res)
        return XmlParser.endDocument(self)

    # Disable the stack of currently parsed elements
    def startElement(self, elem, attrs): pass
    def endElement(self, elem): pass

    def characters(self, content):
        c = normalizeText(content, lower=self.lower, dash=self.dash)
        if len(c) > 1: self.res.append(c)

# ------------------------------------------------------------------------------
class XhtmlIndexer:
    '''Extracts, from XHTML field values, the text to index'''
    def process(self, texts):
        res = set()
        for text in texts:
            extractor = XhtmlTextExtractor(raiseOnError=False)
            cleanText = extractor.parse('<p>%s</p>' % text)
            res = res.union(splitIntoWords(cleanText))
        return list(res)

# ------------------------------------------------------------------------------
class TextIndexer:
    '''Extracts, from text field values, a normalized value to index'''
    def process(self, texts):
        res = set()
        for text in texts:
            cleanText = normalizeText(text)
            res = res.union(splitIntoWords(cleanText))
        return list(res)

class ListIndexer:
    '''This lexicon does nothing: list of values must be indexed as is'''
    def process(self, texts): return texts

# ------------------------------------------------------------------------------
try:
    from Products.ZCTextIndex.PipelineFactory import element_factory as ef
    ef.registerFactory('XHTML indexer', 'XHTML indexer', XhtmlIndexer)
    ef.registerFactory('Text indexer', 'Text indexer', TextIndexer)
    ef.registerFactory('List indexer', 'List indexer', ListIndexer)
except ImportError:
    # May occur at generation time
    pass
# ------------------------------------------------------------------------------
