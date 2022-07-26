# ~license~
# ------------------------------------------------------------------------------
from appy.px import Px
from appy.fields import Field

# ------------------------------------------------------------------------------
class Color(Field):
    '''Field representing a color'''

    pxView = pxCell = Px('''
     <input type="color" disabled=":True" value=":value or '#000000'"
            name=":name" id=":name"/>''')

    pxEdit = pxSearch = Px('''
     <input type="color" id=":name" name=":name" size=":field.width"
            value=":field.getInputValue(inRequest, requestValue, value)"/>
     <script if="hostLayout">:'prepareForAjaxSave(%s,%s,%s,%s)' % \
      (q(name),q(obj.id),q(obj.url),q(hostLayout))</script>''')

    def __init__(self, validator=None, multiplicity=(0,1), default=None,
      defaultOnEdit=None, show=True, page='main', group=None, layouts=None,
      move=0, indexed=False, mustIndex=True, indexValue=None, searchable=False,
      specificReadPermission=False, specificWritePermission=False, width=5,
      height=None, maxChars=13, colspan=1, master=None, masterValue=None,
      focus=False, historized=False, mapping=None, generateLabel=None,
      label=None, sdefault=('',''), scolspan=1, swidth=None, sheight=None,
      persist=True, inlineEdit=False, view=None, cell=None, edit=None, xml=None,
      translations=None):
        # Call the base constructor
        Field.__init__(self, validator, multiplicity, default, defaultOnEdit,
          show, page, group, layouts, move, indexed, mustIndex, indexValue,
          searchable, specificReadPermission, specificWritePermission, width,
          height, maxChars, colspan, master, masterValue, focus, historized,
          mapping, generateLabel, label, sdefault, scolspan, swidth, sheight,
          persist, inlineEdit, view, cell, edit, xml, translations)
        # Define the corresponding Python type for values stored for this type
        self.pythonType = str
# ------------------------------------------------------------------------------
