'''Views for a calendar'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from DateTime import DateTime

from appy.px import Px
from appy.utils import exeC
from ..filter import Filter
from appy.utils import string as sutils
from appy.model.fields.poor import Poor

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class View:
    '''Abstract class representing any calendar view, be it individual or
       multiple, whatever period type: monthly, weekly, daily.'''

    # Among all views, one may distinguish individual views, containing info
    # about a single individual or object, from multiple views, showing info
    # about several individual views.
    multiple = False

    # May events be created, updated or deleted via this view ? Detecting if the
    # current view inherits from class Editable does not work: for example, a
    # MonthMulti is not editable, but inherits from Month, that inherits from
    # Editable.
    editable = False

    # Background cell gradient used when rendering several events in a place
    # (typically, a cell) with very little space.
    cellGradient = 'background-image:radial-gradient(#c2c2c2,#fff)'

    # Make some classes available here
    Poor = Poor

    def __init__(self, o, field):
        '''View constructor'''
        self.o = o
        self.req = o.req
        self.tool = o.tool
        self.field = field
        # Compute the render mode, and variant (see m_getRender)
        self.render = self.getRender()
        self.renderRaw = self.getRender(cheat=False)
        # The default date to show (+ its string representation)
        self.defaultDate = field.getDefaultDate(o)
        self.defaultDateS = self.defaultDate.strftime(self.periodFormat)
        # Today
        self.today = DateTime('00:00 UTC')
        self.now = DateTime() # With the precise hour and minute
        # The time period covered by the calendar may be restricted
        self.startDate = field.getStartDate(o)
        self.endDate = field.getEndDate(o)
        # p_self.around defines the surrounding periods w.r.t the current one
        # (ie: the next and previous months or weeks). The concrete views using
        # this concept must define, in p_self.around, a object having these
        # attributes:
        # - "previous" stores the previous period ~O(s_id,s_text)~ ;
        # - "next"     stores the next period     ~O(s_id,s_text)~ ;
        # - "all"      stores all the surrounding periods, as a list
        #              ~[O(s_id,s_text)]~. Previous and next periods must be in
        #              this latter list as well.
        self.around = None
        # Initialise data related to filters
        self.initFilters()

    def initFilters(self):
        '''Get, when relevant, filters and their currently applied values'''
        # Get the applicable filters, if any
        o = self.o
        field = self.field
        self.filters = filters = Filter.getVisibleOn(o, field)
        # Parse the filter values from the request, if found. Do it even if
        # there is currently no visible filter; that way, values are carried in
        # the page and could be used again once some filters are visible again.
        req = self.req
        values = o.class_.getFilters(self.tool, fields=field.filterFields)
        # Each filter may propose a variant of its selected values. The actual
        # values passed to the filter methods will be the adapted values, if
        # defined, p_values else.
        self.adaptedValues = {}
        if filters:
            # Express values as required by the internal filter fields, in order
            # to correctly render every filter and its currently selected
            # value(s).
            for filteR in filters.values():
                adapted = filteR.patchRequest(req, values)
                if adapted:
                    self.adaptedValues[filteR.name] = adapted
        self.filterValues = values

    def unfiltered(self, event):
        '''Returns True if this p_event hasn't been hidden by any of the
           currently applicable filters.'''
        # Get the currently applied filter values
        allValues = self.filterValues
        if not allValues: return True
        o = self.o
        for name, values in allValues.items():
            # Ignore this entry if it contains no value
            if not values: continue
            filteR = self.filters.get(name)
            # The filter may currently not be shown on p_self
            if not filteR: continue
            # Does this v_filteR hide this p_event ? Use possibly adapted filter
            # values from p_self.adaptedValues.
            usedValues = self.adaptedValues.get(filteR.name) or values
            if filteR.hides(o, event, usedValues):
                return
        # If we are here, no filter has hidden the value
        return True

    def getShownEvents(self, events):
        '''Returns the events, among p_events, being shown despite the currently
           applied filter(s) on p_self.'''
        if not events or not self.filterValues:
            return events
        return [event for event in events if self.unfiltered(event)]

    def getRender(self, cheat=True, value=None):
        '''Gets the render mode as currently set in this view (month, day...)'''
        # Try to get it first from the request (indeed, several modes can be
        # available for the same calendar field); if not found, get the default
        # mode.
        if value is not None:
            # A render p_value may be forced
            r = value
        else:
            req = self.req
            r = req.render or self.field.render
        # A week view is implemented as a day view with its surrounding days.
        # Consequently, in most cases (p_cheat is True), a "week" mode must be
        # re-expressed as a "day" mode.
        if cheat and r == 'week':
            r = 'day'
        return r

    # "Period type" is a synonym for "render mode"
    getPeriodType = getRender

    def getGrid(self, period=None):
        '''Returns the list of DateTime objects (one per day) corresponding to
           the period of time being shown at a time in the view, or to p_period
           if passed.'''
        # Must be called by child classes, within their overridden constructor.
        # The grid must be placed in attribute named p_self.grid.

    def getGridEdge(self, first=True):
        '''Returns the first or last element from the grid, depending on
           p_first.'''
        # Depending on concrete classes, a grid may be a list or DateTime
        # objects or a list of lists of such objects.
        i = 0 if first else -1
        r = self.grid[i]
        if isinstance(r, list):
            r = r[i]
        return r

    def mayGo(self, back=True):
        '''When p_self has surrounding periods defined in p_self.around, may we
           currently go to the next (p_back is False) or previous (p_back is
           True) period ?'''
        around = self.around
        # When no surrounding is defined, there is no constraint on going back
        # or forward.
        if not around: return True
        if back:
            r = not self.startDate or around.previous
        else:
            r = not self.endDate or around.next
        return r

    def switchPeriod(self, period):
        '''Re-express period, being a day or month, into its opposite
           expression: a month or a day.'''
        if '-' in period:
            # Re-express this day (%Y-%m-%d) as a month (%Y/%m)
            parts = period.split('-')
            r = f'{parts[0]}/{parts[1]}'
        else:
            # Re-express this month (%Y/%m) as a day (%Y-%m-%d)
            parts = period.split('/')
            r = f'{parts[0]}-{parts[1]}-01'
        return r

    def getNameOnMulti(self, other):
        '''Returns the name of this p_other calendar as must be shown in a
           multiple view.'''
        method = self.field.timelineName
        # What is the current render mode for the shown multiple calendar ?
        req = self.req
        render = self.render
        # What is the currently shown period ?
        period = req[render] or self.defaultDateS
        # What is the render mode for the sub-calendar ?
        subRender = self.getRender(value=other.field.render)
        if subRender != render:
            # Re-express the period according to v_subRender
            period = self.switchPeriod(period)
        if method:
            r = method(self.o, other, period, self.grid)
        else:
            r = f'<a href="{other.o.url}?{subRender}={period}">' \
                f'{other.o.getShownValue()}</a>'
        return r

    def renderEvent(self, event, o, field, c):
        '''Returns a representation for p_event on p_self'''
        # The name of the render class is passed: the event may be rendered
        # differently according to it.
        className = self.__class__.__name__
        return event.getName(o, field, c.timeslots, c.typeInfo, mode=className)

    def getOthers(self):
        '''Returns info about the other views the user may switch to from this
           one.'''
        # May be overridden by child classes. By default, return value is None:
        # no switch may occur. Overridden methods may either return None, or a
        # list of info about each render mode. Every element in this list must
        # be a tuple whose:
        # - 1st elem is the name of the render mode, as a string whose potential
        #   "Multi" suffix has been removed ;
        # - 2nd elem is a dict of additionnal parameters, used to initialise the
        #   view. For example, if you want to switch to the month view, you may
        #   specify the current month to switch to, with a dict like
        #
        #                       {'month': '2025/05'}

    def getAjaxSwitch(self, hook, other, params):
        '''Return the JS code allowing to switch from the current view to this
           p_other one, with these p_param(eter)s.'''
        # Add, among p_params, the one that specifies the view. It may already
        # been there if p_params is reused from one call to the other.
        params['render'] = other
        params = sutils.getStringFrom(params)
        return f"askAjax('{hook}',null,{params})"

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                              Class methods
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @classmethod
    def get(class_, o, field, ignoreReq=False):
        '''Return a concrete View object for viewing this calendar p_field on
           this p_object.'''
        # Deduce the name of the concrete class from p_field rendering-related
        # attributes.
        suffix = 'Multi' if field.multiple else ''
        if ignoreReq:
            render = field.render
        else:
            render = o.req.render or field.render
        className = f'{render.capitalize()}{suffix}'
        moduleName = f'{render}{suffix}'
        concrete = exeC(f'from appy.model.fields.calendar.views.{moduleName} ' \
                        f'import {className}', className)
        return concrete(o, field)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
