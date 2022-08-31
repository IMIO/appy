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
     <x var="pid='%s_%s' % (name, lg) if lg else name">
      <div contenteditable="true" class="xhtmlE" style=":field.getWidgetStyle()"
           onfocus=":field.onFocus(pid, lg, hostLayout)"
           id=":'%sP' % pid" >::field.getInputValue(inRequest, requestValue,
                                                    value)</div>
      <!-- The hidden form field -->
      <textarea id=":pid" name=":pid" style="display:none"></textarea>
     </x>''')

    # Do not load ckeditor
    def getJs(self, o, layout, r, config): return

    def getWidgetStyle(self):
        '''Returns style for the main poor tag'''
        return 'width:%s;min-height:%s' % (self.width, self.height)

    def onFocus(self, tid, lg, hostLayout):
        '''Returns the Javascript code to execute when the poor widget gets
           focus, in order to link it with the toolbar.'''
        return 'initPoorContent(this)'
#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
