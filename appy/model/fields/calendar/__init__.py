#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import types

from DateTime import DateTime
from persistent import Persistent
from BTrees.IOBTree import IOBTree
from persistent.list import PersistentList

from appy.px import Px
from appy import utils
from .cell import Cell
from .views import View
from .event import Event
from .other import Other
from .. import Field, Show
from .action import Action
from .filter import Filter
from .legend import Legend
from .data import EventData
from .timeslot import Timeslot
from .typeInfo import TypeInfo
from .totals import Total, Totals
from .validation import Validation
from appy.utils import dates as dutils
from appy.utils import string as sutils
from appy.model.utils import Object as O
from appy.ui.layout import Layout, Layouts

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
TL_W_EVTS   = 'A multiple calendar has the objective to display a series of ' \
              'other calendars. Its own calendar is disabled: it is useless ' \
              'to define event types for it.'
RENDER_KO   = 'Wrong render mode "%s". Possible render modes are: %s.'
MISS_EN_M   = "When param 'eventTypes' is a method, you must give another " \
              "method in param 'eventNameMethod'."
S_MONTHS_KO = 'Strict months can only be used with timeline calendars.'
ACT_MISS    = 'Action "%s" does not exist or is not visible.'
EVT_DEL     = '%s deleted (%d)%s.'
EVT_DEL_SL  = '%s deleted at slot %s.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Gradient:
    '''If we need to color the cell of a timeline with a linear gradient,
       this class allows to define the characteristics for this gradient.'''

    def __init__(self, angle='135deg', endColor='transparent'):
        # The angle defining the gradient direction
        self.angle = angle
        # The end color (the start color being defined elsewhere)
        self.endColor = endColor

    def getStyle(self, startColor):
        '''Returns the CSS definition for this gradient'''
        return f'background:linear-gradient({self.angle},{startColor},' \
               f'{self.endColor})'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Layer:
    '''A layer is a set of additional data that can be activated or not on top
       of calendar data. Currently available for timelines only.'''

    def __init__(self, name, label, onCell, activeByDefault=False, legend=None,
                 merge=False):
        # p_name must hold a short name or acronym, unique among all layers
        self.name = name
        # p_label is a i18n label that will be used to produce the layer name in
        # the user interface.
        self.label = label
        # p_onCell must be a method that will be called for every calendar cell
        # and must return a 3-tuple (style, title, content). "style" will be
        # dumped in the "style" attribute of the current calendar cell, "title"
        # in its "title" attribute, while "content" will be shown within the
        # cell. If nothing must be shown at all, None must be returned.
        # This method must accept those args:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   date      | the currently walked day (a DateTime instance) ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   other     | the Other instance representing the currently walked
        #             | calendar ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   events    | the list of events (as a list of Calendar.Cell objects
        #             | whose attribute "event" points to an instance of class
        #             | appy.model.fields.calendar.event::Event) defined at that
        #             | day in this calendar ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # preComputed | the result of Calendar.preCompute (see below).
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.onCell = onCell
        # Is this layer activated by default ?
        self.activeByDefault = activeByDefault
        # p_legend is a method that must produce legend items that are specific
        # to this layer. The method must accept no arg and must return a list of
        # objects (you can use class appy.model.utils.Object) having these
        # attributes:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   name   | The legend item name as shown in the calendar ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   style  | The content of the "style" attribute that will be applied
        #          | to the little square ("td" tag) for this item ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  content | The content of this "td" (if any).
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.legend = legend
        # When p_merge is False, if the layer contains info for a given day, the
        # base info will be hidden. Else, it will be merged.
        self.merge = merge
        # Layers will be chained: one layer will access the previous one in the
        # stack via attribute "previous". "previous" fields will automatically
        # be filled by the Calendar.
        self.previous = None

    def getCellInfo(self, o, activeLayers, date, other, events, preComputed):
        '''Get the cell info from this layer or one previous layer when
           relevant.'''
        # Take this layer into account only if active
        if self.name in activeLayers:
            info = self.onCell(o, date, other, events, preComputed)
            if info: return info
        # Get info from the previous layer
        if self.previous:
            return self.previous.getCellInfo(o, activeLayers, date, other,
                                             events, preComputed)

    def getLegendEntries(self, o):
        '''Returns the legend entries by calling method in self.legend'''
        return self.legend(o) if self.legend else None

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Calendar(Field):
    '''This field allows to produce an agenda (monthly view) and view/edit
       events on it.'''

    # Some elements will be traversable
    traverse  = Field.traverse.copy()

    # A calendar requires calendar.js, that is already among Appy's global
    # includes.

    # Make some classes available here
    View = View
    Cell = Cell
    Other = Other
    Layer = Layer
    Event = Event
    Total = Total
    Action = Action
    Filter = Filter
    Legend = Legend
    TypeInfo = TypeInfo
    DateTime = DateTime
    Timeslot = Timeslot
    IterSub = utils.IterSub
    Validation = Validation

    traverse['Totals'] = 'perm:read'
    Totals = Totals

    class Layouts(Layouts):
        '''Calendar-specific layouts'''
        b = Layouts(edit='f', view='l-d-f')
        n = Layouts(Layout('l-f', width=None))

        @classmethod
        def getDefault(class_, field):
            '''Default layouts for this Calendar p_field'''
            return class_.n if field.multiple else class_.b

    view = cell = buttons = Px('''
     <div var="view=field.View.get(o, field);
               hook=f'{o.iid}{field.name}';
               timeslots=field.Timeslot.getAll(o, field);
               eventTypes=field.getEventTypes(o);
               allowedEventTypes=field.getAllowedEventTypes(o, eventTypes);
               preComputed=field.getPreComputedInfo(o, view);
               mayEdit=field.mayEdit(o);
               objUrl=o.url;
               others=field.Other.getAll(o, field, preComputed);
               typeInfo=field.TypeInfo.create(field,o,eventTypes,others);
               namesOfDays=field.getNamesOfDays(_);
               showTimeslots=len(timeslots) &gt; 1;
               slotIdsStr=','.join(timeslots);
               mayValidate=field.mayValidate(o);
               activeLayers=field.getActiveLayers(req);
               actions=field.Action.getVisibleOn(o, field, view.monthDayOne)"
          id=":hook">
      <script>:f'var {field.name}_maxEventLength={field.maxEventLength};'
      </script>
      <script>:field.getAjaxData(hook, o, view, popup=popup,
                                 activeLayers=','.join(activeLayers))</script>

      <!-- Period selector -->
      <div class="controlsP">
       <x>:view.pxPeriodSelector</x>

       <!-- Global actions -->
       <x>:field.Action.px</x>
      </div>

      <!-- The top PX, if defined -->
      <x if="field.topPx">::field.topPx</x>

      <!-- The calendar in itself, with or without filters -->
      <div if="view.filters" class="viewF">
       <div>:view.px</div>
       <div>:field.Filter.px</div>
      </div>
      <x if="not view.filters">:view.px</x>

      <!-- The bottom PX, if defined -->
      <x if="field.bottomPx">::field.bottomPx</x>
     </div>''',

     css='''
      .controlsP { display:flex; margin-bottom:0.3em; gap:0.5em;
                   align-items:center; position:sticky; top:-1.8em;
                   background-color:|calActBg|; z-index:1 }
      .controlsP select { margin:0 }
      .controlsP input[type=checkbox] { margin-right:0.4em }
      .viewF { display:flex; flex-direction:row-reverse; gap:0.5em }
      .viewF > :nth-child(1) { flex-basis:100% }
      .viewF > :nth-child(2) { display:flex; flex-direction:column; width:10em;
                               gap:0.5em; position:sticky; top:1.5em;
                               align-self:flex-start }
      .calSelect { margin:10px 0; color:|selectColor|; font-size:95% }
      .calSpan { margin-bottom:3px; font-size:92%; color:|selectColor| }
      .calSpan input { color:|selectColor|; text-align:center }''')

    edit = search = ''

    # Currently supported render modes (see p_render below)
    renderModes = ('month', 'monthMulti', 'week', 'dayMulti')

    # PX to use when rendering a calendar cell, in render mode "month"
    monthCell = 'pxCell'

    # The format allowing to produce a key representing a day
    dayKey = '%Y/%m/%d'

    def __init__(self, eventTypes=None, eventNameMethod=None,
      allowedEventTypes=None, validator=None, multiplicity=(0,1), default=None,
      defaultOnEdit=None, show='view', renderable=None, page='main',
      group=None, layouts=None, move=0, readPermission='read',
      writePermission='write', width='100%', height=300, colspan=1, master=None,
      masterValue=None, focus=False, mapping=None, generateLabel=None,
      label=None, maxEventLength=50, render='month', others=None,
      timelineName=None, timelineMonthName=None, additionalInfo=None,
      startDate=None, endDate=None, defaultDate=None, timeslots=None,
      slotMap=None, cellInfo=None, gradients=None, showNoCellInfo=False,
      columnColors=None, preCompute=None, applicableEvents=None, totalRows=None,
      totalCols=None, validation=None, layers=None, layersSelector=True,
      topPx=None, bottomPx=None, actions=None, filters=None,
      selectableEmptyCells=False, legend=None, view=None, cell=None,
      buttons=None, edit=None, editable=True, custom=None, xml=None,
      translations=None, delete=True, beforeDelete=None, afterCreate=None,
      selectableMonths=6, selectableWeeks=4, createEventLabel='which_event',
      style='calTable', strictMonths=False, houredWidth='10em', fullDay=None,
      createObjects=None):

        '''Calendar field constructor'''

        # p_eventTypes can be a "static" list or tuple of strings that identify
        # the types of events that can be stored in this calendar. It can also
        # be a method that computes such a "dynamic" list or tuple. When
        # specifying a static list, an i18n label will be generated for every
        # event type of the list. When specifying a dynamic list, you must also
        # give, in p_eventNameMethod, a method that will accept a single arg
        # (=one of the event types from your dynamic list) and return the "name"
        # of this event as it must be shown to the user.
        self.eventTypes = eventTypes or ()
        self.eventNameMethod = eventNameMethod
        if callable(eventTypes) and not eventNameMethod:
            raise Exception(MISS_EN_M)

        # Among event types, for some users, only a subset of it may be created.
        # "allowedEventTypes" is a method that must accept the list of all
        # event types as single arg and must return the list/tuple of event
        # types that the current user can create.
        self.allowedEventTypes = allowedEventTypes

        # It is not possible to create events that span more days than
        # maxEventLength.
        self.maxEventLength = maxEventLength

        # Various render modes exist. Default is the classical "month" view. The
        # currently proposed renderings are the following. Each value for
        # p_render is a string.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # p_render   | Description
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # month      | [default] Monthly view for an individual calendar
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # monthMulti | Monthly view for a multiple calendar (also called a
        #            | "timeline" view). A multiple calendar collects and
        #            | displays info about individual calendars, each one being
        #            | represented by an instance of class
        #            |
        #            |         appy.model.fields.calendar.other.Other
        #            |
        #            | , via attribute p_others (see below). On a "monthMulti"
        #            | view, on the x axis, we have one column per day, and on
        #            | the y axis, we have one row per individual calendar.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # week       | Week view for an individual calendar
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # dayMulti   | Daily view for a multiple calendar
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.render, self.multiple = self.getRenderInfo(render)

        # It has no sense to define event types in a multiple calendar
        if self.multiple and eventTypes:
            raise Exception(TL_W_EVTS)

        # When displaying a given month for this agenda, one may want to
        # pre-compute, once for the whole month, some information that will then
        # be given as arg for other methods specified in subsequent parameters.
        # This mechanism exists for performance reasons, to avoid recomputing
        # this global information several times. If you specify a method in
        # p_preCompute, it will be called every time a given month is shown, and
        # will receive 2 args: the first day of the currently shown month (as a
        # DateTime object) and the grid of all shown dates (as a result of
        # calling m_getGrid below). This grid may hold a little more than dates
        # of the current month. Subsequently, the return of your method will be
        # given as arg to other methods that you may specify as args of other
        # parameters of this Calendar class (see comments below).
        self.preCompute = preCompute

        # [Multiple only] A method must be specified in parameter p_others. It
        # must accept a single arg (the result of p_self.preCompute) and must
        # return a list of Other objects representing calendars whose events
        # must be shown within this agenda. More precisely, the method can
        # return:
        # - a single Other object;
        # - a list of Other objects;
        # - a list of lists of Other objects, when it has sense to group other
        #   calendars (the month, multiple rendering exploits this).
        self.others = others

        # [Multiple only] A name is shown for every other calendar. If
        # p_timelineName is None (the default), this name will be the title of
        # the object where the other calendar is defined. Else, it will be the
        # result of calling the method specified in p_timelineName. This method
        # must return a string and accepts those args:
        # - other     an Other object;
        # - month     the currently shown month, as a string YYYY/mm
        self.timelineName = timelineName

        # [Month, multiple only] The name of the current month is shown in
        # header in footer rows. If you want to customize this zone, specify a
        # method in the following attribute. It will receive, as args:
        # (1) an object containing infos about the current month, having the
        #     following attributes:
        #     * first: a DateTime object being the first day of the month;
        #     * month: the text representing the current month. The name of the
        #       month may be translated; it may contain XHTML formatting;
        # (2) the calendar's pre-computed data.
        # The method must modify the first arg's "month" attribute.
        self.timelineMonthName = timelineMonthName

        # [Invidual calendars only] One may want to add, day by day, custom
        # information in the calendar. When a method is given in
        # p_additionalInfo, for every zone of the current view, this method will
        # be called with these args:
        # 1. the current day, as a DateTime object whose "hour" part is
        #    irrelevant ;
        # 2. the current hour, as an integer value from 0 to 23 for an houred
        #    view like a day or week view, or None for an unhoured view like a
        #    month view ;
        # 3. the current render mode ('month' or 'week') ;
        # 4. the result of p_self.preCompute.
        # The method must return the content to insert, as a string that can
        # hold text or a chunk of XHTML.
        self.additionalInfo = additionalInfo

        # One may limit event encoding and viewing to some period of time,
        # via p_startDate and p_endDate. Those parameters, if given, must hold
        # methods accepting no arg and returning a DateTime object. The
        # start and end dates will then be converted to UTC at 00.00.
        self.startDate = startDate
        self.endDate = endDate

        # If a default date is specified, it must be a method accepting no arg
        # and returning a DateTime object. As soon as the calendar is shown,
        # the period where this date is included will be shown (day, week,
        # month, ... depending on the render mode). If not default date is
        # specified, it will be 'now' at the moment the calendar is shown.
        self.defaultDate = defaultDate

        # p_timeslots are a way to define, within a single day, time ranges. It
        # must be a list of Timeslot objects or a method producing such a list.
        # If you define timeslots, the first one must be the one representing
        # the whole day and must have id "main". Tip: for performance, when
        # defining a method in attribute "timeslots", it is best if you have the
        # possibility, in your app, to pre-compute lists of static timeslots,
        # and if the method you place in attribute "timeslots" simply returns
        # the correct precomputed list (according to some custom condition),
        # instead of creating a dynamic list within this method.
        Timeslot.init(self, timeslots)

        # By default, any timeslot may be selected, whatever event type is
        # selected. If you want to restrict subsets of timeslots that can be
        # selected for one or several event types, define a method in the
        # following attribute. This method must accept, as args, an event type.
        # If the method returns None, all timeslots from p_self.timeslots will
        # be selectable when the passed event type is selected. If the method
        # returns a list or tuple of timeslot ids, as soon as the passed event
        # type will be selected, the timeslot selector will only allow to select
        # the corresponding timeslots.
        self.slotMap = slotMap

        # [Month, multiple only] p_cellInfo determines what info to dump within
        #                        a given cell, in the "monthMulti" view. It can
        #                        be a dict of the form:
        #
        #                    ~{s_eventType: Cell}~
        #
        # or a method receiving 2 args: an event type and the pre-computed
        # object, and returning a Cell object for this type (or None if the cell
        # into which an event of this type must be dumped must be empty).
        # Indeed, in a month, multiple calendar, cells are too small to display
        # translated names for event types, so cell properties (with, if needed,
        # minimal textual content) are used instead.
        #
        # Tip: for representing background color variants, it is possible to
        # play with the "opacity" CSS property, ie:
        #
        #            Cell(style="background-color:#d08181;opacity:0.5"
        #
        self.cellInfo = cellInfo

        # [Month, multiple only] When p_cellInfo is in use, one may, in
        # combination, define a gradient. It is useful if the event's timeslot
        # doesn't span the whole day: the gradient may represent the "partial"
        # aspect of the timeslot (with, for example, an end color being
        # "transparent"). If you define such gradients in the following
        # attribute, every time a cell will need to be styled, if the timeslot
        # of the corresponding event does not span the whole day, a gradient
        # will be used instead of a plain color. Attribute "gradient" hereafter
        # must hold a dict (or a method returning a dict) whose keys are
        # timeslots (strings) and values are Gradient objects.
        self.gradients = gradients or {}

        # [Month, multiple only] For event types for which p_cellInfo is None,
        # must we still show them ? If yes, they will be represented by a dot
        # with a tooltip containing the event name.
        self.showNoCellInfo = showNoCellInfo

        # [Month, multiple only] In the timeline, the background color for
        # columns can be defined in a method you specify here. This method must
        # accept the current date (as a DateTime object) as unique arg. If None,
        # a default color scheme is used (see appy.model.field.calendar.views.
        # monthMulti.MonthMulti.timelineBgColors). Every time your method
        # returns None, the default color scheme will apply.
        self.columnColors = columnColors

        # [Individual only] For a specific day, all event types may not be
        # applicable. If this is the case, one may specify here a method that
        # defines, for a given day, a sub-set of all event types. This method
        # must accept 3 args:
        #  1. the day in question (as a DateTime object);
        #  2. the list of all event types, which is a copy of the (possibly
        #     computed) p_self.eventTypes;
        #  3. the result of calling p_self.preCompute.
        # The method must modify the 2nd arg and remove, from it, potentially
        # not applicable events. This method can also return a message, that
        # will be shown to the user for explaining him why he can, for this day,
        # only create events of a sub-set of the possible event types (or even
        # no event at all).
        self.applicableEvents = applicableEvents

        # [Month, multiple only] If you want to specify additional rows
        # representing totals, give, in p_totalRows, a list of Totals objects
        # (see appy.model.fields.calendar.totals.Totals) or a method producing
        # such a list.
        monthMulti = self.multiple and self.render == 'month'
        if totalRows and not monthMulti:
            raise Exception(Totals.TOT_KO)
        self.totalRows = totalRows or []

        # Similarly, you can specify additional columns in p_totalCols
        if totalCols and not monthMulti:
            raise Exception(Totals.TOT_KO)
        self.totalCols = totalCols or []

        # A validation process can be associated to a Calendar event. It
        # consists in identifying validators and letting them "convert" event
        # types being wished to final, validated event types. If you want to
        # enable this, define a Validation object (see the hereabove class) in
        # p_validation.
        self.validation = validation

        # [Month, multiple only] p_layers define a stack of layers (as a list or
        # tuple). Every layer must be a Layer object and represents a set of
        # data that can be shown or not on top of calendar data.
        self.layers = self.formatLayers(layers)

        # [Month, multiple only] If p_layersSelector is False, all layers having
        # activeByDefault=True will be shown but the selector allowing to (de)
        # activate layers will not be shown.
        self.layersSelector = layersSelector

        # [Non-multiple only] Beyond permission-based security, p_editable may
        # store a method whose result may prevent the user to edit the calendar
        # field.
        self.editable = editable

        # [Non-multiple only] May the user delete events in this calendar? If
        # p_delete is a method, it must accept an event type as single arg.
        self.delete = delete

        # [Non-multiple only] Before deleting an event, if a method is specified
        # in p_beforeDelete, it will be called with the date and timeslot as
        # args. If the method returns False, the deletion will not occur.
        self.beforeDelete = beforeDelete

        # If you want execute a specific action after an event has added, via
        # the UI, to this calendar, specify a method here, that must accept, as
        # args, the date, event type, timeslot and dayspan.
        self.afterCreate = afterCreate

        # You may specify PXs that will show specific information, respectively,
        # before and after the calendar.
        self.topPx = topPx
        self.bottomPx = bottomPx

        # p_actions is a list of Action objects allowing to define custom
        # actions to execute based on calendar data.
        self.actions = actions or ()

        # p_filters is a list of Filter objects allowing to define custom
        # filters for restricting the events shown on the current calendar view.
        self.filters = filters or ()

        # Each filter from p_self.filters will use, internally, a Field object.
        # These Field objects will, when filters are defined, be added in the
        # following dict, keyed by filter name.
        self.filterFields = None

        # When there is at least one visible action, on a monthly, multiple
        # calendar, timeline cells can be selected: this selection is then given
        # as parameter to the triggered action. If p_selectableEmptyCells is
        # True, all cells are selectable. Else, only cells whose content is not
        # empty are selectable.
        self.selectableEmptyCells = selectableEmptyCells

        # p_legend can hold a Legend object (as an instance of class
        # appy.model.fields.calendar.legend.Legend) that determines legend's
        # characteristcs on a month, multiple calendar.
        self.legend = legend or Legend()

        # [Month, individual only] p_selectableMonths determines the number of
        # months in the past or in the future, relative to the currently shown
        # one, that will be accessible by simply selecting them in a list.
        self.selectableMonths = selectableMonths

        # [Week, individual only] p_selectableWeeks is similar to
        # p_self.selectable months hereabove, but for weeks instead of months.
        self.selectableWeeks = selectableWeeks

        # The i18n label to use when the user creates a new event
        self.createEventLabel = createEventLabel

        # The name of a CSS class for the monthly view table. Several
        # space-separated names can be defined.
        self.style = style

        # [Month, multiple only] If p_strictMonths is True, only days of the
        # current month will be shown. Else, complete weeks will be shown,
        # potentially including some days from the previous and next months.
        if strictMonths and not monthMulti:
            raise Exception(S_MONTHS_KO)
        self.strictMonths = strictMonths

        # Width of a column in an "houred" view, ie, a view displaying events
        # hour after hour (render moes "week" or "dayMulti").
        self.houredWidth = houredWidth

        # If you place a method in the following attribute, it will be called to
        # determine if a day in the month view can be considered as full (ie, no
        # more event can be added into it). This method, if defined, will be
        # called with the following attributes: the target object, a particular
        # day (as a DateTime object), the list of events being defined at that
        # day, and the timeslots as define on p_self. The method must return
        # True if the day is to be considered as full. Note that, if an event on
        # the "main" timeslot is detected, the day will be considered as full
        # and p_self.fullDay will not be called at all. If p_self.fullDay is
        # None, a day will be considered as full if one event of each slot is
        # found or one event in the "main" slot is found.
        self.fullDay = fullDay

        # p_createObjects allows to enable the creation of Appy objects from a
        # monthly calendar cell, by rendering, in it, the corresponding "create"
        # button. It only works for root classes whose "create" button is, for
        # authorized users, available in the Appy portlet.
        #
        # If passed, p_createObjects must be a method accepting 2 args:
        # - the current day (as a DateTime object);
        # - cached info as computed by p_self.preCompute.
        #
        # If you decide an Appy object could be created at this day, return a
        # 2-tuple, with these elements:
        # - the name of the class for which an instance must be created;
        # - an appy.model.utils.Object instance, containing default values for
        #   the edit form.
        #
        # In this latter object, if the class defines a field name "date", Appy
        # will automatically set it to the passed day. For performance, please
        # avoid creating an Object instance everytime the method is called: put
        # such an object in p_self.preCompute or on the request cache, and
        # update it at each method call.
        #
        # It is useless to check whether the current user is allowed to create
        # instances of the returned class: Appy will check it and will render
        # the "create" button only if the check succeeds.
        self.createObjects = createObjects

        # Call the base constructor

        # p_validator, allowing field-specific validation, behaves differently
        # for the Calendar field. If specified, it must hold a method that will
        # be executed every time a user wants to create an event (or series of
        # events) in the calendar. This method must accept those args:
        #  - date       the date of the event (as a DateTime object);
        #  - eventType  the event type (one among p_eventTypes);
        #  - timeslot   the timeslot for the event (see param p_timeslots) ;
        #  - span       the number of additional days on which the event will
        #               span (will be 0 if the user wants to create an event
        #               for a single day).
        # If validation succeeds (ie, the event creation can take place), the
        # method must return True (boolean). Else, it will be canceled and an
        # error message will be shown. If the method returns False (boolean), it
        # will be a standard error message. If the method returns a string, it
        # will be used as specific error message.

        Field.__init__(self, validator, multiplicity, default, defaultOnEdit,
          show, renderable, page, group, layouts, move, False, True, None, None,
          False, None, readPermission, writePermission, width, height, None,
          colspan, master, masterValue, focus, False, mapping, generateLabel,
          label, None, None, None, None, True, False, view, cell, buttons, edit,
          custom, xml, translations)

    def getRenderInfo(self, render):
        '''Extract renderring info from p_render. Raise an error if data is
           incorrect.'''
        # Ensure p_render is among valid values
        modes = Calendar.renderModes
        if render not in modes:
            raise Exception(RENDER_KO % (render, ', '.join(modes)))
        # Extract the "Multi" prefix
        if render.endswith('Multi'):
            r = render[:-5], True
        else:
            r = render, False
        return r

    def formatLayers(self, layers):
        '''Chain layers via attribute "previous"'''
        if not layers: return ()
        i = len(layers) - 1
        while i >= 1:
            layers[i].previous = layers[i-1]
            i -= 1
        return layers

    def log(self, o, msg, date=None):
        '''Logs m_msg, field-specifically prefixed.'''
        prefix = f'{o.iid}:{self.name}'
        if date:
            dateS = date.strftime('%Y/%m/%d')
            prefix = f'{prefix}@{dateS}'
        o.log(f'{prefix}: {msg}')

    def getPreComputedInfo(self, o, view):
        '''Returns the result of calling p_self.preComputed, or None if no such
           method exists.'''
        pre = self.preCompute
        if pre: return pre(o, view.monthDayOne, view.grid)

    weekDays = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')

    def getNamesOfDays(self, _):
        '''Returns the translated names of all week days, short and long
           versions.'''
        r = {}
        for day in self.weekDays:
            r[day] = O(name=_(f'day_{day}'), short=_(f'day_{day}_short'))
        return r

    def getCellInfo(self, o, eventType, preCompute):
        '''Gets the Cell object determining how to render a cell containing an
           event of this p_eventType.'''
        info = self.cellInfo
        if info is None:
            r = None
        elif isinstance(info, dict):
            r = info.get(eventType)
        else: # A method
            r = info(o, eventType, preCompute)
        return r

    def getAdditionalInfoAt(self, o, date, hour, render, preComputed):
        '''If the user has specified a method in self.additionalInfo, we call
           it for displaying this additional info in the calendar, at some
           p_date and p_hour.'''
        info = self.additionalInfo
        return info(o, date, hour, render, preComputed) if info else None

    def getEventTypes(self, o):
        '''Returns the (dynamic or static) event types as defined in
           self.eventTypes.'''
        types = self.eventTypes
        return types(o) if callable(types) else types

    def getAllowedEventTypes(self, o, eventTypes):
        '''Gets the allowed events types for the currently logged user'''
        allowed = self.allowedEventTypes
        return eventTypes if not allowed else allowed(o, eventTypes)

    def getGradients(self, o):
        '''Gets the gradients possibly defined in addition to p_self.colors'''
        gradients = self.gradients
        return gradients(o) if callable(gradients) else gradients

    def dayIsFull(self, o, date, events, timeslots):
        '''In the calendar full at p_date ? Defined events at this p_date are in
           p_events. We check here if the main timeslot is used or if all
           others are used.'''
        if not events: return
        for e in events:
            if e.timeslot == 'main': return True
        # Call p_self.fullDay if defined
        full = self.fullDay
        if full:
            r = full(o, date, events, timeslots)
        else:
            r = len(events) == len(timeslots) - 1
        return r

    def dateInRange(self, date, view):
        '''Is p_date within the range (possibly) defined for this calendar by
           p_startDate and p_endDate ?'''
        tooEarly = view.startDate and date < view.startDate
        tooLate = view.endDate and not tooEarly and date > view.endDate
        return not tooEarly and not tooLate

    def getApplicableEventTypesAt(self, o, date, eventTypes, preComputed,
                                  forBrowser=False):
        '''Returns the event types that are applicable at a given p_date'''
        # More precisely, it returns an object with 2 attributes:
        # * "events" is the list of applicable event types;
        # * "message", not empty if some event types are not applicable,
        #              contains a message explaining those event types are
        #              not applicable.
        if not eventTypes: return # There may be no event type at all
        if not self.applicableEvents:
            # Keep p_eventTypes as is
            message = None
        else:
            eventTypes = eventTypes[:]
            message = self.applicableEvents(o, date, eventTypes, preComputed)
        r = O(eventTypes=eventTypes, message=message)
        if forBrowser:
            r.eventTypes = ','.join(r.eventTypes)
            if not r.message: r.message = ''
        return r

    def getEventsAt(self, o, date, empty=None, typeInfo=None):
        '''Returns the list of events that exist at some p_date (=day)'''
        # p_date can be:
        # - a DateTime object;
        # - a tuple (i_year, i_month, i_day);
        # - a string YYYYmmdd.
        # p_empty is returned if no event is found.
        # p_typeInfo, if passed, is a dict managed by a calendar view that
        # collects data about the event types that characterize the events it
        # shows (see appy.model.fields.calendar.typeInfo::TypeInfo). Among this
        # data, we find the count of events for every type. If p_typeInfo is
        # passed, this method updates this count for the returned events (if
        # any).
        if self.name not in o.values: return empty
        years = getattr(o, self.name)
        if not years: return empty
        # Get year, month and name from p_date
        if isinstance(date, tuple):
            year, month, day = date
        elif isinstance(date, str):
            year, month, day = int(date[:4]), int(date[4:6]), int(date[6:8])
        else:
            year, month, day = date.year(), date.month(), date.day()
        # Dig into the oobtree
        if year not in years: return empty
        months = years[year]
        if month not in months: return empty
        days = months[month]
        if day not in days: return empty
        r = days[day]
        if r and typeInfo:
            typeInfo.update(r)
        return r or empty

    def getEventAt(self, o, date, timeslot='main'):
        '''Get the event defined, for this calendar on this p_o(bject), at this
           p_date and p_timeslot.'''
        events = self.getEventsAt(o, date)
        if not events: return
        for event in events:
            if event.timeslot == timeslot:
                return event

    def getEventTypeAt(self, o, date):
        '''Returns the event type of the first event defined at p_day, or None
           if unspecified.'''
        events = self.getEventsAt(o, date)
        return events[0].eventType if events else None

    def getEventsBySlot(self, o, date, addEmpty=False, ifEmpty='-', expr=None,
                        persist=False):
        '''Returns a list of (s_timeslot, event) tuples for every event defined
           in this calendar on p_o at this p_date.'''
        return Timeslot.getEventsAt(o, self, date, addEmpty, ifEmpty, expr,
                                    persist)

    def standardizeDateRange(self, range):
        '''p_range can have various formats (see m_walkEvents below). This
           method standardizes the date range as a 6-tuple
           (startYear, startMonth, startDay, endYear, endMonth, endDay).'''
        if not range: return
        if isinstance(range, int):
            # p_range represents a year
            return (range, 1, 1, range, 12, 31)
        elif isinstance(range[0], int):
            # p_range represents a month
            year, month = range
            return (year, month, 1, year, month, 31)
        else:
            # p_range is a tuple (start, end) of DateTime instances
            start, end = range
            return (start.year(), start.month(), start.day(),
                    end.year(),   end.month(),   end.day())

    def walkEvents(self, o, callback, dateRange=None):
        '''Walks, on p_o, the calendar value in chronological order for this
           field and calls p_callback for every day containing events. The
           callback must accept 3 args: p_o, the current day (as a DateTime
           instance) and the list of events at that day (the database-stored
           PersistentList instance). If the callback returns True, we stop the
           walk.

           If p_dateRange is specified, it limits the walk to this range. It
           can be:
           * an integer, representing a year;
           * a tuple of integers (year, month) representing a given month
             (first month is numbered 1);
           * a tuple (start, end) of DateTime instances.
        '''
        if self.name not in o.values: return
        yearsDict = getattr(o, self.name)
        if not yearsDict: return
        # Standardize date range
        if dateRange:
            startYear, startMonth, startDay, endYear, endMonth, endDay = \
              self.standardizeDateRange(dateRange)
        # Browse years
        years = list(yearsDict.keys())
        years.sort()
        for year in years:
            # Ignore this year if out of range
            if dateRange:
                if (year < startYear) or (year > endYear): continue
                isStartYear = year == startYear
                isEndYear = year == endYear
            # Browse this year's months
            monthsDict = yearsDict[year]
            if not monthsDict: continue
            months = list(monthsDict.keys())
            months.sort()
            for month in months:
                # Ignore this month if out of range
                if dateRange:
                    if (isStartYear and (month < startMonth)) or \
                       (isEndYear and (month > endMonth)): continue
                    isStartMonth = isStartYear and (month == startMonth)
                    isEndMonth = isEndYear and (month == endMonth)
                # Browse this month's days
                daysDict = monthsDict[month]
                if not daysDict: continue
                days = list(daysDict.keys())
                days.sort()
                for day in days:
                    # Ignore this day if out of range
                    if dateRange:
                        if (isStartMonth and (day < startDay)) or \
                           (isEndMonth and (day > endDay)): continue
                    date = DateTime(f'{year}/{month}/{day} UTC')
                    stop = callback(o, date, daysDict[day])
                    if stop: return

    def hasEventsAt(self, o, date, events):
        '''Returns True if, at p_date, events are exactly of the same type as
           p_events.'''
        if not events: return
        others = self.getEventsAt(o, date)
        if not others: return
        if len(events) != len(others): return
        i = 0
        while i < len(events):
            if not events[i].sameAs(others[i]): return
            i += 1
        return True

    def getEventName(self, o, eventType):
        '''Gets the name of the event corresponding to p_eventType as it must
           appear to the user.'''
        if self.eventNameMethod:
            return self.eventNameMethod(o, eventType)
        else:
            return o.translate(f'{self.labelId}_event_{eventType}')

    def getStartDate(self, o):
        '''Get the start date for this calendar if defined'''
        if self.startDate:
            d = self.startDate(o)
            # Return the start date without hour, in UTC
            return DateTime(f'{d.year()}/{d.month()}/{d.day()} UTC')

    def getEndDate(self, o):
        '''Get the end date for this calendar if defined'''
        if self.endDate:
            d = self.endDate(o)
            # Return the end date without hour, in UTC
            return DateTime(f'{d.year()}/{d.month()}/{d.day()} UTC')

    def getDefaultDate(self, o):
        '''Get the default date that must appear as soon as the calendar is
           shown.'''
        default = self.defaultDate
        if default:
            r = default(o)
            if r: return r
        # Return the start date if defined, now else
        return self.getStartDate(o) or dutils.Date.toUTC(DateTime())

    def mayDelete(self, o, events):
        '''May the user delete p_events ?'''
        delete = self.delete
        if not delete: return
        return delete(o, events[0].eventType) if callable(delete) else True

    def mayEdit(self, o, raiseError=False):
        '''May the user edit calendar events ?'''
        # Check the security-based condition
        if not o.guard.mayEdit(o, self.writePermission, raiseError=raiseError):
            return
        # Check the field-specific condition
        return self.getAttribute(o, 'editable')

    def deleteEvent(self, o, date, timeslot, handleEventSpan=True, log=True,
                    say=True, executeMethods=True):
        '''Deletes an event. If t_timeslot is "*", it deletes all events at
           p_date, be there a single event on the main timeslot or several
           events on other timeslots. Else, it only deletes the event at
           p_timeslot. If p_handleEventSpan is True, req.deleteNext will be used
           to delete successive events, too. Returns the number of deleted
           events.'''
        events = self.getEventsAt(o, date)
        if not events: return 0
        # Execute "beforeDelete"
        if executeMethods and self.beforeDelete:
            ok = self.beforeDelete(o, date, timeslot)
            # Abort event deletion when required
            if ok is False: return 0
        daysDict = getattr(o, self.name)[date.year()][date.month()]
        count = len(events)
        if timeslot == '*':
            # Delete all events at this p_date, and possible at subsequent days,
            # too, of p_handleEventSpan is True. Remember their v_eNames.
            eNames = ', '.join([e.getName(o, self, None, xhtml=False) \
                                for e in events])
            r = count
            del daysDict[date.day()]
            req = o.req
            suffix = ''
            if handleEventSpan and req.deleteNext == 'True':
                # Delete similar events spanning the next days when relevant
                nbOfDays = 0
                while True:
                    date += 1
                    if self.hasEventsAt(o, date, events):
                        r += self.deleteEvent(o, date, timeslot, say=False,
                                    handleEventSpan=False, executeMethods=False)
                        nbOfDays += 1
                    else:
                        break
                if nbOfDays: suffix = f', span+{nbOfDays}'
            if log:
                msg = EVT_DEL % (eNames, count, suffix)
                self.log(o, msg, date)
        else:
            # Delete the event at p_timeslot
            r = 1
            i = len(events) - 1
            while i >= 0:
                if events[i].timeslot == timeslot:
                    name = events[i].getName(o, self, None, xhtml=False)
                    msg = EVT_DEL_SL % (name, timeslot)
                    del events[i]
                    if log: self.log(o, msg, date)
                    break
                i -= 1
        if say:
            o.say(o.translate('object_deleted'), fleeting=False)
        return r

    def deleteEvents(self, o, start, end, timeslot, handleEventSpan=True,
                     log=True, say=True, executeMethods=True):
        '''Calls m_deleteEvent to delete all events between these p_start and
           p_end dates (DateTime objects), transmitting all other parameters to
           m_deleteEvent. Returns the number of deleted events.'''
        r = 0
        for day in dutils.DayIterator(start, end):
            r += self.deleteEvent(o, day, timeslot,
                                  handleEventSpan=handleEventSpan, log=log,
                                  say=say, executeMethods=executeMethods)
        return r

    def validate(self, o, date, eventType, timeslot, span=0):
        '''The validation process for a calendar is a bit different from the
           standard one, that checks a "complete" request value. Here, we only
           check the validity of some insertion of events within the
           calendar.'''
        if not self.validator: return
        r = self.validator(o, date, eventType, timeslot, span)
        if isinstance(r, str):
            # Validation failed, and we have the error message in "r"
            return r
        # Return a standard message if the validation fails without producing a
        # specific message.
        return r or o.translate('field_invalid')

    traverse['process'] = 'perm:write'
    def process(self, o):
        '''Processes an action coming from the calendar widget, ie, the creation
           or deletion of a calendar event.'''
        # Refined security check
        self.mayEdit(o, raiseError=True)
        req = o.req
        action = req.actionType
        # Get the date and timeslot for this action
        date = DateTime(req.day)
        eventType = req.eventType
        eventSpan = req.eventSpan or 0
        eventSpan = min(int(eventSpan), self.maxEventLength)
        if action == 'createEvent':
            # Trigger validation
            timeslot = req.timeslot or 'main'
            valid = self.validate(o, date, eventType, timeslot, eventSpan)
            if isinstance(valid, str): return valid
            return Event.create(o, self, date, eventType, timeslot=timeslot,
                                eventSpan=eventSpan)
        elif action == 'deleteEvent':
            self.deleteEvent(o, date, req.timeslot or '*')

    def splitList(self, l, sub): return utils.splitList(l, sub)

    def mayValidate(self, o):
        '''May the currently logged user validate wish events ?'''
        valid = self.validation
        return valid.mayValidate(o) if valid else None

    def completeAjaxParams(self, hook, o, view, params):
        '''Complete these p_params, to be used for performing an Ajax request
           for refreshing the widget view.'''
        # If the calendar is used as mode for a search, carry request keys
        # allowing to identify this search.
        req = o.req
        if req.search:
            params['resultMode'] = 'calendar'
        # Add the key corresponding to the current period type (month, day,...)
        period = view.periodType
        params[period] = getattr(view, period)
        params['layout'] = o.H().getLayout()
        params['multiple'] = '1' if self.multiple else '0'
        params['filters'] = view.filterValues
        params['render'] = req.render or view.field.render

    def getAjaxData(self, hook, o, view, **params):
        '''Initializes an AjaxData object on the DOM node corresponding to
           this calendar field.'''
        # If the calendar is used in the context of a search, take the
        # search-based AjaxData parent object into account.
        parent = ",'searchResults',null,null,null,true" if o.req.search else ''
        # Update p_params
        self.completeAjaxParams(hook, o, view, params)
        params = sutils.getStringFrom(params)
        # Define a JS objet that manages filters, if appropriate
        if view.filters:
            info = {f.name: f.getWidgetType() for f in view.filters.values()}
            info = sutils.getStringFrom(info)
            jsf = f"; new Filters('{o.iid}','{self.name}',{info})"
        else:
            jsf = ''
        return f"new AjaxData('{o.url}/{self.name}/view','POST',{params}," \
               f"'{hook}'{parent}){jsf}"

    traverse['validateEvents'] = 'perm:write'
    def validateEvents(self, o):
        '''Validate or discard events from the request'''
        return self.validation.do(o, self)

    def getActiveLayers(self, req):
        '''Gets the layers that are currently active'''
        if 'activeLayers' in req:
            # Get them from the request
            layers = req.activeLayers or ()
            r = layers if not layers else layers.split(',')
        else:
            # Get the layers that are active by default
            r = [layer.name for layer in self.layers if layer.activeByDefault]
        return r

    traverse['executeAction'] = 'perm:read'
    def executeAction(self, o):
        '''An action has been triggered from the ui'''
        # Find the action to execute
        req = o.req
        name = req.actionName
        monthDayOne = DateTime(f'{req.month}/01')
        action = None
        for act in self.Action.getVisibleOn(o, self, monthDayOne):
            if act.name == name:
                action = act
                break
        if not action: raise Exception(ACT_MISS % name)
        # Get the selected cells
        selected = []
        tool = o.tool
        sel = req.selected
        if sel:
            for elems in sel.split(','):
                id, date = elems.split('_')
                # Get the calendar object from "id"
                calendarObj = tool.getObject(id)
                # Get a DateTime instance from "date"
                calendarDate= DateTime(f'{date[:4]}/{date[4:6]}/{date[6:]} UTC')
                selected.append((calendarObj, calendarDate))
        # Execute the action
        return action.action(o, selected, req.comment)

    def store(self, o, value):
        '''Stores this complete p_value on p_o'''
        if not self.persist or value is None: return
        # Data can be a IOBTree
        if isinstance(value, IOBTree):
            super().store(o, value)
            return
        # Data can also be a standard dict. It is the case, for example, for
        # calendar data imported from a distant site.
        for year, sub1 in value.items():
            if not sub1: continue
            for month, sub2 in sub1.items():
                if not sub2: continue
                for day, events in sub2.items():
                    if not events: continue
                    date = DateTime(f'{year}/{month}/{day}')
                    for event in events:
                        Event.create(o, self, date, event.eventType,
                                     timeslot=event.timeslot, log=False)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
