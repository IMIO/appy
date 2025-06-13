#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.model.utils import Object as O

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class TypeInfo(dict):
    '''Collects info about the event types in use in some calendar view'''

    # Every key is an event type, be it from a main calendar or from other tied
    # calendars; every value is an object storing the translated event type name
    # and a count of events matching this type in the current calendar view.

    # ~{s_eventType: O(s_name, i_used)}~

    @classmethod
    def create(class_, cal, o, eventTypes, others):
        '''Compute and return a TypeInfo object, collecting info about all event
           types, from this p_cal(endar) and p_others as defined on this
           p_o(bject).'''
        r = TypeInfo() 
        if eventTypes:
            # p_eventTypes are those defined on the main p_cal(endar)
            for et in eventTypes:
                r[et] = O(name=cal.getEventName(o, et), used=0)
        if others:
            for other in cal.IterSub(others):
                types = other.getEventTypes()
                if types:
                    for et in types:
                        if et not in r:
                            r[et] = O(name=other.field.getEventName(other.o,et),
                                      used=0)
        return r

    def getName(self, eventType, missing=None):
        '''Returns the translated name corresponding to this p_eventType, or
           p_missing if not found.'''
        info = self.get(eventType)
        r = info.name if info else None
        return r or missing

    def update(self, events):
        '''Updates p_self, taking into account these calendar p_events'''
        # Update p_typeInfo with every event from v_r
        for event in events:
            eventType = event.eventType
            # Ignore the event if its type is not found in p_self (should not
            # occur).
            if eventType and eventType in self:
                self[eventType].used += 1
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
