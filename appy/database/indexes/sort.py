'''An index for Text or other string fields, suitable for sorting'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from . import Index
from .options import Options
from appy.utils.string import Normalize

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class SortOptions(Options):
    '''Options for sort indexes'''

    def __init__(self, keep=100):
        # The number of relevant chars to keep, at the start of a string value,
        # for the purpose of sorting.
        self.keep = keep

    def __repr__(self):
        '''p_self as a short string'''
        return f'‹SortOptions keep={self.keep}›'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class SortIndex(Index):
    '''Sortable index for free-text fields'''

    # Index options for a sort index
    options = SortOptions()

    @classmethod
    def toIndexed(class_, value, field):
        '''Keeps only p_keep first chars and normalizes p_value, for the purpose
           of sorting.'''
        if not value: return
        keep = class_.getOptions(field).keep
        val = value[:keep]
        return Normalize.sortable(val) or None

    @classmethod
    def toTerm(class_, value, field):
        '''Normalizes p_value in order to be used as a search term'''
        # Similar to p_toIndexed, but does not restrict the number of chars and
        # does not concatenate search terms.
        return Normalize.text(value)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
