'''Search results can be displayed in various "modes": as a list, grid,
   calendar, etc.'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from DateTime import DateTime

from appy.px import Px
from appy.model.batch import Batch
from appy.database.operators import in_
from appy.utils import string as sutils
from appy.model.utils import Object as O
from appy.ui import LinkTarget, Columns, Title
from appy.model.searches.gridder import Gridder

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
E_CUST   = 'This must be a sub-class from appy.model.searches.modes.Custom.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Mode:
    '''Abstract base class for search modes. A concrete Mode instance is created
       every time search results must be computed.'''

    # The default mode(s) for displaying instances of any Appy class
    default = ('list',)

    # All available predefined concrete modes
    concrete = ('list', 'grid', 'calendar')

    # The list of custom actions that can be triggered on search results
    pxActions = Px('''
     <table>
      <tr><td for="action in actions"
            var2="multi=action.getMulti('searchResults', mode.outerHook);
                  field=action; fieldName=field.name;
                  layout='query'">:action.pxRender</td></tr>
     </table>''')

    @classmethod
    def get(class_, uiSearch):
        '''Create and return the Mode instance corresponding to the current
           result mode to apply to a list of instances.'''
        name = uiSearch.req.resultMode or uiSearch.getModes()[0]
        # Determine the concrete mode class
        if name in Mode.concrete:
            concrete = eval(name.capitalize())
        else:
            # Get the concrete mode on the Appy class
            for mode in uiSearch.container.python.resultModes:
                if not isinstance(mode, str):
                    concrete = mode
                    break
        # Create the Mode instance
        r = concrete(uiSearch)
        r.init()
        return r

    @classmethod
    def getClasses(class_, names):
        '''Return the Mode sub-classes corresponding to their p_names'''
        r = []
        for name in names:
            if isinstance(name, str):
                # A standard mode
                mode = eval(name.capitalize())
            else:
                # A custom Mode
                mode = name
                if not issubclass(mode, Custom):
                    raise Exception(E_CUST)
            r.append(mode)
        return r

    @classmethod
    def getText(class_, _):
        '''Gets the i18n text corresponding to mode named p_name'''
        name = class_.__name__.lower()
        name = name.rsplit('_', 1)[0] if '_' in name else name
        return _('result_mode_%s' % name) if name in Mode.concrete else _(name)

    @classmethod
    def isGrid(class_, o):
        '''Are we currently rendering a Search with "grid" mode ?'''
        ctx = o.traversal.context
        return ctx and ctx.mode and isinstance(ctx.mode, Grid)

    def __init__(self, uiSearch):
        # The tied UI search
        self.uiSearch = uiSearch
        # The class from which we will search instances
        self.class_ = uiSearch.container
        # Are we in a popup ?
        self.popup = uiSearch.popup
        # The tool
        self.tool = uiSearch.tool
        # The ID of the tag that will be ajax-filled with search results
        self.hook = 'searchResults'
        # Matched objects
        self.objects = None
        # A Batch instance, when only a sub-set of the result set is shown at
        # once.
        self.batch = None
        # Determine result's "emptiness". If a search produces results without
        # any filter, it is considered not being empty. Consequently, a search
        # that would produce results without filters, but for which there is no
        # result, due to current filters, is not considered being empty.
        self.empty = True
        # URL for triggering a new search
        self.newSearchUrl = None
        # Is the search triggered from a Ref field ?
        self.fromRef = False
        self.refField = None
        # Is the search integrated into another field ?
        self.inField = False
        # The target for "a" tags
        self.target = LinkTarget(self.class_.python,
                                 popup=uiSearch.search.viaPopup)
        # The notion of "column" does not apply to any mode
        self.columns = None

    def init(self):
        '''Lazy mode initialisation. Can be completed by sub-classes.'''
        # Store criteria for custom searches
        tool = self.tool
        req = tool.req
        self.criteria = req.criteria
        ui = self.uiSearch
        search = ui.search
        self.rootHook = ui.getRootHook()
        # The search may be triggered via a Ref field
        io, ifield = search.getRefInfo(tool, nameOnly=False)
        if io:
            self.refObject = io
            self.refField = ifield
        else:
            self.refObject, self.refField = None, None
        # Build the URL allowing to trigger a new search
        if search.name == 'customSearch':
            part = '&ref=%s:%s' % (io.iid, ifield.name) if io else ''
            self.newSearchUrl = '%s/Search/advanced?className=%s%s' % \
                                (tool.url, search.container.name, part)
        self.fromRef = bool(ifield)
        # This search may lie within another field (a Ref or a Computed)
        self.inField = (ifield and ('search*' in req.search)) or \
                       (req.search and ',' in req.search)
        if self.fromRef and self.inField:
            # The search is a simple view of objects from a Ref field: inner
            # elements (like checkboxes) must have IDs being similar to the
            # standard view of these objects via the Ref field.
            self.outerHook = '%s_%s' % (self.refObject.iid, self.refField.name)
        else:
            self.outerHook = self.rootHook

    def getAjaxData(self):
        '''Initializes an AjaxData object on the DOM node corresponding to the
           ajax hook for this search result.'''
        search = self.uiSearch
        name = search.name
        params = {'className': self.class_.name, 'search': name,
                  'popup': self.popup}
        # Add initiator-specific params
        if search.initiator:
            initatorParams = search.initiator.getAjaxParams()
            if initatorParams: params.update(initatorParams)
        # Add custom search criteria
        if self.criteria:
            params['criteria-'] = self.criteria
        # Add the "ref" key if present
        ref = self.tool.req.ref
        if ref:
            params['ref'] = ref
        # Concrete classes may add more parameters
        self.updateAjaxParameters(params)
        # Convert params into a JS dict
        params = sutils.getStringFrom(params)
        # Set the appropriate context object for the PX. If the search is within
        # a field, this context object is the object containing the field. Else,
        # it is the tool.
        id = name.split(',',1)[0] if ',' in name else 'tool'
        return "new AjaxData('%s/%s/Search/batchResults', 'POST', %s, '%s')" % \
               (self.tool.siteUrl, id, params, self.hook)

    def updateAjaxParameters(self, params):
        '''To be overridden by subclasses for adding Ajax parameters
           (see m_getAjaxData above)'''

    def getHookFor(self, o):
        '''When p_o is shown within a list/grid/... of search results, this
           method computes the ID of the ajax-refreshable hook tag containing
           p_o.'''
        # Currently, this tag is only made of the object ID. Tthis could lead to
        # problems if several searches are shown on the same page. The solution
        # would be to prefix the ID with the search name. But some searchs do
        # not have any name or have a long name (being found within other
        # fields).
        return str(o.iid)

    def getAjaxDataRow(self, o, rhook, **params):
        '''Initializes an AjaxData object on the DOM node corresponding to the
           row displaying info about p_o within the results.'''
        return "new AjaxData('%s/pxResult','GET',%s,'%s','%s')" % \
               (o.url, sutils.getStringFrom(params), rhook, self.hook)

    def getRefUrl(self):
        '''When the search is triggered from a Ref field, this method returns
           the URL allowing to navigate back to the page where this Ref field
           lies.'''

    def isSummable(self):
        '''May totals be computed on searh results using this mode ?'''
        return # To be overridden by child classes

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class List(Mode):
    '''Displays search results as a table containing one row per object'''

    # Icon for switching to this mode
    icon = 'list' # .svg

    # Name for this mode
    name = 'list'

    px = Px('''
     <x var="genCss=mode.columns.getCss(showHeaders, uiSearch.search.rowAlign);
             genName=mode.columns.name if genCss else None">
      <style if="genCss">::genCss</style>
      <table class=":mode.getMainCss(_ctx_)">

       <!-- Headers, with filters and sort arrows -->
       <tr if="showHeaders">
        <x for="col in mode.columns" var2="field=col.field">:col.pxHeader</x>
       </tr>

       <!-- Results -->
       <tr if="not mode.objects">
        <td colspan=":len(mode.columns)+1">::_('query_no_result')</td>
       </tr>
       <x for="o in mode.objects"
          var2="@currentNumber=currentNumber + 1">:o.pxResult</x>
       <!-- Totals -->
       <x if="totals">:totals.px</x>
      </table>
     </x>

     <!-- The button for selecting objects and closing the popup -->
     <div if="popup and mode.cbShown" align=":dleft">
      <input type="button"
             var="label=_('object_link_many'); css=ui.Button.getCss(label)"
             value=":label" class=":css"
             style=":svg('linkMany', bg='18px 18px')"
             onclick=":uiSearch.initiator.jsSelectMany(\
                   q, mode.sortKey, mode.sortOrder, mode.getFiltersString())"/>
     </div>

     <!-- Custom actions -->
     <x var="actions=uiSearch.search.getActions(tool)"
        if="actions and not popup">:mode.pxActions</x>

     <!-- Init checkboxes if present -->
     <script if="mode.checkboxes">:'initCbs(%s)' % q(mode.checkboxesId)</script>

     <!-- Init field focus and store object IDs in the session storage -->
     <script>:'initFocus(%s); %s;' % (q(mode.hook), mode.store)</script>''')

    def init(self):
        '''List-specific initialization'''
        Mode.init(self)
        ui = self.uiSearch
        search = ui.search
        tool = self.tool
        req = tool.req
        # Build search parameters (start number, sort and filter)
        start = int(req.start or '0')
        self.sortKey = req.sortKey
        self.sortOrder = req.sortOrder or 'asc'
        self.filters = self.class_.getFilters(tool)
        # Run the search
        self.batch = search.run(tool.H(), start=start, sortBy=self.sortKey,
          sortOrder=self.sortOrder, filters=self.filters,
          refObject=self.refObject, refField=self.refField)
        self.batch.hook = self.hook
        self.objects = self.batch.objects
        # Show sub-titles ? Show filters ?
        if not self.class_.toggleSubTitles(self.tool, None):
            # When toggling is disabled, always show sub-titles, do not depend
            # on the cookie value.
            self.showSubTitles = True
        else:
            # Show sub-titles depending on the cookie value
            self.showSubTitles = req.showSubTitles in ('True', None)
        # Every matched object may be selected via a checkbox
        self.checkboxes = ui.checkboxes
        self.checkboxesId = self.outerHook + '_objs'
        self.cbShown = ui.showCheckboxes()
        self.cbClass = '' if self.cbShown else 'hide'
        self.cbChecked = eval(req.cbChecked or 'False')
        # Determine result emptiness
        self.empty = not self.objects and not self.filters
        # Compute info related to every column in the list
        self.columns = Columns.get(tool, self.class_, self.getColumnInfos(),
                                   addCB=self.checkboxes)
        # Get the Javascript code allowing to store IDs from batch objects in
        # the browser's session storage.
        self.store = self.batch.store(search, name=ui.name)

    def updateAjaxParameters(self, params):
        '''List-specific ajax parameters'''
        params.update(
          {'start': self.batch.start, 'filters': self.filters,
           'sortKey': self.sortKey or '', 'sortOrder': self.sortOrder,
           'checkboxes': self.checkboxes, 'checkboxesId': self.checkboxesId,
           'total': self.batch.total,
           'resultMode': self.__class__.__name__.lower()})

    def getMainCss(self, c):
        '''Get the CSS class(es) to apply to the main tag'''
        r = self.uiSearch.search.listCss
        if r:
            # Use the CSS class(es) defined at the Search level, plus a
            # potential CSS class generated from column layouts.
            if c.genName:
                r = '%s %s' % (r, c.genName)
        else:
            # Use the CSS class(es) as defined on the tied class
            r = c.class_.getCssFor(c.tool, 'list', add=c.genName)
        return r

    def getColumnInfos(self):
        '''Returns infos about search results' columns'''
        r = None
        tool = self.tool
        name = self.uiSearch.name
        search = self.uiSearch.search
        # Try first to retrieve this info from a potential source Ref field
        o = self.refObject
        if o and not search.shownInfo:
            # When a Ref field and the search both define columns, those from
            # the search are preferred. Indeed, colums may define search-
            # specific elements (ie, configuring filters).
            field = self.refField
            r = field.getAttribute(o, 'shownInfo')
        elif ',' in name:
            id, fieldName, x = name.split(',')
            o = tool.getObject(id)
            field = o.getField(fieldName)
            if field.type == 'Ref':
                r = search.getShownInfo(o) or field.getAttribute(o, 'shownInfo')
        if r: return r
        # Try to retrieve this info via search.shownInfo
        r = search.getShownInfo(o or tool)
        return r if r else self.class_.getListColumns(tool)

    def getFiltersString(self):
        '''Converts dict p_self.filters into its string representation'''
        filters = self.filters
        if not filters: return ''
        r = []
        for k, v in filters.items():
            r.append('%s:%s' % (k, v))
        return ','.join(r)

    def inFilter(self, name, value):
        '''Returns True if this p_value, for field named p_name, is among the
           currently set p_self.filters.'''
        values = self.filters.get(name)
        if not values: return
        # Normalize the value to a string
        value = str(value) if isinstance(value, int) else value
        if isinstance(values, str):
            r = value == values
        else:
            r = value in values
        return r

    def getNavInfo(self, number, mayAdd=None):
        '''Gets the navigation string corresponding to the element having this
           p_number within the list of results.'''
        if mayAdd is None or mayAdd.io is None:
            # A standard search nav string
            r = 'search.%s.%s.%d.%d' % (self.class_.name, self.uiSearch.name,
                                        self.batch.start + number,
                                        self.batch.total)
        else:
            # We are in the context of creating an object from a search: the nav
            # string must be converted to a ref-based string.
            total = mayAdd.io.countRefs(mayAdd.ifield.name)
            r = 'ref.%d.%s.0.%d' % (mayAdd.io.iid, mayAdd.ifield.name, total)
        return r

    def getRefUrl(self):
        '''See Mode::getRefUrl's docstring'''
        o = self.refObject
        return '%s/view?page=%s' % (o.url, self.refField.page.name)

    def isSummable(self):
        '''May totals be computed on searh results using this mode ?'''
        return self.batch.isComplete()

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Grid(List):
    '''Displays search results as a table containing one cell per object'''

    # Icon for switching to this mode
    icon = 'grid' # .svg

    # Name for this mode
    name = 'grid'

    px = Px('''
     <!-- Filters -->
     <div var="search=uiSearch.search" if="search.showFilters" class="gfilters"
          style=":'justify-content:%s' % search.gridFiltersAlign">
      <div for="field, filterPx in mode.columns.getFiltered()">
       <label>:_(field.labelId)</label><x>:filterPx</x>
      </div>
     </div>

     <!-- The grid itself -->
     <div style=":mode.gridder.getContainerStyle()">
      <div for="o in mode.objects" class=":uiSearch.search.thumbnailCss"
           var2="mayView=guard.mayView(o);
                 showFields=mode.gridder.showFields">

       <!-- A complete table will all visible fields -->
       <table class="thumbtable" if="showFields">
        <tr var="@currentNumber=currentNumber + 1" valign="top"
            for="column in mode.columns"
            var2="field=column.field; backHook='searchResults'">
         <td if="field.name == 'title'" colspan="2">:field.pxResult</td>
         <x if="field.name != 'title'">
          <td><label lfor=":field.name">::_('label', field=field)</label></td>
          <td>:field.pxResult</td>
         </x>
        </tr>
       </table>

       <!-- The object title only, when other fields must not be shown -->
       <x if="not showFields"
          var2="@currentNumber=currentNumber + 1;
                field=o.getField('title')">:field.pxResult</x>

       <!-- The "more" section -->
       <div class="thumbmore">
        <img src=":url('more')" class="clickable"
             onclick="followTitleLink(this)"/>
       </div>
      </div>
      <!-- Store object IDs in the session storage -->
      <script>:mode.store</script>

      <!-- Show a message if there is no visible object, due to filters -->
      <div if="not mode.objects">::_('query_no_filtered_result')</div>
     </div>''',

     css='''
      .gfilters { display:flex; flex-wrap:wrap; margin:|gridFiltersMargin|}
      .gfilters > div { margin: 10px 20px; display:inline-flex;
                        align-items:center }
      .gfilters input[type=text] { margin:0 0 0 0.4em }
      .gfilters label { padding:0 0.4em 0 0 }''',

     js='''
      followTitleLink = function(img) {
        var parent = img.parentNode.parentNode,
            atag = parent.querySelector("a[name=title]");
        atag.click();
      }
      ''')

    def __init__(self, *args):
        List.__init__(self, *args)
        # Extract the gridder defined on p_self.class_ or create a default one
        gridder = getattr(self.class_.python, 'gridder', None)
        if callable(gridder): gridder = gridder(self.tool)
        self.gridder = gridder or Gridder()

    def init(self):
        '''Lazy initialisation'''
        List.init(self)
        # Disable the possibility to show/hide sub-titles
        self.showSubTitles = True

    def isSummable(self):
        '''Although some List modes may be summable, for the moment, Grids are
           not.'''
        return

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Calendar(Mode):
    '''Displays search results in a monthly calendar view'''

    # Icon for switching to this mode
    icon = 'calendar' # .svg

    # Name for this mode
    name = 'calendar'

    px = Px('''<x var="layoutType='view';
                       field=tool.getField('calendar')">:field.view</x>''')

    # Formats for keys representing dates
    dayKey = '%Y%m%d'

    # Format for representing hours in the UI
    hourFormat = '%H:%M'

    def __init__(self, *args):
        Mode.__init__(self, *args)
        # For this calendar view to work properly, objects to show inside it
        # must have the following fields:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # date    | an indexed and required Date field with format =
        #         | Date.WITH_HOUR storing the object's start date and hour;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # endDate | a not necessarily required Date field with format =
        #         | Date.WITH_HOUR storing the object's end date and hour.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # Optionnally, if you want to use index "months" (we advice you to do
        # so), an indexed Computed field with this name must also be defined
        # (see details in m_init below).
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # Optionally, too, if objects define the following attributes, special
        # icons indicating repeated events will be shown.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # successor   | Ref field with multiplicity = (0,1), allowing to
        #             | navigate to the next object in the list (for a repeated
        #             | event);
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # predecessor | Ref field with multiplicity = (0,1), allowing to
        #             | navigate to the previous object in the list.
        #             | "predecessor" must be the back ref of field "successor"
        #             | hereabove.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def getMonthIndex(self):
        '''Deduce, from p_self.class_, what is the month index to use'''
        # Is there, on p_self.class_, a field name "months" ?
        months = getattr(self.class_.python, 'months', None)
        if not months: return 'date'
        return 'months' if months.type == 'Computed' and months.indexed \
                        else 'date'

    def init(self):
        '''Creates a stub calendar field'''
        Mode.init(self)
        # Always consider the result as not empty. This way, the calendar is
        # always shown, even if no object is visible.
        self.empty = False
        # The matched objects, keyed by day. For every day, a list of entries to
        # show. Every entry is a 2-tuple (s_entryType, Object) allowing to
        # display an object at this day. s_entryType can be:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  "start"  | the object starts and ends at this day: display its start
        #           | hour and title;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  "start+" | the object starts at this day but ends at another day:
        #           | display its start hour, title and some sign indicating
        #           | that it spans on another day;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  "end"    | the object started at a previous day and ends at this day.
        #           | Display its title and a sign indicating this fact;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  "pass"   | The object started at a previous day and ends at a future
        #           | day.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.objects = {} # ~{s_YYYYmmdd: [(s_entryType, Object)]}~
        # If filters are defined from a list mode, get it
        self.filters = self.class_.getFilters(self.tool)
        # The name of the index to use to restrict the search to the currently
        # shown month. If p_self.klass defines a Computed indexed TextIndex
        # field named "months", this index will be used. Else, index "date" will
        # be used. These 2 indexes are described hereafter.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "date"   | This index is expected to define the (start) date of the
        #          | objects to search. So, the search will match any object
        #          | whose (start) date is included in the range of dates
        #          | defined by the currently shown month. Recall that this
        #          | range may be larger than the month itself: because complete
        #          | weeks are shown, some days from the previous and next
        #          | months may be present, too.
        #          |
        #          | While this index is the easiest to implement, it has the
        #          | following problem: objects spanning several days (by using
        #          | fields "date" and "endate") and whose start date is not
        #          | among the range of visible dates, will not be part of the
        #          | result. This is why an alternate index named "month' is
        #          | also proposed (see below).
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "months" | When using index "months", every object is expected to
        #          | hold, in a Computed indexed TextIndex field named "months",
        #          | the space-separated list of months the object crosses
        #          | (every crossing month must be represented as a string of
        #          | the form YYYYmm). "Crossing a month" means: there must be a
        #          | not-empty intersection between the range of visible days
        #          | for this month, and the object's range of days. For objects
        #          | defining no end date, this range is reduced to a unique day
        #          | (defined by field "date").
        #          |
        #          | Because this list of crossing months is relatively complex
        #          | to produce, Appy provides a function that computes it:
        #          |
        #          |           appy.shared.dates.getCalendarMonths
        #          |
        #          | Here is a complete example of a Appy class using index
        #          | "months".
        #          |
        #          | from appy.shared.dates import getCalendarMonths
        #          |
        #          | class Event:
        #          |     ...
        #          |     date    = Date(format=Date.Date.WITH_HOUR,
        #          |                    multiplicity=(1,1), indexed=True, ...)
        #          |     endDate = Date(format=Date.Date.WITH_HOUR,
        #          |                    indexed=True, ...)
        #          |     ...
        #          |     def computeMonths(self):
        #          |         '''Compute the months crossed by p_self'''
        #          |         # p_self.endDate may be None
        #          |         return ' '.join(getCalendarMonths(self.date,
        #          |                                           self.endDate))
        #          |
        #          |     months  = Computed(method=computeMonths,
        #          |                        indexed='TextIndex', show=False)
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.monthIndex = self.getMonthIndex()

    def updateAjaxParameters(self, params):
        '''Grid-specific ajax parameters'''
        # If filters are in use, carry them
        if self.filters:
            params['filters'] = self.filters

    # For every hereabove-defined entry type, this dict stores info about how
    # to render events having this type. For every type:
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # start      | bool | Must we show the event's start hour or not ?
    # end        | bool | Must we show the event's end hour or not ?
    # css        | str  | The CSS class to add the table event tag
    # past       | bool | True if the event spanned more days in the past
    # future     | bool | True if the event spans more days in the future
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    entryTypes = {
     'start':  O(start=True,  end=True,  css=None,      past=None, future=None),
     'start+': O(start=True,  end=False, css='calMany', past=None, future=True),
     'end':    O(start=False, end=True,  css='calMany', past=True, future=None),
     'pass':   O(start=False, end=False, css='calMany', past=True, future=True),
    }

    def addEntry(self, dateKey, entry):
        '''Adds an p_entry as created by m_addEntries below into self.objects
           @key p_dateKey.'''
        r = self.objects
        if dateKey not in r:
            r[dateKey] = [entry]
        else:
            r[dateKey].append(entry)

    def addEntries(self, o, gridFirst, gridLast):
        '''Add, in self.objects, entries corresponding to p_o. If p_o spans a
           single day, a single entry of the form ("start", p_o) is added at the
           key corresponding to this day. Else, a series of entries are added,
           each of the form (s_entryType, p_o), with the same object, for every
           day in p_o's timespan.'''
        # For example, for an p_o(bject) starting at "1975/12/11 12:00" and
        # ending at "1975/12/13 14:00", m_addEntries will produce the following
        # entries:
        #      key "19751211"  >  value ("start+", o)
        #      key "19751212"  >  value ("pass", o)
        #      key "19751213"  >  value ("end", o)
        # ~
        # Get p_o's start and end dates
        fmt = Calendar.dayKey
        start = o.date
        startKey = start.strftime(fmt)
        end = o.endDate
        endKey = end.strftime(fmt) if end else None
        # Shorthand for self.objects
        r = self.objects
        if not endKey or endKey == startKey:
            # A single entry must be added for p_obj, at the start date
            self.addEntry(startKey, ('start', o))
        else:
            # Insert one event per day, provided the events are in the grid
            # ~
            # Add one entry at the start day
            if start >= gridFirst:
                self.addEntry(startKey, ('start+', o))
                next = start + 1
            else:
                # Ignore any day between v_start and p_gridFirst
                next = gridFirst
            # Add "pass" entries for every day between the event's start and end
            # dates.
            nextKey = next.strftime(fmt)
            while nextKey != endKey and next <= gridLast:
                # Add a "pass" event
                self.addEntry(nextKey, ('pass', o))
                # Go the the next day
                next += 1
                nextKey = next.strftime(fmt)
            # Add an "end" entry at the end day
            if end <= gridLast:
                self.addEntry(endKey, ('end', o))

    def search(self, first, grid):
        '''Performs the search, restricted to the visible date range as defined
           by p_grid.'''
        # # The first date in the p_grid, that may be earlier than the p_first
        # day of the month.
        gridFirst = grid[0][0]
        # The last date in the grid, calibrated
        gridLast = DateTime(grid[-1][-1].strftime('%Y/%m/%d 23:59:59'))
        # Get the search parameters being specific to the range of dates
        params = {'sortBy':'date', 'sortOrder':'asc'}
        if self.monthIndex == 'date':
            # Define the search based on every event's (start) date.
            # ~~~
            # As first date, prefer the first visible date in the p_grid instead
            # of the p_first day of the month.
            params['date'] = in_(gridFirst, gridLast)
        else: # p_self.monthIndex is "months"
            # Define the search based on index "months"
            params['months'] = first.strftime('%Y%m')
        # Create a specific search with the parameters restricted to the visible
        # date range, and execute the main search, merged with the specific one.
        dateSearch = self.tool.Search(**params)
        r = self.uiSearch.search.run(self.tool.H(), batch=False,
                                     filters=self.filters, other=dateSearch)
        # Produce, in self.objects, the dict of matched objects
        for o in r:
            self.addEntries(o, gridFirst, gridLast)

    def dumpObjectsAt(self, date):
        '''Returns info about the object(s) that must be shown in the cell
           corresponding to p_date.'''
        # There may be no object dump at this date
        dateStr = date.strftime(Calendar.dayKey)
        if dateStr not in self.objects: return
        # Objects exist
        r = []
        types = self.entryTypes
        for entryType, o in self.objects[dateStr]:
            # Dump the event hour and title. The back hook allows to refresh the
            # whole calendar view when coming back from the popup.
            eType = types[entryType]
            # What CSS class(es) to apply ?
            css = ('calEvt %s' % eType.css) if eType.css else 'calEvt'
            # Show start and/or end hour ?
            eHour = sHour = ''
            if eType.start:
                sHour = '<td width="2em">%s</td>' % \
                        o.date.strftime(self.hourFormat)
            if eType.end:
                endDate = o.endDate
                if endDate:
                    eHour = ' <abbr title="%s">¬</abbr>' % \
                            endDate.strftime(self.hourFormat)
            # Display indicators that the event spans more days
            past = '⇠ ' if eType.past else ''
            future = ' ⇢' if eType.future else ''
            # The event title
            title = Title.get(o, target=self.target, popup=True,
                              backHook='configcalendar', maxChars=24)
            # Display a "repetition" icon if the object is part of a series
            hasSuccessor = o.successor
            hasPredecessor = o.predecessor
            if hasSuccessor or hasPredecessor:
                # For the last event of a series, show a more stressful icon
                name = 'repeated' if hasSuccessor else 'repeated_last'
                icon = '<img src="%s" class="help" title="%s"/>' % \
                       (o.buildUrl(name), o.translate(name))
            else:
                icon = ''
            # Produce the complete entry
            r.append('<table class="%s"><tr valign="top">%s<td>%s%s%s%s%s</td>'\
                     '</tr></table>' % (css,sHour,past,title,future,eHour,icon))
        return '\n'.join(r)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Custom(Mode):
    '''Displays search results via a custom PX'''

    # Icon for switching to this mode
    icon = 'custom' # .svg

    # Name for this mode
    name = 'custom'

    def init(self):
        '''By default, the Custom mode performs full (unpaginated) searches'''
        Mode.init(self)
        # Run the search
        self.objects = self.uiSearch.search.run(self.tool.H(), batch=False)
        # Initialise Mode's mandatory fields
        self.empty = not self.objects
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
