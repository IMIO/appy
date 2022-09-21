#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import time

from DateTime import DateTime
from DateTime.interfaces import DateError

from appy.px import Px
from appy.utils import dates
from appy.model.fields import Field
from appy.model.fields.hour import Hour
from appy.database.operators import in_
from appy.database.indexes.date import DateIndex

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Date(Field):

    # Required CSS and Javascript files for this type
    cssFiles = {'edit': ('jscalendar/calendar-blue.css',)}
    jsFiles = {'edit': ('jscalendar/calendar.js',
                        'jscalendar/lang/calendar-en.js',
                        'jscalendar/calendar-setup.js')}

    # Possible values for "format"
    WITH_HOUR    = 0
    WITHOUT_HOUR = 1
    dateParts = ('year', 'month', 'day')
    hourParts = ('hour', 'minute')

    # Types of the native HTML inputs, for every format
    nativeWidgets = {WITH_HOUR: 'datetime-local', WITHOUT_HOUR: 'date'}

    # Date formats as understood by native widgets
    nativeFormats = {WITH_HOUR: '%Y-%m-%dT%H:%M', WITHOUT_HOUR: '%Y-%m-%d'}

    # Default value on the search screen
    searchDefault = (None, None, None)

    # Precision of the indexed value, in minutes
    indexPrecision = 1

    # The name of the index class storing values of this field in the catalog
    indexType = 'DateIndex'

    view = cell = buttons = Px('''<x>:value or field.empty</x>''')

    # PX for selecting hour and minutes, kindly provided by field Hour
    pxHour = Hour.edit

    edit = Px('''
     <!-- Native variant -->
     <input if="field.native" name=":name" id=":name"
            type=":field.nativeWidgets[field.format]"
            value=":field.getNativeValue(
             field.getInputValue(inRequest, requestValue, rawValue))"/>

     <!-- Variant with one select widget for every part of the date/time -->
     <x if="not field.native" var="years=field.getSelectableYears(o)">
      <!-- Day -->
      <select if="field.showDay" var2="days=range(1,32); part='%s_day' % name"
              name=":part" id=":part">
       <option value="">-</option>
       <option for="day in days" var2="zDay=str(day).zfill(2)" value=":zDay"
         selected=":field.isSelected(o, part, 'day', \
                                     day, rawValue)">:zDay</option>
      </select> 

      <!-- Month -->
      <select var="months=range(1,13); part='%s_month' % name"
              name=":part" id=":part">
       <option value="">-</option>
       <option for="month in months"
         var2="zMonth=str(month).zfill(2)" value=":zMonth"
         selected=":field.isSelected(o, part, 'month', \
                                     month, rawValue)">:zMonth</option>
      </select> 

      <!-- Year -->
      <select var="part='%s_year' % name" name=":part" id=":part">
       <option value="">-</option>
       <option for="year in years" value=":year"
         selected=":field.isSelected(o, part, 'year', \
                                     year, rawValue)">:year</option>
      </select>

      <!-- The icon for displaying the calendar popup -->
      <x if="field.calendar">
       <input type="hidden" id=":name" name=":name"/>
       <img id=":'%s_img' % name" src=":svg('calendar')" class="iconS"/>
       <script>::field.getJsInit(name, years)</script>
      </x>

      <!-- Hour and minutes -->
      <x if="field.format == 0">:field.pxHour</x>
     </x>''')

    search = Px('''
     <table var="years=field.getSelectableYears(o);
                 dstart,dend=field.getDefaultSearchValues(o)">
       <!-- From -->
       <tr var="fromName='%s_from' % name;
                dayFromName='%s_from_day' % name;
                monthFromName='%s_from_month' % name">
        <td><label>:_('date_from')</label></td>
        <td>
         <select id=":dayFromName" name=":dayFromName">
          <option value="">--</option>
          <option for="value in [str(v).zfill(2) for v in range(1, 32)]"
                  value=":value" selected=":value == dstart[2]">:value</option>
         </select> / 
         <select id=":monthFromName" name=":monthFromName">
          <option value="">--</option>
          <option for="value in [str(v).zfill(2) for v in range(1, 13)]"
                  value=":value" selected=":value == dstart[1]">:value</option>
         </select> / 
         <select id=":widgetName" name=":widgetName">
          <option value="">--</option>
          <option for="value in years"
                  value=":value" selected=":value == dstart[0]">:value</option>
         </select>
         <!-- The icon for displaying the calendar popup -->
         <x if="field.calendar">
          <input type="hidden" id=":fromName" name=":fromName"/>
          <img id=":'%s_img' % fromName" src=":svg('calendar')"
               class="iconS"/>
          <script>::field.getJsInit(fromName, years)</script>
         </x>
         <!-- Hour and minutes when relevant -->
         <x if="(field.format == 0) and field.searchHour"
            var2="hPart='%s_from_hour' % name;
                  mPart='%s_from_minute' % name">:field.pxHour</x>
        </td>
       </tr>

       <!-- To -->
       <tr var="toName='%s_to' % name;
                dayToName='%s_to_day' % name;
                monthToName='%s_to_month' % name;
                yearToName='%s_to_year' % name">
        <td><label>:_('date_to')</label></td>
        <td height="20px">
         <select id=":dayToName" name=":dayToName">
          <option value="">--</option>
          <option for="value in [str(v).zfill(2) for v in range(1, 32)]"
                  value=":value" selected=":value == dend[2]">:value</option>
         </select> / 
         <select id=":monthToName" name=":monthToName">
          <option value="">--</option>
          <option for="value in [str(v).zfill(2) for v in range(1, 13)]"
                  value=":value" selected=":value == dend[1]">:value</option>
         </select> / 
         <select id=":yearToName" name=":yearToName">
          <option value="">--</option>
          <option for="value in years"
                  value=":value" selected=":value == dend[0]">:value</option>
         </select>
         <!-- The icon for displaying the calendar popup -->
         <x if="field.calendar">
          <input type="hidden" id=":toName" name=":toName"/>
          <img id=":'%s_img' % toName" src=":svg('calendar')" class="iconS"/>
          <script>::field.getJsInit(toName, years)</script>
         </x>
         <!-- Hour and minutes when relevant -->
         <x if="(field.format == 0) and field.searchHour"
            var2="hPart='%s_to_hour' % name;
                  mPart='%s_to_minute' % name">:field.pxHour</x>
        </td>
       </tr>
      </table>''')

    def __init__(self, validator=None, multiplicity=(0,1), default=None,
      defaultOnEdit=None, format=WITH_HOUR, dateFormat=None, hourFormat=None,
      calendar=True, startYear=time.localtime()[0]-10,
      endYear=time.localtime()[0]+10, reverseYears=False, minutesPrecision=5,
      show=True, renderable=None, page='main', group=None, layouts=None, move=0,
      indexed=False, mustIndex=True, indexValue=None, emptyIndexValue=0,
      searchable=False, filterField=None, readPermission='read',
      writePermission='write', width=None, height=None, maxChars=None,
      colspan=1, master=None, masterValue=None, focus=False, historized=False,
      mapping=None, generateLabel=None, label=None, sdefault=None, scolspan=1,
      swidth=None, sheight=None, persist=True, view=None, cell=None,
      buttons=None, edit=None, xml=None, translations=None, showDay=True,
      searchHour=False, native=False, empty='-'):
        self.format = format
        self.calendar = calendar
        self.startYear = startYear
        self.endYear = endYear
        # If reverseYears is True, in the selection box, available years, from
        # self.startYear to self.endYear will be listed in reverse order.
        self.reverseYears = reverseYears
        # If p_showDay is False, the list for choosing a day will be hidden
        self.showDay = showDay
        # If no p_dateFormat/p_hourFormat is specified, the application-wide
        # tool.dateFormat/tool.hourFormat is used instead.
        self.dateFormat = dateFormat
        self.hourFormat = hourFormat
        # In the context of a Date, the max hour is always 23. But it can be
        # more in the context of an Hour field.
        self.maxHour = 23
        # If "minutesPrecision" is 5, only a multiple of 5 can be encoded. If
        # you want to let users choose any number from 0 to 59, set it to 1.
        self.minutesPrecision = minutesPrecision
        # The search widget will only allow to specify start and end dates
        # without hour, event if format is WITH_HOUR, excepted if searchHour is
        # True.
        self.searchHour = searchHour
        # Value for p_sdefault must be a tuple (start, end), where each value
        # ("start" or "end"), if not None, must be a tuple (year, month, day).
        # Each of these sub-values can be None or an integer value. p_sdefault
        # can also be a method that produces the values in the specified format.
        # ~
        # [Experimental] the "native" mode makes use of HTML native input fields
        # "date" (if p_format is WITHOUT_HOUR) or "datetime-local" (if p_format
        # is WITH_HOUR).
        self.native = native
        # What to show on cell or view when there is no date ?
        self.empty = empty
        # Call the base constructor
        Field.__init__(self, validator, multiplicity, default, defaultOnEdit,
          show, renderable, page, group, layouts, move, indexed, mustIndex,
          indexValue, emptyIndexValue, searchable, filterField, readPermission,
          writePermission, width, height, None, colspan, master, masterValue,
          focus, historized, mapping, generateLabel, label, sdefault, scolspan,
          swidth, sheight, persist, False, view, cell, buttons, edit, xml,
          translations)

    def getCss(self, o, layout, r):
        '''CSS files are only required if the calendar must be shown'''
        if self.calendar: Field.getCss(self, o, layout, r)

    def getJs(self, o, layout, r, config):
        '''Javascript files are only required if the calendar must be shown'''
        if self.calendar: Field.getJs(self, o, layout, r, config)

    def getSelectableYears(self, o):
        '''Gets the list of years one may select for this field'''
        startYear = self.getAttribute(o, 'startYear')
        r = list(range(startYear, self.endYear + 1))
        if self.reverseYears: r.reverse()
        return r

    def validateValue(self, o, value):
        try:
            value = DateTime(value)
        except (DateError, ValueError):
            return o.translate('bad_date')

    def getFormattedValue(self, o, value, layout='view', showChanges=False,
                          language=None):
        if self.isEmptyValue(o, value): return ''
        # Get the applicable date format
        ui = o.config.ui
        dateFormat = self.dateFormat or ui.dateFormat
        # A problem may occur with some extreme year values. Replace the "year"
        # part "by hand".
        if '%Y' in dateFormat:
            dateFormat = dateFormat.replace('%Y', str(value.year()))
        r = dates.Date.format(o.tool, value, dateFormat, withHour=False)
        if self.format == Date.WITH_HOUR:
            r += ' %s' % value.strftime(self.hourFormat or ui.hourFormat)
        return r

    def getRequestValue(self, o, requestName=None):
        req = o.req
        name = requestName or self.name
        # Manage a native date
        if self.native: return req[name]
        # Manage the "date" part
        value = ''
        for part in self.dateParts:
            # The "day" part may be hidden. Use "1" by default.
            if part == 'day' and not self.showDay:
                valuePart = '01'
            else:
                valuePart = req['%s_%s' % (name, part)]
            if not valuePart: return
            value += valuePart + '/'
        value = value[:-1]
        # Manage the "hour" part
        if self.format == self.WITH_HOUR:
            value += ' '
            for part in self.hourParts:
                valuePart = req['%s_%s' % (name, part)]
                if not valuePart: return
                value += valuePart + ':'
            value = value[:-1]
        return value

    def getNativeValue(self, value):
        '''Ensure p_value is a string being understood by the native HTML
           inputs.'''
        return value.strftime(Date.nativeFormats[self.format]) \
               if isinstance(value, DateTime) else value

    def searchValueIsEmpty(self, req):
        '''We consider a search value being empty if both "from" and "to" values
           are empty. At an individual level, a "from" or "to" value is
           considered not empty if at least the year is specified.'''
        # The base method determines if the "from" year is empty
        isEmpty = Field.searchValueIsEmpty
        return isEmpty(self, req) and \
               isEmpty(self, req, widgetName='%s_to_year' % self.name)

    def getRequestSuffix(self):
        return '' if self.native else '_year'

    def getStorableValue(self, o, value, single=False):
        '''Converts this string p_value too a DateTime instance'''
        if not self.isEmptyValue(o, value):
            if self.native:
                # Standardise this value: else, timezone may be wrong
                value = value.replace('-', '/').replace('T', ' ')
            return DateTime(value)

    def getDateFromSearchValue(self, year, month, day, hour, setMin):
        '''Gets the index representation of a valid DateTime instance, built
           from date information coming from the request.'''
        # This info comes as strings in p_year, p_month, p_day and p_hour.
        # The method returns None if p_year is empty. If p_setMin is True, when
        # some information is missing (month or day), it is replaced with the
        # minimum value (=1). Else, it is replaced with the maximum value
        # (=12, =31).
        if not year: return
        # Set month and day
        if not month:
            month = 1 if setMin else 12
        if not day:
            day = 1 if setMin else 31
        # Set the hour
        if hour is None:
            hour = '00:00' if setMin else '23:59'
        # The specified date may be invalid (ie, 2018/02/31): ensure to produce
        # a valid date in all cases.
        try:
            r = DateTime('%s/%s/%s %s' % (year, month, day, hour))
        except:
            base = DateTime('%s/%s/01' % (year, month))
            r = dates.getLastDayOfMonth(base, hour=hour)
        return r

    def getSearchPart(self, req, to=False, value=None):
        '''Gets the search value from p_req corresponding to the "from" or "to"
           part (depending on boolean p_to).'''
        name = self.name
        part = 'to' if to else 'from'
        # Get the year. For the "from" part, it corresponds to the name of
        # field. For the "to" part, there is a specific key in the request.
        year = req['%s_to_year' % name] \
               if to else Field.getSearchValue(self, req, value=value)
        month = req['%s_%s_month' % (name, part)]
        day = req['%s_%s_day' % (name, part)]
        hour = None
        if self.searchHour:
            hour = '%s:%s' % (req['%s_%s_hour' % (name, part)] or '00',
                              req['%s_%s_minute' % (name, part)] or '00')
        return self.getDateFromSearchValue(year, month, day, hour, not to)

    def getSearchValue(self, req, value=None):
        '''Converts raw search values from p_req into an interval of dates'''
        return in_(self.getSearchPart(req, False, value),
                   self.getSearchPart(req, True, value))

    def getDefaultSearchValues(self, o):
        '''Gets the default value for this field when shown on a search
           layout.'''
        default = self.getAttribute(o, 'sdefault')
        if not default:
            r = self.searchDefault, self.searchDefault
        else:
            # Convert months and days to zfilled strings
            r = []
            for i in (0, 1):
                value = default[i]
                if value:
                    year, month, day = value
                    if month is not None: month = str(month).zfill(2)
                    if day is not None: day = str(day).zfill(2)
                    value = year, month, day
                else:
                    value = self.searchDefault
                r.append(value)
        return r

    def isSelected(self, o, part, fieldPart, dateValue, dbValue):
        '''When displaying this field in non-native mode, must the particular
           p_dateValue be selected in the sub-field p_fieldPart corresponding to
           the date part ?'''
        # Get the value we must compare (from request or from database)
        req = o.req
        if part in req:
            compValue = req[part]
            if compValue.isdigit():
                compValue = int(compValue)
        else:
            compValue = dbValue
            if compValue:
                compValue = getattr(compValue, fieldPart)()
        # Compare the value
        return compValue == dateValue

    def isSortable(self, inRefs=False):
        '''Can this field be sortable ?'''
        return True if inRefs else Field.isSortable(self) # Sortable in Refs

    def getJsInit(self, name, years):
        '''Gets the Javascript init code for displaying a calendar popup for
           this field, for an input named p_name (which can be different from
           self.name if, ie, it is a search field).'''
        # Always express the range of years in chronological order.
        years = [years[0], years[-1]]
        years.sort()
        return 'Calendar.setup({inputField: "%s", button: "%s_img", ' \
               'onSelect: onSelectDate, range:%s, firstDay: 1})' % \
               (name, name, str(years))
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
