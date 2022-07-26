# ~license~
# ------------------------------------------------------------------------------
from appy.fields import Field, Layouts

# ------------------------------------------------------------------------------
class Custom(Field):
    '''A custom field has the purpose of storing a data structure that is not
       proposed by other available fields.'''

    # If your objective is to build a complete custom widget, with specific
    # "edit" and "view" PXs and with a custom data structure, please use a field
    # of type Computed(unfreezable=True).

    # Indeed, the purpose of the Custom field is simpler and aims at storing a
    # data structure that is produced by your code independently of any UI
    # concern. Of course, if you wish, you can define a PX in attribute "view"
    # in order to add UI-visibility.

    # Typically, a Custom field is only "viewable" in the XML layout
    pxView = pxEdit = pxCell = pxSearch = ''

    def __init__(self, validator=None, multiplicity=(1,1), show='xml',
      page='main', group=None, layouts=None, move=0,
      specificReadPermission=False, specificWritePermission=False, width=None,
      height=None, maxChars=None, colspan=1, master=None, masterValue=None,
      focus=False, historized=False, mapping=None, generateLabel=None,
      label=None, view=None, cell=None, edit=None, xml=None, translations=None):
        # Parameter "persist" is not available and is automatically set to True
        Field.__init__(self, None, (0,1), None, None, show, page, group,
          layouts, move, False, True, None, False, specificReadPermission,
          specificWritePermission, width, height, None, colspan, master,
          masterValue, focus, historized, mapping, generateLabel, label, None,
          None, None, None, True, False, view, cell, edit, xml, translations)

    def getDefaultLayouts(self): return Layouts.Custom.b
# ------------------------------------------------------------------------------
