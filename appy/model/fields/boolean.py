#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.px import Px
from appy.model.fields import Field
from appy.ui.layout import Layouts, Layout

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Boolean(Field):
    '''Field for storing boolean values'''

    yesNo = {'true': 'yes', 'false': 'no', True: 'yes', False: 'no'}
    trueFalse = {True: 'true', False: 'false'}

    # Values coming from the request and being considered as True
    trueValues = ('True', 1, '1')

    # In some situations, if may be appropriate to consider False as an empty
    # value for a boolean field.
    nullValuesVariants = {
      True:  (None, False), # False is considered to represent emptiness
      False: (None,)        # False does not represent emptiness
    }

    class Layouts(Layouts):
        '''Boolean-specific layouts'''

        es = 'f;lrv;-'
        ds = 'flrv;=d'

        # Default layout (render = "checkbox") ("b" stands for "base"), followed
        # by the "grid" variant (if the field is in a group with "grid" style).
        b   = Layouts(edit=Layout(es,        width=None),   view='lf')
        g   = Layouts(edit=Layout('frvl',    width=None),   view='fl')
        d   = Layouts(edit=Layout(ds,        width=None),   view='lf')
        t   = Layouts(edit=Layout(es, width=None, css='topSpace'), view='lf')

        # With bottom space
        bP  = {'css': 'bottomSpaceS'}
        bb  = Layouts(edit=Layout('fl', **bP)  , view=Layout('lf', **bP))
        bbd = Layouts(edit=Layout('fl-d', **bP), view=Layout('lf', **bP))

        # *d*escription also visible on "view"
        dv = Layouts(edit=d['edit'], view='lf-d')

        # *d*escription, with *t*op space
        dt  = Layouts(edit=Layout(ds, width=None, css='topSpace'), view='lf')
        h   = Layouts(edit=Layout('flhv',    width=None),   view='lf')
        dh  = Layouts(edit=Layout('flhv-d',  width=None),   view='lf')
        gd  = Layouts(edit=Layout('f;dv-',   width=None),   view='fl')

        # The base layout, plus bottom space
        bs = Layouts(edit=Layout(es, width=None, css='bottomSpaceS'), view='lf')

        # The "long" version of the previous layout (if the description is
        # long), with vertical alignment on top instead of middle.
        gdl = Layouts(edit=Layout('f;dv=',   width=None),   view='fl')

        # Centered layout, no description
        c   = Layouts(edit='flrv|',                         view='lf|')

        # Layout for radio buttons (render = "radios")
        r   = Layouts(edit='f',                             view='f')
        rl  = Layouts(edit='l-f',                           view='lf')
        rld = Layouts(edit='l-d-f',                         view='lf')
        grl = Layouts(edit='fl',                            view='fl')
        gdr = Layouts(edit=Layout('d-fv=',   width=None),   view='fl')
        rt = r.clone(css='topSpace')

        @classmethod
        def getDefault(class_, field):
            '''Default layouts for this Boolean p_field'''
            if field.asRadios: return class_.r
            return class_.g if field.inGrid() else class_.b

    # The name of the index class storing values of this field in the catalog
    indexType = 'BooleanIndex'

    view = cell = buttons = Px('''
    <x var="asSwitch=field.renderAsSwitch(_ctx_)">
     <x if="not asSwitch">::field.getInlineEditableValue(o, value, layout,
                                                         name=name)</x>
     <x if="asSwitch"
        var2="disabled=field.getDisabled(o);
              css='unallowed' if disabled else 'clickable'">
      <img var="icon=field.getSwitchIcon(_ctx_); newVal=not rawValue"
           src=":svg(icon)" class=":f'{css} iconL'"
           title=":disabled if disabled else ''"
           onclick=":field.getJsSwitch(_ctx_)"/>
     </x>
    </x>
    <input type="hidden" if="masterCss|None"
           class=":masterCss" value=":rawValue" name=":name" id=":name"/>''')

    edit = Px('''<x var="isTrue=field.isTrue(o, name, rawValue);
                         visibleName=f'{name}_visible'">
     <x if="not field.asRadios">
      <input type="checkbox" name=":visibleName" id=":name"
             class=":masterCss" checked=":isTrue"
             onclick=":field.getOnChange(o, layout)"/>
     </x>
     <x if="field.asRadios"
        var2="disabled=field.getDisabled(o)">::field.getRadios(_ctx_)</x>

     <input type="hidden" name=":name" id=":f'{name}_hidden'"
            value=":'True' if isTrue else 'False'"/>

     <script if="hostLayout" var2="x=o.Lock.set(o, field=field)">:\
      'prepareForAjaxSave(%s,%s,%s,%s)' % \
       (q(name), q(o.iid), q(o.url), q(hostLayout))</script></x>''',

     js='''
      updateHiddenBool = function(elem) {
        // Determine the value of the boolean field
        var value = elem.checked,
            hiddenName = elem.name.replace('_visible', '_hidden');
        if ((elem.type == 'radio') && elem.id.endsWith('_false')) value= !value;
        value = (value)? 'True': 'False';
        // Set this value in the hidden field
        document.getElementById(hiddenName).value = value;
      }''')

    search = Px('''
      <x var="valueId=f'{name}_yes'">
       <input type="radio" value="True" name=":widgetName" id=":valueId"/>
       <label lfor=":valueId">:_(field.getValueLabel(True))</label>
      </x>
      <x var="valueId=f'{name}_no'">
       <input type="radio" value="False" name=":widgetName" id=":valueId"/>
       <label lfor=":valueId">:_(field.getValueLabel(False))</label>
      </x>
      <x var="valueId=f'{name}_whatever'">
       <input type="radio" value="" name=":widgetName" id=":valueId"
              checked="checked"/>
       <label lfor=":valueId">:_('whatever')</label>
      </x><br/>''')

    def __init__(self, validator=None, multiplicity=(0,1), default=None,
      defaultOnEdit=None, show=True, renderable=None, page='main', group=None,
      layouts=None, move=0, indexed=False, mustIndex=True, indexValue=None,
      searchable=False, filterField=None, readPermission='read',
      writePermission='write', width=None, height=None, maxChars=None,
      colspan=1, master=None, masterValue=None, focus=False, historized=False,
      mapping=None, generateLabel=None, label=None, sdefault=False, scolspan=1,
      swidth=None, sheight=None, persist=True, render='checkbox',
      falseFirst=True, inlineEdit=False, view=None, cell=None, buttons=None,
      edit=None, custom=None, xml=None, translations=None,
      falseMeansEmpty=False, disabled=False, confirm=False):

        # The following p_render modes are available.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "checkbox" | (the default) The boolean field is render as a checkbox
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "radios"   | The field is rendered via 2 radio buttons, with custom
        #            | labels corresponding to the 2 truth values.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "switch"   | The field is rendered as a checkbox on the edit layout,
        #            | but as a clickable, button-like "on/off" switch on the
        #            | view/cell layout (for those having write permission).
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.render = render
        self.asRadios = render == 'radios'

        # When render is "radios", in what order should the buttons appear ?
        self.falseFirst = falseFirst

        # When render is "switch", the field may be rendered on button layouts
        if renderable is None and render == 'switch':
            renderable = Layouts.onButtons

        # When render is "switch", and p_self.confirm is True, when clicking on
        # the switch, a confirmation popup will appear first. In that case, 2
        # i18n labels will be generated: one as confirmation text before
        # switching to False, another as confirmation text for switching to
        # True. Setting p_self.confirm to True for a Boolean field whose render
        # mode is not "switch" has no effect.
        self.confirm = confirm

        # Call the base constructor
        super().__init__(validator, multiplicity, default, defaultOnEdit, show,
          renderable, page, group, layouts, move, indexed, mustIndex,
          indexValue, None, searchable, filterField, readPermission,
          writePermission, width, height, None, colspan, master, masterValue,
          focus, historized, mapping, generateLabel, label, sdefault, scolspan,
          swidth, sheight, persist, inlineEdit, view, cell, buttons, edit,
          custom, xml, translations)
        self.pythonType = bool

        # Must value False be interpreted as an empty value or not ?
        self.nullValues = Boolean.nullValuesVariants[falseMeansEmpty]

        # Must the edit widget, for p_self, be rendered as a disabled widget ?
        # It it only applicable:
        # - when render mode is "radios", on the "edit" layout,
        # - when render mode is "switch", when the switch is actually rendered.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # When render | p_disabled must be ...
        # mode is ... |
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "radios"    | a boolean value or a method computing it ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "switch"    | a method returning False or None if the widget must be
        #             | enabled, or returning a translated text if the widget
        #             | must be enabled. This text will appear as a tooltip on
        #             | on the switch.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.disabled = disabled

    def getValue(self, o, name=None, layout=None, single=None, at=None):
        '''Do not return "None": return "True" or "False", even if "None" is
           stored in the DB (or no value is stored), excepted if render is
           "radios".'''
        value = super().getValue(o, name, layout, single, at)
        if self.asRadios:
            return value # Can be None
        # In any other case, value is always True or False
        return False if value is None else value

    def getValueLabel(self, value):
        '''Returns the label for p_value (True or False): if self.render is
           "checkbox", the label is simply the translated version of "yes" or
           "no"; if self.render is "radios", there are specific labels.'''
        if self.asRadios:
            if value is None:
                r = '-'
            else:
                r = f'{self.labelId}_{self.trueFalse[value]}'
            return r
        return self.yesNo[bool(value)]

    def getFormattedValue(self, o, value, layout='view', showChanges=False,
                          language=None):
        return o.translate(self.getValueLabel(value), language=language)

    def getMasterTag(self, layout):
        '''The tag driving slaves is the hidden field'''
        return f'{self.name}_hidden' if layout == 'edit' else self.name

    def getOnChange(self, o, layout, className=None):
        '''Updates the hidden field storing the actual UI value for the field'''
        r = 'updateHiddenBool(this)'
        # Call the base behaviour
        base = Field.getOnChange(self, o, layout, className=className)
        return f'{r};{base}' if base else r

    def getStorableValue(self, o, value, single=False):
        '''Converts this string p_value to a boolean value'''
        if not self.isEmptyValue(o, value):
            r = eval(value)
            return r

    def getSearchValue(self, req, value=None):
        '''Converts the raw search value from p_form into a boolean value'''
        return eval(Field.getSearchValue(self, req, value=value))

    def isSortable(self, inRefs=False):
        '''Can this field be sortable ?'''
        return True if inRefs else Field.isSortable(self) # Sortable in Refs

    def isTrue(self, o, name, dbValue):
        '''When the UI widget is rendered, must it store True or False ?'''
        req = o.req
        # Get the value we must compare (from request or from database)
        return req[name] in self.trueValues if name in req else dbValue

    # Template for a radio button
    radioTemplate = '<div class="flex1"><input type="radio" name="%s" id="%s"' \
                    ' class="%s" value="%s"%s%s onclick="%s"/><label for="%s"' \
                    ' class="subLabel">%s</label></div>'''

    def getRadioButton(self, c, value):
        '''Renders a radio button for this p_value, being True or False'''
        # Get the boolean p_value as a lowered string
        o = c.o
        sval = str(value).lower()
        # Get the HTML input ID
        widgetId = f'{c.name}_{sval}'
        # Is the radio disabled ?
        disabled = ' disabled="disabled"' if c.disabled else ''
        # Is the radio checked ?
        checked = value == c.isTrue
        checked = ' checked="checked"' if checked else ''
        label = f'{self.labelId}_{sval}'
        # Produce the complete button
        return self.radioTemplate % (c.visibleName, widgetId, c.masterCss,
                                    str(value), checked, disabled,
                                    self.getOnChange(o, c.layout), widgetId,
                                    o.translate(label))

    def getRadios(self, c):
        '''Renders radio buttons for a boolean field with render = "radios"'''
        true = self.getRadioButton(c, True)
        false = self.getRadioButton(c, False)
        return f'{false}{true}' if self.falseFirst else f'{true}{false}'

    def renderAsSwitch(self, c):
        '''Must p_self be rendered as a switch ?'''
        # Yes, if we are not on the edit layout and the user has write access to
        # p_self.
        return c.layout != 'edit' and c.o.allows(c.field.writePermission)

    def getSwitchIcon(self, c):
        '''Returns the switch icon to show, depending on p_self's value on this
           p_o(bject).'''
        return 'on' if c.rawValue else 'off'

    def getJsSwitch(self, c):
        '''Get the JS code to execute for switching the field value'''
        if c.disabled: return
        newVal = str(c.newVal)
        r = f"askField('{c.tagId}','{c.o.url}','cell'," \
            f"{{'action':'storeFromAjax','fieldContent':'{str(c.newVal)}'}})"
        if self.confirm:
            # Compute the confirmation text
            suffix = newVal.lower()
            text = c._(f'{self.labelId}_confirm_{suffix}')
            # Wrap the call into a askConfirm
            r = f"askConfirm('script',`{r}`,{c.q(text)})"
        return r
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
