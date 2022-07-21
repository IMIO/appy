# -*- coding: utf-8 -*-

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.px import Px
from appy import utils
from appy.model.fields import Field
from appy.ui.layout import Layouts, Layout
from appy.database.operators import Operator

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
emptyList = []

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
RADIOS_KO  = 'You cannot render this field as radio buttons if it may ' \
             'contain several values (max multiplicity is higher than 1).'
CBS_KO     = 'You cannot render this field as checkboxes if it can ' \
             'only contain a single value (max multiplicity is 1).'
IEDIT_KO   = 'It is currently not possible to inline-edit a multi-' \
             'valued Select field.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Selection:
    '''If you want to have dynamically computed possible values for a Select
       field, use a Selection instance.'''

    def __init__(self, method, single=None):
        # p_method must be a method that will be called every time Appy will
        # need to get the list of possible values for the related field.
        #  - p_method can be the method object in itself, or the method name.
        #  - it can be (or correspond to) an instance method of the class
        #    defining the related field; it can also refer to a method defined
        #    on the tool. In this latter case, you are forced to define a method
        #    name (not a method object), prefixed with "tool:".

        # m_method, in most cases, accepts no arg and return a list (or tuple)
        # of pairs (lists or tuples): (id, text), where:
        #   - "id" is one of the possible values for the field;
        #   - "text" is the value as will be shown in the UI.
        # You can nevertheless specify args to the method. In that case, specify
        # the method name, followed by args separated with stars, like in
        #
        #                      method1*arg1*arg2
        #
        # Only string args are supported.
        # Within m_method, you will usually call the standard translation method
        # (m_translate) to produce an i18n version of "text".
        self.method = method

        # While p_method is called on edit and filter layouts to list the
        # possible values to select, the method you specify in p_single allows
        # to produce the translated text for a single value. It accepts a single
        # arg, being one of the values as stored by the select field, and must
        # return its translated text. If you don't specify a p_single method,
        # p_method will be used instead, but useless processing will take place,
        # because p_method produces texts for the complete list of possible
        # values. Moreover, a stored select value may not be among the list of
        # values as returned by p_method anymore.
        self.single = single

    def getText(self, o, value, field, language=None):
        '''Gets the text that corresponds to p_value'''
        # Use method p_single if specified
        if self.single: return self.single(o, value)
        # Use p_self.method
        withTranslations = language if language else True
        vals = field.getPossibleValues(o, ignoreMasterValues=True,
                                       withTranslations=withTranslations)
        for v, text in vals:
            if v == value: return text
        return value

    def getValues(self, o, className=None):
        '''Gets the translated values in this selection'''
        method = self.method
        # Call self.method for getting the (dynamic) values
        if isinstance(method, str):
            # This is the name of a method, not the method itself. Unwrap args
            # if any.
            if method.find('*') != -1:
                elems = method.split('*')
                method = elems[0]
                args = elems[1:]
            else:
                args = []
            # On what object must we call the method ?
            if method.startswith('tool:'):
                o = o.tool
                method = method[5:]
            # Get the method from its name
            method = getattr(o, method)
        else:
            args = [o]
        # If a p_className is given, transmit the corresponding class as method
        # arg.
        if className:
            args.append(o.model.classes.get(className))
        # Call the method
        try:
            r = method(*args)
        except TypeError:
            args.pop()
            r = method(*args)
        return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Select(Field):
    '''Field allowing to choose a value among a list of possible values. Each
       value is represented and stored as a string.'''

    class Layouts(Layouts):
        '''Select-specific layouts'''
        d  = Layouts(Layout('d2-l-f;rv=', width=None))
        # With a description, but no label
        dn = Layouts(Layout('d-frv=', width=None))
        # Within grid groups
        g  = Layouts(edit=Layout('f;rv=', width=None),
                     view=Layout('fl', width=None))
        gd = Layouts(edit=Layout('d;rv=-f2=', width=None),
                     view=Layout('fl', width=None))
        gh = Layouts(edit=Layout('f;hrv=', width=None), view=gd['view'])

        @classmethod
        def getDefault(class_, field):
            '''Default layouts for this Select p_field'''
            return class_.g if field.inGrid() else class_.b

    view = Px('''
     <!-- No value at all -->
     <span if="not value" class="smaller">-</span>
     <!-- A single value -->
     <x if="value and not isMultiple">::field.getInlineEditableValue(o, \
                                          value, layout, name=name)</x>
     <!-- Several values -->
     <ul if="value and isMultiple"><li for="sv in value"><i>::sv</i></li></ul>
     <!-- If this field is a master field -->
     <input type="hidden" if="masterCss" class=":masterCss" value=":rawValue"
            name=":name" id=":name"/>''')

    # More compact representation on cell and button layouts
    cell = buttons = Px('''
     <x var="isMultiple=value and field.isMultiValued(); masterCss=None">
      <x if="isMultiple">:', '.join(value)</x>
      <x if="not isMultiple">:field.view</x>
     </x>''')

    edit = Px('''
     <x var="isSelect=field.render == 'select';
             possibleValues=field.getPossibleValues(o, withTranslations=True, \
               withBlankValue=isSelect);
             charsWidth=field.getWidthInChars(False)">

     <!-- As a "select" widget -->
     <select if="isSelect" name=":name" id=":name" class=":masterCss"
       multiple=":isMultiple" onchange=":field.getOnChange(o, layout)"
       size=":field.getSelectSize(False, isMultiple)"
       style=":field.getSelectStyle(False, isMultiple)">
      <option for="val, text in possibleValues" value=":val"
              selected=":field.isSelected(o, name, val, rawValue)"
              title=":text">:Px.truncateValue(text, charsWidth)</option>
     </select>

     <!-- As radio buttons or checkboxes -->
     <div if="not isSelect" style=":field.getWidgetStyle()">

      <!-- (Un)check all -->
      <div if="field.render == 'checkbox' and len(possibleValues) &gt; 1"
           class="divAll" var="allId='%s_all' % name">
       <input type="checkbox" class="checkAll" id=":allId" name=":allId"
              onclick="toggleCheckboxes(this)"/>
       <label lfor=":allId">:_('check_uncheck')</label>
      </div>

      <div for="val, text in possibleValues" class="flex1"
           var2="vid='%s_%s' % (name, val)">
       <input type=":field.render" name=":name" id=":vid" value=":val"
              class=":masterCss" onchange=":field.getOnChange(o, layout)"
              checked=":field.isSelected(o, name, val, rawValue)"/>
       <label lfor=":vid" class="subLabel">:text</label>
      </div>
     </div>
     <script if="hostLayout" var2="x=o.Lock.set(o, user, field=field)">:\
      'prepareForAjaxSave(%s,%s,%s,%s)' % \
       (q(name), q(o.iid), q(o.url), q(hostLayout))</script></x>''')

    # On the search form, show a multi-selection widget with a "AND/OR" selector
    search = Px('''
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
       onchange=":field.getOnChange(tool, 'search', className)">
      <option for="val, text in field.getPossibleValues(tool, \
            withTranslations=True, withBlankValue=False, className=className)"
        selected=":val in preSelected" value=":val"
        title=":text">:Px.truncateValue(text, charsWidth)</option>
     </select><br/>''')

    # Widget for filtering object values on search results
    pxFilter = Px('''
     <div class="dropdownMenu fdrop"
          var="name=field.name;
               charsWidth=field.getWidthInChars(True)"
          onmouseover="toggleDropdown(this)"
          onmouseout="toggleDropdown(this,'none')">
        <img src=":svg('fdrop')"/>
        <span if="name in mode.filters">›</span>

       <!-- The menu -->
       <div class="dropdown fdown" style=":field.getWidgetStyle('f')">
        <div for="val, text in field.getPossibleValues(tool,
                   withTranslations=True, withBlankValue='forced',
                   blankLabel='everything', className=className)">
         <x if="mode.inFilter(name, val)">→ </x>
         <a onClick=":'askBunchFiltered(%s,%s,%s)' % (q(mode.hook), q(name),
              q(val))" title=":text">::Px.truncateValue(text, charsWidth)</a>
        </div>
       </div>
     </div>''')

    def __init__(self, validator=None, multiplicity=(0,1), default=None,
      defaultOnEdit=None, show=True, renderable=None, page='main', group=None,
      layouts=None, move=0, indexed=False, mustIndex=True, indexValue=None,
      emptyIndexValue='-', searchable=False, filterField=None,
      readPermission='read', writePermission='write', width=None, height=None,
      maxChars=None, colspan=1, master=None, masterValue=None, focus=False,
      historized=False, mapping=None, generateLabel=None, label=None,
      sdefault='', scolspan=1, swidth=None, sheight=None, fwidth='7em',
      fheight=None, persist=True, inlineEdit=False, view=None, cell=None,
      buttons=None, edit=None, xml=None, translations=None,
      noValueLabel='choose_a_value', render='select', svalidator=None):
        # When choosing a value in a select widget, the entry representing no
        # value is translated according the label defined in attribute
        # "noValueLabel". The default one is something like "[ choose ]", but if
        # you prefer a less verbose version, you can use "no_value" that simply
        # displays a dash, or your own label.
        self.noValueLabel = noValueLabel
        # A Select field, is, by default, rendered as a HTML select widget, but
        # there are alternate render modes. Here are all the possible render
        # modes.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  render    | The field is rendered as...
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "select"   | an HTML select widget, rendered as a dropdown list if
        #            | max multiplicity is 1 or as a selection box if several
        #            | values can be chosen.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "radio"    | radio buttons. This mode is valid for fields with a max
        #            | multiplicity being 1.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "checkbox" | checkboxes. This mode is valid for fields with a max
        #            | multiplicity being higher than 1.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.render = render
        # Call the base constructor
        Field.__init__(self, validator, multiplicity, default, defaultOnEdit,
          show, renderable, page, group, layouts, move, indexed, mustIndex,
          indexValue, emptyIndexValue, searchable, filterField, readPermission,
          writePermission, width, height, maxChars, colspan, master,
          masterValue, focus, historized, mapping, generateLabel, label,
          sdefault, scolspan, swidth, sheight, persist, inlineEdit, view, cell,
          buttons, edit, xml, translations)
        # Default value on the *s*earch form. It must be a list of values.
        self.sdefault = sdefault or []
        # Validator to use on the *s*earch form. This has sense only if you use
        # a Selection instance as validator.
        self.svalidator = svalidator or validator
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
        # The *f*ilter width and height
        self.fwidth = fwidth
        self.fheight = fheight
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

    def isSelected(self, o, name, possibleValue, dbValue):
        '''When displaying a Select field, must the p_possibleValue appear as
           selected? p_name is given and used instead of field.name because it
           may contain a row number from a field within a List field.'''
        req = o.req
        # Get the value we must compare (from request or from database)
        if name in req:
            compValue = req[name]
        else:
            compValue = dbValue
        # Compare the value
        if type(compValue) in utils.sequenceTypes:
            return possibleValue in compValue
        return possibleValue == compValue

    def getValue(self, o, name=None, layout=None, single=None):
        value = Field.getValue(self, o, name, layout, single)
        if not value:
            return emptyList if self.isMultiValued() else value
        if isinstance(value, str) and self.isMultiValued():
            value = [value]
        elif isinstance(value, tuple):
            value = list(value)
        return value

    def getTranslatedValue(self, o, value, language=None):
        '''Get the translated text for p_value, when p_value is one of p_self's
           authorized "static" values according to its p_self.validator (being a
           list or tuple o values).'''
        if self.translations:
            # Translations are available via a FieldTranslations instance
            language = language or o.guard.userLanguage
            r = self.translations.get('value', language, value=value)
        else:
            r = o.translate('%s_list_%s' % (self.labelId, value))
        return r

    def getFormattedValue(self, o, value, layout='view', showChanges=False,
                          language=None):
        '''Select-specific value formatting'''
        # Return an empty string if there is no p_value
        if Field.isEmptyValue(self, o, value) and not showChanges: return ''
        if isinstance(self.validator, Selection):
            # Value(s) come from a dynamic vocabulary
            val = self.validator
            if self.isMultiValued():
                r = [val.getText(o, v, self, language) for v in value]
            else:
                r = val.getText(o, value, self, language)
        else:
            # Values come from a fixed vocabulary whose texts are in i18n files
            _ = self.getTranslatedValue
            if self.isMultiValued():
                r = [_(o, v, language=language) for v in value]
            else:
                r = _(o, value, language=language)
        return r

    def getSearchValue(self, req, value=None):
        '''The search value as encoded in a search form for a Select field can
           be a simple string value or a list of values with an and/or
           operator.'''
        r = Field.getSearchValue(self, req, value=value)
        if isinstance(r, list):
            # It is a list of values. Get the operator to use.
            r = Operator.fromRequest(req, self.name)(*r)
        return r

    def getPossibleValues(self, o, withTranslations=False,
                          withBlankValue=False, blankLabel=None, className=None,
                          ignoreMasterValues=False):
        '''Returns the list of possible values for this field.
           If p_withTranslations is True, instead of returning a list of string
           values, the result is a list of tuples (s_value, s_translation).
           Moreover, p_withTranslations can hold a given language: in this case,
           this language is used instead of the user language. If
           p_withBlankValue is True, a blank value is prepended to the list,
           excepted if the type is multivalued. Used in combination with
           p_withTranslations being True, the i18n label for translating the
           blank value is given in p_blankLabel. If p_className is given, p_o is
           the tool and we are called from a context where no object is
           available (ie, a search form).'''
        # Get the user language for translations, from p_withTranslations
        lg = isinstance(withTranslations, str) and withTranslations or None
        req = o.req
        master = self.master
        if not ignoreMasterValues and master and callable(self.masterValue):
            # This field is an ajax-updatable slave. Get the master value...
            if master.valueIsInRequest(o, req):
                # ... from the request if available
                requestValue = master.getRequestValue(o)
                masterValues = master.getStorableValue(o, requestValue,
                                                       single=True)
            elif not className:
                # ... or from the database if we are editing an object
                masterValues = master.getValue(o, single=True)
            else:
                # We don't have any master value
                masterValues = None
            # Get possible values by calling self.masterValue
            if masterValues:
                values = self.masterValue(o, masterValues)
            else:
                values = []
            # Manage parameter p_withTranslations
            if not withTranslations: res = values
            else:
                res = []
                for v in values:
                    # Translations may already have been included
                    if not isinstance(v ,tuple):
                        v = (v, self.getFormattedValue(o,v,language=lg))
                    res.append(v)
        else:
            # Get the possible values from attribute "[s]validator"
            validator = self.svalidator if className else self.validator
            if isinstance(validator, Selection):
                res = validator.getValues(o, className)
                if not withTranslations: res = [v[0] for v in res]
                elif isinstance(res, list): res = res[:]
            else:
                # The list of (static) values is in self.validator
                res = []
                for value in validator:
                    if withTranslations:
                        text = self.getTranslatedValue(o, value, language=lg)
                        res.append((value, text))
                    else:
                        res.append(value)
        if (withBlankValue == 'forced') or \
           (withBlankValue and not self.isMultiValued()):
            # Create the blank value to insert at the beginning of the list
            if withTranslations:
                label = blankLabel or self.noValueLabel
                blankValue = ('', o.translate(label, language=lg))
            else:
                blankValue = ''
            # Insert the blank value in the result
            if isinstance(res, tuple):
                res = (blankValue,) + res
            else:
                res.insert(0, blankValue)
        return res

    def validateValue(self, o, value):
        '''Ensure p_value is among possible values'''
        possibleValues = self.getPossibleValues(o, ignoreMasterValues=True)
        # In the context of a slave whose possible values depend on the selected
        # master, while the object is temp, possible values could not have been
        # computed yet.
        if not possibleValues: return
        if isinstance(value, str):
            error = value not in possibleValues
        else:
            error = False
            for v in value:
                if v not in possibleValues:
                    error = True
                    break
        if error: return o.translate('bad_select_value')

    def getStorableValue(self, o, value, single=False):
        '''Get a multivalued value when appropriate'''
        if value and self.isMultiValued() and \
           type(value) not in utils.sequenceTypes:
            value = [value]
        return value
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
