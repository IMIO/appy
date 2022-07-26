'''Date-related classes and functions'''

# ~license~
# ------------------------------------------------------------------------------
import sys
try:
    from DateTime import DateTime
except ImportError:
    pass # Zope is required

# ------------------------------------------------------------------------------
# Days of the week
weekDays = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
weekDays_ = weekDays + ('Off',)

# ------------------------------------------------------------------------------
S_E_KO   = 'End date cannot be prior to start date.'

# ------------------------------------------------------------------------------
def toUTC(d):
    '''When manipulating DateTime instances, like p_d, errors can raise when
       performing operations on dates that are not in Universal time, during
       months when changing from/to summer/winter hour. This function returns
       p_d set to UTC.'''
    return DateTime('%d/%d/%d UTC' % (d.year(), d.month(), d.day()))

# ------------------------------------------------------------------------------
class DayIterator:
    '''Class allowing to iterate over a range of days'''

    def __init__(self, startDay, endDay, back=False):
        self.start = toUTC(startDay)
        self.end = toUTC(endDay)
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
    next = __next__ # Python2-3 compliance

# ------------------------------------------------------------------------------
def getLastDayOfMonth(date, hour=None):
    '''Returns a DateTime object representing the last day of date.month()'''
    day = 31
    month = date.month()
    year = date.year()
    found = False
    while not found:
        try:
            res = DateTime('%d/%d/%d %s' % (year, month, day, hour or '12:00'))
            found = True
        except DateTime.DateError:
            day -= 1
    return res

def getDayInterval(date):
    '''Returns a tuple (startOfDay, endOfDay) representing the whole day into
       which p_date occurs.'''
    day = date.strftime('%Y/%m/%d')
    return DateTime('%s 00:00' % day), DateTime('%s 23:59' % day)

def getMonthInterval(date, hour=None):
    '''Returns a tuple (start, end) representing the start and end days for the
       month into which p_date is included.'''
    return DateTime(date.strftime('%Y/%m/01')), \
           getLastDayOfMonth(date, hour=hour)

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
    except Exception, e:
        # Start with the first day of the target month and get its last day
        fmt = '%d/%s/01' % (year, month)
        r = getLastDayOfMonth(DateTime(date.strftime(fmt)),
                              hour=date.strftime('%H:%M:%S'))
    return r

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

def periodsIntersect(start1, end1, start2, end2):
    '''Is there an intersection between intervals [start1, end1] and
       [start2, end2] ?'''
    # p_start1 and p_start2 must be DateTime instances.
    # p_end1 and p_end2 may be DateTime instances or None.
    # ~~~
    # Convert all parameters to seconds since the epoch
    if end1 is not None:
        end1 = end1._millis
    else:
        end1 = sys.maxint
    if end2 is not None:
        end2 = end2._millis
    else:
        end2 = sys.maxint
    start1 = start1._millis
    start2 = start2._millis
    # Intervals intersect if they are not disjoint
    if (start1 > end2) or (start2 > end1): return
    return True
# ------------------------------------------------------------------------------
