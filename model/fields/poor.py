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
     <x var="inputId='%s_%s' % (name, lg) if lg else name">
      <div contenteditable="true" class="xhtmlE" style=":field.getWidgetStyle()"
           id=":'%sP' % inputId">:field.getInputValue(inRequest, requestValue,
                                                      value)</div>
      <!-- The hidden form field -->
      <textarea id=":inputId" name=":inputId" style="display:none"></textarea>
     </x>''')

    # Do not load ckeditor
    def getJs(self, o, layout, r, config): return

    def getWidgetStyle(self):
        '''Returns style for the main poor tag'''
        return 'width:%s;min-height:%s' % (self.width, self.height)
#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
