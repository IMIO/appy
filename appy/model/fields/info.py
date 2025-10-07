#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy import n
from appy.model.fields import Field
from appy.ui.layout import Layout, LayoutF, Layouts

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Info(Field):
    '''An info is a field whose purpose is to present information (text,
       html...) to the user.'''

    class Layouts(Layouts):
        '''Info-specific layouts'''

        singleLine = LayoutF('ld=') # Label and description on a single line
        b   = Layouts(edit='l')
        d   = Layouts(edit=Layout('l-d', width=n))
        ds  = Layouts(edit=singleLine) # *S*ingle line
        dsv = Layouts(edit=singleLine,
                      view=singleLine) # *S*ingle line on *v*iew
        c   = Layouts(edit='l|')
        dc  = Layouts(edit='l|-d|')
        do  = Layouts(edit='f', view='d') # Description only
        doe = Layouts(edit='d', view='d') # Description only, also on edit
        vdc = Layouts(edit='l', view='l|-d|')

        @classmethod
        def getDefault(class_, field):
            '''Default layouts for this Info p_field'''
            return class_.b

    # An info only displays a label: PXs for showing content are empty
    view = edit = cell = buttons = search = ''

    def __init__(self, validator=n, multiplicity=(1,1), show='view',
      renderable=n, page='main', group=n, layouts=n, move=0,
      readPermission='read', writePermission='write', width=n, height=n,
      maxChars=n, colspan=1, master=n, masterValue=n, masterSnub=n, focus=False,
      historized=False, mapping=n, generateLabel=n, label=n, view=n, cell=n,
      buttons=n, edit=n, custom=n, xml=n, translations=n):

        # Call the base constructor
        super().__init__(n, (0,1), n, n, show, renderable, page, group, layouts,
          move, False, True, n, n, False, n, n, readPermission, writePermission,
          width, height, n, colspan, master, masterValue, masterSnub, focus,
          historized, mapping, generateLabel, label, n, n, n, n, False, False,
          view, cell, buttons, edit, custom, xml, translations)

        self.validable = False
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
