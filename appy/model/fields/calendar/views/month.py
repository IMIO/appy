#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from DateTime import DateTime

from . import View
from appy.px import Px
from .editable import Editable
from appy.utils import dates as dutils
from appy.model.utils import Object as O

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Month(Editable, View):
    '''Represents a calendar, monthly view for an individual calendar'''

    # Default month format
    periodFormat = '%Y/%m'

    # This view is editable
    editable = True

    def __init__(self, o, field):
        # Call the base constructor
        super().__init__(o, field)
        # Determine the month to show
        self.month = self.req.month or self.defaultDateS
        # What is the first day of the month ?
        self.monthDayOne = DateTime(f'{self.month}/01')
        # Set the grid
        self.grid = self.getGrid()
        # Get the surrounding months
        self.around = self.getSurrounding()

    def getOthers(self):
        '''Returns the names of the other views the user may switch to from this
           one.'''
        # All calendars do not allow switching between views (ie, the Picker
        # doesn't allow it).
        if not self.field.switchViews: return
        # Currently, the only view to switch to is "week". If today is part of
        # the current monthly view, ensure it is part of the view to switch to.
        # Else, use the first day of the shown month as basis for switching.
        switchDay = self.today if self.today in self.grid else self.monthDayOne
        return [('week', {'day': switchDay.strftime('%Y-%m-%d')})]

    def getInfo(self, first):
        '''Returns an Object instance representing information about the month
           having this day as p_first day (DateTime object).'''
        text = self.tool.formatDate(first, '%MT %Y', withHour=False)
        return O(id=first.strftime(self.periodFormat), text=text)

    def getGrid(self, period=None):
        '''Creates a list of DateTime objects representing the calendar grid to
           render for the current p_self.month, or the month specified in
           p_period if passed. If p_self is a Month object, it is a list of
           lists (one sub-list for every week; indeed, every week is rendered as
           a row). If p_self is a MonthMulti object, the result is a linear list
           of DateTime objects.'''
        # Month is a string "YYYY/mm"
        month = period or self.month
        currentDay = DateTime(f'{month}/01 UTC')
        currentMonth = currentDay.month()
        isLinear = self.multiple
        r = [] if isLinear else [[]]
        dayOneNb = currentDay.dow() or 7 # This way, Sunday is 7 and not 0
        strictMonths = self.field.strictMonths
        if dayOneNb != 1 and not strictMonths:
            # If I write "previousDate = DateTime(currentDay)", the date is
            # converted from UTC to GMT.
            previousDate = DateTime(f'{month}/01 UTC')
            # If the 1st day of the month is not a Monday, integrate the last
            # days of the previous month.
            for i in range(1, dayOneNb):
                previousDate -= 1
                target = r if isLinear else r[0]
                target.insert(0, previousDate)
        finished = False
        while not finished:
            # Insert currentDay in the result
            if isLinear:
                r.append(currentDay)
            else:
                if len(r[-1]) == 7:
                    # Create a new row
                    r.append([currentDay])
                else:
                    r[-1].append(currentDay)
            currentDay += 1
            if currentDay.month() != currentMonth:
                finished = True
        # Complete, if needed, the last row with the first days of the next
        # month. Indeed, we may need to have a complete week, ending with a
        # Sunday.
        if not strictMonths:
            target = r if isLinear else r[-1]
            while target[-1].dow() != 0:
                target.append(currentDay)
                currentDay += 1
        return r

    def getSurrounding(self):
        '''Gets the months surrounding the current one'''
        first = self.monthDayOne
        r = O(next=None, previous=None, all=[self.getInfo(first)])
        # Calibrate p_startDate and p_endDate to the first and last days of
        # their month. Indeed, we are interested in months, not days, but we use
        # arithmetic on days.
        start = self.startDate
        if start: start = DateTime(start.strftime('%Y/%m/01 UTC'))
        end = self.endDate
        if end: end = dutils.Month.getLastDay(end)
        # Get the x months after p_first
        mfirst = first
        i = 1
        selectable = self.field.selectableMonths
        # Get the months in the future
        while i <= selectable:
            # Get the first day of the next *m*onth
            mfirst = DateTime((mfirst + 33).strftime('%Y/%m/01 UTC'))
            # Stop if we are above self.endDate
            if end and mfirst > end:
                break
            info = self.getInfo(mfirst)
            r.all.append(info)
            if i == 1:
                r.next = info
            i += 1
        # Get the x months before p_first
        mfirst = first
        i = 1
        while i <= selectable:
            # Get the first day of the previous month
            mfirst = DateTime((mfirst - 2).strftime('%Y/%m/01 UTC'))
            # Stop if we are below self.startDate
            if start and mfirst < start:
                break
            info = self.getInfo(mfirst)
            r.all.insert(0, info)
            if i == 1:
                r.previous = info
            i += 1
        return r

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                                  PXs
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Month selector

    pxPeriodSelector = Px('''
     <div var="around=view.around;
               iid=str(o.iid);
               name=field.name;
               goBack=view.mayGo(back=True);
               goForward=view.mayGo(back=False)">

      <!-- Go to the previous month -->
      <img class="calicon iconS" if="goBack"
           var2="prev=around.previous" title=":prev.text"
           src=":svg('arrow')" style="transform:rotate(90deg)"
           onclick=":f'askMonth({q(iid)},{q(name)},{q(prev.id)})'"/>

      <!-- Go back to the default date -->
      <input type="button" if="goBack or goForward"
        var2="fmt=view.periodFormat;
              sdef=view.defaultDateS;
              disabled=sdef == view.monthDayOne.strftime(fmt);
        label='today' if sdef == view.today.strftime(fmt) else 'go_back'"
        value=":_(label)" disabled=":disabled"
        style=":'color:%s' % ('grey' if disabled else 'black')"
        onclick=":f'askMonth({q(iid)},{q(name)},{q(view.defaultDateS)})'"/>

      <!-- Display the current month and allow to select another one -->
      <select id="monthChooser"
              onchange=":f'askMonth({q(iid)},{q(name)},this.value)'">
       <option for="m in around.all" value=":m.id"
               selected=":m.id == view.month">:m.text</option>
      </select>

      <!-- Go to the next month -->
      <img if="goForward" class="calicon iconS"
           var2="next=around.next" title=":next.text" src=":svg('arrow')"
           style="transform:rotate(270deg)"
           onclick=":f'askMonth({q(iid)},{q(name)},{q(next.id)})'"/>
     </div>''')

    # Main PX

    px = Px('''
     <table cellpadding="0" cellspacing="0" width=":field.width"
            class=":field.style" id=":f'{hook}_cal'"
            var="rowHeight=int(field.height/float(len(view.grid)));
                 hasEventFields='true' if field.eventFields else 'false'">

      <!-- 1st row: names of days -->
      <tr height="22px">
       <th for="dayId in field.weekDays"
           width="14%">:namesOfDays[dayId].short</th>
      </tr>

      <!-- The calendar in itself -->
      <tr for="row in view.grid" valign="top" height=":rowHeight">
       <x for="date in row"
          var2="inRange=field.dateInRange(date, view);
                cssClasses=view.getCellClass(date)">

        <!-- Dump an empty cell if we are out of the supported date range -->
        <td if="not inRange" class=":cssClasses"></td>

        <!-- Dump a normal cell if we are in range -->
        <x if="inRange"
           var2="dayString=date.strftime(field.dayKey);
                 day=date.day();">:getattr(view, field.monthCell)</x>
       </x>
      </tr>
     </table>

     <!-- Popups for creating, updating or deleting a calendar event -->
     <x if="mayEdit and eventTypes">
      <x>:view.pxEditPopup</x><x>:view.pxDelPopup</x></x>

     <!-- Popup for validating events -->
     <x if="mayValidate">:field.validation.pxPopup</x>''',

     css='''.pickCB { margin:0 4px 0 0 }
            .pickSB { padding-right: 0.3em}''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
