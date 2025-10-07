#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from persistent import Persistent

from appy import n
from appy.ui.layout import Layouts
from appy.model.fields import Field

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Custom(Field):
    '''A custom field has the purpose of storing a data structure that is not
       proposed by other available fields.'''

    class Layouts(Layouts):
        '''Info-specific layouts'''
        b = Layouts(edit='f')

        @classmethod
        def getDefault(class_, field):
            '''Default layouts for this Custom p_field'''
            return class_.b

    # If your objective is to build a complete custom widget, with specific
    # "edit" and "view" PXs and with a custom data structure, please use a field
    # of type Computed(unfreezable=True).

    # Indeed, the purpose of the Custom field is simpler and aims at storing a
    # data structure that is produced by your code independently of any UI
    # concern. Of course, if you wish, you can define a PX in attribute "view"
    # in order to add UI-visibility.

    # Typically, a Custom field is only "viewable" in the XML layout
    view = edit = cell = buttons = search = ''

    def __init__(self, validator=n, multiplicity=(1,1), show='xml',
      renderable=n, page='main', group=n, layouts=n, move=0,
      readPermission='read', writePermission='write', width=n, height=n,
      maxChars=n, colspan=1, master=n, masterValue=n, masterSnub=n, focus=False,
      historized=False, mapping=n, generateLabel=n, label=n, view=n, cell=n,
      buttons=n, edit=n, custom=n, xml=n, translations=n):

        # Parameter "persist" is not available and is automatically set to True
        super().__init__(n, (0,1), n, n, show, renderable, page, group, layouts,
          move, False, True, n, n, False, n, n, readPermission, writePermission,
          width, height, n, colspan, master, masterValue, masterSnub, focus,
          historized, mapping, generateLabel, label, n, n, n, n, True, False,
          view, cell, buttons, edit, custom, xml, translations)

    def isEmptyValue(self, o, value):
        '''An empty persistent value must not be considered as empty'''
        # Indeed, an empty persistent list or dict is an existing data container
        # being significant. Supposed you have initialised an empty persistent
        # dict on your custom field o.myCustom:
        #
        #                 o.myCustom = PersistentMapping()
        #
        # If this empty persistent mapping was considered as an "empty" value,
        # getting:
        #
        #                          o.myCustom
        #
        # would return None, and not the persistent mapping, because, when a
        # value is considered being empty, a default value is searched. If no
        # default value is found, None is returned.
        if isinstance(value, Persistent): return
        return super().isEmptyValue(o, value)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
