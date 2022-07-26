# ~license~
# ------------------------------------------------------------------------------
from appy.fields import Field, Layouts

# ------------------------------------------------------------------------------
class Info(Field):
    '''An info is a field whose purpose is to present information
       (text, html...) to the user.'''
    # An info only displays a label. So PX for showing content are empty.
    pxView = pxEdit = pxCell = pxSearch = ''

    def __init__(self, validator=None, multiplicity=(1,1), show='view',
      page='main', group=None, layouts=None, move=0,
      specificReadPermission=False, specificWritePermission=False, width=None,
      height=None, maxChars=None, colspan=1, master=None, masterValue=None,
      focus=False, historized=False, mapping=None, generateLabel=None,
      label=None, view=None, cell=None, edit=None, xml=None, translations=None):
        Field.__init__(self, None, (0,1), None, None, show, page, group,
          layouts, move, False, True, None, False, specificReadPermission,
          specificWritePermission, width, height, None, colspan, master,
          masterValue, focus, historized, mapping, generateLabel, label, None,
          None, None, None, False, False, view, cell, edit, xml, translations)
        self.validable = False

    def getDefaultLayouts(self): return Layouts.Info.b
# ------------------------------------------------------------------------------
