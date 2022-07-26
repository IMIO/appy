# -*- coding: utf-8 -*-
# ~license~

# ------------------------------------------------------------------------------
from appy.px import Px
from appy.fields import Field
from appy.gen.layout import Layouts
from appy.shared import utils as sutils
from appy.gen.indexer import ValidValue

# ------------------------------------------------------------------------------
emptyTuple = ()
RADIOS_KO = "This field can't be rendered as radio buttons because it may " \
            "contain several values (max multiplicity is higher than 1)."
CBS_KO    = "This field can't be rendered as checkboxes because it can " \
            "only contain a single value (max multiplicity is 1)."
IEDIT_KO  = 'It is currently not possible to inline-edit a multi-valued ' \
            'Select field.'

# ------------------------------------------------------------------------------
class Selection:
    '''If you want to have dynamically computed possible values for a Select
       field, use a Selection instance.'''

    def __init__(self, methodName, single=None):
        # p_methodName must be the name of a method that will be called every
        # time Appy will need to get the list of possible values for the related
        # field. It must correspond to an instance method of the class defining
        # the related field. This method accepts no argument and must return a
        # list (or tuple) of pairs (lists or tuples): (id, text), where "id" is
        # one of the possible values for the field, and "text" is the value as
        # will be shown on the screen. You can use self.translate within this
        # method to produce an i18n version of "text" if needed.
        self.methodName = methodName

        # While the method whose name is p_methodName is called on edit and
        # filter layouts to list the possible values to select, the method you
        # specify in p_single allows to produce the translated text for a single
        # value. It accepts a single arg, being one of the values as stored by
        # the select field, and must return its translated text. If you don't
        # specify a p_single method, p_methodName will be used instead, but
        # useless processing will take place, because p_method produces texts
        # for the complete list of possible values. Moreover, a stored select
        # value may not be among the list of values as returned by p_method
        # anymore.
        self.single = single

    def getText(self, obj, value, field, language=None):
        '''Gets the text that corresponds to p_value'''
        # Use method p_single if specified
        if self.single: return self.single(obj.appy(), value)
        # Use p_self.methodName
        if language:
            withTranslations = language
        else:
            withTranslations = True
        vals = field.getPossibleValues(obj, ignoreMasterValues=True,\
                                       withTranslations=withTranslations)
        for v, text in vals:
            if v == value: return text
        return value

