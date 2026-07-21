'''An index for Text fields, splitting text into words'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from . import Index
from .options import Options
from appy.utils.string import Normalize

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class TextOptions(Options):
    '''Options for text indexes'''

    def __init__(self, ignore=2, ignoreNumbers=False):
        # Within indexed text, words whose length is <= p_ignore are ignored,
        # excepted, if p_ignoreNumbers is False, words being numbers.
        self.ignore = ignore
        self.ignoreNumbers = ignoreNumbers

    def __repr__(self):
        '''p_self as a short string'''
        return f'‹TextOptions ignore={self.ignore};ignoreNumbers=' \
               f'{self.ignoreNumbers}›'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class TextIndex(Index):
    '''Index for Text fields'''

    # Index options for a text index
    options = TextOptions()

    # For a Text index, a value to store in the index is already and always
    # built as a tuple (by m_toIndexed below): so it it always considered to
    # be "multiple", and it is useless to convert it to a tuple.
    def isMultiple(self, value, inIndex=False): return isinstance(value, tuple)
    def getMultiple(self, value): return value

    # A Text index potentially contains a large number of values. Comparing
    # values while reindexing an object may be inefficient, so here, we force
    # bypassing value comparison: everytime an object will be reindexed, all
    # existing values for a Text index will be removed and new ones will be
    # re-inserted.
    def valueEquals(self, value, current): return

    @classmethod
    def toIndexed(class_, value, field, normalize=True, words=None):
        '''Splits the plain text p_value into words'''
        # If p_words is passed, it is a dict of the form ~{s_word:None}~: every
        # found word is added into it. Else, words are returned, as a tuple.
        if not value: return
        # Create a set
        noWords = words is None
        if noWords:
            r = set()
        if normalize:
            value = Normalize.text(value)
        options = class_.getOptions(field)
        for word in value.split():
            # Keep this word or not ?
            if len(word) <= options.ignore:
                keepIt = not options.ignoreNumbers and word.isdigit()
            else:
                keepIt = True
            if keepIt:
                if noWords:
                    r.add(word)
                else:
                    words[word] = None
        if noWords:
            return tuple(r)

    # No need to override m_toString in order to normalize the value: it will be
    # done by the global "searchable" index.

    @classmethod
    def toTerm(class_, value, field):
        '''Normalizes p_value in order to be used as a search term'''
        return Normalize.text(value)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
