#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from DateTime import DateTime

from appy.px import Px
from appy.model.fields.calendar.views import View

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Day(View):
    '''Represents a calendar, individual daily view'''

    # Default day format (the one in use in the HTML input[type=date] widget)
    periodFormat = '%Y-%m-%d'

    def __init__(self, o, field):
        # Call the base constructor
        super().__init__(o, field)
        # Determine the day to show
        day = self.req.day
        if day:
            dayO = DateTime(f'{day} UTC')
        else:
            dayO = self.defaultDate
        self.dayO = self.calibrateDay(dayO)
        self.day = self.dayO.strftime(self.periodFormat)
        # The first day of the month must be defined, in order to conform to the
        # View API.
        month = self.dayO.strftime('%Y/%m')
        self.monthDayOne = DateTime(f'{month}/01')
        # Define the grid
        self.grid = self.getGrid()

    def calibrateDay(self, day):
        '''Some views may need to calibrate the currently shown p_day (ie, a
           week view will calibrate it to the first day of the week.'''
        return day

    def getGrid(self, period=None):
        '''The grid, for a daily view, only contains the day in question'''
        day = DateTime(period) if period else self.dayO
        return [day]

    def getEventsPerHour(self, typeInfo, other=None, day=None):
        '''Returns a dict containing all events occurring at p_self.dayO (or at
           p_day, if passed), in calendar p_self.field or (an)p_other one if
           passed.'''
        # Within this dict, keys are the hours into which the event's start hour
        # is included.
        #
        # For example, if event A starts at 9:15, B at 9:55 and C at 23:06, the
        # dict will be {9: [A, B], 23: C}.
        #
        # Any event having a timeslot for which no hour range is defined, will
        # be added in a list at key None.
        if other:
            cal = other.field
            o = other.o
        else:
            cal = self.field
            o = self.o
        # The info can be cached, excepted if a specific p_day is passed
        if day is None:
            cache = o.cache
            key = f'{o.iid}{cal.name}'
            if key in cache: return cache[key]
        # Walk all events at self.day
        day = day or self.dayO
        r = {}
        for event in cal.getEventsAt(o, day, empty=(), typeInfo=typeInfo):
            start = getattr(event, 'start', None) # Can be None
            if start:
                start = start.hour()
            if start in r:
                r[start].append(event)
            else:
                r[start] = [event]
        # Cache and return the result
        if day is None:
            cache[key] = r
        return r

    def scrollToHour(self):
        '''Produce the JS code allowing to scroll to the current hour within a
           daily view.'''
        # JS method scrollIntoView scrolls vertically as well as horizontally.
        # When filters are shown, it hides them. After calling it, we must then
        # reset the scroll container's left to 0.
        return f'getNode("h{self.now.hour()}",true).' \
               f'scrollIntoView(false);getNode("appyContent",true)' \
               f'.scrollLeft=0;'

    def getHourInfo(self):
        '''Returns info about the hours of the day'''
        # Return value is a 3-tuple containing
        # - the hour as an integer from 0 to 23 ;
        # - the hour formatted variant, ie 12:00 ;
        # - the ID of the corresponding html tag into which the hour appears
        r = []
        for i in range(24):
            r.append((i, f'{str(i).zfill(2)}:00', f'h{i}'))
        # Add a first slot corresponding to not-houred events
        r.insert(0, (None, '', ''))
        return r

    def getHouredColumnWidth(self, cal):
        '''Returns the width and min-width properties for every column in an
           houred view.'''
        return f'width:{cal.houredWidth};min-width:{cal.houredWidth}'

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                                  PXs
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Day selector

    # The day selector
    pxPeriodSelector = Px('''
     <div class="daySel" var="js='askAjax(%s,null,{%%s:%%s})' % q(hook)">

      <!-- Go to the previous day -->
      <img class="calicon iconS" src=":svg('arrow')"
           style="transform:rotate(90deg)"
           var="prevDay=(view.dayO-1).strftime(view.periodFormat)"
           onclick=":js % (q('day'), q(prevDay))"/>

      <!-- The current day, in a date widget -->
      <div>:tool.formatDate(view.dayO, format="%DT", withHour=False)</div>
      <input type="date" value=":view.day"
             onchange=":js % (q('day'), 'this.value')"/>

      <!-- Go to the next day -->
      <img class="calicon iconS" src=":svg('arrow')"
           style="transform:rotate(270deg)"
           var="nextDay=(view.dayO+1).strftime(view.periodFormat)"
           onclick=":js % (q('day'), q(nextDay))"/>
     </div>''',

     css='''
      .daySel { display:flex; align-items:center; padding:0.5em; width:100%;
                background-color:#f7f8fb; opacity:0.92 }
      .daySel input[type=date] { margin:0 0 0 0.4em; width:7.5em }''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
