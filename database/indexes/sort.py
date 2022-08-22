'''An index for Text or other string fields, suitable for sorting'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.database.indexes import Index
from appy.utils.string import Normalize

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class SortIndex(Index):
    '''Sortable index for free-text fields'''

    @classmethod
    def toIndexed(class_, value, field, keep=100):
        '''Keeps only p_keep first chars and normalizes p_value, for the purpose
           of sorting.'''
        if not value: return
        return Normalize.text(value[:keep], keepBlank=False) or None

    @classmethod
    def toTerm(class_, value, field):
        '''Normalizes p_value in order to be used as a search term'''
        # Similar to p_toIndexed, but do not restrict the number of chars
        return Normalize.text(value, keepBlank=False)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
