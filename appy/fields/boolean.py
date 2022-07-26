# ~license~
# ------------------------------------------------------------------------------
from appy.fields import Field
from appy.px import Px
from appy.gen.layout import Table

# ------------------------------------------------------------------------------
class Boolean(Field):
    '''Field for storing boolean values'''
    yesNo = {'true': 'yes', 'false': 'no', True: 'yes', False: 'no'}
    trueFalse = {True: 'true', False: 'false'}

    # Default layout (render = "checkbox") ("b" stands for "base"), followed by
    # the 'grid' variant (if the field is in a group with 'grid' style).
    bLayouts = {'view': 'lf', 'edit': Table('f;lrv;-', width=None),
                'search': 'l-f'}
    gLayouts = {'view': 'fl', 'edit': Table('frvl', width=None),
                'search': 'l-f'}
    # Layout including a description (followed by grid variant)
    dLayouts = {'view': 'lf', 'edit': Table('flrv;=d', width=None)}
    # *d*escription also visible on "view"
    dvLayouts = {'view': 'lf-d', 'edit': dLayouts['edit']}
    gdLayouts = {'view': 'lf', 'edit': Table('f;dv-', width=None)}
    # Centered layout, no description
    cLayouts = {'view': 'lf|', 'edit': 'flrv|'}
    # Layout for radio buttons (render = "radios")
    rLayouts = {'edit': 'f', 'view': 'f', 'search': 'l-f'}
    rlLayouts = {'edit': 'l-f', 'view': 'lf', 'search': 'l-f'}
    grlLayouts = {'edit': 'fl', 'view': 'fl', 'search': 'l-f'}

    pxView = pxCell = Px('''
    <x>::field.getInlineEditableValue(obj, value, layoutType, name=name)</x>
    <input type="hidden" if="masterCss"
           class=":masterCss" value=":rawValue" name=":name" id=":name"/>''')

    pxEdit = Px('''<x var="isTrue=field.isTrue(zobj, name, rawValue);
                           visibleName=name + '_visible'">
     <x if="field.render == 'checkbox'">
      <input type="checkbox" name=":visibleName" id=":name"
             class=":masterCss" checked=":isTrue"
             onclick=":field.getOnChange(zobj, layoutType)"/>
     </x>
     <x if="field.render == 'radios'"
        var2="falseId='%s_false' % name;
              trueId='%s_true' % name">
      <input type="radio" name=":visibleName" id=":falseId" class=":masterCss"
             value="False" checked=":not isTrue"
             onclick=":field.getOnChange(zobj, layoutType)"/>
      <label lfor=":falseId">:_(field.labelId + '_false')</label><br/>
      <input type="radio" name=":visibleName" id=":trueId" class=":masterCss"
             value="True" checked=":isTrue"
             onclick=":field.getOnChange(zobj, layoutType)"/>
      <label lfor=":trueId">:_(field.labelId + '_true')</label>
     </x>
     <input type="hidden" name=":name" id=":'%s_hidden' % name"
            value=":isTrue and 'True' or 'False'"/>

     <script if="hostLayout" var2="x=zobj.setLock(user, field=field)">:\
       'prepareForAjaxSave(%s,%s,%s,%s)' % \
        (q(name),q(obj.id),q(obj.url),q(hostLayout))</script></x>''',

     js='''
      updateHiddenBool = function(elem) {
        // Determine the value of the boolean field
        var value = elem.checked,
            hiddenName = elem.name.replace('_visible', '_hidden');
        if ((elem.type == 'radio') && endsWith(elem.id,'_false')) value= !value;
        value = (value)? 'True': 'False';
        // Set this value in the hidden field
        document.getElementById(hiddenName).value = value;
      }''')

    pxSearch = Px('''
      <x var="valueId='%s_yes' % name">
       <input type="radio" value="True" name=":widgetName" id=":valueId"/>
       <label lfor=":valueId">:_(field.getValueLabel(True))</label>
      </x>
      <x var="valueId='%s_no' % name">
       <input type="radio" value="False" name=":widgetName" id=":valueId"/>
       <label lfor=":valueId">:_(field.getValueLabel(False))</label>
      </x>
      <x var="valueId='%s_whatever' % name">
       <input type="radio" value="" name=":widgetName" id=":valueId"
              checked="checked"/>
       <label lfor=":valueId">:_('whatever')</label>
      </x><br/>''')

    def __init__(self, validator=None, multiplicity=(0,1), default=None,
      defaultOnEdit=None, show=True, page='main', group=None, layouts = None,
      move=0, indexed=False, mustIndex=True, indexValue=None, searchable=False,
      specificReadPermission=False, specificWritePermission=False, width=None,
      height=None, maxChars=None, colspan=1, master=None, masterValue=None,
      focus=False, historized=False, mapping=None, generateLabel=None,
      label=None, sdefault=False, scolspan=1, swidth=None, sheight=None,
      persist=True, render='checkbox', inlineEdit=False, view=None, cell=None,
      edit=None, xml=None, translations=None):
        # By default, a boolean is edited via a checkbox. It can also be edited
        # via 2 radio buttons (p_render="radios").
        self.render = render
        Field.__init__(self, validator, multiplicity, default, defaultOnEdit,
          show, page, group, layouts, move, indexed, mustIndex, indexValue,
          searchable, specificReadPermission, specificWritePermission, width,
          height, None, colspan, master, masterValue, focus, historized,
          mapping, generateLabel, label, sdefault, scolspan, swidth, sheight,
          persist, inlineEdit, view, cell, edit, xml, translations)
        self.pythonType = bool

    def getDefaultLayouts(self):
        if self.render == 'radios': return Boolean.rLayouts
        return self.inGrid() and Boolean.gLayouts or Boolean.bLayouts

    def getValue(self, obj, name=None, layout=None):
        '''Never returns "None". Returns always "True" or "False", even if
           "None" is stored in the DB.'''
        value = Field.getValue(self, obj, name, layout)
        if value is None: return False
        return value

    def getValueLabel(self, value):
        '''Returns the label for p_value (True or False): if self.render is
           "checkbox", the label is simply the translated version of "yes" or
           "no"; if self.render is "radios", there are specific labels.'''
        if self.render == 'radios':
            return '%s_%s' % (self.labelId, self.trueFalse[value])
        return self.yesNo[value]

    def getFormattedValue(self, obj, value, layoutType='view',
                          showChanges=False, language=None):
        return obj.translate(self.getValueLabel(value), language=language)

    def getMasterTag(self, layoutType):
        '''The tag driving slaves is the hidden field'''
        return (layoutType == 'edit') and ('%s_hidden' % self.name) or self.name

    def getOnChange(self, zobj, layoutType, className=None):
        '''Updates the hidden field storing the actual UI value for the field'''
        r = 'updateHiddenBool(this)'
        # Call the base behaviour
        base = Field.getOnChange(self, zobj, layoutType, className=className)
        return base and '%s; %s' % (r, base) or r

    def getStorableValue(self, obj, value, complete=False):
        if not self.isEmptyValue(obj, value):
            exec 'r = %s' % value
            return r

    def getSearchValue(self, form):
        '''Converts the raw search value from p_form into a boolean value'''
        r = Field.getSearchValue(self, form)
        exec 'r = %s' % r
        return r

    def isSortable(self, usage):
        '''Can this field be sortable ?'''
        if usage == 'search': return Field.isSortable(self, usage)
        return True # Sortable in Ref fields

    def isTrue(self, obj, name, dbValue):
        '''When rendering this field as a checkbox, must it be checked or
           not?'''
        rq = obj.REQUEST
        # Get the value we must compare (from request or from database)
        if rq.has_key(name):
            return rq.get(name) in ('True', 1, '1')
        return dbValue
# ------------------------------------------------------------------------------
