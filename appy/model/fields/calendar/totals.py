#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy import utils
from appy.px import Px
from appy.xml.escape import Escape
from appy.model.utils import Object as O

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Total:
    '''Represents a computation that will be executed on a series of cells
       (in a row or a column) within a multiple calendar.'''

    def __init__(self, totals, color=None, title=None, bgColor=None,style=None):
        '''Total constructor'''
        # The corresponding Totals object
        self.totals = totals
        # The name associated to this total (see class Totals)
        self.name = totals.name
        # Get the initial value for the total to compute
        initV = totals.initValue
        # If it is mutable, get a copy of it
        if isinstance(initV, dict):
            initV = initV.copy()
        elif isinstance(initV, list):
            initV = initV[:]
        self.value = initV
        # Beyond p_value, if one wants to produce a grand total for a sequence
        # of Total objects, also update p_self.grand with the raw content of
        # p_self.value, without applying any formatting to it. If p_self.grand
        # is left to None, no grand total will be computed. Grand totals can
        # only be computed if the same Totals object is used both as a column
        # and row total.
        self.grand = None
        # The following attributes allow to style the cell into which the total
        # will be dumped.
        self.color = color # The font color
        self.title = title # The cell's tooltip
        self.bgColor = bgColor # The cell's background color
        self.style = style # Any additional CSS property can be expressed here,
                           # as a classic semi-colon-separated list of CSS
                           # properties.

    def __repr__(self):
        '''p_self's short string representation'''
        return f'‹Total::{self.name}={str(self.value)}›'

    def getStyles(self):
        '''Returns potential CSS attributes to apply to the HTML cell as
           produced by m_asCell.'''
        r = None
        # Font color
        if self.color:
            color = f'color:{self.color}'
            if r is None: r = []
            r.append(color)
        # Background color
        if self.bgColor:
            bgColor = f'background-color:{self.bgColor}'
            if r is None: r = []
            r.append(bgColor)
        # Other CSS attributes
        if self.style:
            if r is None: r = []
            r.append(self.style)
        if r is None: return ''
        r = ';'.join(r)
        return f' style="{r}"'

    def asCell(self, c, tag='td'):
        '''Renders the "td" tag containing p_self's value'''
        val = self.value
        if val is None:
            val = ''
        elif not isinstance(val, str):
            formaT = self.totals.formaT
            val = formaT(val, c) if formaT else str(val)
        # Integrate CSS and other elements
        title = f' title={Escape.xhtml(self.title)}' if self.title else ''
        return f'<{tag}{title}{self.getStyles()}>{val}</{tag}>'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Totals:
    '''Represents, on a multi-calendar, additional rows or columns containing
       totals computed from data associated to inner, individual calendars.'''

    # Class Running (see below) will be traversable from this class
    traverse = {'Running': True}

    # Totals objects are to be defined in attributes Calendar.totalRows and
    # Calendar.totalCols.

    # A Totals object may apply to all views or be restricted to a single view
    SCOPE_ALL   = 0
    SCOPE_MONTH = 1
    SCOPE_WEEK  = 2

    TOT_KO = 'Totals cannot be set on non-multiple calendars.'

    def __init__(self, name, label, onCell, initValue=0, translated=False,
                 scope=SCOPE_ALL, formaT=None):
        # p_name must hold a short name or acronym and will directly appear
        # at the beginning of the row. It must be unique within all Totals
        # objects defined for a given Calendar field.
        self.name = name
        # p_label is a i18n label that will be used to produce a longer name
        # that will be shown as an "abbr" tag around the name.
        self.label = label
        # If p_translated is True, p_label is not a i18n label, but an already
        # translated term.
        self.translated = translated
        # p_onCell must hold a method that will be called every time a cell is
        # walked in the agenda. It will get a single arg being the current PX
        # context, onto which the following attributes have an interest here:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #    date     | The date representing the current day (a DateTime
        #             | object) ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #    other    | the Other object representing the currently walked
        #             | calendar ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #    events   | the list of events (as Event objects) defined at that
        #             | day in this calendar. Be careful: this can be None ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # shownEvents | the sub-list of shown events, when filters are applied.
        #             | If no filter applies, it is the same as the list in
        #             | attribute "events". It can also be None ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #    total    | the Total object (see above) corresponding to the
        #             | current column ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #    last     | a boolean that is True if we are walking the last shown
        #             | calendar ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   checked   | a value "checked" indicating the status of the possible
        #             | validation checkbox corresponding to this cell. If there
        #             | is a checkbox in this cell, the value will be True or
        #             | False; else, the value will be None ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #    cache    | the result of Calendar.cache (see below). This is a
        #             | cache at the Calendar field level, not to be confused
        #             | with the cache from the Appy request handler.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # This method must, when appropriate, update attribute total.value with
        # the value from the current cell. If last is True, total.value is
        # completed, and p_onCell can convert it to a string. Before performing
        # such transform, if you want to have the possibility to compute a grand
        # total, copy the unformatted total.value to total.grand. Here is an
        # example:
        #
        # if c.last:
        #     total.grand = total.value
        #     total.value = youFormatStuff(total.value)
        #
        # If, when Appy must render the total, total.value is unformatted (ie,
        # it is not a string):
        # 1. if you have specified a format method in p_formaT, it will be
        #    called ;
        # 2. else, the value will be converted that way: value = str(value).
        self.onCell = onCell
        # p_initValue is the initial value given to created Total objects
        self.initValue = initValue
        # The p_scope, for a Totals object, determines on what calendar view(s)
        # it must be shown and computed (see constants defined hereabove).
        self.scope = scope
        # When a total, once all p_onCell calls have been performed, is
        # complete, the following method will be called to produce a showable,
        # formatted value. This method will be called with 2 args: the value to
        # format and the current PX context (the same as passed to p_onCell).
        # This method will also be used (and is the unique way) to format grand
        # totals.
        self.formaT = formaT

    def __repr__(self):
        '''p_self as a short string'''
        return f'‹Totals {self.name}, scope={self.scope}›'

    def inScope(self, render):
        '''Must this Totals object (p_self) be rendered on this p_calendar
           field ?'''
        # It depends on p_self.scope
        scope = self.scope
        if scope == Totals.SCOPE_ALL:
            r = True
        elif scope == Totals.SCOPE_MONTH:
            r = render == 'month'
        elif scope == Totals.SCOPE_WEEK:
            r = render == 'week'
        else:
            r = False
        return r

    def getGrand(self, totals, c):
        '''Compute, format and return the grand total corresponding to the sum
           of p_totals, being a list of Total objects corresponding to
           p_self.'''
        # Compute the grand total
        r = 0
        for total in totals:
            tgrand = total.grand
            if tgrand:
                r += tgrand
        # Format it
        return self.formaT(c.outer.o, r, c) if self.formaT else str(r)

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                             Class methods
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @classmethod
    def getAjaxData(class_, field, o, type, hook):
        '''Initializes an AjaxData object on the DOM node corresponding to
           the zone containing the total rows/cols (depending on p_type) in a
           timeline calendar.'''
        suffix = 'trs' if type == 'rows' else 'tcs'
        return f"new AjaxData('{o.url}/{field.name}/Totals/pxFromAjax','GET'," \
               f"{{'multiple':'1'}},'{hook}_{suffix}','{hook}')"

    @classmethod
    def get(class_, o, field, typE, render):
        '''Returns the Totals objects by getting them from p_field.totalRows
           or p_field.totalCols (depending on p_typE).'''
        r = getattr(field, f'total{typE.capitalize()}')
        r = r(o) if callable(r) else r
        # Keep only those that must be rendered, depending on their scope
        return [totals for totals in r if totals.inScope(render)]

    # Status for checkboxes used to (in)validate calendar events
    checkboxStatuses = {'validated': True, 'discarded': False}

    @classmethod
    def getValidationCBStatus(class_, req):
        '''Gets the status of the validation checkboxes from the request'''
        r = {}
        for status, value in class_.checkboxStatuses.items():
            ids = req[status]
            if ids:
                for id in ids.split(','): r[id] = value
        return r

    @classmethod
    def compute(class_, field, allTotals, totalType, c):
        '''Compute the totals for every column (p_totalType == 'row') or row
           (p_totalType == "col").'''
        if not allTotals: return
        # Count other calendars and dates in the grid
        grid = c.grid
        date = c.date
        others = c.others
        othersCount = 0
        for group in others: othersCount += len(group)
        datesCount = len(grid)
        isRow = totalType == 'row'
        # Initialise, for every (row or col) totals, Total objects
        totalCount = datesCount if isRow else othersCount
        lastCount = othersCount if isRow else datesCount
        r = {}
        for totals in allTotals:
            name = totals.name
            r[name] = [Total(totals) for i in range(totalCount)]
        # Get the status of validation checkboxes
        status = class_.getValidationCBStatus(c.o.req)
        # Walk every date within every calendar
        indexes = {'i': -1, 'j': -1}
        ii = 'i' if isRow else 'j'
        jj = 'j' if isRow else 'i'
        o = c.o
        for other in utils.IterSub(others):
            indexes['i'] += 1
            indexes['j'] = -1
            c.other = other
            for date in grid:
                indexes['j'] += 1
                c.date = c.day = date
                # Get the events in this other calendar at this date
                c.events = other.field.getEventsAt(other.o, date)
                c.shownEvents = c.view.getShownEvents(c.events)
                # From info @this date, update the total for every totals
                c.last = indexes[ii] == lastCount - 1
                # Get the status of the validation checkbox that is possibly
                # present at this date for this calendar
                c.checked = None
                dateS = date.strftime('%Y%m%d')
                cbId = f'{other.o.iid}_{other.field.name}_{dateS}'
                if cbId in status:
                    c.checked = status[cbId]
                # Update the Total object for every Totals object, at v_date
                for totals in allTotals:
                    c.total = r[totals.name][indexes[jj]]
                    totals.onCell(o, c)
        return r

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                                  PX
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Total rows shown at the bottom of a timeline calendar.
    # Obsolete :: Currently used by the monthMulti view only.
    # Will be replaced by PX Running.pxRows.

    pxRows = Px('''
     <tbody id=":f'{hook}_trs'"
            var="grid=view.grid;
                 rows=field.Totals.get(o, field, 'rows', view.renderRaw);
                 totals=field.Totals.compute(field, rows, 'row', _ctx_)">
      <script>:field.Totals.getAjaxData(field, o, 'rows', hook)</script>
      <tr for="row in rows"
          var2="rowTitle=row.label if row.translated else _(row.label)">
       <td class="tlLeft">
        <abbr title=":rowTitle"><b>:row.name</b></abbr></td>
       <x for="date in grid">::totals[row.name][loop.date.nb].asCell(_ctx_)</x>
       <td class="tlRight">
        <abbr title=":rowTitle"><b>:row.name</b></abbr></td>
      </tr>
     </tbody>''')

    # Total columns besides the calendar, as a separate table
    pxCols = Px('''
     <table cellpadding="0" cellspacing="0" class="list timeline"
            style="float:right" id=":f'{hook}_tcs'"
            var="grid=view.grid;
                 render=view.renderRaw;
                 cols=field.Totals.get(o, field, 'cols', render);
                 rows=field.Totals.get(o, field, 'rows', render);
                 totals=field.Totals.compute(field, cols, 'col', _ctx_)">
      <script>:field.Totals.getAjaxData(field, o, 'cols', hook)</script>

      <!-- 2 empty rows -->
      <tr><th for="col in cols" class="hidden">-</th></tr>
      <tr><td for="col in cols" class="hidden">-</td></tr>

      <!-- The column headers -->
      <tr>
       <td for="col in cols"><abbr title=":_(col.label)">:col.name</abbr></td>
      </tr>

      <!-- Re-create one row for every other calendar -->
      <x var="i=-1" for="groupO in others">
       <tr for="other in groupO" var2="@i=i+1">
        <x for="col in cols">::totals[col.name][i].asCell(_ctx_)</x>
       </tr>

       <!-- The separator between groups of other calendars -->
       <x if="not loop.groupO.last">::field.Other.getSep(len(cols))</x>
      </x>

      <!-- Add empty rows for every total row -->
      <tr for="row in rows"><td for="col in cols">&nbsp;</td></tr>

      <!-- Repeat the column headers -->
      <tr>
       <td for="col in cols"><abbr title=":_(col.label)">:col.name</abbr></td>
      </tr>

      <!-- 2 empty rows -->
      <tr><td for="col in cols" class="hidden">-</td></tr>
      <tr><th for="col in cols" class="hidden">-</th></tr>
     </table>''')

    # Ajax-call pxRows or pxCols
    pxFromAjax = Px('''
     <x var="view=field.View.get(o, field);
             totalType=req.totalType.capitalize();
             hook=f'{o.iid}{field.name}';
             cache=field.getCache(o, view);
             others=field.Other.getAll(o, field,
                      cache)">:getattr(field.Totals, f'px{totalType}')</x>''')

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Running:
    '''Running totals, being built while rendering a calendar view'''

    # 2 types of running totals are computed: column and row totals
    types = 'cols', 'rows'

    def __init__(self, outer, c, compute=False):
        '''Create and initialise Total objects onto which to compute totals for
           every row and every column total, on the current view as defined in
           the p_c(ontext).'''
        # The multiple planning, represented as an Other object, onto which
        # totals are ran.
        self.outer = outer
        # The calendar view being rendered
        self.view = c.view
        # Store Total objects for columns
        self.cols = {}
        # Store Total objects for rows
        self.rows = {}
        # The row (i) and column (j) indexes of the currently walked cell in the
        # current view.
        self.i = self.j = 0
        # The total number of rows and colums
        self.iCount = self.jCount = 0
        # Initialise p_self.cols and p_self.rows
        self.init(c)
        # Compute totals, if we are in a specific context (see m_compute)
        if compute:
            self.compute(c)

    def count(self, c, typE):
        '''Counts the number of columns or rows (p_typE) for the current view'''
        if typE == 'cols':
            # For a column, there will be one Total objet per row. There is one
            # row per Other calendar. Other calendars a grouped.
            r = 0
            for group in c.others:
                r += len(group)
        else: # typE == 'rows'
            # For a row, there will be one Total object per column. There is one
            # column per day.
            r = len(c.view.grid)
        return r

    def init(self, c):
        '''Initialise p_self.cols and p_self.rows'''
        # Each one is a dict that contains, for every Totals to render, a list
        # of Total objects: one for every row or column.
        #
        #                         ~{Totals: [Total]}~
        #
        T = 0
        o, field = self.outer.o, self.outer.field
        for typE in self.types:
            T += 1
            cols = T == 1 # Are we handling v_col(umns) or rows ?
            d = getattr(self, typE)
            # Get the applicable Totals objects
            totals = Totals.get(o, field, typE, c.view.renderRaw)
            # Count the number of Total objects to create
            count = self.count(c, typE)
            attr = 'iCount' if cols else 'jCount'
            setattr(self, attr, count)
            # Create the list of Total objects for each Totals object
            for tot in totals:
                d[tot] = [Total(tot) for i in range(count)]

    def update(self, c):
        '''A new cell is being rendered: update our totals'''
        # Update impacted Total objects, for all Totals
        T = 0
        for typE in self.types:
            T += 1
            cols = T == 1 # Are we handling v_col(umns) or rows ?
            for tot, totals in getattr(self, typE).items():
                # Get the possibly impacted Total object
                if cols:
                    k = self.i
                    # Is it the last value to add to the total ?
                    c.last = self.j == self.jCount - 1
                else:
                    k = self.j
                    c.last = self.i == self.iCount - 1
                c.total = totals[k]
                # Call the method that will update the total
                tot.onCell(self.outer.o, c)
        # Go to the next cell in the current row. If we reached the end of the
        # row, don't go now to the next row: total column cells must be dumped
        # first.
        self.j += 1

    def compute(self, c):
        '''Simulates a walk through all the cells of the current view, in order
           to compute all running totals.'''
        # This method is used when we are in a specific context, where the
        # complete calendar view is not rendered (ie, while ajax-refreshing
        # total rows).
        #
        # Walk all Other calendars
        view = c.view
        for other in utils.IterSub(c.others):
            c.other = other
            c.o = o = other.o
            c.field = field = other.field
            # For the current calendar, walk all days of the grid
            for day in view.grid:
                c.date = day
                c.events = field.getEventsAt(o, day)
                c.shownEvents = view.getShownEvents(c.events)
                # Update all totals
                self.update(c)
            self.gotoNextRow()

    def gotoNextRow(self):
        '''Once an entire row has been dumped, go to the next one'''
        self.i += 1
        self.j = 0

    @classmethod
    def getAjaxData(class_, outer, hook):
        '''Initializes an AjaxData object on the DOM node corresponding to
           the zone containing the total rows as defined by class_pxRows.'''
        url = outer.o.url
        return f"new AjaxData('{url}/{outer.field.name}/Totals/Running/" \
               f"pxRowsFromAjax','GET',{{}},'{hook}_rows','{hook}')"

    # Render columns as last cells in a view row
    pxCols = Px('''
     <x for="tots in totals.cols.values()">::tots[totals.i].asCell(_ctx_, 'th')
     </x>
     <x var="x=totals.gotoNextRow()"></x>''')

    # Render rows at the bottom of a view
    pxRows = Px('''
     <tbody id=":f'{hook}_rows'">
      <script>:field.Totals.Running.getAjaxData(outer, hook)</script>
      <tr for="row, tots in totals.rows.items()"
          var2="rowTitle=row.label if row.translated else _(row.label)">

       <!-- The row name -->
       <th class="tlLeft">
        <abbr title=":rowTitle"><b>:row.name</b></abbr>
       </th>

       <!-- Columns -->
       <x for="date in view.grid">::tots[loop.date.nb].asCell(_ctx_, 'th')</x>

       <!-- Repeat the row name -->
       <th class="tlRight">
        <abbr title=":rowTitle"><b>:row.name</b></abbr>
       </th>

       <!-- One more cell for every total column -->
       <th for="col in totals.cols|()">
        <!-- If the row and column totals are the same, render a grand total -->
        <x if="col.name == row.name">:row.getGrand(tots, _ctx_)</x>
       </th>
      </tr>
     </tbody>''')

    # Prepare a call to pxRows from an Ajax request
    pxRowsFromAjax = Px('''
     <x var="hook=f'{o.iid}{field.name}';
             outer=field.Other(o, field.name);
             view=field.View.get(o, field);
             cache=outer.field.getCache(outer.o, view);
             others=field.Other.getAll(outer.o, outer.field, cache);
             Running=field.Totals.Running;
             totals=Running(outer, _ctx_, compute=True)">:Running.pxRows</x>''')

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
Totals.Running = Running
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
