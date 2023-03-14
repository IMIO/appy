'''An index for Rich fields, extracting pure text and splitting it into words'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.xml.extractor import Extractor
from appy.database.indexes.text import TextIndex

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class RichIndex(TextIndex):
    '''Index for Rich fields'''

    @classmethod
    def toIndexed(class_, value, field):
        '''Converts p_value, which is a chunk of XHTML code, into pure text and
           splits it into words.'''
        if not value: return
        # Use an XHTML text extractor. p_value represents a chunk of XHTML code,
        # but there is no guarantee that this code contains a single root tag,
        # so add one.
        extractor = Extractor(normalize=True, keepCRs=False)
        value = extractor.parse('<x>%s</x>' % value)
        # Tokenize the result, but text has already been normalized
        return TextIndex.toIndexed(value, field, normalize=False)

    @classmethod
    def toString(class_, o, value):
        '''Converts p_value to pure text via an XHTML text extractor'''
        # No need to normalize p_value here: it will be done by the global
        # "searchable" index.
        return Extractor(keepCRs=False).parse('<x>%s</x>' % value) if value \
                                                                   else None
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
