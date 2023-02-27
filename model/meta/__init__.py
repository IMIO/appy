'''The Appy meta-model contains meta-classes representing classes of Appy
   classes: essentially, Appy classes and workflows.'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.model.base import Base
from appy.model.root import Model

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
ATTR       = 'Attribute "%s" in %s "%s"'
UNDERS     = 'contains at least one underscore, which is not allowed'

US_IN_ATTR = '%s %s. Please consider naming your fields, searches, states ' \
             'and transitions in camelCase style, the first letter being a ' \
             'lowercase letter. For example: "myField", instead of ' \
             '"my_field". Furthermore, there is no need to define "private" ' \
             'fields starting with an underscore.' % (ATTR, UNDERS)
US_IN_CLS = 'ClassS or workflow "%%s" %s. Please consider naming your classes ' \
            'and workflows in CamelCase style, the first letter being an ' \
            'uppercase letter. For example: "MyClass", instead of ' \
            '"my_class".' % UNDERS
UP_NAME    = '%s must start with a lowercase letter. This rule holds for any ' \
             'field, search, state or transition.' % ATTR
LOW_NAME   = 'Name of %s "%s" must start with an uppercase letter.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Meta:
    '''Abstract base class representing a Appy class or workflow'''

    # Reserved attribute names unallowed for naming a meta-class related
    # attribute, like a field, search, state, transition...

    unallowedNames = {
      'id':         None, # The object's identifier
      'iid':        None, # The object's integer identifier
      'values':     None, # Dict storing all field values
      'container':  None, # Info about the objet's container
      'history':    None, # The object's history
      'localRoles': None, # The object's local roles
      'locks':      None, # Locks on object pages
    }

    @classmethod
    def unallowedName(class_, name):
        '''Return True if p_name can't be used for naming a Field or Search'''
        # A name is unallowed if
        # (a) it corresponds to some standard attribute added at object creation
        #     on any Appy object (but not declared at the class level);
        # (b) it corresponds to an attribute or method defined in class Base.
        return name in class_.unallowedNames or name in Base.__dict__

    def __init__(self, class_, appOnly):
        # p_class_ is the Python class found in the Appy app. Its full name is
        #              <Python file name>.py.<class name>
        self.python = class_
        # Make this link bidirectional
        class_.meta = self
        # Its name. Ensure it is valid.
        self.name = self.checkClassName(class_)
        # If p_appOnly is True, stuff related to the Appy base model must not be
        # defined on this meta-class. This minimalist mode is in use when
        # loading the model for creating or updating translation files.
        self.appOnly = appOnly

    def asString(self):
        r = '<class %s.%s' % (self.__module__, self.name)
        for attribute in self.attributes.keys():
            r += '\n %s:' % attribute
            for name, field in getattr(self, attribute).items():
                r += '\n  %s : %s' % (name, str(field))
        return r

    def checkClassName(self, class_):
        '''The name of a class or workflow must start with an uppercase letter
           and cannot contain an underscore.'''
        name = class_.__name__
        if '_' in name:
            raise Model.Error(US_IN_CLS % (name))
        if name[0].islower():
            type = self.__class__.__name__.lower()
            raise Model.Error(LOW_NAME % (type, name))
        return name

    def checkAttributeName(self, name):
        '''Checks if p_name is valid for being used as attribute (field, search,
           state or transition) for this class or workflow.'''
        # Underscores are not allowed
        if '_' in name:
            type = self.__class__.__name__.lower()
            raise Model.Error(US_IN_ATTR % (name, type, self.name))
        # The name must start with a lowercase char
        if not name[0].islower():
            type = self.__class__.__name__.lower()
            raise Model.Error(UP_NAME % (name, type, self.name))

    def __repr__(self):
        '''p_self's string representation'''
        return '<meta%s %s from module %s>' % (self.__class__.__name__.lower(),
                                              self.name, self.python.__module__)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
