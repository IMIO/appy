#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from DateTime import DateTime

from appy.px import Px
from appy.model.searches import Search
from appy.model.fields.text import Text
from appy.model.fields.date import Date
from appy.model.fields import Field, Show
from appy.ui.layout import Layouts, Layout
from appy.model.fields.string import String

# Error messages - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
UNFREEZ   = 'This field is unfreezable.'
METHOD_NO = 'Specify a method in parameter "method".'
METHOD_KO = 'Wrong value "%s". Parameter "method" must contain a method or ' \
            'a PX.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Computed(Field):
    '''Useful for computing a custom field via a Python method'''

    class Layouts(Layouts):
        '''Computed-specific layouts'''
        # Layouts for fields in a grid group, with description
        gd = Layouts('f-drvl')
        # Idem, but with a help icon
        gdh = Layouts('f-dhrvl')

    # Values produced by a Computed fields may be summable
    summable = True

    # By default, Computed values are considered to be freezable, excepted if
    # explicitly declared as unfreezable, via instance attribute "unfreezable".
    freezable = True

    # Precision, in minutes, of the indexed value, if of type "DateIndex"
    indexPrecision = 1

    view = cell = buttons = edit = Px('''<x if="field.plainText">:value</x><x
      if="not field.plainText">::value</x>''')

    search = Px('''
     <input type="text" name=":widgetName" maxlength=":field.maxChars"
            size=":field.width" value=":field.sdefault"/>''')

    # If dates are stored in a Computed field, the date filter may be required
    pxFilterDate = Date.pxFilter

    def __init__(self, multiplicity=(0,1), default=None, defaultOnEdit=None,
      show=None, renderable=None, page='main', group=None, layouts=None, move=0,
      indexed=False, mustIndex=True, indexType=None, indexValue=None,
      emptyIndexValue=None, searchable=False, filterField=None,
      readPermission='read', writePermission='write', width=None, height=None,
      maxChars=None, colspan=1, method=None, formatMethod=None, plainText=False,
      master=None, masterValue=None, focus=False, historized=False,
      mapping=None, generateLabel=None, label=None, sdefault='', scolspan=1,
      swidth=None, sheight=None, fwidth=4, context=None, view=None, cell=None,
      buttons=None, edit=None, xml=None, translations=None, unfreezable=False,
      validable=False, pythonType=None):
        # The Python method used for computing the field value, or a PX
        self.method = method
        # A specific method for producing the formatted value of this field.
        # This way, if, for example, the value is a DateTime instance which is
        # indexed, you can specify in m_formatMethod the way to format it in
        # the user interface while m_method computes the value stored in the
        # catalog.
        self.formatMethod = formatMethod
        # If field computation produces a string, does this string value
        # represent plain text or XHTML ?
        self.plainText = plainText
        if isinstance(method, Px):
            # When field computation is done with a PX, the result is XHTML
            self.plainText = False
        # Determine the default value for attribute "show"
        if show is None:
            # XHTML content in a Computed field generally corresponds to some
            # custom XHTML widget. This is why, by default, we do not render it
            # in the xml layout.
            show = Show.E_ if self.plainText else Show.TR
        # If method is a PX, its context can be given in p_context
        self.context = context
        # For any other Field subclass, the type of the index to use (indexType)
        # and the type of the value to store in the database (pythonType) are
        # statically determined. But for an indexed Computed field, which may
        # hold any data of any type, the index type (and, possibly, Python type)
        # must be specified in p_indexType (and p_pythonType). Choose it in this
        # list, depending on the values that your field will store.
        self.indexType = indexType or 'Index'
        self.pythonType = pythonType
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   Index type   | is suitable...
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   "RefIndex"   | ... for storing lists of Appy objects (=instances of
        #                |     Appy classes). You should not use this type of 
        #                |     index and use a Ref field for storing lists of
        #                |     objects ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   "DateIndex"  | ... if your field stores DateTime instances ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   "TextIndex"  | ... if your field stores raw text and you want to
        #                |     index words found in it ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   "RichIndex"  | ... if your field stores a chunk of XHTML code and 
        #                |     you want to index text extracted from it ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  "FloatIndex"  | ... if your field stores float values ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "BooleanIndex" | ... if your field stores boolean values ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #     "Index"    | ... in any other case. Additionnally, if your field
        #                |     stores an integer value, set pythonType to *int*
        #                |     (=the Python basic type). If it stores a string,
        #                |     specify *str*. This is because Appy uses the base
        #                |     Index class indifferently for several fields like
        #                |     Integer, String or Select.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # Call the base constructor
        Field.__init__(self, None, multiplicity, default, defaultOnEdit, show,
          renderable, page, group, layouts, move, indexed, mustIndex,
          indexValue, emptyIndexValue, searchable, filterField, readPermission,
          writePermission, width, height, None, colspan, master, masterValue,
          focus, historized, mapping, generateLabel, label, sdefault, scolspan,
          swidth, sheight, False, False, view, cell, buttons, edit, xml,
          translations)
        # When a custom widget is built from a computed field, its values are
        # potentially editable and validable, so "validable" must be True.
        self.validable = validable
        # One classic use case for a Computed field is to build a custom widget.
        # In this case, self.method stores a PX or method that produces, on
        # view or edit, the custom widget. Logically, you will need to store a
        # custom data structure on the object, in an attribute named according
        # to this field, ie o.[self.name]. Typically, you will set or update a
        # value for this attribute in m_onEdit, by getting, on the o.req object,
        # values encoded by the user in your custom widget (edit mode). This
        # "custom widget" use case is incompatible with "freezing". Indeed,
        # freezing a Computed field implies storing the computed value at
        # o.[self.name] instead of recomputing it as usual. So if you want to
        # build a custom widget, specify the field as being unfreezable.
        self.unfreezable = unfreezable
        # The base Python type corresponding to values computed by this field
        self.pythonType = pythonType
        # Set a filter PX if this field is indexed
        if self.indexed:
            itype = self.indexType
            if itype in ('TextIndex', 'RichIndex') or self.pythonType == str:
                self.filterPx = 'pxFilterText'
            elif itype == 'DateIndex':
                self.filterPx = 'pxFilterDate'
        # The *f*ilter width
        self.fwidth = fwidth
        self.checkParameters()

    def checkParameters(self):
        '''Ensures a valid method is specified'''
        method = self.method
        # A method must be there
        if not method: raise Exception(METHOD_NO)
        # It cannot be a string, but a true method
        if isinstance(method, str): raise Exception(METHOD_KO % method)

    def renderPx(self, o, px):
        '''Renders the p_px and returns the result'''
        context = o.traversal.getContext()
        # Complete the context when relevant
        custom = self.context
        custom = custom if not callable(custom) else custom(o)
        if custom:
            context.update(custom)
        return px(context)

    def renderSearch(self, o, search):
        '''Executes the p_search and return the result'''
        req = o.req
        # This will allow the UI to find this search
        req.search = '%d,%s,view' % (o.iid, self.name)
        req.className = search.container.name
        traversal = o.traversal
        existingContext = traversal.context
        context = traversal.createContext()
        r = context.uiSearch.search.innerResults(context)
        # Reinitialise the context correctly
        if existingContext:
            traversal.context = existingContext
        return r

    def getSearch(self, o):
        '''Gets the Search instance possibly linked to this Computed field'''
        method = self.method
        if not method: return
        if isinstance(method, Search): return method
        # Maybe a dynamically-computed Search ?
        r = self.callMethod(o, method, cache=False)
        if isinstance(r, Search): return r

    def getValue(self, o, name=None, layout=None, single=None,
                 forceCompute=False):
        '''Computes the field value on p_obj or get it from the database if it
           has been frozen.'''
        # Is there a database value ?
        if not self.unfreezable and not forceCompute:
            r = o.values.get(self.name)
            if r is not None: return r
        # Compute the value
        meth = self.method
        if not meth: return
        if isinstance(meth, Px): return self.renderPx(o, meth)
        elif isinstance(meth, Search): return self.renderSearch(o, meth)
        else:
            # self.method is a method that will return the field value
            r = self.callMethod(o, meth, cache=False)
            # The field value can be a dynamically computed PX or Search
            if isinstance(r, Px): return self.renderPx(o, r)
            elif isinstance(r, Search): return self.renderSearch(o, r)
            return r

    def getSearchValue(self, req, value=None):
        '''Depending on p_self.indexType and p_self.pythonType, call the
           appropriate method.'''
        if self.indexType in ('TextIndex', 'RichIndex'):
            fun = Text.computeSearchValue
        elif self.indexType == 'DateIndex':
            fun = Date.computeSearchValue
        elif self.pythonType == str:
            fun = String.computeSearchValue
        else:
            fun = Field.getSearchValue
        return fun(self, req, value=value)

    def getFilterValue(self, value):
        '''The filter value must be transformed in various ways, depending on
           index type.'''
        return DateTime(value) if self.indexType == 'DateIndex' else value

    def getFormattedValue(self, o, value, layout='view', showChanges=False,
                          language=None):
        if self.formatMethod:
            r = self.formatMethod(o, value)
        else:
            r = value
        if not isinstance(r, str): r = str(r)
        return r

    # If you build a custom widget with a Computed field, Appy can't tell if the
    # value in your widget is complete or not. So it returns True by default.
    # It is up to you, in method obj.validate, to perform a complete validation,
    # including verifying if there is a value if your field is required.
    def isCompleteValue(self, o, value): return True

    def freeze(self, o, value=None):
        '''Normally, no field value is stored for a Computed field: the value is
           computed on-the-fly by p_self.method. But if you freeze it, a value
           is stored: either p_value if not None, or the result of calling
           p_self.method else. Once a Computed field value has been frozen,
           everytime its value will be requested, the frozen value will be
           returned and p_self.method will not be called anymore. Note that the
           frozen value can be unfrozen (see method below).'''
        if self.unfreezable: raise Exception(UNFREEZ)
        # Compute for the last time the field value if p_value is None
        if value is None: value = self.getValue(o, forceCompute=True)
        # Freeze the given or computed value (if not None) in the database
        if value is not None: o.values[self.name] = value

    def unfreeze(self, o):
        '''Removes the database value that was frozen for this field on p_o'''
        if self.unfreezable: raise Exception(UNFREEZ)
        if self.name in o.values: del(o.values[self.name])
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
