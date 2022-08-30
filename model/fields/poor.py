# -*- coding: utf-8 -*-

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.px import Px
from appy.model.fields.rich import Rich

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Poor(Rich):
    '''Field allowing to encode XHTML text'''

    # Unilingual edit
    editUni = Px('''
     <div contenteditable="true" class="xhtmlE" style=":field.getWidgetStyle()"
          var="inputId=not lg and name or '%s_%s' % (name, lg)"
          id=":inputId">:field.getInputValue(inRequest, requestValue, value)
     </div>''')

    # Do not load ckeditor
    def getJs(self, o, layout, r, config): return

    def getWidgetStyle(self):
        '''Returns style for the main poor tag'''
        return 'width:%s;min-height:%s' % (self.width, self.height)
#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
