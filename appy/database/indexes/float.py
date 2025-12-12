'''An index for Float fields'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.utils import formatNumber
from appy.database.indexes import Index

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class FloatIndex(Index):
    '''Index for a Float field'''

    # Python type for values stored in a float index
    valuesType = float

    @classmethod
    def toIndexed(class_, value, field):
        '''Converts p_value to its internal representation, taking care of the
           required precision.'''
        return round(value, field.indexPrecision) if value is not None else None

    @classmethod
    def toString(class_, o, value):
        '''Returns the string representation for p_value'''
        return formatNumber(value) if value is not None else None
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
