'''Date-related classes and functions'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import sys, time, re
try:
    from DateTime import DateTime
    from DateTime.interfaces import DateError
except ImportError:
    # This module manipulates DateTime objects from the non-standard DateTime
    # module, installable via command "pip3 install DateTime"
    pass

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Days of the week
weekDays = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
weekDays_ = weekDays + ('Off',)

S_E_KO   = 'End date cannot be prior to start date.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Date:
    '''Date-related methods'''

    # Regex for matching Appy-specific date parts
    rexPart = re.compile('\%(dt|DT|mt|MT|dd)(\d?)')

    # Info about evert date part. For every tuple in this data structure:
    # - elem #1 is the prefix for the i18n label;
    # - elem #2 is the name of the corresponding DateTime attribute.
    infoParts = {'dt': ('day', '_aday'), 'mt': ('month', '_amon')}

    @classmethod
    def resolvePart(class_, part, date, language, _, nb=None):
        '''Resolve this date p_part'''
        # p_part corresponds to one of the symbols as defined in Date.rexPart
        if part == 'dd':
            r = str(date.day())
        else:
            # Get the translated text corresponding to this p_part
            prefix, attr = Date.infoParts[part.lower()]
            r = _('%s_%s' % (prefix, getattr(date, attr)), language=language)
            # Translated texts are capitalized. Lowerize it when needed.
            r = r.lower() if part.islower() else r
            if nb:
                r = r[:int(nb)]
        return r

    @classmethod
    def toUTC(class_, d):
        '''When manipulating DateTime instances, like p_d, errors can raise when
           performing operations on dates that are not in Universal time, during
           months when changing from/to summer/winter hour. This function
           returns p_d set to UTC.'''
        return DateTime('%d/%d/%d UTC' % (d.year(), d.month(), d.day()))

    @classmethod
    def format(class_, tool, date, format=None, withHour=True, language=None):
        '''Returns p_d(ate) formatted as specified by p_format, or
           config.ui.dateFormat if not specified. If p_withHour is True, hour is
           appended, with a format specified in config.ui.hourFormat.'''
        fmt = format or tool.config.ui.dateFormat
        # Resolve Appy-specific formatting symbols used for getting translated
        # names of days or months:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  %dt[nb] | translated name of day (all lowercase). If a [nb] is
        #          | specified, only the [nb] first chars of the name will be
        #          | kept. For example, "%DT2" applied to a Monday, in english,
        #          | would produce "Mo".
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  %DT[nb] | translated name of day, capitalized
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  %mt[nb] | translated name of month (all lowercase)
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  %MT[nb] | translated name of month, capitalized
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  %dd     | day number, but without leading '0' if < 10
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # Resolve Appy symbols by producing a version of p_fmt whose Appy
        # symbols have been resolved.
        fun = lambda m: class_.resolvePart(m.group(1), date, language, \
                                           tool.translate, nb=m.group(2))
        fmt = Date.rexPart.sub(fun, fmt)
        # Resolve all other, standard, symbols
        r = date.strftime(fmt)
        # Append hour from tool.hourFormat
        if withHour and (date._hour or date._minute):
            r += ' (%s)' % date.strftime(tool.config.ui.hourFormat)
        return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class DayIterator:
    '''Class allowing to iterate over a range of days'''

    def __init__(self, startDay, endDay, back=False):
        self.start = Date.toUTC(startDay)
        self.end = Date.toUTC(endDay)
        # If p_back is True, the iterator will allow to browse days from end to
        # start.
        self.back = back
        self.finished = False
        # Store where we are within [start, end] (or [end, start] if back)
        if not back:
            self.current = self.start
        else:
            self.current = self.end

    def __iter__(self): return self
    def __next__(self):
        '''Returns the next day'''
        if self.finished:
            raise StopIteration
        res = self.current
        # Get the next day, forward
        if not self.back:
            if self.current >= self.end:
                self.finished = True
            else:
                self.current += 1
        # Get the next day, backward
        else:
            if self.current <= self.start:
                self.finished = True
            else:
                self.current -= 1
        return res

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def getLastDayOfMonth(date, hour=None):
    '''Returns a DateTime object representing the last day of date.month()'''
    day = 31
    month = date.month()
    year = date.year()
    found = False
    while not found:
        try:
            r = DateTime('%d/%d/%d %s' % (year, month, day, hour or '12:00'))
            found = True
        except DateError:
            day -= 1
    return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def sameDay(date, other):
    '''Do p_date and p_other occur at the same day ?'''
    d1 = date.year() , date.month() , date.day()
    d2 = other.year(), other.month(), other.day()
    return d1 == d2

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def getDayInterval(date):
    '''Returns a tuple (startOfDay, endOfDay) representing the whole day into
       which p_date occurs.'''
    day = date.strftime('%Y/%m/%d')
    return DateTime('%s 00:00' % day), DateTime('%s 23:59' % day)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def getMonthInterval(date, hour=None):
    '''Returns a tuple (start, end) representing the start and end days for the
       month into which p_date is included.'''
    return DateTime(date.strftime('%Y/%m/01')), \
           getLastDayOfMonth(date, hour=hour)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def getSiblingMonth(date, next=True):
    '''Computes and returns a date corresponding to p_date but one month later
       (if p_next is True) or earlier (if p_next is False).'''
    if next:
        if date.month() == 12:
            year = date.year() + 1
            month = 1
        else:
            year = date.year()
            month = date.month() + 1
    else: # Get the previous month
        if date.month() == 1:
            year = date.year() - 1
            month = 12
        else:
            year = date.year()
            month = date.month() - 1
    month = str(month).zfill(2)
    fmt = '%d/%s/%%d %%H:%%M:%%S' % (year, month)
    dateStr = date.strftime(fmt)
    try:
        r = DateTime(dateStr)
    except Exception as e:
        # Start with the first day of the target month and get its last day
        fmt = '%d/%s/01' % (year, month)
        r = getLastDayOfMonth(DateTime(date.strftime(fmt)),
                              hour=date.strftime('%H:%M:%S'))
    return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def getCalendarMonths(date, end=None, fmt='%Y%m'):
    '''Returns, as a set of strings with this p_fmt, the months being crossed
       by p_date, or, if p_end is passed, being crossed by range
       (p_date, p_end).'''
    # By "month", we mean: the complete range of dates being shown when a month
    # is shown in a monthly-view calendar. Because, in that kind of view, full
    # weeks are rendered, the "month" generally encompasses several days from
    # the previous and next months.
    r = set()
    fdate = date.strftime(fmt)
    r.add(fdate)
    # Get the first day of the week into which p_date is. dow
    # (*d*ay *o*f *w*eek) for Sunday is 0: we convert it to 7.
    dow = date.dow() or 7
    first = date - (dow-1)
    r.add(first.strftime(fmt)) # May be from the previous month
    # Take p_end into account if present
    if end:
        # Ensure p_end is not prior to p_date
        if end < date: raise Exception(S_E_KO)
        fend = end.strftime(fmt)
        r.add(fend)
    else:
        end = date
        fend = fdate
    # Get the last day of the week into which p_end is
    dow = end.dow()
    if dow != 0: # If Sunday, there will be no overflow on the next month
        last = end + (7-dow)
        r.add(last.strftime(fmt))
    # Add intermediary months between p_date and p_end, if distant from more
    # than one month.
    if fdate != fend and end - date > 28:
        month = getSiblingMonth(date)
        smonth = month.strftime(fmt)
        while smonth not in r:
            r.add(smonth)
            month = getSiblingMonth(month)
            smonth = month.strftime(fmt)
    return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def periodsIntersect(start1, end1, start2, end2):
    '''Is there an intersection between intervals [start1, end1] and
       [start2, end2] ?'''
    # p_start1 and p_start2 must be DateTime instances.
    # p_end1 and p_end2 may be DateTime instances or None.
    # ~
    # Convert all parameters to seconds since the epoch
    end1 = sys.maxsize if end1 is None else end1.millis()
    end2 = sys.maxsize if end2 is None else end2.millis()
    start1 = start1.millis()
    start2 = start2.millis()
    # Intervals intersect if they are not disjoint
    if (start1 > end2) or (start2 > end1): return
    return True

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Year:
    '''Represents a year'''

    @classmethod
    def isLeap(class_, year=None):
        '''Is this p_year (or the current year by default) a leap year ?'''
        # In french, leap = "bissextile"
        year = time.localtime()[0] if year is None else year
        return ((year%400) == 0) or (((year%4) == 0) and ((year%100) != 0))

    @classmethod
    def getDays(class_, year=None):
        '''Returns the number of days within this p_year (or the current year by
           default).'''
        return 366 if Year.isLeap(year) else 365
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
