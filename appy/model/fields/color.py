#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy import n
from appy.px import Px
from appy.model.fields import Field

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Color(Field):
    '''Field representing a color'''

    view = cell = buttons = Px('''
     <input type="color" disabled=":True" value=":value or '#000000'"
            name=":name" id=":name"/>''')

    edit = search = Px('''
     <input type="color" id=":name" name=":name" size=":field.width"
            value=":field.getInputValue(inRequest, requestValue, value)"/>
     <script if="hostLayout">:'prepareForAjaxSave(%s,%s,%s,%s)' % \
      (q(name), q(o.iid), q(o.url), q(hostLayout))</script>''')

    def __init__(self, validator=n, multiplicity=(0,1), default=n,
      defaultOnEdit=n, show=True, renderable=n, page='main', group=n, layouts=n,
      move=0, indexed=False, mustIndex=True, indexValue=n, emptyIndexValue='-',
      searchable=False, filterField=n, readPermission='read',
      writePermission='write', width=5, height=n, maxChars=13, colspan=1,
      master=n, masterValue=n, masterSnub=n, focus=False, historized=False,
      mapping=n, generateLabel=n, label=n, sdefault=n, scolspan=1, swidth=n,
      sheight=n, persist=True, inlineEdit=False, view=n, cell=n, buttons=n,
      edit=n, custom=n, xml=n, translations=n):

        # Call the base constructor
        super().__init__(validator, multiplicity, default, defaultOnEdit, show,
          renderable, page, group, layouts, move, indexed, mustIndex,
          indexValue, emptyIndexValue, searchable, filterField, readPermission,
          writePermission, width, height, maxChars, colspan, master,
          masterValue, masterSnub, focus, historized, mapping, generateLabel,
          label, sdefault, scolspan, swidth, sheight, persist, inlineEdit, view,
          cell, buttons, edit, custom, xml, translations)

        # Define the corresponding Python type for values stored for this type
        self.pythonType = str

        # The "Color" HTML field requires a default value
        if not default:
            self.default = '#000000' # Black
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
