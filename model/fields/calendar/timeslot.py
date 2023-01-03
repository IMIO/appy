#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
TS_NO       = 'At least one timeslot must be defined.'
TS_FIRST    = 'The first timeslot must have id "main", day part of 1.0: it ' \
              'is the one representing the whole day.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Timeslot:
    '''A timeslot defines a time range within a single day'''

    def __init__(self, id, start=None, end=None, name=None, eventTypes=None,
                 dayPart=1.0, default=False):
        # A short, human-readable string identifier, unique among all timeslots
        # for a given Calendar. ID "main" is reserved for the main timeslot that
        # represents the whole day.
        self.id = id
        # The time range can be defined by p_start ~(i_hour, i_minute)~ and
        # p_end (idem), or by a simple name, like "AM" or "PM".
        self.start = start
        self.end = end
        self.name = name or id
        # The event types (among all event types defined at the Calendar level)
        # that can be assigned to this slot.
        self.eventTypes = eventTypes # "None" means "all"
        # p_dayPart is the part of the day (from 0 to 1.0) that is taken by
        # the timeslot. If your timeslot is a kind of virtual timeslot, or if it
        # has no interest or sense to define this day part, set it to 0.
        self.dayPart = dayPart
        # A timeslot being set as the default one will appear preselected in the
        # popup for adding a new event. Among all timeslots defined for a given
        # field, a single one must be set as being the default one.
        self.default = default

    def allows(self, eventType):
        '''It is allowed to have an event of p_eventType in this timeslot ?'''
        # self.eventTypes being None means that no restriction applies
        if not self.eventTypes: return True
        return eventType in self.eventTypes

    @classmethod
    def check(class_, cal, timeslots=None):
        '''Checks that p_timeslots (or p_cal.timeslots if p_timeslots is
           None) are correctly defined.'''
        if timeslots is None:
            timeslots = cal.timeslots
        # The first timeslot must be the global one, named 'main'
        if not timeslots:
            raise Exception(TS_NO)
            first = timeslots[0].id
            if first.id != 'main' or first.dayPart != 1.0:
                # When getting the dayPart for an event, for performance
                # reasons, when the timeslot is "main", the timeslot object is
                # not retrieved and 1.0 is returned. this is why, here, a value
                # being different from 1.0 is not allowed.
                raise Exception(TS_FIRST)

    @classmethod
    def init(class_, cal, timeslots):
        '''Initializes these p_timeslots on this p_cal(endar) field'''
        if not timeslots:
            cal.timeslots = [Timeslot('main')]
        else:
            cal.timeslots = timeslots
            if not callable(timeslots):
                class_.check(cal)

    @classmethod
    def getAll(class_, o, cal):
        '''Gets all timeslots for this p_cal(endar) field on this p_o(bject)'''
        r = cal.timeslots
        if callable(r):
            r = r(o)
            class_.check(cal, r)
        return r

    @classmethod
    def get(class_, id, o, cal, timeslots=None):
        '''Returns the timeslot having this p_id'''
        # Get or compute timeslots if not passed
        if timeslots is None:
            timeslots = class_.getAll(o, cal)
        # Get the one having this p_id
        for slot in timeslots:
            if slot.id == id: return slot

    @classmethod
    def getAllNamed(class_, o, timeslots):
        '''Returns tuple (name, slot) for all defined p_timeslots. Position the
           default one as the first one in the list.'''
        r = []
        for slot in timeslots:
            name = o.translate('timeslot_main') if slot.id == 'main' \
                                                else slot.name
            if slot.default:
                r.insert(0, (name, slot))
            else:
                r.append((name, slot))
        return r

    @classmethod
    def getFreeAt(class_, date, events, slotIds, slotIdsStr, forBrowser=False):
        '''Gets the free timeslots in the current calendar for some p_date'''
        # As a precondition, we know that the day is not full (so timeslot
        # "main" cannot be taken). p_events are those already defined at p_date.
        # p_slotIds is the precomputed list of timeslot ids.
        if not events:
            return slotIdsStr if forBrowser else slotIds
        # Remove any taken slot
        r = slotIds[:]
        r.remove('main') # "main" cannot be chosen: p_events is not empty
        for event in events: r.remove(event.timeslot)
        # Return the result
        return ','.join(r) if forBrowser else r
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
