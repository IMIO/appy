'''An index for Ref fields'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.database.indexes import Index

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class RefIndex(Index):
    '''Index for a Ref field'''

    # Types of atomic values this index may store
    atomicTypes = (int, str)

    @classmethod
    def toIndexed(class_, value, field):
        '''Converts p_value, a list of tied objects, into their internal index
           representation = a list of their IIDs, or an alternate attribute as
           defined in p_field.indexAttribute.'''
        # If there is no value at all, nothing must be indexed
        if value is None:
            return
        elif isinstance(value, class_.atomicTypes):
            # Already an object IID (or alternate attribute coming from
            # p_field.indexAttribute) ready to be indexed (probably a default
            # value to index from field.emptyIndexValue).
            return value
        elif not hasattr(value, '__iter__'):
            # An object: get its indexable value
            return getattr(value, field.indexAttribute)
        else:
            # Convert a list of objects into a list of their indexable values
            return [getattr(o, field.indexAttribute) for o in value]

    @classmethod
    def toTerm(class_, value, field):
        '''Ensure p_value is an object's indexable value'''
        if isinstance(value, int):
            r = value
        elif isinstance(value, str):
            # p_value can be from a specific attribute, or be an IID encoded as
            # a string.
            r = int(value) if value.isdigit() else value
        else:
            # p_value is an object
            r = getattr(value, field.indexAttribute)
        return r

    @classmethod
    def toString(class_, o, value):
        '''The string representation for tied objects stored in p_value is the
           concatenation of their titles.'''
        if not value:
            r = None
        elif not hasattr(value, '__iter__'):
            # A single object
            r = value.getShownValue()
        else:
            # Several objects
            r = ' '.join([tied.getShownValue() for tied in value])
        return r

    # The CSS class to use when rendering the "recompute" icon for a Ref index
    boxIconCss = 'boxIconR'
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
