#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import time

from appy.px import Px
from appy.model.fields import Field

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Hour(Field):
    '''Field allowing to define an hour independently of a complete date'''

    view = cell = buttons = Px('''<x>:value</x>''')

    edit = Px('''
     <x var="hPart=hPart | '%s_hour' % name;
             mPart=mPart | '%s_minute' % name;
             hours=range(0,field.maxHour+1)">
      <select name=":hPart" id=":hPart">
       <option value="">-</option>
       <option for="hour in hours"
         var2="zHour=str(hour).zfill(2)" value=":zHour"
         selected=":field.isSelected(o, hPart, 'hour', \
                                     hour, rawValue)">:zHour</option>
      </select> : 
      <select var="minutes=range(0, 60, field.minutesPrecision)"
              name=":mPart" id=":mPart">
       <option value="">-</option>
       <option for="min in minutes"
         var2="zMin=str(min).zfill(2)" value=":zMin"
         selected=":field.isSelected(o, mPart, 'minute', \
                                     min, rawValue)">:zMin</option>
      </select>
     </x>''')

    hourParts = ('hour', 'minute')

    def __init__(self, validator=None, multiplicity=(0,1), default=None,
      defaultOnEdit=None, hourFormat=None, maxHour=23, minutesPrecision=5,
      show=True, renderable=None, page='main', group=None, layouts=None, move=0,
      readPermission='read', writePermission='write', width=None, height=None,
      maxChars=None, colspan=1, master=None, masterValue=None, focus=False,
      historized=False, mapping=None, generateLabel=None, label=None,
      sdefault=None, scolspan=1, swidth=None, sheight=None, persist=True,
      view=None, cell=None, buttons=None, edit=None, xml=None,
      translations=None):
        # If no p_hourFormat is specified, the application-wide tool.hourFormat
        # is used instead.
        self.hourFormat = hourFormat
        # By default, an hour is meant to represent an hour within a day, ie
        # from 00:00 to 23h59. But it could also represent a higher number of
        # hours, ie, the number of worked hours in a week. In that case, set
        # attribute "maxHour" to a number being higher than 23.
        self.maxHour = maxHour
        # If "minutesPrecision" is 5, only a multiple of 5 can be encoded. If
        # you want to let users choose any number from 0 to 59, set it to 1.
        self.minutesPrecision = minutesPrecision
        Field.__init__(self, validator, multiplicity, default, defaultOnEdit,
          show, renderable, page, group, layouts, move, False, True, None, None,
          False, None, readPermission, writePermission, width, height, None,
          colspan, master, masterValue, focus, historized, mapping,
          generateLabel, label, sdefault, scolspan, swidth, sheight, persist,
          False, view, cell, buttons, edit, xml, translations)

    def getFormattedValue(self, o, value, layout='view', showChanges=False,
                          language=None):
        if self.isEmptyValue(o, value): return ''
        format = self.hourFormat or o.config.ui.hourFormat
        hour, minute = [str(part).zfill(2) for part in value]
        return format.replace('%H', hour).replace('%M', minute)

    def getRequestValue(self, o, requestName=None):
        req = o.req
        name = requestName or self.name
        r = []
        empty = True
        for partName in self.hourParts:
            part = req['%s_%s' % (name, partName)] or ''
            if part: empty = False
            r.append(part)
        return None if empty else ':'.join(r)

    def getRequestSuffix(self): return '_hour'

    def getStorableValue(self, o, value, single=False):
        '''Convert the string p_value to a tuple'''
        if not self.isEmptyValue(o, value):
            return tuple(map(int, value.split(':')))

    def validateValue(self, o, value):
        '''Ensure p_value is complete: all parts must be there (minutes and
           seconds).'''
        if value.startswith(':') or value.endswith(':'):
            # A part is missing
            return o.translate('field_required')

    def isSelected(self, o, part, fieldPart, hourValue, dbValue):
        '''When displaying this field, must the particular p_hourValue be
           selected in the sub-field p_fieldPart corresponding to the hour
           p_part ?'''
        # Get the value we must compare (from request or from database)
        req = o.req
        if part in req:
            compValue = req[part]
            if compValue.isdigit():
                compValue = int(compValue)
        else:
            compValue = dbValue
            if compValue:
                i = 1 if fieldPart == 'minute' else 0
                compValue = dbValue[i]
        # Compare the value
        return compValue == hourValue

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                           Class methods
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @classmethod
    def hourDifference(class_, h1, h2):
        '''Computes the number of hours between h1 and h2'''
        if h2 < h1:
            # h2 is the day after
            h2 += 24
        return h2 - h1

    @classmethod
    def getMinutes(class_, value):
        '''Converts an Hour p_value ~(i_hours, i_minutes)~ into an integer
           number of minutes.'''
        return value[1] + (60 * value[0])

    @classmethod
    def fromMinutes(class_, minutes):
        '''Converts a number of p_minutes into a Hour-compliant tuple
           (i_hour, i_minutes)'''
        mins = int(minutes % 60)
        hours = int(minutes / 60.0)
        return hours, mins

    @classmethod
    def addMinutes(class_, value, minutes):
        '''Adds this number of p_minutes to p_value ~(i_hours, i_minutes)~ and
           returns the result as a tuple of the same format as p_value.'''
        hour, mins = value
        h, m = class_.fromMinutes(minutes)
        hour += h
        mins += m
        # If, after the addition, the v_hour part is higher than 23, it goes
        # "through 0". For example, (23,55) + 62 = (00,57)
        if mins >= 60:
            mins -= 60
            hour += 1
            if hour > 23:
                hour = hour % 24
        return hour, mins

    @classmethod
    def fromString(class_, s, sep=':'):
        '''Converts the string representation p_s of an hour (ie, "1:15",
           "-0:30", "165:34", "00:00"...) into a integer number of minutes.'''
        negate = s.startswith('-')
        h, m = s.split(sep)
        r = class_.getMinutes((abs(int(h)), int(m)))
        return -r if negate else r

    @classmethod
    def getDuration(class_, start, end):
        '''Returns the duration, in minutes, of the interval [start, end],
           "start" and "end" each being of the form ~(i_hours, i_minutes)~.'''
        # Manage minutes
        minutes = end[1] - start[1]
        if minutes < 0:
            minutes += 60
            endHour = 23 if end[0] == 0 else end[0] - 1
        else:
            deltaHour = 0
            endHour = end[0]
        return ((class_.hourDifference(start[0], endHour))*60) + minutes

    @classmethod
    def formatDuration(class_, minutes, sep='h', no='-'):
        '''Returns a formatted version of this number of p_minutes'''
        if minutes is None: return no
        if minutes < 0:
            prefix = '-'
            minutes = abs(minutes)
        else:
            prefix = ''
        modulo = int(minutes % 60)
        hours = int(minutes / 60.0)
        return '%s%d%s%s' % (prefix, hours, sep, str(modulo).zfill(2))

    @classmethod
    def getRanges(class_, start, end):
        '''Return a tuple of tuples representing the ranges of hours included
           in time interval (start, end). p_start and p_end are each a tuple of
           the form ~(i_hour, i_minutes)~.'''
        # If p_start and p_end occur at the same day, the returned tuple
        # contains a single entry. For example, if
        # 
        #                 start = (9,0) & end = (16,0)
        #
        # the result will be a tuple containing a single interval:
        #
        #                        (((9,0),(16,0)),)
        #
        # But if the end hour occurs the day after, like in this example:
        # 
        #                 start = (19,0) & end = (8,45)
        #
        # the result will be a tuple containing two intervals:
        #
        #                 (((19,0),(24,0)),((0,0),(8,45)))

        # As a preamble, calibrate p_end
        if end == (0,0): end = (24,0)
        # Compute the range(s)
        if end >= start:
            # A single range
            r = ((start, end),)
        else:
            # "end" occurs the day after: 2 ranges must be produced
            r = ((start, (24,0)), ((0,0), end))
        return r

    @classmethod
    def inRange(class_, value, start, end):
        '''Is the p_value within range [start, end] ? All parameters have the
           form ~(i_hour, i_minutes)~'''
        # Note that p_value must be between (00,00) and (23,59)
        if end > start:
            r = value >= start and value <= end
        else:
            r = class_.inRange(value, start, (23,59)) or \
                class_.inRange(value, (0,0), end)
        return r

    @classmethod
    def intersection(class_, rangeA, rangeB, recurse=True):
        '''Compute and return the number of minutes being common to p_rangeA and
           p_rangeB. Each range is of the form

               ((i_startHour, i_startMinutes), (i_endHour, i_endMinutes))

           Never call this method with p_recurse=False.
        '''
        # Each range can spread more than one day. Consequently, each range will
        # be split into a tuple of "day-specific" ranges.
        if recurse:
            r = 0
            for subA in class_.getRanges(*rangeA):
                for subB in class_.getRanges(*rangeB):
                    r += class_.intersection(subA, subB, recurse=False)
            return r
        # Unwrap ranges
        startA, endA = rangeA
        startB, endB = rangeB
        # Intersection may be empty
        if (startB >= endA) or (endB <= startA):
            r = 0
        else:
            # Compute the intersection, as a new range [start, end]
            start = (startA > startB) and startA or startB
            end = (endA > endB) and endB or endA
            r = class_.getDuration(start, end)
        return r
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
