#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import importlib.util

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def importModule(name, fileName):
    '''Imports module p_name given its absolute file p_name'''
    spec = importlib.util.spec_from_file_location(name, fileName)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Object:
    '''At every place we need an object, but without any requirement on its
       class (methods, attributes,...) we will use this minimalist class.'''

    def __init__(self, **fields):
        for k, v in fields.items(): setattr(self, k, v)

    def __repr__(self):
        '''A compact, string representation of this object for debugging
           purposes.'''
        r = '<O '
        for name, value in self.__dict__.items():
            # Avoid infinite recursion if p_self it auto-referenced
            if value == self: continue
            v = value
            if hasattr(v, '__repr__'):
                try:
                    v = v.__repr__()
                except TypeError:
                    pass
            try:
                r += '%s=%s ' % (name, v)
            except UnicodeDecodeError:
                r += '%s=<encoding problem> ' % name
        return r.strip() + '>'

    def __bool__(self): return bool(self.__dict__)
    def d(self): return self.__dict__
    def get(self, name, default=None): return self.__dict__.get(name, default)
    def __contains__(self, k): return k in self.__dict__
    def keys(self): return self.__dict__.keys()
    def values(self): return self.__dict__.values()
    def items(self): return self.__dict__.items()

    def __setitem__(self, k, v):
        '''Dict-like attribute set'''
        self.__dict__[k] = v

    def __getitem__(self, k):
        '''Dict-like access self[k] must return None if key p_k doesn't exist'''
        return self.__dict__.get(k)

    def __delitem__(self, k):
        '''Dict-like attribute removal'''
        del(self.__dict__[k])

    def __getattr__(self, name):
        '''Object access o.<name> must return None if attribute p_name does not
           exist.'''
        return

    def __eq__(self, other):
        '''Equality between objects is, like standard Python dicts, based on
           equality of all their attributes and values.'''
        if isinstance(other, Object):
            return self.__dict__ == other.__dict__
        return False

    def update(self, other):
        '''Set information from p_other (another Object instance or a dict) into
           p_self.'''
        other = other.__dict__ if isinstance(other, Object) else other
        for k, v in other.items(): setattr(self, k, v)

    def clone(self, **kwargs):
        '''Creates a clone from p_self'''
        r = self.__class__() # p_self's class may be an Object sub-class
        r.update(self)
        # Cloning can be altered by specifying values in p_kwargs, that will
        # override those from p_self.
        for k, v in kwargs.items():
            r[k] = v
        return r

    # Allow this highly manipulated Object class to be picklable
    def __getstate__(self): return self.__dict__
    def __setstate__(self, state): self.__dict__.update(state)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Fake:
    '''An instance of this Fake class may be used, in some contexts, in place of
       a standard instance from an Appy class, in order to render a field value
       in a specific context where the standard instance is unusable as-is.'''

    # For example, a fake object is useful in order to manipulate a value being
    # stored in an object's history, because this value is not directly related
    # to the object itself anymore, as are the current values of its fields.

    def __init__(self, field, value, req):
        # The field whose value must be manipulated
        self.field = field
        # The value for this field will be stored in a dict named "values", in
        # order to mimic a standard Appy instance.
        self.values = {field.name: value}
        # Other useful standard attributes
        self.req = req
        self.id = 0
        self.iid  = 0

    def getField(self, name):
        '''If p_self.field is an outer field, method m_getField may be called to
           retrieve this outer field when rendering an inner field.'''
        return self.field

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Hack:
    '''This class proposes methods for patching some existing code with
       alternative methods.'''

    H_PATCHED = '%d method(s) patched from %s to %s: %s.'
    H_ADDED   = '%d method(s) and/or attribute(s) added from %s to %s: %s.'

    @staticmethod
    def patch(class_, method, replacement, isStatic):
        '''This method replaces, on p_class_, this m_method with a p_replacement
           method (being static if p_isStatic is True), but keeps p_method on
           p_class_ under name "_base_<initial_method_name>_".'''
        # In the patched method, one may use method Hack.base to call the base
        # method.
        name = method.__name__
        baseName = '_base_%s_' % name
        if isStatic:
            # If "staticmethod" isn't called hereafter, the static functions
            # will be wrapped in methods.
            method = staticmethod(method)
            replacement = staticmethod(replacement)
        setattr(class_, baseName, method)
        setattr(class_, name, replacement)

    @staticmethod
    def base(method, class_=None):
        '''Allows to call the base (replaced) method. If p_method is static,
           you must specify its p_class_.'''
        class_ = class_ or method.__self__.__class__
        return getattr(class_, '_base_%s_' % method.__name__)

    @staticmethod
    def inject(patchClass, class_, verbose=False):
        '''Injects any method or attribute from p_patchClass into p_class_'''
        # As a preamble, inject methods and attributes from p_patchClass's base
        # classes, if any.
        for base in patchClass.__bases__:
            if base == object: continue
            Hack.inject(base, class_, verbose=verbose)
        patched = []
        added = []  
        # Inject p_patchClass' own methods and attributes
        for name, attr in patchClass.__dict__.items():
            # Ignore special methods
            if name.startswith('__'): continue
            # Unwrap functions from static methods
            typeName = attr.__class__.__name__
            if typeName == 'staticmethod':
                attr = attr.__get__(attr)
                static = True
            else:
                static = False
            # Is this name already defined on p_class_ ?
            if hasattr(class_, name):
                hasAttr = True
                classAttr = getattr(class_, name)
            else:
                hasAttr = False
                classAttr = None
            if hasAttr and typeName != 'type' and callable(attr) and \
               callable(classAttr):
                # Patch this method via Hack.patch
                Hack.patch(class_, classAttr, attr, static)
                patched.append(name)
            else:
                # Simply replace the static attr or add the new static
                # attribute or method.
                setattr(class_, name, attr)
                added.append(name)
        if verbose:
            pName = patchClass.__name__
            cName = class_.__name__
            print(Hack.H_PATCHED % (len(patched), pName, cName,
                                    ', '.join(patched)))
            print(Hack.H_ADDED % (len(added), pName, cName, ', '.join(added)))

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def notFromPortlet(tool):
    '''When set in a root class' attribute "createVia", this function prevents
       instances being created from the portlet.'''

    # This is practical if you want to get the facilities provided by the
    # "portlet zone" for a class (ie, all search facilities) but without
    # allowing people people to create such classes at the root level.
    try:
        return 'form' if not tool.traversal.context.rootClasses else None
    except AttributeError:
        pass
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
