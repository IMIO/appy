#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy import utils
from appy.px import Px

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
TOT_KO = 'Totals can only be specified for timelines (render == "timeline").'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Total:
    '''Represents a computation that will be executed on a series of cells
       within a timeline calendar.'''

    def __init__(self, initValue):
        # If p_initValue is mutable, get a copy of it
        if isinstance(initValue, dict):
            initValue = initValue.copy()
        elif isinstance(initValue, list):
            initValue = initValue[:]
        self.value = initValue

    def __repr__(self):
        '''p_self's short string representation'''
        return f'<Total={str(self.value)}>'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Totals:
    '''For a timeline calendar, if you want to add rows or columns representing
       totals computed from other rows/columns (representing agendas), specify
       it via Totals instances (see Agenda fields "totalRows" and "totalCols"
       below).'''

    def __init__(self, name, label, onCell, initValue=0):
        # "name" must hold a short name or acronym and will directly appear
        # at the beginning of the row. It must be unique within all Totals
        # instances defined for a given Calendar field.
        self.name = name
        # "label" is a i18n label that will be used to produce a longer name
        # that will be shown as an "abbr" tag around the name.
        self.label = label
        # A method that will be called every time a cell is walked in the
        # agenda. It will get these args:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #    date     | The date representing the current day (a DateTime
        #             | instance) ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #    other    | The Other instance representing the currently walked
        #             | calendar ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #    events   | The list of events (as Event instances) defined at that
        #             | day in this calendar. Be careful: this can be None ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #    total    | The Total object (see above) corresponding to the
        #             | current column ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #    last     | A boolean that is True if we are walking the last shown
        #             | calendar ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   checked   | A value "checked" indicating the status of the possible
        #             | validation checkbox corresponding to this cell. If there
        #             | is a checkbox in this cell, the value will be True or
        #             | False; else, the value will be None.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # preComputed | The result of Calendar.preCompute (see below).
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.onCell = onCell
        # "initValue" is the initial value given to created Total objects
        self.initValue = initValue

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
               f"{{}},'{hook}_{suffix}','{hook}')"

    @classmethod
    def get(class_, o, field, type):
        '''Returns the Totals objects by getting or computing them from
           p_field.totalRows or p_field.totalCols (depending on p_type).'''
        r = getattr(field, f'total{type.capitalize()}')
        return r(o) if callable(r) else r

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
    def compute(class_, field, allTotals, totalType, o, grid, others,
                preComputed):
        '''Compute the totals for every column (p_totalType == 'row') or row
           (p_totalType == "col").'''
        if not allTotals: return
        # Count other calendars and dates in the grid
        othersCount = 0
        for group in others: othersCount += len(group)
        datesCount = len(grid)
        isRow = totalType == 'row'
        # Initialise, for every (row or col) totals, Total instances
        totalCount = datesCount if isRow else othersCount
        lastCount = othersCount if isRow else datesCount
        r = {}
        for totals in allTotals:
            r[totals.name]= [Total(totals.initValue) for i in range(totalCount)]
        # Get the status of validation checkboxes
        status = class_.getValidationCBStatus(o.req)
        # Walk every date within every calendar
        indexes = {'i': -1, 'j': -1}
        ii = 'i' if isRow else 'j'
        jj = 'j' if isRow else 'i'
        for other in utils.IterSub(others):
            indexes['i'] += 1
            indexes['j'] = -1
            for date in grid:
                indexes['j'] += 1
                # Get the events in this other calendar at this date
                events = other.field.getEventsAt(other.o, date)
                # From info @this date, update the total for every totals
                last = indexes[ii] == lastCount - 1
                # Get the status of the validation checkbox that is possibly
                # present at this date for this calendar
                checked = None
                dateS = date.strftime('%Y%m%d')
                cbId = f'{other.o.iid}_{other.field.name}_{dateS}'
                if cbId in status: checked = status[cbId]
                # Update the Total instance for every totals at this date
                for totals in allTotals:
                    total = r[totals.name][indexes[jj]]
                    totals.onCell(o, date, other, events, total, last,
                                  checked, preComputed)
        return r

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                                  PX
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Total rows shown at the bottom of a timeline calendar
    pxRows = Px('''
     <tbody id=":f'{hook}_trs'"
            var="rows=field.Totals.get(o, field, 'rows');
                 totals=field.Totals.compute(field, rows, 'row', o, grid,
                                             others, preComputed)">
      <script>:field.Totals.getAjaxData(field, o, 'rows', hook)</script>
      <tr for="row in rows" var2="rowTitle=_(row.label)">
       <td class="tlLeft">
        <abbr title=":rowTitle"><b>:row.name</b></abbr></td>
       <td for="date in grid">::totals[row.name][loop.date.nb].value</td>
       <td class="tlRight">
        <abbr title=":rowTitle"><b>:row.name</b></abbr></td>
      </tr>
     </tbody>''')

    # Total columns besides the calendar, as a separate table
    pxCols = Px('''
     <table cellpadding="0" cellspacing="0" class="list timeline"
            style="float:right" id=":f'{hook}_tcs'"
            var="cols=field.Totals.get(o, field, 'cols');
                 rows=field.Totals.get(o, field, 'rows');
                 totals=field.Totals.compute(field, cols, 'col', o , grid,
                                             others, preComputed)">
      <script>:field.Totals.getAjaxData(field, o, 'cols', hook)</script>

      <!-- 2 empty rows -->
      <tr><th for="col in cols" class="hidden">-</th></tr>
      <tr><td for="col in cols" class="hidden">-</td></tr>

      <!-- The column headers -->
      <tr>
       <td for="col in cols"><abbr title=":_(col.label)">:col.name</abbr></td>
      </tr>

      <!-- Re-create one row for every other calendar -->
      <x var="i=-1" for="otherGroup in others">
       <tr for="other in otherGroup" var2="@i=i+1">
        <td for="col in cols">::totals[col.name][i].value</td>
       </tr>

       <!-- The separator between groups of other calendars -->
       <x if="not loop.otherGroup.last">::field.getOthersSep(len(cols))</x>
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
     <x var="month=req.month;
             totalType=req.totalType.capitalize();
             hook=f'{o.iid}{field.name}';
             monthDayOne=field.DateTime(f'{month}/01');
             grid=field.getGrid(month, 'timeline');
             preComputed=field.getPreComputedInfo(o, monthDayOne, grid);
             others=field.getOthers(o, \
               preComputed)">:getattr(field.Totals, f'px{totalType}')</x>''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
