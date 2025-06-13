#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.px import Px
from appy.model.fields.calendar.views.day import Day

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class DayMulti(Day):
    '''Represents a calendar, daily view for several individual calendars'''

    multiple = True

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                                  PXs
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Main PX
    px = Px('''
     <table width="100%" class="houred">
      <!-- First row: sub-calendar names -->
      <thead>
       <tr>
        <th></th>
        <x for="groupO in others">
         <th for="other in groupO" style=":view.getHouredColumnWidth(field)">
          <b>::view.getNameOnMulti(other)</b>
         </th>
        </x>
        <th></th>
       </tr>
      </thead>
      <!-- Next rows: one row per hour of the day -->
      <tbody>
       <tr for="h, hf, hid in view.getHourInfo()" id=":hid"
           class=":'current' if view.now.hour()==h else ''">
        <td>:hf</td>
         <x for="groupO in others">
          <td for="other in groupO"
              var2="allEvents=view.getEventsPerHour(typeInfo, other);
                    events=allEvents.get(h) or ()">
           <x for="event in events"
              if="view.unfiltered(event)">::view.renderEvent(event, other.o,
                                                         other.field, _ctx_)</x>
          </td>
         </x>
        <td>:hf</td>
       </tr>
      </tbody>
     </table>
     <script>::view.scrollToHour()</script>''',)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
