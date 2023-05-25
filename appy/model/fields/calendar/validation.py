#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from DateTime import DateTime

from appy.model.utils import Object as O

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
E_TYPE_KO   = 'Calendar validation :: wrong event type "%s".'
NOT_RM      = ' (but not removed)'
FINAL_MSG   = '%d event(s) validated and %d discarded%s.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class ValidationMailing:
    '''When validation (see the class below) must generate emails, info about
       those emails is collected in a ValidationMailing instance.'''

    def __init__(self, validation, calendar, o):
        # Get links to the Validation instance and the Calendar fiels
        self.validation = validation
        self.calendar = calendar
        self.o = o
        # "emails" is a dict containing one entry for every mail to send
        self.emails = {} # ~{s_userLogin: (User, [s_eventInfo])}~
        # Translated texts to use for terms "validated" and "discarded" (when
        # talking avout events)
        _ = o.translate
        self.texts = O(validated=_('event_validated'),
                       discarded=_('event_discarded'))

    def addEvent(self, o, field, date, event, action):
        '''An event has been validated or discarded. Store this event in the
           mailing.'''
        validation = self.validation
        # Get info about the user to which to send the email
        user = validation.email(o)
        login = user.login
        # Add an entry if this user is encountered for the first time
        if login not in self.emails:
            self.emails[login] = (user, [])
        # Add the event string: "date - [timeslot] name : status"
        name = field.getEventName(o, event.eventType)
        if event.timeslot != 'main':
            name = f'[{event.timeslot}] {name}'
        dateS = date.strftime(validation.dateFormat)
        eventString = f'{dateS} - {name} - {self.texts[action]}'
        self.emails[login][1].append(eventString)

    def send(self):
        '''Sends the emails'''
        # The subject is the same for every email
        validation = self.validation
        _ = self.o.translate
        subject = _(validation.emailSubjectLabel)
        tool = self.o.tool
        # Create a unique mapping for the body of every translated message,
        # containing what is common to all messages.
        mapping = {'fromUser': self.o.user.getTitle(),
                   'toUser': None, 'details': None}
        # Send one email for every entry in self.emails
        for login in self.emails:
            user, details = self.emails[login]
            mapping['toUser'] = user.getTitle()
            mapping['details'] = '\n'.join(details)
            body = _(validation.emailBodyLabel, mapping=mapping, asText=True)
            tool.sendMail(user.getMailRecipient() or login, subject, body)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Validation:
    '''The validation process for a calendar consists in "converting" some event
       types being "wishes" to other event types being the corresponding final,
       validated events.'''

    # This class holds information about this validation process. For more
    # information, see the Calendar constructor, parameter "validation".

    def __init__(self, mayValidate, mapper, removeDiscarded=False, email=None,
                 emailSubjectLabel=None, emailBodyLabel=None,
                 dateFormat='%d/%m/%Y'):

        # p_mayValidate must hold a method as defined on the Appy class
        # containing the concerned Calendar field. This method accepts no arg
        # and must return True if the  currently logged user can validate whish
        # events.
        self.mayValidate = mayValidate

        # p_mapper must hold a method that will accept, as single arg, an event
        # type and must return, if the input type is a wish, its corresponding
        # final, validated event type. If the input event type is not a wish,
        # the method must return None.
        self.mapper = mapper

        # When discarding events, must we simply let them there or remove them ?
        # If you want to remove them, instead of giving the boolean value
        # "True", you can specify a method. In this case, prior to removing
        # every discarded event, the method will be called, with those args:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #     o     | the target object. It can be the object onto which this
        #           | calendar is defined, or another object if we are
        #           | validating an event from an "other" calendar ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  calendar | the target calendar, that can be different from the one
        #           | tied to this Validation instance if we are validating an
        #           | event from an "other" calendar ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   event   | the event to remove (an instance of class
        #           | appy.model.fields.calendar.Event) ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   date    | the event date, as a DateTime instance.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.removeDiscarded = removeDiscarded

        # When validation occurs, emails can be sent, explaining which events
        # have been validated or discarded. In the following attribute "email",
        # specify a method belonging to the object linked to this calendar. This
        # method must accept no parameter and return a User instance, that will
        # be used as email recipient. If we are on a month view, the method will
        # be called once and a single email will be sent. For a timeline view,
        # the method will be called for every "other" calendar for which events
        # have been validated or rejected, on the object where the other
        # calendar is defined.
        self.email = email

        # When email sending is enabled (see the above parameter), specify here
        # i18n labels for the email subject and body. Within translations for
        # the "body" label, you can use the following variables:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # ${fromUser} | is the name of the user that triggered validation ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # ${toUser}   | is the name of user to which the email is sent (deduced
        #             | from calling method in parameter "email" hereabove) ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # ${details}  | is the list of relevant events. In this list, the
        #             | following information will appear, for every event:
        #             | - its date (including the timeslot if not "main");
        #             | - its type ;
        #             | - its status: validated or discarded.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.emailSubjectLabel = emailSubjectLabel
        self.emailBodyLabel = emailBodyLabel

        # Date format at will appear in the emails
        self.dateFormat = dateFormat

    def getValidatedType(self, o, eventType):
        '''Gets the final, validated event type corresponding to this p_wish
           event type.'''
        return self.mapper(o, eventType)

    def isWish(self, o, eventType):
        '''Is this p_eventType a wish, for which a final, validated event type
           exists ?'''
        return bool(self.getValidatedType(o, eventType))

    def getMailingInfo(self, calendar, o):
        '''Returns a ValidationMailing instance for collecting info about emails
           to send when events are validated and/or discarded.'''
        return ValidationMailing(self, calendar, o)

    def manageMonthCB(self, o, calendar, info, action, mailing, counts):
        '''Manage p_info about a given checkbox, representing an event from a
           monthly, uni-personal p_calendar, that must be validated or discarded
           (depending on p_action).'''
        # p_info corresponds to an event at a given date, with a given event
        # type at a given timeslot, in this p_calendar on p_o.
        date, eventType, timeslot = info.split('_')
        oDate = DateTime(f'{date[:4]}/{date[4:6]}/{date[6:]}')
        # Get the events defined at that date
        events = calendar.getEventsAt(o, date)
        removeDiscarded = self.removeDiscarded
        i = len(events) - 1
        while i >= 0:
            # Get the event at that timeslot
            event = events[i]
            if event.timeslot == timeslot:
                # We have found the event
                if event.eventType != eventType:
                    raise Exception(E_TYPE_KO % event.eventType)
                # Validate or discard it
                if action == 'validated':
                    # Validate it: convert the demand to a validated type
                    event.eventType = self.getValidatedType(o, eventType)
                else:
                    # Discard it: remove it if appropriate
                    if removeDiscarded:
                        if callable(removeDiscarded):
                            removeDiscarded(o, o, calendar, event, oDate)
                        del events[i]
                # Count this event and put it among email info
                counts[action] += 1
                if mailing:
                    mailing.addEvent(o, calendar, oDate, event, action)
            i -= 1

    def manageTimelineCB(self, o, calendar, info, action, mailing, counts):
        '''Manage p_info about a given checkbox, representing an event from a
           timeline, multi-personal p_calendar, that must be validated or
           discarded (depending on p_action).'''
        # p_info corresponds to a given date in some calendar (p_calendar or one
        # among p_self.others). It means that all "impactable" events at that
        # date will be the target of the p_action.
        iid, name, date = info.split('_')
        oDate = DateTime(f'{date[:4]}/{date[4:6]}/{date[6:]}')
        otherO = o.getObject(iid)
        otherF = otherO.getField(name)
        # Get, on this calendar, the events defined at that date
        events = otherF.getEventsAt(otherO, date)
        # Among them, validate or discard any impactable one
        otherV = otherF.validation
        # p_calendar will impose its own "removeDiscarded" on all sub-calendars
        removeDiscarded = self.removeDiscarded
        i = len(events) - 1
        while i >= 0:
            event = events[i]
            # Take this event into account only if it is a wish
            finalEventType = otherV.getValidatedType(otherO, event.eventType)
            if finalEventType:
                if action == 'validated':
                    event.eventType = finalEventType
                else:
                    if removeDiscarded:
                        if callable(removeDiscarded):
                            removeDiscarded(o, otherO, otherF, event, oDate)
                        del events[i]
                # Count this event and put it among email info
                counts[action] += 1
                if mailing:
                    mailing.addEvent(otherO, otherF, oDate, event, action)
            i -= 1

    def do(self, o, calendar):
        '''Validate or discard events from the request'''
        req = o.req
        counts = O(validated=0, discarded=0)
        # Collect info for sending emails
        mailing = self.getMailingInfo(calendar, o) if self.email else None
        # Validate or discard events
        for action in ('validated', 'discarded'):
            if not req[action]: continue
            for info in req[action].split(','):
                if req.render == 'month':
                    self.manageMonthCB(o,calendar,info,action,mailing,counts)
                elif req.render == 'timeline':
                    self.manageTimelineCB(o,calendar,info,action,mailing,counts)
        if not counts.validated and not counts.discarded:
            return o.translate('action_null')
        part = '' if self.removeDiscarded else NOT_RM
        calendar.log(o, FINAL_MSG % (counts.validated, counts.discarded, part))
        # Send the emails
        if self.email: mailing.send()
        o.resp.fleetingMessage = False
        return o.translate('validate_events_done', mapping=counts.d())
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -