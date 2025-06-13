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
    <x>::field.getInlineEditableValue(o, value, layout, name=name)</x>
    <input type="hidden" if="masterCss|None"
           class=":masterCss" value=":rawValue" name=":name" id=":name"/>''')

    edit = Px('''<x var="isTrue=field.isTrue(o, name, rawValue);
                         visibleName=name + '_visible'">
     <x if="field.render == 'checkbox'">
      <input type="checkbox" name=":visibleName" id=":name"
             class=":masterCss" checked=":isTrue"
             onclick=":field.getOnChange(o, layout)"/>
     </x>
     <x if="field.asRadios"
        var2="falseId=f'{name}_false';
              trueId=f'{name}_true';
              disabled=field.getDisabled(o)">
      <div class="flex1">
       <input type="radio" name=":visibleName" id=":falseId" class=":masterCss"
              value="False" checked=":not isTrue" disabled=":disabled"
              onclick=":field.getOnChange(o, layout)"/>
       <label lfor=":falseId"
              class="subLabel">::_(f'{field.labelId}_false')</label>
      </div>
      <div class="flex1">
       <input type="radio" name=":visibleName" id=":trueId" class=":masterCss"
              value="True" checked=":isTrue" disabled=":disabled"
              onclick=":field.getOnChange(o, layout)"/>
       <label lfor=":trueId"
              class="subLabel">::_(f'{field.labelId}_true')</label>
      </div>
     </x>
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
      inlineEdit=False, view=None, cell=None, buttons=None, edit=None,
      custom=None, xml=None, translations=None, falseMeansEmpty=False,
      disabled=False):
        # By default, a boolean is edited via a checkbox. It can also be edited
        # via 2 radio buttons (p_render="radios").
        self.render = render
        self.asRadios = render == 'radios'
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
        # Must p_self be shown, on "edit", in "disabled" mode? It works only if
        # p_self is rendered as a radio buttons.
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
        '''When rendering this field as a checkbox, must it be checked or
           not?'''
        req = o.req
        # Get the value we must compare (from request or from database)
        return req[name] in self.trueValues if name in req else dbValue
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