# ------------------------------------------------------------------------------
class Select(Field):
    '''Field allowing to choose a value among a list of possible values. Each
       value is represented and stored as a string.'''

    pxView = Px('''
     <!-- No value at all -->
     <span if="not value" class="smaller">-</span>
     <!-- A single value -->
     <x if="value and not isMultiple">::field.getInlineEditableValue(obj, \
                                          value, layoutType, name=name)</x>
     <!-- Several values -->
     <ul if="value and isMultiple"><li for="sv in value"><i>::sv</i></li></ul>
     <!-- If this field is a master field -->
     <input type="hidden" if="masterCss" class=":masterCss" value=":rawValue"
            name=":name" id=":name"/>''')

    # More compact representation on the cell layout
    pxCell = Px('''
     <x var="multiple=value and isMultiple">
      <x if="multiple">:', '.join(value)</x>
      <x if="not multiple">:field.pxView</x>
     </x>''')

    pxEdit = Px('''
     <x var="isSelect=field.render == 'select';
             possibleValues=field.getPossibleValues(zobj, \
               withTranslations=True, withBlankValue=isSelect);
             charsWidth=field.getWidthInChars(False)">
     <select if="isSelect" name=":name" id=":name" class=":masterCss"
       multiple=":isMultiple" onchange=":field.getOnChange(zobj, layoutType)"
       size=":field.getSelectSize(False, isMultiple)"
       style=":field.getSelectStyle(False, isMultiple)">
      <option for="val, text in possibleValues" value=":val"
              selected=":field.isSelected(zobj, name, val, rawValue)"
              title=":text">:ztool.truncateValue(text, charsWidth)</option>
     </select>
     <x if="not isSelect">
      <div for="val, text in possibleValues" class="flex1">
       <input type=":field.render" name=":name" id=":val" value=":val"
              class=":masterCss" onchange=":field.getOnChange(zobj, layoutType)"
              checked=":field.isSelected(zobj, name, val, rawValue)"/>
       <label lfor=":val" class="subLabel">:text</label>
      </div>
     </x>
     <script if="hostLayout" var2="x=zobj.setLock(user, field=field)">:\
       'prepareForAjaxSave(%s,%s,%s,%s)' % \
        (q(name),q(obj.id),q(obj.url),q(hostLayout))</script></x>''')

    # On the search form, show a multi-selection widget with a "AND/OR" selector
    pxSearch = Px('''
     <!-- The "and" / "or" radio buttons -->
     <x if="field.multiplicity[1] != 1"
        var2="operName='o_%s' % name;
              orName='%s_or' % operName;
              andName='%s_and' % operName">
      <input type="radio" name=":operName" id=":orName"
             checked="checked" value="or"/>
      <label lfor=":orName">:_('search_or')</label>
      <input type="radio" name=":operName" id=":andName" value="and"/>
      <label lfor=":andName">:_('search_and')</label><br/>
     </x>

     <!-- The list of values -->
     <select var="preSelected=field.sdefault;
                  charsWidth=field.getWidthInChars(True)"
       name=":widgetName" multiple="multiple"
       size=":field.getSelectSize(True, True)"
       style=":field.getSelectStyle(True, True)"
       onchange=":field.getOnChange(ztool, 'search', className)">
      <option for="val, text in field.getPossibleValues(ztool, \
            withTranslations=True, withBlankValue=False, className=className)"
        selected=":val in preSelected" value=":val"
        title=":text">:ztool.truncateValue(text, charsWidth)</option>
     </select><br/>''')

    # Widget for filtering object values on search results
    pxFilter = Px('''
     <select var="name=field.name;
                  filterId='%s_%s' % (mode.ajaxHookId, name);
                  charsWidth=field.getWidthInChars(True)"
        id=":filterId" name=":filterId" class="discreet"
          onchange=":'askBunchFiltered(%s,%s)' % (q(mode.ajaxHookId), q(name))">
      <option for="val, text in field.getPossibleValues(ztool, \
                withTranslations=True, withBlankValue='forced', \
                blankLabel='everything', className=className)"
       selected=":(name in mode.filters) and (mode.filters[name] == val)"
       value=":val" title=":text">:ztool.truncateValue(text,charsWidth)</option>
     </select>''')

    def __init__(self, validator=None, multiplicity=(0,1), default=None,
      defaultOnEdit=None, show=True, page='main', group=None, layouts=None,
      move=0, indexed=False, mustIndex=True, indexValue=None, searchable=False,
      specificReadPermission=False, specificWritePermission=False, width=None,
      height=None, maxChars=None, colspan=1, master=None, masterValue=None,
      focus=False, historized=False, mapping=None, generateLabel=None,
      label=None, sdefault='', scolspan=1, swidth=None, sheight=None,
      persist=True, inlineEdit=False, view=None, cell=None, edit=None, xml=None,
      translations=None, noValueLabel='choose_a_value', render='select'):
        # When choosing a value in a select widget, the entry representing no
        # value is translated according the label defined in attribute
        # "noValueLabel". The default one is something like "[ choose ]", but if
        # you prefer a less verbose version, you can use "no_value" that simply
        # displays a dash, or your own label.
        self.noValueLabel = noValueLabel
        # A Select field, is, by default, rendered as a HTML select widget, but
        # there are alternate render modes. Here are all the possible render
        # modes.
        # ----------------------------------------------------------------------
        #  render    | The field is rendered as...
        # ----------------------------------------------------------------------
        # "select"   | an HTML select widget, rendered as a dropdown list if
        #            | max multiplicity is 1 or as a selection box if several
        #            | values can be chosen.
        # ----------------------------------------------------------------------
        # "radio"    | radio buttons. This mode is valid for fields with a max
        #            | multiplicity being 1.
        # ----------------------------------------------------------------------
        # "checkbox" | checkboxes. This mode is valid for fields with a max
        #            | multiplicity being higher than 1.
        # ----------------------------------------------------------------------
        self.render = render
        # Call the base constructor
        Field.__init__(self, validator, multiplicity, default, defaultOnEdit,
          show, page, group, layouts, move, indexed, mustIndex, indexValue,
          searchable, specificReadPermission, specificWritePermission, width,
          height, maxChars, colspan, master, masterValue, focus, historized,
          mapping, generateLabel, label, sdefault, scolspan, swidth, sheight,
          persist, inlineEdit, view, cell, edit, xml, translations)
        # self.sdefault must be a list of value(s)
        self.sdefault = sdefault or []
        # Default width, height and maxChars
        if width is None:
            self.width = 30
        if height is None:
            self.height = 4
        # Define the filter PX when appropriate
        if self.indexed:
            self.filterPx = 'pxFilter'
        self.swidth = self.swidth or self.width
        self.sheight = self.sheight or self.height
        self.checkParameters()

    def checkParameters(self):
        '''Ensure coherence between parameters'''
        # Valid render modes depend on multiplicities
        multiple = self.isMultiValued()
        if multiple and (self.render == 'radio'):
            raise Exception(RADIOS_KO)
        if not multiple and (self.render == 'checkbox'):
            raise Exception(CBS_KO)
        # It is currently not possible to inline-edit a multi-valued field
        if multiple and self.inlineEdit:
            raise Exception(IEDIT_KO)

    def isSelected(self, obj, name, possibleValue, dbValue):
        '''When displaying a Select field, must the p_possibleValue appear as
           selected? p_name is given and used instead of field.name because it
           may contain a row number from a field within a List field.'''
        req = obj.REQUEST
        # Get the value we must compare (from request or from database)
        if req.has_key(name):
            compValue = req.get(name)
        else:
            compValue = dbValue
        # Compare the value
        if type(compValue) in sutils.sequenceTypes:
            return possibleValue in compValue
        return possibleValue == compValue

    def getDefaultLayouts(self):
        '''Returns the default layouts for this type'''
        return self.inGrid() and Layouts.Select.g or Layouts.b

    def getValue(self, obj, name=None, layout=None, noListIfSingleObj=False):
        value = Field.getValue(self, obj, name, layout)
        if not value:
            if self.isMultiValued(): return emptyTuple
            else: return value
        if isinstance(value, basestring) and self.isMultiValued():
            value = [value]
        elif isinstance(value, tuple):
            value = list(value)
        return value

    def getTranslatedValue(self, obj, value, language=None):
        '''Get the translated text for p_value, when p_value is one of p_self's
           authorized "static" values according to its p_self.validator (being a
           list or tuple o values).'''
        if self.translations:
            # Translations are available via a FieldTranslations instance
            language = language or obj.getUserLanguage()
            r = self.translations.get('value', language, value=value)
        else:
            r = obj.translate('%s_list_%s' % (self.labelId, value))
        return r

    def getFormattedValue(self, obj, value, layoutType='view',
                          showChanges=False, language=None):
        '''Select-specific value formatting'''
        # Return an empty string if there is no p_value
        if Field.isEmptyValue(self, obj, value) and not showChanges: return ''
        if isinstance(self.validator, Selection):
            # Value(s) come from a dynamic vocabulary
            val = self.validator
            if self.isMultiValued():
                r = [val.getText(obj, v, self, language) for v in value]
            else:
                r = val.getText(obj, value, self, language)
        else:
            # Values come from a fixed vocabulary whose texts are in i18n files
            _ = self.getTranslatedValue
            if self.isMultiValued():
                r = [_(obj, v, language=language) for v in value]
            else:
                r = _(obj, value, language=language)
        return r

    def getPossibleValues(self, obj, withTranslations=False,
                          withBlankValue=False, blankLabel=None, className=None,
                          ignoreMasterValues=False):
        '''Returns the list of possible values for this field (only for fields
           with self.isSelect=True). If p_withTranslations is True, instead of
           returning a list of string values, the result is a list of tuples
           (s_value, s_translation). Moreover, p_withTranslations can hold a
           given language: in this case, this language is used instead of the
           user language. If p_withBlankValue is True, a blank value is
           prepended to the list, excepted if the type is multivalued. Used in
           combination with p_withTranslations being True, the i18n label for
           translating the blank value is given in p_blankLabel. If p_className
           is given, p_obj is the tool and, if we need an instance of
           p_className, we will need to use p_obj.executeQuery to find one.'''
        # Get the user language for translations, from p_withTranslations
        lg = isinstance(withTranslations, str) and withTranslations or None
        req = obj.REQUEST
        master = self.master
        aobj = obj.appy()
        if not ignoreMasterValues and master and callable(self.masterValue):
            # This field is an ajax-updatable slave. Get the master value...
            if master.valueIsInRequest(obj, req):
                # ... from the request if available
                requestValue = master.getRequestValue(obj)
                masterValues = master.getStorableValue(obj, requestValue,
                                                       complete=True)
            elif not className:
                # ... or from the database if we are editing an object
                if master.type == 'Ref':
                    masterValues = master.getValue(obj, noListIfSingleObj=True)
                else:
                    masterValues = master.getValue(obj)
            else:
                # We don't have any master value
                masterValues = None
            # Get possible values by calling self.masterValue
            if masterValues:
                values = self.masterValue(aobj, masterValues)
            else:
                values = []
            # Manage parameter p_withTranslations
            if not withTranslations: res = values
            else:
                res = []
                for v in values:
                    res.append((v, self.getFormattedValue(obj,v,language=lg)))
        else:
            # Get the possible values from attribute "validator"
            if isinstance(self.validator, Selection):
                # We need to call self.methodName for getting the (dynamic)
                # values. If methodName begins with _appy_, it is a special Appy
                # method: we will call it on the Mixin (=p_obj) directly. Else,
                # it is a user method: we will call it on the wrapper
                # (p_obj.appy()). Some args can be hidden into p_methodName,
                # separated with stars, like in this example: method1*arg1*arg2.
                # Only string params are supported.
                methodName = self.validator.methodName
                # Unwrap parameters if any.
                if methodName.find('*') != -1:
                    elems = methodName.split('*')
                    methodName = elems[0]
                    args = elems[1:]
                else:
                    args = ()
                # On what object must we call the method that will produce the
                # values?
                if methodName.startswith('tool:'):
                    obj = obj.getTool()
                    methodName = methodName[5:]
                else:
                    # We must call on p_obj. But if we have something in
                    # p_className, p_obj is the tool and not an instance of
                    # p_className as required. So find such an instance.
                    if className:
                        brains = obj.executeQuery(className, maxResults=1,
                                                  brainsOnly=True)
                        if brains:
                            obj = brains[0]._unrestrictedGetObject()
                # Do we need to call the method on the object or on the wrapper?
                if methodName.startswith('_appy_'):
                    exec 'res = obj.%s(*args)' % methodName
                else:
                    exec 'res = obj.appy().%s(*args)' % methodName
                if not withTranslations: res = [v[0] for v in res]
                elif isinstance(res, list): res = res[:]
            else:
                # The list of (static) values is in self.validator
                res = []
                for value in self.validator:
                    if withTranslations:
                        text = self.getTranslatedValue(obj, value, language=lg)
                        res.append((value, text))
                    else:
                        res.append(value)
        if (withBlankValue == 'forced') or \
           (withBlankValue and not self.isMultiValued()):
            # Create the blank value to insert at the beginning of the list
            if withTranslations:
                label = blankLabel or self.noValueLabel
                blankValue = ('', obj.translate(label, language=lg))
            else:
                blankValue = ''
            # Insert the blank value in the result
            if isinstance(res, tuple):
                res = (blankValue,) + res
            else:
                res.insert(0, blankValue)
        return res

    def validateValue(self, obj, value):
        '''Ensure p_value is among possible values'''
        possibleValues = self.getPossibleValues(obj, ignoreMasterValues=True)
        if isinstance(value, basestring):
            error = value not in possibleValues
        else:
            error = False
            for v in value:
                if v not in possibleValues:
                    error = True
                    break
        if error: return obj.translate('bad_select_value')

    def getStorableValue(self, obj, value):
        '''Get a multivalued value when appropriate'''
        if value and self.isMultiValued() and \
           (type(value) not in sutils.sequenceTypes):
            value = [value]
        return value

    def getIndexType(self): return 'ListIndex'

    def getIndexValue(self, obj, forSearch=False):
        '''Take care of empty values'''
        r = Field.getIndexValue(self, obj, forSearch)
        return ValidValue.forString(r, forSearch)
# ------------------------------------------------------------------------------
