'''Module for managing iCal files'''

# ~license~
# ------------------------------------------------------------------------------
class ICalConfig:
    '''How to map an Appy object to iCal attributes'''
    def __init__(self):
        self.fields = {
          'meet': ('DTSTART', 'DTEND', 'UID', 'CREATED', 'DESCRIPTION',
                   'LAST_MODIFIED', 'STATUS', 'SUMMARY'),
          'task': ('DTSTART', 'DUE', 'UID', 'CREATED', 'DESCRIPTION',
                   'LAST_MODIFIED', 'STATUS', 'SUMMARY'),
        }
        self.appyFields = {
          'meet': {'DTSTART': 'date', 'DTEND': 'endDate', 'UID': 'id',
                   'CREATED': 'created', 'LAST_MODIFIED': 'modified',
                   'SUMMARY': 'title'},
          'task': {'DTSTART': 'date', 'DUE': 'date', 'UID': 'id',
                   'CREATED': 'created', 'LAST_MODIFIED': 'modified',
                   'SUMMARY': 'title'},
        }
        self.defaultValues = {'STATUS': 'CONFIRMED',
                              'DTEND': ':self.getEndDate(startDate)'}
        self.eventTypes = {'meet': 'VEVENT', 'task': 'VTODO'}

# ------------------------------------------------------------------------------
class ICalExporter:
    '''Allows to to produce a .ics file (iCal)'''

    def __init__(self, name, config=None, dateFormat='%Y%m%dT%H%M00'):
        # The name of the file that will be created
        self.name = name
        self.config = config or ICalConfig()
        self.dateFormat = dateFormat
        # Open the result file
        self.f = file(name, 'w')

    def write(self, s):
        '''Writes content p_s into the result'''
        self.f.write('%s\n' % s)

    def start(self):
        '''Dumps the start of the file'''
        self.write('BEGIN:VCALENDAR\nPRODID:Appy\nVERSION:2.0\n' \
                   'CALSCALE:GREGORIAN\nMETHOD:PUBLISH')

    def end(self):
        '''Dumps the end of the file'''
        self.write('END:VCALENDAR')
        self.f.close()

    def getValue(self, value):
        '''Returns the iCal value given the Appy p_value'''
        if not isinstance(value, basestring): # It is a date
             res = value.strftime(self.dateFormat)
        else:
            res = value
            if res and ('\n' in res):
                # Truncate the value if a carriage return is found
                res = res[:res.index('\n')]
        return res

    def getEndDate(self, startDate):
        '''When no end date is found, create one, 1 hour later than
           p_startDate'''
        return self.getValue(startDate + (1.0/24))

    def dumpEntry(self, type, obj):
        '''Dumps a calendar entry of some p_type ("event" or "task") in the
           file, from p_obj.'''
        config = self.config
        eventType = config.eventTypes[type]
        w = self.write
        w('BEGIN:%s' % eventType)
        # We must remember the start date
        startDate = None
        for icalName in config.fields[type]:
            # Get the corresponding Appy field
            appyName = config.appyFields[type].get(icalName)
            # Try to get the value on p_obj
            value = None
            if appyName:
                if appyName.startswith(':'):
                    # It is a Python expression
                    value = eval(appyName[1:])
                else:
                    value = getattr(obj, appyName, None)
                # Remember the start date
                if icalName == 'DTSTART':
                    startDate = value
            # If not found, try to get it from default values
            if (value is None) and (icalName in config.defaultValues):
                default = config.defaultValues[icalName]
                if default.startswith(':'):
                    # It is a Python expression
                    value = eval(default[1:])
                else:
                    value = default
            # Ensure the value is a string
            value = value or ''
            # Get the name of the iCal attribute
            name = icalName.replace('_', '-')
            # Get the value of the iCal attribute
            w('%s:%s' % (name, self.getValue(value)))
        w('END:%s' % eventType)
# ------------------------------------------------------------------------------
