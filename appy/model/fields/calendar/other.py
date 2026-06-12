#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.px import Px
from appy import utils
from .cell import Cell
from .timeslot import Timeslot
from appy.model.utils import Object as O

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Other:
    '''Represents a Calendar field that must be shown within another, multiple,
       Calendar'''

    # See parameter "others" in class appy.model.fields.calendar.Calendar

    def __init__(self, o, name, color='grey', excludedEvents=(),
                 highlight=False):
        # The object on which this calendar is defined
        self.o = o
        # The other Calendar object
        self.field = o.getField(name)
        self.timeslots = Timeslot.getAll(o, self.field)
        # The color into which events from this calendar must be shown (in the
        # month rendering) in the calendar integrating this one.
        self.color = color
        # The list of event types, in the other calendar, that the integrating
        # calendar does not want to show. Every type in p_excludedEvents may be
        # a mask, starting and/or ending with a *.
        self.excludedEvents = excludedEvents
        # Must this calendar be highlighted ?
        self.highlight = highlight

    def __repr__(self):
        '''p_self as a short string'''
        return f'‹Other calendar {self.o.strinG(path=False)}, ' \
               f'field={self.field.name}›'

    def exclude(self, eventType):
        '''Must this p_eventType be excluded according to
           p_self.excludedEvents ?'''
        toExclude = self.excludedEvents
        if not toExclude: return
        for mask in toExclude:
            # v_mask may be a complete event type or a mask
            starEnds = mask.endswith('*')
            if mask.startswith('*') and starEnds:
                condition = mask[1:-1] in eventType
            elif starEnds:
                condition = eventType.startswith(mask[:-1])
            else:
                condition = eventType == mask
            if condition:
                return True

    def getEventsInfoAt(self, r, calendar, date, typeInfo, view, inTimeline,
                        cache, gradients):
        '''Gets the events defined at p_date in this calendar and append them in
           p_r.'''
        events = self.field.getEventsAt(self.o, date, typeInfo=typeInfo)
        if not events: return
        for event in events:
            eventType = event.eventType
            # Ignore it if not among current filters
            if not view.unfiltered(event): continue
            # Ignore it if among self.excludedEvents
            if self.exclude(eventType): continue
            # Info will be collected in a Calendar.Cell object
            if inTimeline:
                # Get info about this cell if it has been defined, or
                # (a) nothing if p_self.field.showNoCellInfo is False,
                # (b) a tooltipped dot else.
                info = calendar.getCellInfo(self.o, eventType, cache)
                if info:
                    # If the event does not span the whole day, a gradient can
                    # be used to color the cell instead of just a plain
                    # background.
                    if event.timeslot in gradients:
                        dayPart = event.getDayPart(self.o, self.field,
                                                   self.timeslots)
                        info.gradient = gradients[event.timeslot] \
                                        if dayPart < 1.0 else None
                else:
                    info = Cell()
                    if calendar.showNoCellInfo:
                        nameE = typeInfo[eventType].name
                        info.text = f'<abbr title="{nameE}">▪</abbr>'
            else:
                # Get the event name
                info = Cell(color=self.color, title=typeInfo[eventType].name)
            if info:
                info.event = event
                r.append(info)

    def getEventTypes(self):
        '''Gets the event types from this Other calendar, ignoring
           self.excludedEvents if any.'''
        r = []
        for eventType in self.field.getEventTypes(self.o):
            if not self.exclude(eventType):
                r.append(eventType)
        return r

    def getCss(self):
        '''When this calendar is shown in a timeline, get the CSS class for the
           row into which it is rendered.'''
        return 'highlightRow' if self.highlight else ''

    def mayValidate(self, view):
        '''Is validation enabled for this other calendar?'''
        return self.field.mayValidate(self.o, view)

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #              Render this other calendar on a multiple view
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def getHook(self):
        '''Returns the ID of the DOM node representing this other calendar on a
           multiple view.'''
        return f'{self.o.iid}{self.field.name}'

    def getAjaxData(self, c):
        '''Initializes an AjaxData object on the DOM node representing this
           other calendar field, as rendered within a multiple, outer calendar
           field.'''
        # If total rows are there, define them as a peer Ajax node
        peerHook = f'{c.hook}_rows'
        return f"new AjaxData('{c.o.url}/{self.field.name}/Other/px','POST'," \
               f"{{}},'{self.getHook()}','{c.hook}',null,null,null,null," \
               f"['{peerHook}'])"

    # This PX is not yet used by view.monthMulti

    px = Px('''
     <tr var="F=field;
              outer=outer|F.Other.getOuter(o, outerS);
              hook=hook|outer.getHook();
              view=view|F.View.get(outer.o, outer.field);
              cache=cache|outer.field.getCache(outer.o, view);
              others=others|F.Other.getAll(outer.o, outer.field, cache);
              other=other|F.Other.get(others, o, field.name);
              tlName=view.getNameOnMulti(other);
              outerValidate=mayValidate|outer.mayValidate(view);
              mayValidate=outerValidate and other.mayValidate(view);
              outerEdit=mayEdit|outer.field.mayEdit(outer.o);
              mayEdit=outerEdit and field.mayEdit(o);
              csS=other.getCss();
              timeslots=other.timeslots;
              eventTypes=field.getEventTypes(o);
              typeInfo=typeInfo|F.TypeInfo.create(field, o, eventTypes);
              hasEventFields='true' if field.eventFields else 'false';
              allowedTypes=field.getAllowedTypes(o, eventTypes);
              totals=totals|F.Totals.Running(outer, _ctx_)"
         id=":other.getHook()">
      <script>:other.getAjaxData(_ctx_)</script>

      <!-- The first cell identifies the individual calendar -->
      <td class=":f'tlLeft {csS}'.strip()">::tlName</td>

      <!-- One cell for every day in the view grid -->
      <x for="date in view.grid"
         var2="inRange=field.dateInRange(date, view);
               cssClasses=view.getCellClass(date)">
       <td if="not inRange" class=":cssClasses"></td>
       <x if="inRange"
          var2="dayString=date.strftime(field.dayKey)">:view.pxCell</x>
      </x>

      <!-- The last cell repeats the first one -->
      <td class=":f'tlRight {csS}'.strip()">::tlName</td>

      <!-- Column totals -->
      <x if="outer.field.totalCols">:field.Totals.Running.pxCols</x>
     </tr>''')

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                             Class methods
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @classmethod
    def getAll(class_, o, field, cache):
        '''Returns the list of other calendars whose events must also be shown
           on this calendar p_field.'''
        r = None
        others = field.others
        if others:
            r = others(o, cache)
            if r:
                # Ensure we have a list of lists
                if isinstance(r, Other): r = [r]
                if isinstance(r[0], Other): r = [r]
        return r if r is not None else [[]]

    @classmethod
    def get(class_, alL, o, name):
        '''Return, among p_alL Other objects as computed by m_getAll, the one
           corresponding to this p_o(bject) and field p_name.'''
        for group in alL:
            for other in group:
                if other.o == o and other.field.name == name:
                    return other

    @classmethod
    def getSep(class_, colspan):
        '''Produces the separator between groups of other calendars'''
        return f'<tr style="height:8px"><th colspan="{colspan}" ' \
               f'style="background-colo r:grey"></th></tr>'

    @classmethod
    def getEventsAt(class_, field, date, others, typeInfo, view, cache,
                    gradients=None):
        '''Gets events that are defined in p_others at some p_date'''
        r = []
        isTimeline = field.multiple and view.render == 'month'
        if isinstance(others, Other):
            others.getEventsInfoAt(r, field, date, typeInfo, view, isTimeline,
                                   cache, gradients)
        else:
            for other in utils.IterSub(others):
                other.getEventsInfoAt(r, field, date, typeInfo, view,
                                      isTimeline, cache, gradients)
        return r

    @classmethod
    def getOuter(class_, o, outer):
        '''Returns an Other object representing an outer calendar field'''
        # The returned object misuses the concept of Other calendar: an outer
        # field containing other calendars is itself represented here by an
        # Other object.
        #
        # p_outer is a string of the form <object_iid>_<field_name>
        iid, name = outer.split('_', 1)
        outerObject = o.getObject(iid)
        return Other(outerObject, name)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
