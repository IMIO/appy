#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class ColSet:
    '''Represents a named set of columns to show when displaying Search results
       or tied objects from a Ref.'''

    def __init__(self, identifier, label, columns):
        # A short identifier for the set
        self.identifier = identifier
        # The i18n label to use for giving a human-readable name to the set
        self.label = label
        # The list/tuple of column layouts. To be more precise: if you are a
        # developer and you instantiate a ColSet instance, p_columns must
        # contain column layouts. If Appy instantiates a ColSet instance,
        # p_columns is an instance of class appy.ui.columns.Columns.
        self.columns = columns
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
