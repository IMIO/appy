#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from .week import Week
from appy.px import Px
from .editable import Editable
from appy.model.utils import Object as O

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class WeekMulti(Editable, Week):
    '''Represents a calendar, weekly view for several individual calendars'''

    multiple = True
    editable = True

    # CSS styles to set to column headers
    headerStyles = 'top:0px'

    def countOthers(self, others):
        '''Counts the number of other calendars being shown in this multiple
           view.'''
        # p_others is a list of lists: other calendars are grouped
        r = 0
        for group in others:
            r += len(group)
        return r

    # Main PX

    # Currently, validation is disabled on this week view (v_mayValidate is
    # redefined to False), because currently implemented on a monthly basis.

    px = Px('''
     <x var="rowHeight=int(field.height/float(view.countOthers(others)));
             outer=field.Other(o, field.name)">
      <table class="list timeline weekline">

       <!-- Day names and numbers, as column headers -->
       <x>:view.pxHeaders</x>

       <!-- One row per individual calendar -->
       <tbody>

        <!-- Calendars can be grouped -->
        <x for="groupO in others">

         <!-- One row for every sub-calendar -->
         <x for="other in groupO"
            var2="o=other.o; field=other.field">:other.px</x>

         <!-- The separator between groups of other calendars -->
         <x if="not loop.groupO.last">::field.Other.getSep(len(view.grid)+2)</x>
        </x>
       </tbody>
      </table>

      <!-- Total columns, as a separate table, and legend -->
      <x if="field.totalCols">:field.Totals.pxCols</x>

      <!-- Popups for creating, updating or deleting a calendar event -->
      <x if="mayEdit">
       <x>:view.pxEditPopup</x><x>:view.pxDelPopup</x></x>

      <!-- Popup for validating events  -->
      <x if="mayValidate">:field.validation.pxPopup</x>

     </x>''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
