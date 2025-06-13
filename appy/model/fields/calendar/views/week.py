#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.px import Px
from appy.utils import dates as dutils
from appy.model.utils import Object as O
from appy.model.fields.calendar.views.day import Day

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Week(Day):
    '''Represents a calendar, weekly view for an individual calendar'''

    # A week view inherits from the Day view: it is built as a day + its
    # surrounding week days.

    def __init__(self, o, field):
        # Call the base constructor
        super().__init__(o, field)
        # Get the surrounding weeks
        self.around = self.getSurrounding()

    def calibrateDay(self, day):
        '''Calibrate the p_day to show to the first day of the week'''
        return dutils.Week.getFirstDay(day)

    def getOthers(self):
        '''Returns the names of the other views the user may switch to from this
           one.'''
        # Currently, the only view to switch to is "month"
        return [('month', {'month': self.grid[-1].strftime('%Y/%m')})]

    def getInfo(self, first):
        '''Returns an Object instance representing information about the week
           having this day as p_first day (DateTime object).'''
        start = first.strftime('%d/%m')
        end = (first+6).strftime('%d/%m')
        return O(id=first.strftime(self.periodFormat), text=f'{start} ➔ {end}')

    def getGrid(self, period=None):
        '''The grid, for a week view, contains the 7 days of the week to which
           the current day belongs.'''
        # The base constructor builds a grid made of a single day
        r = super().getGrid(period=period)
        # Get the other days of the same week
        current = r[0]
        dayName = current.aDay()
        i = dutils.weekDays.index(dayName)
        # Get the days preceding the v_current day in the week
        if i > 0:
            j = i - 1
            while j >= 0:
                r.insert(0, current - i-j)
                j -= 1
        # Get the days following the v_current day in the week
        if i < 6:
            j = i + 1
            while j <= 6:
                r.append(current + j-i)
                j += 1
        # Returns the complete week
        return r

    def getSurrounding(self):
        '''Get info about the weeks surrounding the current one'''
        cfirst = self.grid[0] # The first day of the current week
        r = O(next=None, previous=None, all=[self.getInfo(cfirst)])
        # Get the number of weeks one may select in the future and in the past.
        # Ensure we cannot lead the user before the start date and/or after the
        # end date, when defined.
        start = self.startDate
        if start:
            # Calibrate the start date to the first day of its week
            start = dutils.Week.getFirstDay(start)
        end = self.endDate
        selectable = self.field.selectableWeeks
        i = 1
        wfirst = cfirst
        # Get the weeks in the future
        while i <= selectable:
            # Get the first day of the next *w*eek
            wfirst += 7
            # Stop if we are above p_self.endDate
            if end and wfirst > end:
                break
            info = self.getInfo(wfirst)
            r.all.append(info)
            if i == 1:
                r.next = info
            i += 1
        # Get the weeks in the past
        i = 1
        wfirst = cfirst
        while i <= selectable:
            # Get the first day of the next *w*eek
            wfirst -= 7
            # Stop if we are below p_self.startDate
            if start and wfirst < start:
                break
            info = self.getInfo(wfirst)
            r.all.insert(0, info)
            if i == 1:
                r.previous = info
            i += 1
        return r

    def getPeriodType(self):
        '''To stay in the same logic, the period type must be "day" and not
           "week".'''
        return 'day'

    def getDayName(self, day):
        '''Returns the name of this p_day as it must appear in a column
           header.'''
        dayName = self.o.translate(f'day_{day.aDay()}_short')
        return f'<span class="discreet">{dayName}.</span> {day.day()}' \
               f'<span class="discreet"> / {str(day.month()).zfill(2)}</span>'

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                                  PXs
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Week selector
    pxPeriodSelector = Px('''
     <div var="around=view.around;
               goBack=view.mayGo(back=True);
               goForward=view.mayGo(back=False);
               js='askAjax(%s,null,{%%s:%%s})' % q(hook)">

      <!-- Go to the previous week -->
      <img class="calicon iconS" if="goBack"
           var2="prev=around.previous" title=":prev.text"
           src=":svg('arrow')" style="transform:rotate(90deg)"
           onclick=":js % (q('day'), q(prev.id))"/>

      <!-- Go back to the default date -->
      <input type="button" if="goBack or goForward"
        var2="disabled=view.defaultDate in view.grid;
        label='today' if view.today not in view.grid else 'go_back'"
        value=":_(label)" disabled=":disabled"
        style=":'color:%s' % ('grey' if disabled else 'black')"
        onclick=":js % (q('day'), q(''))"/>

      <!-- Display the current week and allow to select another one -->
      <select id="weekChooser" onchange=":js % (q('day'),'this.value')">
       <option for="m in around.all" value=":m.id"
               selected=":m.id == view.day">:m.text</option>
      </select>

      <!-- Go to the next week -->
      <img if="goForward" class="calicon iconS"
           var2="next=around.next" title=":next.text" src=":svg('arrow')"
           style="transform:rotate(270deg)"
           onclick=":js % (q('day'), q(next.id))"/>
     </div>''')

    # Main PX
    px = Px('''
     <table width="100%" class="houred">
      <!-- First row: names of days -->
      <thead>
       <tr>
        <th></th>
        <th for="day in view.grid" style=":view.getHouredColumnWidth(field)">
          <b>::view.getDayName(day)</b>
        </th>
        <th></th>
       </tr>
      </thead>
      <!-- Next rows: one row per hour of the day -->
      <tbody>
       <tr for="h, hf, hid in view.getHourInfo()" id=":hid">
        <td class=":'current' if view.now.hour()==h else ''">:hf</td>
        <td for="day in view.grid"
            class=":'current' if day == view.today else ''"
            var2="allEvents=view.getEventsPerHour(typeInfo, day=day);
                  events=allEvents.get(h) or ()">
         <x for="ev in events"
            if="view.unfiltered(ev)">::view.renderEvent(ev, o, field, _ctx_)</x>
         <!-- Additional info -->
         <x var="info=field.getAdditionalInfoAt(o,day,h,'week',preComputed)"
            if="info">::info</x>
        </td>
        <td>:hf</td>
       </tr>
      </tbody>
     </table>
     <script>::view.scrollToHour()</script>''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
