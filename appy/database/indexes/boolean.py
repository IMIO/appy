'''An index for Boolean fields'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.database.indexes import Index

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class BooleanIndex(Index):
    '''Index for a Boolean field'''

    # Python type for values stored in a boolean index
    valuesType = bool

    @classmethod
    def toIndexed(class_, value, field):
        '''Converts p_value to a boolean value if it is not the case'''
        # In other words, value None must be converted to False
        return bool(value)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
