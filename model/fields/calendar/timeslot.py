#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from persistent.list import PersistentList

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
TS_NO       = 'At least one timeslot must be defined.'
TS_MAIN     = 'The "main" timeslot must have a day part of 1.0.'

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

    def __repr__(self):
        '''p_self's string representation'''
        return '<Slot %s:%d>' % (self.id, self.dayPart)

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
        if not timeslots:
            raise Exception(TS_NO)
        for slot in timeslots:
            if slot.id == 'main' and slot.dayPart != 1.0:
                # The "main" timeslot must take the whole day. When getting the
                # "dayPart" for an event, for performance reasons, when the
                # timeslot is "main", the timeslot object is not retrieved and
                # 1.0 is returned.
                raise Exception(TS_MAIN)

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
            if not r:
                # No timeslot at all is returned by the app method. Return a
                # default timeslot.
                r = [Timeslot('main')]
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
        try:
            r.remove('main') # "main" cannot be chosen: p_events is not empty
        except ValueError:
            pass # The "main" slot may be absent
        for event in events: r.remove(event.timeslot)
        # Return the result
        return ','.join(r) if forBrowser else r

    # A static empty dict is required by the following method
    emptyD = {}

    @classmethod
    def getEventsAt(class_, o, cal, date, addEmpty, ifEmpty, expr, persist):
        '''Returns a list of the form [(s_timeslot, event)] containing all
           events defined on p_o for this p_cal(endar) at this p_date.'''
        # If p_addEmpty is True, the list contains one entry for every timeslot
        # defined on p_cal but for which there is no event at p_date. In such
        # entries, the "event" part will contain the value as defined by
        # p_ifEmpty. If p_expr is None, the "event" part of a return entry
        # contains the Event object. Else, the "event" part will be the result
        # of evaluating a Python expression in p_expr. This expression will
        # receive, in its context:
        # - the event object as name "event":
        # - the current object as name "o".
        r = PersistentList() if persist else []
        # Get the events defined at this p_date
        events = cal.getEventsAt(o, date) or ()
        if not addEmpty:
            # Siimply return one entry per event defined at p_date
            for event in events:
                e = eval(expr) if expr else event
                r.append((event.timeslot, e))
        else:
            # Turn v_events as a dict, keyed by timeslot
            events = {e.timeslot:e for e in events} if events else class_.emptyD
            # Add one entry per timeslot
            for slot in class_.getAll(o, cal):
                id = slot.id
                if id in events:
                    event = events[id]
                    e = eval(expr) if expr else event
                    r.append((id, e))
                else:
                    r.append((id, ifEmpty))
        return r
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
