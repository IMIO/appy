# -*- coding: utf-8 -*-

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import types
from DateTime import DateTime
from persistent import Persistent
from BTrees.IOBTree import IOBTree
from persistent.list import PersistentList

from appy.px import Px
from appy import utils
from appy.utils import string as sutils
from appy.model.utils import Object as O
from appy.model.fields import Field, Show
from appy.ui.layout import Layout, Layouts
from appy.utils.dates import getLastDayOfMonth

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Timeslot:
    '''A timeslot defines a time range within a single day'''

    def __init__(self, id, start=None, end=None, name=None, eventTypes=None,
                 default=False):
        # A short, human-readable string identifier, unique among all timeslots
        # for a given Calendar. Id "main" is reserved for the main timeslot that
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
        # "day part" is the part of the day (from 0 to 1.0) that is taken by
        # the timeslot.
        self.dayPart = 1.0
        # A timeslot being set as the default one will appear preselected in the
        # popup for adding a new event. Among all timeslots defined for a given
        # field, a single one must be set as being the default one.
        self.default = default

    def allows(self, eventType):
        '''It is allowed to have an event of p_eventType in this timeslot?'''
        # self.eventTypes being None means that no restriction applies
        if not self.eventTypes: return True
        return eventType in self.eventTypes

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
        self.texts = {'validated': _('event_validated'),
                      'discarded': _('event_discarded')}

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
            name = '[%s] %s' % (event.timeslot, name)
        eventString = '%s - %s - %s' % \
          (date.strftime(validation.dateFormat), name, self.texts[action])
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
       types being "wishes" to other event types being the corresponding
       validated events. This class holds information about this validation
       process. For more information, see the Calendar constructor, parameter
       "validation".'''
    def __init__(self, method, schema, removeDiscarded=False,
                 email=None, emailSubjectLabel=None, emailBodyLabel=None,
                 dateFormat='%d/%m/%Y'):
        # p_method holds a method that must return True if the currently logged
        # user can validate whish events.
        self.method = method
        # p_schema must hold a dict whose keys are the event types being wishes
        # and whose values are the event types being the corresponding validated
        # event types.
        self.schema = schema
        # When discarding events, must we simply let them there or remove them?
        # If you want to remove them, instead of giving the boolean value
        # "True", you can specify a method. In this case, prior to removing
        # every discarded event, the method will be called, with those args:
        # * obj       the target object. It can be the object onto which this
        #             calendar is defined, or another object if we are
        #             validating an event from an "other" calendar;
        # * calendar  the target calendar, that can be different from the one
        #             tied to this Validation instance if we are validating an
        #             event from an "other" calendar;
        # * event     the event to remove (an instance of class Event below);
        # * date      the event date, as a DateTime instance.
        self.removeDiscarded = removeDiscarded
        # When validation occurs, emails can be sent, explaining which events
        # have been validated or discarded. In the following attribute "email",
        # specify a method belonging to the object linked to this
        # calendar. This method must accept no parameter and return a User
        # instance, that will be used as email recipient. If we are on a month
        # view, the method will be called once and a single email will be sent.
        # For a timeline view, the method will be called for every "other"
        # calendar for which events have been validated or rejected, on the
        # object where the other calendar is defined.
        self.email = email
        # When email sending is enabled (see the above parameter), specify here
        # i18n labels for the email subject and body. Within translations for
        # the "body" label, you can use the following variables:
        # - ${fromUser} is the name of the user that triggered validation;
        # - ${toUser} is the name of user to which the email is sent (deduced
        #             from calling method in parameter "email" hereabove);
        # - ${details} is the list of relevant events. In this list, the
        #              following information will appear, for every event:
        #   * its date (including the timeslot if not "main");
        #   * its type;
        #   * its status: validated or discarded.
        self.emailSubjectLabel = emailSubjectLabel
        self.emailBodyLabel = emailBodyLabel
        # Date format at will appear in the emails
        self.dateFormat = dateFormat

    def getMailingInfo(self, calendar, o):
        '''Returns a ValidationMailing instance for collecting info about emails
           to send when events are validated and/or discarded.'''
        return ValidationMailing(self, calendar, o)

    def do(self, o, calendar):
        '''Validate or discard events from the request'''
        req = o.req
        counts = {'validated': 0, 'discarded': 0}
        # Determine what to do with discarded events
        removeDiscarded = self.removeDiscarded
        removeIsCallable = callable(removeDiscarded)
        tool = o.tool
        # Collect info for sending emails
        if self.email: mailing = self.getMailingInfo(calendar, o)
        # Validate or discard events
        for action in ('validated', 'discarded'):
            if not req[action]: continue
            for info in req[action].split(','):
                if req.render == 'month':
                    # Every checkbox corresponds to an event at a given date,
                    # with a given event type at a given timeslot, in this
                    # p_calendar on p_obj.
                    date, eventType, timeslot = info.split('_')
                    oDate = DateTime('%s/%s/%s' % (date[:4],date[4:6],date[6:]))
                    # Get the events defined at that date
                    events = calendar.getEventsAt(o, date)
                    i = len(events) - 1
                    while i >= 0:
                        # Get the event at that timeslot
                        event = events[i]
                        if event.timeslot == timeslot:
                            # We have found the event
                            if event.eventType != eventType:
                                raise Exception('Wrong event type')
                            # Validate or discard it
                            if action == 'validated':
                                schema = self.schema
                                event.eventType = schema[eventType]
                            else:
                                if removeDiscarded:
                                    if removeIsCallable:
                                        removeDiscarded(o, o, calendar,
                                                        events[i], oDate)
                                    del events[i]
                            # Count this event and put it among email info
                            counts[action] += 1
                            if self.email:
                                mailing.addEvent(o, calendar, oDate, event,
                                                 action)
                        i -= 1
                elif req.render == 'timeline':
                    # Every checkbox corresponds to a given date in some
                    # calendar (p_calendar or one among self.others). It means
                    # that all "impactable" events at that date will be the
                    # target of the action.
                    otherId, fieldName, date = info.split('_')
                    oDate = DateTime('%s/%s/%s' % (date[:4],date[4:6],date[6:]))
                    otherObj = tool.getObject(otherId)
                    otherField = otherObj.getField(fieldName)
                    # Get, on this calendar, the events defined at that date
                    events = otherField.getEventsAt(otherObj, date)
                    # Among them, validate or discard any impactable one
                    schema = otherField.validation.schema
                    i = len(events) - 1
                    while i >= 0:
                        event = events[i]
                        # Take this event into account only if in the schema
                        if event.eventType in schema:
                            if action == 'validated':
                                event.eventType = schema[event.eventType]
                            else:
                                # p_calendar imposes its own "removeDiscarded"
                                if removeDiscarded:
                                    if removeIsCallable:
                                        removeDiscarded(o, otherObj, otherField,
                                                        events[i], oDate)
                                    del events[i]
                            # Count this event and put it among email info
                            counts[action] += 1
                            if self.email:
                                mailing.addEvent(otherObj, otherField, oDate,
                                                 event, action)
                        i -= 1
        if not counts['validated'] and not counts['discarded']:
            return o.translate('action_null')
        part = '' if removeDiscarded else ' (but not removed)'
        calendar.log(o, '%d event(s) validated and %d discarded%s.' % \
                     (counts['validated'], counts['discarded'], part))
        # Send the emails
        if self.email: mailing.send()
        o.resp.fleetingMessage = False
        return o.translate('validate_events_done', mapping=counts)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Gradient:
    '''If we need to color the cell of a timeline with a linear gradient,
       this class allows to define the characteristics for this gradient.'''

    def __init__(self, angle='135deg', endColor='transparent'):
        # The angle defining the gradient direction
        self.angle = angle
        # The end color (the start color being defined elsewhere)
        self.endColor = endColor

    def getStyle(self, startColor):
        '''Returns the CSS definition for this gradient'''
        return 'background: linear-gradient(%s, %s, %s)' % \
               (self.angle, startColor, self.endColor)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Other:
    '''Identifies a Calendar field that must be shown within another Calendar
       (see parameter "others" in class Calendar).'''
    def __init__(self, o, name, color='grey', excludedEvents=(),
                 highlight=False):
        # The object on which this calendar is defined
        self.o = o
        # The other calendar instance
        self.field = o.getField(name)
        # The color into which events from this calendar must be shown (in the
        # month rendering) in the calendar integrating this one.
        self.color = color
        # The list of event types, in the other calendar, that the integrating
        # calendar does not want to show.
        self.excludedEvents = excludedEvents
        # Must this calendar be highlighted ?
        self.highlight = highlight

    def getEventsInfoAt(self, r, calendar, date, eventNames, inTimeline,
                        preComputed, gradients):
        '''Gets the events defined at p_date in this calendar and append them in
           p_r.'''
        events = self.field.getEventsAt(self.o, date)
        if not events: return
        for event in events:
            eventType = event.eventType
            # Ignore it if among self.excludedEvents
            if eventType in self.excludedEvents: continue
            # Gathered info will be an Object instance
            info = O(event=event, color=self.color)
            if inTimeline:
                # Get the background color for this cell if it has been defined,
                # or (a) nothing if showUncolored is False, (b) a tooltipped dot
                # else.
                bgColor = calendar.getColorFor(self.o, eventType, preComputed)
                if bgColor:
                    info.bgColor = bgColor
                    info.symbol = None
                    # If the event does not span the whole day, a gradient can
                    # be used to color the cell instead of just a plain
                    # background.
                    if (event.getDayPart(self.field) < 1.0) and \
                       (event.timeslot in gradients):
                        info.gradient = gradients[event.timeslot]
                    else:
                        info.gradient = None
                else:
                    info.bgColor = info.gradient = None
                    if calendar.showUncolored:
                        info.symbol = '<abbr title="%s">▪</abbr>' % \
                                      eventNames[eventType]
                    else:
                        info.symbol = None
            else:
                # Get the event name
                info.name = eventNames[eventType]
            r.append(info)

    def getEventTypes(self):
        '''Gets the event types from this Other calendar, ignoring
           self.excludedEvents if any.'''
        r = []
        for eventType in self.field.getEventTypes(self.o):
            if eventType not in self.excludedEvents:
                r.append(eventType)
        return r

    def getCss(self):
        '''When this calendar is shown in a timeline, get the CSS class for the
           row into which it is rendered.'''
        return 'highlightRow' if self.highlight else ''

    def mayValidate(self):
        '''Is validation enabled for this other calendar?'''
        return self.field.mayValidate(self.o)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Total:
    '''Represents a computation that will be executed on a series of cells
       within a timeline calendar.'''

    def __init__(self, initValue):
        # If p_initValue is mutable, get a copy of it
        if isinstance(initValue, dict):
            initValue = initValue.copy()
        elif isinstance(initValue, list):
            initValue = initValue[:]
        self.value = initValue

    def __repr__(self): return '<Total=%s>' % str(self.value)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Totals:
    '''For a timeline calendar, if you want to add rows or columns representing
       totals computed from other rows/columns (representing agendas), specify
       it via Totals instances (see Agenda fields "totalRows" and "totalCols"
       below).'''
    def __init__(self, name, label, onCell, initValue=0):
        # "name" must hold a short name or acronym and will directly appear
        # at the beginning of the row. It must be unique within all Totals
        # instances defined for a given Calendar field.
        self.name = name
        # "label" is a i18n label that will be used to produce a longer name
        # that will be shown as an "abbr" tag around the name.
        self.label = label
        # A method that will be called every time a cell is walked in the
        # agenda. It will get these args:
        # * date        - the date representing the current day (a DateTime
        #                 instance);
        # * other       - the Other instance representing the currently walked
        #                 calendar;
        # * events      - the list of events (as Event instances) defined at
        #                 that day in this calendar. Be careful: this can be
        #                 None;
        # * total       - the Total instance (see above) corresponding to the
        #                 current column;
        # * last        - a boolean that is True if we are walking the last
        #                 shown calendar;
        # * checked     - a value "checked" indicating the status of the
        #                 possible validation checkbox corresponding to this
        #                 cell. If there is a checkbox in this cell, the value
        #                 will be True or False; else, the value will be None.
        # * preComputed - the result of Calendar.preCompute (see below)
        self.onCell = onCell
        # "initValue" is the initial value given to created Total instances
        self.initValue = initValue

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Layer:
    '''A layer is a set of additional data that can be activated or not on top
       of calendar data. Currently available for timelines only.'''

    def __init__(self, name, label, onCell, activeByDefault=False, legend=None,
                 merge=False):
        # "name" must hold a short name or acronym, unique among all layers
        self.name = name
        # "label" is a i18n label that will be used to produce the layer name in
        # the user interface.
        self.label = label
        # "onCell" must be a method that will be called for every calendar cell
        # and must return a 3-tuple (style, title, content). "style" will be
        # dumped in the "style" attribute of the current calendar cell, "title"
        # in its "title" attribute, while "content" will be shown within the
        # cell. If nothing must be shown at all, None must be returned.
        # This method must accept those args:
        # * date        - the currently walked day (a DateTime instance);
        # * other       - the Other instance representing the currently walked
        #                 calendar;
        # * events      - the list of events (as a list of custom Object
        #                 instances whose attribute "event" points to an Event
        #                 instance) defined at that day in this calendar.
        # * preComputed - the result of Calendar.preCompute (see below)
        self.onCell = onCell
        # Is this layer activated by default ?
        self.activeByDefault = activeByDefault
        # "legend" is a method that must produce legend items that are specific
        # to this layer. The method must accept no arg and must return a list of
        # objects (you can use class appy.Object) having these attributes:
        # * name        - the legend item name as shown in the calendar
        # * style       - the content of the "style" attribute that will be
        #                 applied to the little square ("td" tag) for this item;
        # * content     - the content of this "td" (if any).
        self.legend = legend
        # When p_merge is False, if the layer contains info for a given day, the
        # base info will be hidden. Else, it will be merged.
        self.merge = merge
        # Layers will be chained: one layer will access the previous one in the
        # stack via attribute "previous". "previous" fields will automatically
        # be filled by the Calendar.
        self.previous = None

    def getCellInfo(self, o, activeLayers, date, other, events, preComputed):
        '''Get the cell info from this layer or one previous layer when
           relevant.'''
        # Take this layer into account only if active
        if self.name in activeLayers:
            info = self.onCell(o, date, other, events, preComputed)
            if info: return info
        # Get info from the previous layer
        if self.previous:
            return self.previous.getCellInfo(o, activeLayers, date, other,
                                             events, preComputed)

    def getLegendEntries(self, o):
        '''Returns the legend entries by calling method in self.legend'''
        return self.legend(o) if self.legend else None

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Legend:
    '''Represents a legend on a timeline calendar'''

    px = Px('''
     <table class=":field.legend.getCss()"
            var="entries=field.legend.getEntries(field, o, allEventTypes, \
                    allEventNames, url, _, activeLayers, preComputed)">
      <tr for="row in field.splitList(entries, field.legend.cols)" valign="top">
       <x for="entry in row">
        <td align="center">
         <table width="13px">
          <tr><td style=":entry.style"
                  align="center">:entry.content or '&nbsp;'</td></tr>
         </table>
        </td>
        <td style=":field.legend.getCssText()">:entry.name</td>
       </x>
      </tr>
     </table>''')

    def __init__(self, position='bottom', cols=4, width='115px', entryName=None,
                 concatenate=', ', update=None):
        # The legend can be positioned at the "bottom" or to the "right" of the
        # timeline
        self.position = position
        # It spans a given number of columns
        self.cols = cols
        # A width for the column(s) displaying the text for a legend entry
        self.width = width
        # By default, when an entry, corresponding to an event type, must be
        # added to the legend, the event name, as defined by the tied Calendar
        # field, is used as name for the legend entry. If you prefer to define
        # another name, specify a method in attribute p_entryName. This method
        # will receive these args:
        # 1) an event type (eventType)
        # 2) the dict of all encountered event names (eventNames), keyed by
        # event type.
        # The method must return the name of the corresponding entry.
        self.entryName = entryName
        # If several event types share the same color, a single entry must be
        # produced in the legend. Attribute p_concatenate defines the separator
        # to use between all the event names related to the same legend entry.
        # If p_concatenate is None, once a first event type has been found for a
        # given color, any other event type corresponding to the same color will
        # simply be ignored.
        self.concatenate = concatenate
        # A method that will, once the legend is build, receive it a single arg
        # and possibly update it if necessary.
        self.update = update

    def getCss(self):
        '''Gets the CSS class(es) for the legend table'''
        r = 'legend'
        if self.position == 'right': r += ' legendRight'
        return r

    def getCssText(self):
        '''Gets CSS attributes for a text entry'''
        return 'padding-left: 5px; width: %s' % self.width

    def getEntryNameFor(self, o, eventType, allEventNames):
        '''Get the name of the legend entry corresponding to this p_eventType'''
        method = self.entryName
        if method:
            r = method(o, eventType, allEventNames)
        else:
            r = allEventNames[eventType]
        return r

    def getEntries(self, field, o, allEventTypes, allEventNames, url, _,
                   activeLayers, preComputed):
        '''Gets information needed to produce the legend for a timeline'''
        # Produce one legend entry by event type, provided it is shown and
        # colored.
        r = []
        byStyle = {}
        concat = self.concatenate
        for eventType in allEventTypes:
            # Create a new entry for every not-yet-encountered color
            eventColor = field.getColorFor(o, eventType, preComputed)
            if not eventColor: continue
            style = 'background-color:%s' % eventColor
            if style not in byStyle:
                entryName = self.getEntryNameFor(o, eventType, allEventNames)
                entry = O(name=entryName, content='', style=style)
                r.append(entry)
                byStyle[style] = entry
            elif concat is not None:
                # Update the existing entry with this style
                entry = byStyle[style]
                entryName = self.getEntryNameFor(o, eventType, allEventNames)
                entry.name = '%s%s%s' % (entry.name, concat, entryName)
        # Add the background indicating that several events are hidden behind
        # the timeline cell
        r.append(O(name=_('several_events'), content='',
                   style=url('angled', bg=True)))
        # Add layer-specific items
        for layer in field.layers:
            if layer.name not in activeLayers: continue
            entries = layer.getLegendEntries(o)
            if entries:
                # Take care of entry duplicates
                for entry in entries:
                    style = '%s%s' % (entry.content or '', entry.style)
                    if style not in byStyle:
                        r.append(entry)
                        byStyle[style] = entry
                    elif concat is not None:
                        # Update the existing entry with this style
                        existingEntry = byStyle[style]
                        existingEntry.name = '%s%s%s' % \
                                        (existingEntry.name, concat, entry.name)
        # Update the legend with a custom method if needed
        if self.update: self.update(o, r)
        return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Action:
    '''An action represents a custom method that can be executed, based on
       calendar data. If at least one action is visible, the shown calendar
       cells will become selectable: the selected cells will be available to the
       action.

       Currently, actions can be defined in timeslot calendars only.'''
    def __init__(self, name, label, action, show=True, valid=None):
        # A short name that must identify this action among all actions defined
        # in this calendar.
        self.name = name
        # "label" is a i18n label that will be used to name the action in the
        # user interface.
        self.label = label
        # "labelConfirm" is the i18n label used in the confirmation popup. It
        # is based on self.label, suffixed with "_confirm".
        self.labelConfirm = label + '_confirm'
        # "action" is the method that will be executed when the action is
        # triggered. It accepts 2 args:
        # - "selected": a list of tuples (obj, date). Every such tuple
        #               identifies a selected cell: "obj" is the object behind
        #               the "other" calendar into which the cell is; "date" is a
        #               DateTime instance that represents the date selected in
        #               this calendar.
        #               The list can be empty if no cell has been selected.
        # - "comment"  the comment entered by the user in the confirm popup.
        self.action = action
        # Must this action be shown or not? "show" can be a boolean or a method.
        # If it is a method, it must accept a unique arg: a DateTime instance
        # being the first day of the currently shown month.
        self.show = show
        # Is the combination of selected events valid for triggering the action?
        self.valid = None

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Event(Persistent):
    '''A calendar event as will be stored in the database'''
    def __init__(self, eventType, timeslot='main'):
        self.eventType = eventType
        self.timeslot = timeslot

    def getName(self, o, field, allEventNames=None, xhtml=True):
        '''Gets the name for this event, that depends on it type and may include
           the timeslot if not "main".'''
        # If we have the translated names for event types, use it.
        r = None
        if allEventNames:
            if self.eventType in allEventNames:
                r = allEventNames[self.eventType]
            else:
                # This can be an old deactivated event not precomputed anymore
                # in p_allEventNames. Try to use field.getEventName to
                # compute it.
                try:
                    r = field.getEventName(o, self.eventType)
                except Exception:
                    pass
        # If no name was found, use the raw event type
        r = r or self.eventType
        if self.timeslot != 'main':
            # Prefix it with the timeslot
            prefix = xhtml and ('<b>[%s]</b> ' % self.timeslot) or \
                               ('[%s] ' % self.timeslot)
            r = '%s%s' % (prefix, r)
        return r

    def sameAs(self, other):
        '''Is p_self the same as p_other?'''
        return (self.eventType == other.eventType) and \
               (self.timeslot == other.timeslot)

    def getDayPart(self, field):
        '''What is the day part taken by this event ?'''
        return field.getTimeslot(self.timeslot).dayPart

    def __repr__(self):
        return '<Event %s @slot %s>' % (self.eventType, self.timeslot)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Calendar(Field):
    '''This field allows to produce an agenda (monthly view) and view/edit
       events on it.'''

    # Some elements will be traversable
    traverse  = Field.traverse.copy()

    # Required Javascript files
    jsFiles = {'view': ('calendar.js',)}

    # Make some classes available here
    DateTime = DateTime
    Timeslot = Timeslot
    Validation = Validation
    Other = Other
    Totals = Totals
    Layer = Layer
    Legend = Legend
    Action = Action
    Event = Event
    IterSub = utils.IterSub

    # Error messages
    TIMELINE_WITH_EVENTS = 'A timeline calendar has the objective to display ' \
      'a series of other calendars. Its own calendar is disabled: it is ' \
      'useless to define event types for it.'
    MISSING_EVENT_NAME_METHOD = "When param 'eventTypes' is a method, you " \
      "must give another method in param 'eventNameMethod'."
    TIMESLOT_USED = 'An event is already defined at this timeslot.'
    DAY_FULL = 'No more place for adding this event.'
    TOTALS_MISUSED = 'Totals can only be specified for timelines ' \
      '(render == "timeline").'
    STRICT_MONTHS_MISUSED = 'Strict months can only be used with timeline ' \
      'calendars.'
    ACTION_NOT_FOUND = 'Action "%s" does not exist or is not visible.'
    UNSORTED_EVENTS = 'Events must be sorted if you want to get spanned ' \
      'events to be grouped.'

    timelineBgColors = {'Fri': '#dedede', 'Sat': '#c0c0c0', 'Sun': '#c0c0c0'}
    validCbStatuses = {'validated': True, 'discarded': False}

    class Layouts(Layouts):
        '''Calendar-specific layouts'''
        b = Layouts(edit='f', view='l-d-f')
        n = Layouts(Layout('l-f', width=None))

        @classmethod
        def getDefault(class_, field):
            '''Default layouts for this Calendar p_field'''
            return class_.n if field.render == 'timeline' else class_.b

    # For timeline rendering, the row displaying month names
    pxTimeLineMonths = Px('''
     <tr>
      <th class="hidden"></th>
      <th for="mInfo in monthsInfos" colspan=":mInfo.colspan">::mInfo.month</th>
      <th class="hidden"></th>
     </tr>''')

    # For timeline rendering, the row displaying day letters
    pxTimelineDayLetters = Px('''
     <tr>
      <td class="hidden"></td>
      <td for="date in grid"><b>:namesOfDays[date.aDay()].name[0]</b></td>
      <td class="hidden"></td>
     </tr>''')

    # For timeline rendering, the row displaying day numbers
    pxTimelineDayNumbers = Px('''
     <tr>
      <td class="hidden"></td>
      <td for="date in grid"><b>:str(date.day()).zfill(2)</b></td>
      <td class="hidden"></td>
     </tr>''')

    # Displays the total rows at the bottom of a timeline calendar
    pxTotalRows = Px('''
     <tbody id=":'%s_trs' % hook"
            var="totals=field.computeTotals('row',o,grid,others,preComputed)">
      <script>:field.getAjaxDataTotals(o,'rows',hook)</script>
      <tr for="row in field.totalRows" var2="rowTitle=_(row.label)">
       <td class="tlLeft">
        <abbr title=":rowTitle"><b>:row.name</b></abbr></td>
       <td for="date in grid">::totals[row.name][loop.date.nb].value</td>
       <td class="tlRight">
        <abbr title=":rowTitle"><b>:row.name</b></abbr></td>
      </tr>
     </tbody>''')

    # Displays the total columns besides the calendar, as a separate table
    pxTotalCols = Px('''
     <table cellpadding="0" cellspacing="0" class="list timeline"
            style="float:right" id=":'%s_tcs' % hook"
            var="totals=field.computeTotals('col',o,grid,others,preComputed)">
      <script>:field.getAjaxDataTotals(o,'cols',hook)</script>
      <!-- 2 empty rows -->
      <tr><th for="col in field.totalCols" class="hidden">-</th></tr>
      <tr><td for="col in field.totalCols" class="hidden">-</td></tr>
      <tr> <!-- The column headers -->
       <td for="col in field.totalCols">
        <abbr title=":_(col.label)">:col.name</abbr>
       </td>
      </tr>
      <!-- Re-create one row for every other calendar -->
      <x var="i=-1" for="otherGroup in others">
       <tr for="other in otherGroup" var2="@i=i+1">
        <td for="col in field.totalCols">::totals[col.name][i].value</td>
       </tr>
       <!-- The separator between groups of other calendars -->
       <x if="not loop.otherGroup.last">::field.getOthersSep(\
         len(field.totalCols))</x>
      </x>
      <!-- Add empty rows for every total row -->
      <tr for="i in range(len(field.totalRows))">
       <td for="col in field.totalCols">&nbsp;</td>
      </tr>
      <tr> <!-- Repeat the column headers -->
       <td for="col in field.totalCols">
        <abbr title=":_(col.label)">:col.name</abbr>
       </td>
      </tr>
      <tr><td for="col in field.totalCols" class="hidden">-</td></tr>
      <tr><th for="col in field.totalCols" class="hidden">-</th></tr>
     </table>''')

    # Ajax-call pxTotalRows or pxTotalCols
    pxTotalsFromAjax = Px('''
     <x var="month=req.month;
             totalType=req.totalType.capitalize();
             hook=str(o.iid) + field.name;
             monthDayOne=field.DateTime('%s/01' % month);
             grid=field.getGrid(month, 'timeline');
             preComputed=field.getPreComputedInfo(o, monthDayOne, grid);
             others=field.getOthers(o, \
               preComputed)">:getattr(field, 'pxTotal%s' % totalType)</x>''')

    # Timeline view for a calendar
    pxViewTimeline = Px('''
     <table cellpadding="0" cellspacing="0" class="list timeline"
            id=":hook + '_cal'" style="display: inline-block"
            var="monthsInfos=field.getTimelineMonths(grid, o, preComputed);
                 gradients=field.getGradients(o)">
      <colgroup> <!-- Column specifiers -->
       <col/> <!-- 1st col: Names of calendars -->
       <col for="date in grid"
            style=":field.getColumnStyle(o, date, render, today)"/>
       <col/>
      </colgroup>
      <tbody>
       <!-- Header rows (months and days) -->
       <x>:field.pxTimeLineMonths</x>
       <x>:field.pxTimelineDayLetters</x><x>:field.pxTimelineDayNumbers</x>
       <!-- Other calendars -->
       <x for="otherGroup in others">
        <tr for="other in otherGroup" id=":other.o.iid"
            var2="tlName=field.getTimelineName(o, other, month, grid);
                  mayValidate=mayValidate and other.mayValidate();
                  css=other.getCss()">
         <td class=":('tlLeft ' + css).strip()">::tlName</td>
         <!-- A cell in this other calendar -->
         <x for="date in grid"
            var2="inRange=field.dateInRange(date, startDate, endDate)">
          <td if="not inRange"></td>
          <x if="inRange">::field.getTimelineCell(_ctx_, o, date, actions)</x>
         </x>
         <td class=":('tlRight ' + css).strip()">::tlName</td>
        </tr>
        <!-- The separator between groups of other calendars -->
        <x if="not loop.otherGroup.last">::field.getOthersSep(len(grid)+2)</x>
       </x>
      </tbody>
      <!-- Total rows -->
      <x if="field.totalRows">:field.pxTotalRows</x>
      <tbody> <!-- Footer (repetition of months and days) -->
       <x>:field.pxTimelineDayNumbers</x><x>:field.pxTimelineDayLetters</x>
       <x>:field.pxTimeLineMonths</x>
      </tbody>
     </table>
     <!-- Total columns, as a separate table, and legend -->
     <x if="field.legend.position == 'right'">:field.legend.px</x>
     <x if="field.totalCols">:field.pxTotalCols</x>
     <x if="field.legend.position == 'bottom'">:field.legend.px</x>''')

    # Popup for adding an event in the month view
    pxAddPopup = Px('''
     <div var="popupId=hook + '_new';
               submitJs='triggerCalendarEvent(%s, %s, %s_maxEventLength)' % \
                        (q(hook), q('new'), field.name)"
          id=":popupId" class="popup" align="center">
      <form id=":popupId + 'Form'" method="post" data-sub="process">
       <input type="hidden" name="actionType" value="createEvent"/>
       <input type="hidden" name="day"/>

       <!-- Choose an event type -->
       <div align="center">:_(field.createEventLabel)</div>
       <select name="eventType" class="calSelect">
        <option value="">:_('choose_a_value')</option>
        <option for="eventType in allowedEventTypes"
                value=":eventType">:allEventNames[eventType]</option>
       </select>

       <!-- Choose a timeslot -->
       <div if="showTimeslots">
        <span class="discreet">:_('timeslot')</span> 
        <select if="showTimeslots" name="timeslot" class="calSelect">
         <option for="sname, slot in field.getAllSlots(o)"
                 value=":slot.id">:sname</option>
        </select>
       </div>

       <!-- Span the event on several days -->
       <div align="center" class="calSpan">
        <x>::_('event_span')</x>
        <input type="text" size="1" name="eventSpan"
               onkeypress="return (event.keyCode != 13)"/>
       </div>
       <input type="button" value=":_('object_save')" onclick=":submitJs"/>
       <input type="button" value=":_('object_cancel')"
              onclick=":'closePopup(%s)' % q(popupId)"/>
      </form>
     </div>''',

     css='''.calSelect { margin:10px 0; color:|selectColor|; font-size:95% }
            .calSpan { margin-bottom:3px; font-size:92%; color:|selectColor| }
            .calSpan input { color:|selectColor|; text-align:center }
     ''')

    # Popup for removing events in the month view
    pxDelPopup = Px('''
     <div var="popupId=hook + '_del'"
          id=":popupId" class="popup" align="center">
      <form id=":popupId + 'Form'" method="post" data-sub="process">
       <input type="hidden" name="actionType" value="deleteEvent"/>
       <input type="hidden" name="timeslot" value="main"/>
       <input type="hidden" name="day"/>
       <div align="center"
            style="margin-bottom: 5px">:_('action_confirm')</div>

       <!-- Delete successive events ? -->
       <div class="discreet" style="margin-bottom: 10px"
            id=":hook + '_DelNextEvent'"
            var="cbId=popupId + '_cb'; hdId=popupId + '_hd'">
         <input type="checkbox" name="deleteNext_cb" id=":cbId"
                onClick="toggleCheckbox(this)"/><input
          type="hidden" id=":hdId" name="deleteNext"/>
         <label lfor=":cbId" class="simpleLabel">:_('del_next_events')</label>
       </div>
       <input type="button" value=":_('yes')"
              onClick=":'triggerCalendarEvent(%s, %s)' % (q(hook), q('del'))"/>
       <input type="button" value=":_('no')"
              onclick=":'closePopup(%s)' % q(popupId)"/>
      </form>
     </div>''')

    # Month view for a calendar
    pxViewMonth = Px('''
      <table cellpadding="0" cellspacing="0" width=":field.width"
             class=":field.style" id=":hook + '_cal'"
             var="rowHeight=int(field.height/float(len(grid)))">
       <!-- 1st row: names of days -->
       <tr height="22px">
        <th for="dayId in field.weekDays"
            width="14%">:namesOfDays[dayId].short</th>
       </tr>
       <!-- The calendar in itself -->
       <tr for="row in grid" valign="top" height=":rowHeight">
        <x for="date in row"
           var2="inRange=field.dateInRange(date, startDate, endDate);
                 cssClasses=field.getCellClass(o, date, render, today)">
         <!-- Dump an empty cell if we are out of the supported date range -->
         <td if="not inRange" class=":cssClasses"></td>
         <!-- Dump a normal cell if we are in range -->
         <td if="inRange"
             var2="events=field.getEventsAt(o, date);
                   single=events and len(events) == 1;
                   spansDays=field.hasEventsAt(o, date+1, events);
                   mayCreate=mayEdit and not field.dayIsFull(date, events);
                   mayDelete=mayEdit and events and field.mayDelete(o, events);
                   day=date.day();
                   dayString=date.strftime('%Y/%m/%d');
                   js=mayEdit and 'itoggle(this)' or ''"
             style=":'font-weight:%s' % \
                     ('bold' if date.isCurrentDay() else 'normal')"
             class=":cssClasses" onmouseover=":js" onmouseout=":js">
          <span>:day</span> 
          <span if="day == 1">:_('month_%s_short' % date.aMonth())</span>
          <!-- Icon for adding an event -->
          <x if="mayCreate">
           <img class="clickable" style="visibility:hidden"
                var="info=field.getApplicableEventTypesAt(o, date, \
                           eventTypes, preComputed, True)"
                if="info and info.eventTypes" src=":url('plus')"
                var2="freeSlots=field.getFreeSlotsAt(date, events, slotIds,\
                                                     slotIdsStr, True)"
                onclick=":'openEventPopup(%s,%s,%s,null,null,%s,%s,%s)' % \
                 (q(hook), q('new'), q(dayString), q(info.eventTypes), \
                  q(info.message), q(freeSlots))"/>
          </x>
          <!-- Icon for deleting event(s) -->
          <img if="mayDelete" class="clickable iconS" style="visibility:hidden"
               src=":svg('deleteS' if single else 'deleteMany')"
               onclick=":'openEventPopup(%s,%s,%s,%s,%s)' %  (q(hook), \
                          q('del'), q(dayString), q('main'), q(spansDays))"/>
          <!-- Events -->
          <x if="events">
          <div for="event in events" style="color: grey">
           <!-- Checkbox for validating the event -->
           <input type="checkbox" checked="checked" class="smallbox"
               if="mayValidate and (event.eventType in field.validation.schema)"
               id=":'%s_%s_%s' % (date.strftime('%Y%m%d'), event.eventType, \
                                  event.timeslot)"
               onclick=":'onCheckCbCell(this,%s)' % q(hook)"/>
           <x>::event.getName(o, field, allEventNames)</x>
           <!-- Icon for delete this particular event -->
            <img if="mayDelete and not single" class="clickable iconS"
                 src=":svg('deleteS')"  style="visibility:hidden"
                 onclick=":'openEventPopup(%s,%s,%s,%s)' % (q(hook), \
                            q('del'), q(dayString), q(event.timeslot))"/>
          </div>
          </x>
          <!-- Events from other calendars -->
          <x if="others"
             var2="otherEvents=field.getOtherEventsAt(date, others, \
                                           allEventNames, render, preComputed)">
           <div style=":'color: %s; font-style: italic' % event.color"
                for="event in otherEvents">:event.name</div>
          </x>
          <!-- Additional info -->
          <x var="info=field.getAdditionalInfoAt(o, date, preComputed)"
             if="info">::info</x>
         </td>
        </x>
       </tr>
      </table>

      <!-- Popups for creating and deleting a calendar event -->
      <x if="mayEdit and eventTypes">
       <x>:field.pxAddPopup</x><x>:field.pxDelPopup</x></x>''')

    # The range of widgets (checkboxes, buttons) allowing to trigger actions
    pxActions = Px('''
     <!-- Validate button, with checkbox for automatic checbox selection -->
     <x if="mayValidate" var2="cbId='%s_auto' % hook">
      <input if="mayValidate" type="button" value=":_('validate_events')"
             class="buttonSmall button" style=":url('validate', bg=True)"
             var2="js='validateEvents(%s,%s)' % (q(hook), q(month))"
             onclick=":'askConfirm(%s,%s,%s)' % (q('script'), q(js, False), \
                       q(_('validate_events_confirm')))"/>
      <input type="checkbox" checked="checked" id=":cbId"/>
      <label lfor=":cbId" class="simpleLabel">:_('select_auto')</label>
     </x>
     <!-- Checkboxes for (de-)activating layers -->
     <x if="field.layers and field.layersSelector">
      <x for="layer in field.layers"
         var2="cbId='%s_layer_%s' % (hook, layer.name)">
       <input type="checkbox" id=":cbId" checked=":layer.name in activeLayers"
              onclick=":'switchCalendarLayer(%s, this)' % q(hook)"/>
       <label lfor=":cbId" class="simpleLabel">:_(layer.label)</label>
      </x>
     </x>
     <x if="actions"> <!-- Custom actions -->
      <input for="action in actions" type="button" value=":_(action.label)"
             var2="js='calendarAction(%s,%s,comment)' % \
                       (q(hook), q(action.name))"
             onclick=":'askConfirm(%s,%s,%s,true)' % (q('script'), \
                        q(js,False), q(_(action.labelConfirm)))"/>
      <!-- Icon for unselecting all cells -->
      <img src=":url('unselect')" title=":_('unselect_all')" class="clickable"
          onclick=":'calendarUnselect(%s)' % q(hook)"/>
     </x>''')

    view = cell = buttons = Px('''
     <div var="defaultDate=field.getDefaultDate(o);
               defaultDateMonth=defaultDate.strftime('%Y/%m');
               hook=str(o.iid) + field.name;
               month=req.month or defaultDate.strftime('%Y/%m');
               monthDayOne=field.DateTime('%s/01' % month);
               render=req.render or field.render;
               today=field.DateTime('00:00');
               grid=field.getGrid(month, render);
               eventTypes=field.getEventTypes(o);
               allowedEventTypes=field.getAllowedEventTypes(o, eventTypes);
               preComputed=field.getPreComputedInfo(o, monthDayOne, grid);
               mayEdit=field.mayEdit(o);
               objUrl=o.url;
               startDate=field.getStartDate(o);
               endDate=field.getEndDate(o);
               around=field.getSurroundingMonths(monthDayOne, tool, \
                                                 startDate, endDate);
               others=field.getOthers(o, preComputed);
               events=field.getAllEvents(o, eventTypes, others);
               allEventTypes,allEventNames=events;
               namesOfDays=field.getNamesOfDays(_);
               showTimeslots=len(field.timeslots) &gt; 1;
               slotIds=[slot.id for slot in field.timeslots];
               slotIdsStr=','.join(slotIds);
               mayValidate=field.mayValidate(o);
               activeLayers=field.getActiveLayers(req);
               actions=field.getVisibleActions(o, monthDayOne)"
          id=":hook">
      <script>:'var %s_maxEventLength = %d;' % \
                (field.name, field.maxEventLength)</script>
      <script>:field.getAjaxData(hook, o, render=render, month=month, \
               activeLayers=','.join(activeLayers), popup=popup)</script>

      <!-- Month chooser -->
      <div style="margin-bottom: 5px"
           var="fmt='%Y/%m/%d';
                goBack=not startDate or around.previous;
                goForward=not endDate or around.next">

       <!-- Go to the previous month -->
       <img class="clickable iconS" if="goBack"
            var2="prev=around.previous" title=":prev.text"
            src=":svg('arrow')" style="transform: rotate(90deg)"
            onclick=":'askMonth(%s,%s)' % (q(hook), q(prev.id))"/>

       <!-- Go back to the default date -->
       <input type="button" if="goBack or goForward"
         var2="fmt='%Y/%m';
               sdef=defaultDate.strftime(fmt);
               disabled=sdef == monthDayOne.strftime(fmt);
               label='today' if sdef==today.strftime(fmt) else 'goto_source'"
         value=":_(label)" disabled=":disabled"
         style=":'color:%s' % ('grey' if disabled else 'black')"
         onclick=":'askMonth(%s,%s)' % (q(hook), q(defaultDateMonth))"/>

       <!-- Display the current month and allow to select another one -->
       <select onchange=":'askMonth(%s, this.value)' % q(hook)">
        <option for="m in around.all" value=":m.id"
                selected=":m.id == month">:m.text</option>
       </select>

       <!-- Go to the next month -->
       <img if="goForward" class="clickable iconS" 
            var2="next=around.next" title=":next.text" src=":svg('arrow')"
            style="transform: rotate(270deg)"
            onclick=":'askMonth(%s,%s)' % (q(hook), q(next.id))"/>

       <!-- Global actions -->
       <x>:field.pxActions</x>
      </div>

      <!-- The top PX, if defined -->
      <x if="field.topPx">::field.topPx</x>

      <!-- The calendar in itself -->
      <x>:getattr(field, 'pxView%s' % render.capitalize())</x>

      <!-- The bottom PX, if defined -->
      <x if="field.bottomPx">::field.bottomPx</x>
     </div>''')

    edit = search = ''

    def __init__(self, eventTypes=None, eventNameMethod=None,
      allowedEventTypes=None, validator=None, default=None, defaultOnEdit=None,
      show=Show.ER_, renderable=None, page='main', group=None, layouts=None,
      move=0, readPermission='read', writePermission='write', width='100%',
      height=300, colspan=1, master=None, masterValue=None, focus=False,
      mapping=None, generateLabel=None, label=None, maxEventLength=50,
      render='month', others=None, timelineName=None, timelineMonthName=None,
      additionalInfo=None, startDate=None, endDate=None, defaultDate=None,
      timeslots=None, colors=None, gradients=None, showUncolored=False,
      columnColors=None, preCompute=None, applicableEvents=None, totalRows=None,
      totalCols=None, validation=None, layers=None, layersSelector=True,
      topPx=None, bottomPx=None, actions=None, selectableEmptyCells=False,
      legend=None, view=None, cell=None, buttons=None, edit=None, editable=True,
      xml=None, translations=None, delete=True, beforeDelete=None,
      selectableMonths=6, createEventLabel='which_event', style='calTable',
      strictMonths=False):
        # eventTypes can be a "static" list or tuple of strings that identify
        # the types of events that are supported by this calendar. It can also
        # be a method that computes such a "dynamic" list or tuple. When
        # specifying a static list, an i18n label will be generated for every
        # event type of the list. When specifying a dynamic list, you must also
        # give, in p_eventNameMethod, a method that will accept a single arg
        # (=one of the event types from your dynamic list) and return the "name"
        # of this event as it must be shown to the user.
        self.eventTypes = eventTypes
        if (render == 'timeline') and eventTypes:
            raise Exception(Calendar.TIMELINE_WITH_EVENTS)
        self.eventNameMethod = eventNameMethod
        if callable(eventTypes) and not eventNameMethod:
            raise Exception(Calendar.MISSING_EVENT_NAME_METHOD)
        # Among event types, for some users, only a subset of it may be created.
        # "allowedEventTypes" is a method that must accept the list of all
        # event types as single arg and must return the list/tuple of event
        # types that the current user can create.
        self.allowedEventTypes = allowedEventTypes
        # It is not possible to create events that span more days than
        # maxEventLength.
        self.maxEventLength = maxEventLength
        # Various render modes exist. Default is the classical "month" view.
        # It can also be "timeline": in this case, on the x axis, we have one
        # column per day, and on the y axis, we have one row per calendar (this
        # one and others as specified in "others", see below).
        self.render = render
        # When displaying a given month for this agenda, one may want to
        # pre-compute, once for the whole month, some information that will then
        # be given as arg for other methods specified in subsequent parameters.
        # This mechanism exists for performance reasons, to avoid recomputing
        # this global information several times. If you specify a method in
        # p_preCompute, it will be called every time a given month is shown, and
        # will receive 2 args: the first day of the currently shown month (as a
        # DateTime instance) and the grid of all shown dates (as a result of
        # calling m_getGrid below). This grid may hold a little more than dates
        # of the current month. Subsequently, the return of your method will be
        # given as arg to other methods that you may specify as args of other
        # parameters of this Calendar class (see comments below).
        self.preCompute = preCompute
        # If a method is specified in parameter "others" below, it must accept a
        # single arg (the result of self.preCompute) and must return a list of
        # calendars whose events must be shown within this agenda. More
        # precisely, the method can return:
        # - a single Other instance (see at the top of this file);
        # - a list of Other instances;
        # - a list of lists of Other instances, when it has sense to group other
        #   calendars (the timeline rendering exploits this).
        self.others = others
        # When displaying a timeline calendar, a name is shown for every other
        # calendar. If "timelineName" is None (the default), this name will be
        # the title of the object where the other calendar is defined. Else, it
        # will be the result of the method specified in "timelineName". This
        # method must return a string and accepts those args:
        # - other     an Other instance;
        # - month     the currently shown month, as a string YYYY/mm
        self.timelineName = timelineName
        # When displaying a timeline calendar, the name of the current month is
        # shown in header in footer rows. If you want to customize this zone,
        # specify a method in the following attribute. It will receive, as args:
        # (1) an instance containing infos about the current month, having the
        #     following attributes:
        #     * first: a DateTime instance being the first day of the month;
        #     * month: the text representing the current month. The name of the
        #       month may be translated; it may contain XHTML formatting;
        # (2) the calendar's pre-computed data.
        # The method must modify the first arg's "month" attribute.
        self.timelineMonthName = timelineMonthName
        # One may want to add, day by day, custom information in the calendar.
        # When a method is given in p_additionalInfo, for every cell of the
        # month view, this method will be called with 2 args: the cell's date
        # and the result of self.preCompute. The method's result (a string that
        # can hold text or a chunk of XHTML) will be inserted in the cell.
        self.additionalInfo = additionalInfo
        # One may limit event encoding and viewing to some period of time,
        # via p_startDate and p_endDate. Those parameters, if given, must hold
        # methods accepting no arg and returning a DateTime instance. The
        # startDate and endDate will be converted to UTC at 00.00.
        self.startDate = startDate
        self.endDate = endDate
        # If a default date is specified, it must be a method accepting no arg
        # and returning a DateTime instance. As soon as the calendar is shown,
        # the month where this date is included will be shown. If not default
        # date is specified, it will be 'now' at the moment the calendar is
        # shown.
        self.defaultDate = defaultDate
        # "timeslots" are a way to define, within a single day, time ranges. It
        # must be a list of Timeslot instances (see above). If you define
        # timeslots, the first one must be the one representing the whole day
        # and must have id "main".
        if not timeslots: self.timeslots = [Timeslot('main')]
        else:
            self.timeslots = timeslots
            self.checkTimeslots()
        # "colors" must either be a dict {s_eventType:s_color} or a method
        # receiving 2 args: an event type and the pre-computed object, and
        # returning an HTML-compliant color for this type (or None if the type
        # must not be colored). Indeed, in a timeline, cells are too small to
        # display translated names for event types, so colors are used instead.
        self.colors = colors
        # When the above-defined attribute "colors" is in use, instead of simply
        # coloring the background of a cell in a timeline with that color, one
        # may define a gradient. It is useful if the event's timeslot doesn't
        # span the whole day: the gradient may represent the "partial" aspect of
        # the timeslot (with, for example, an end color being "transparent"). If
        # you define such gradients in the following attribute, every time a
        # cell will need to be colored, if the timeslot of the corresponding
        # event does not span the whole day, a gradient will be used instead of
        # a plain color. Attribute "gradient" hereafter must hold a dict (or a
        # method returning a dict) whose keys are timeslots (strings) and values
        # a Gradient instances.
        self.gradients = gradients or {}
        # For event types for which p_colors is None, must we still show them ?
        # If yes, they will be represented by a dot with a tooltip containing
        # the event name.
        self.showUncolored = showUncolored
        # In the timeline, the background color for columns can be defined in a
        # method you specify here. This method must accept the current date (as
        # a DateTime instance) as unique arg. If None, a default color scheme
        # is used (see Calendar.timelineBgColors). Every time your method
        # returns None, the default color scheme will apply.
        self.columnColors = columnColors
        # For a specific day, all event types may not be applicable. If this is
        # the case, one may specify here a method that defines, for a given day,
        # a sub-set of all event types. This method must accept 3 args:
        #  1. the day in question (as a DateTime instance);
        #  2. the list of all event types, which is a copy of the (possibly
        #     computed) self.eventTypes;
        #  3. the result of calling self.preCompute.
        # The method must modify the 2nd arg and remove from it potentially not
        # applicable events. This method can also return a message, that will be
        # shown to the user for explaining him why he can, for this day, only 
        # create events of a sub-set of the possible event types (or even no
        # event at all).
        self.applicableEvents = applicableEvents
        # In a timeline calendar, if you want to specify additional rows
        # representing totals, give in "totalRows" a list of Totals instances
        # (see above).
        if totalRows and (self.render != 'timeline'):
            raise Exception(Calendar.TOTALS_MISUSED)
        self.totalRows = totalRows or []
        # Similarly, you can specify additional columns in "totalCols"
        if totalCols and (self.render != 'timeline'):
            raise Exception(Calendar.TOTALS_MISUSED)
        self.totalCols = totalCols or []
        # A validation process can be associated to a Calendar event. It
        # consists in identifying validators and letting them "convert" event
        # types being wished to final, validated event types. If you want to
        # enable this, define a Validation instance (see the hereabove class)
        # in parameter "validation".
        self.validation = validation
        # "layers" define a stack of layers (as a list or tuple). Every layer
        # must be a Layer instance and represents a set of data that can be
        # shown or not on top of calendar data (currently, only for timelines).
        self.layers = self.formatLayers(layers)
        # If "layersSelector" is False, all layers with activeByDefault=True
        # will be shown but the selector allowing to (de)activate layers will
        # not be shown.
        self.layersSelector = layersSelector
        # Beyond permission-based security, p_editable may store a method whose
        # result may prevent the user to edit the field.
        self.editable = editable
        # May the user delete events in this calendar? If "delete" is a method,
        # it must accept an event type as single arg.
        self.delete = delete
        # Before deleting an event, if a method is specified in "beforeDelete",
        # it will be called with the date and timeslot as args. If the method
        # returns False, the deletion will not occur.
        self.beforeDelete = beforeDelete
        # You may specify PXs that will show specific information, respectively,
        # before and after the calendar.
        self.topPx = topPx
        self.bottomPx = bottomPx
        # "actions" is a list of Action instances allowing to define custom
        # actions to execute based on calendar data.
        self.actions = actions or ()
        # When there is at least one visible action, timeline cells can be
        # selected: this selection is then given as parameter to the triggered
        # action. If "selectableEmptyCells" is True, all cells are selectable.
        # Else, only cells whose content is not empty are selectable.
        self.selectableEmptyCells = selectableEmptyCells
        # "legend" can hold a Legend instance (see class above) that determines
        # legend's characteristcs on a timeline calendar.
        self.legend = legend or Legend()
        # "selectableMonths" determines, in a calendar monthly view, the number
        # of months in the past or in the future, relative to the currently
        # shown one, that will be accessible by simply selecting them in a list.
        self.selectableMonths = selectableMonths
        # The i18n label to use when the user creates a new event
        self.createEventLabel = createEventLabel
        # The name of a CSS class for the monthly view table. Several
        # space-separated names can be defined.
        self.style = style
        # When rendering a timeline, if p_strictMonths is True, only days of the
        # current month will be shown. Else, complete weeks will be shown,
        # potentially including some days from the previous and next months.
        if strictMonths and (self.render != 'timeline'):
            raise Exception(Calendar.STRICT_MONTHS_MISUSED)
        self.strictMonths = strictMonths
        # ~~~ Call the base constructor ~~~
        # The "validator" attribute, allowing field-specific validation, behaves
        # differently for the Calendar field. If specified, it must hold a
        # method that will be executed every time a user wants to create an
        # event (or series of events) in the calendar. This method must accept
        # those args:
        #  - date       the date of the event (as a DateTime instance);
        #  - eventType  the event type (one among p_eventTypes);
        #  - timeslot   the timeslot for the event (see param "timeslots"
        #               below);
        #  - span       the number of additional days on which the event will
        #               span (will be 0 if the user wants to create an event
        #               for a single day).
        # If validation succeeds (ie, the event creation can take place), the
        # method must return True (boolean). Else, it will be canceled and an
        # error message will be shown. If the method returns False (boolean), it
        # will be a standard error message. If the method returns a string, it
        # will be used as specific error message.
        Field.__init__(self, validator, (0,1), default, defaultOnEdit, show,
          renderable, page, group, layouts, move, False, True, None, None,
          False, None, readPermission, writePermission, width, height, None,
          colspan, master, masterValue, focus, False, mapping, generateLabel,
          label, None, None, None, None, True, False, view, cell, buttons, edit,
          xml, translations)

    def checkTimeslots(self):
        '''Checks whether self.timeslots defines correct timeslots'''
        # The first timeslot must be the global one, named 'main'
        if self.timeslots[0].id != 'main':
            raise Exception('The first timeslot must have id "main" and is ' \
                            'the one representing the whole day.')
        # Set the day parts for every timeslot
        count = len(self.timeslots) - 1 # Count the timeslots, main excepted
        for timeslot in self.timeslots:
            if timeslot.id == 'main': continue
            timeslot.dayPart = 1.0 / count

    def formatLayers(self, layers):
        '''Chain layers via attribute "previous"'''
        if not layers: return ()
        i = len(layers) - 1
        while i >= 1:
            layers[i].previous = layers[i-1]
            i -= 1
        return layers

    def log(self, o, msg, date=None):
        '''Logs m_msg, field-specifically prefixed.'''
        prefix = '%d:%s' % (o.iid, self.name)
        if date: prefix += '@%s' % date.strftime('%Y/%m/%d')
        o.log('%s: %s' % (prefix, msg))

    def getPreComputedInfo(self, o, monthDayOne, grid):
        '''Returns the result of calling self.preComputed, or None if no such
           method exists.'''
        if self.preCompute:
            return self.preCompute(o, monthDayOne, grid)

    def getMonthInfo(self, first, tool):
        '''Returns an Object instance representing information about the month
           whose p_first day (DateTime instance) is given.'''
        text = tool.formatDate(first, '%MT %Y', withHour=False)
        return O(id=first.strftime('%Y/%m'), text=text)

    def getSurroundingMonths(self, first, tool, startDate, endDate):
        '''Gets the months surrounding the one whose p_first day is given'''
        res = O(next=None, previous=None, all=[self.getMonthInfo(first, tool)])
        # Calibrate p_startDate and p_endDate to the first and last days of
        # their month. Indeed, we are interested in months, not days, but we use
        # arithmetic on days.
        if startDate: startDate = DateTime(startDate.strftime('%Y/%m/01 UTC'))
        if endDate: endDate = getLastDayOfMonth(endDate)
        # Get the x months after p_first
        mfirst = first
        i = 1
        while i <= self.selectableMonths:
            # Get the first day of the next month
            mfirst = DateTime((mfirst + 33).strftime('%Y/%m/01 UTC'))
            # Stop if we are above self.endDate
            if endDate and (mfirst > endDate):
                break
            info = self.getMonthInfo(mfirst, tool)
            res.all.append(info)
            if i == 1:
                res.next = info
            i += 1
        # Get the x months before p_first
        mfirst = first
        i = 1
        while i <= self.selectableMonths:
            # Get the first day of the previous month
            mfirst = DateTime((mfirst - 2).strftime('%Y/%m/01 UTC'))
            # Stop if we are below self.startDate
            if startDate and (mfirst < startDate):
                break
            info = self.getMonthInfo(mfirst, tool)
            res.all.insert(0, info)
            if i == 1:
                res.previous = info
            i += 1
        return res

    weekDays = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
    def getNamesOfDays(self, _):
        '''Returns the translated names of all week days, short and long
           versions.'''
        r = {}
        for day in self.weekDays:
            r[day] = O(name=_('day_%s' % day), short=_('day_%s_short' % day))
        return r

    def getGrid(self, month, render):
        '''Creates a list of DateTime objects representing the calendar grid to
           render for a given p_month. If p_render is "month", it is a list of
           lists (one sub-list for every week; indeed, every week is rendered as
           a row). If p_render is "timeline", the result is a linear list of
           DateTime instances.'''
        # Month is a string "YYYY/mm"
        currentDay = DateTime('%s/01 UTC' % month)
        currentMonth = currentDay.month()
        isLinear = render == 'timeline'
        r = [] if isLinear else [[]]
        dayOneNb = currentDay.dow() or 7 # This way, Sunday is 7 and not 0
        strictMonths = self.strictMonths
        if (dayOneNb != 1) and not strictMonths:
            # If I write "previousDate = DateTime(currentDay)", the date is
            # converted from UTC to GMT
            previousDate = DateTime('%s/01 UTC' % month)
            # If the 1st day of the month is not a Monday, integrate the last
            # days of the previous month.
            for i in range(1, dayOneNb):
                previousDate -= 1
                target = r if isLinear else r[0]
                target.insert(0, previousDate)
        finished = False
        while not finished:
            # Insert currentDay in the result
            if isLinear:
                r.append(currentDay)
            else:
                if len(r[-1]) == 7:
                    # Create a new row
                    r.append([currentDay])
                else:
                    r[-1].append(currentDay)
            currentDay += 1
            if currentDay.month() != currentMonth:
                finished = True
        # Complete, if needed, the last row with the first days of the next
        # month. Indeed, we may need to have a complete week, ending with a
        # Sunday.
        if not strictMonths:
            target = r if isLinear else r[-1]
            while target[-1].dow() != 0:
                target.append(currentDay)
                currentDay += 1
        return r

    def getOthers(self, o, preComputed):
        '''Returns the list of other calendars whose events must also be shown
           on this calendar.'''
        r = None
        if self.others:
            r = self.others(o, preComputed)
            if r:
                # Ensure we have a list of lists
                if isinstance(r, Other): r = [r]
                if isinstance(r[0], Other): r = [r]
        return r if r is not None else [[]]

    def getOthersSep(self, colspan):
        '''Produces the separator between groups of other calendars'''
        return '<tr style="height: 8px"><th colspan="%s" style="background-' \
               'color: grey"></th></tr>' % colspan

    def getTimelineName(self, o, other, month, grid):
        '''Returns the name of some p_other calendar as must be shown in a
           timeline.'''
        if not self.timelineName:
            return '<a href="%s?month=%s">%s</a>' % \
                   (other.o.url, month, other.o.title)
        return self.timelineName(o, other, month, grid)

    def getCellSelectParams(self, date, content):
        '''For a timeline cell, gets the parameters allowing to (de)select it,
           as a tuple ("onclick", "class") to be used as HTML attributes for
           the cell (td tag).'''
        if not content and not self.selectableEmptyCells: return '', ''
        return ' onclick="onCell(this,\'%s\')"' % date.strftime('%Y%m%d'), \
               ' class="clickable"'

    def getColorFor(self, o, eventType, preCompute):
        '''Gets the background color for a cell containing some p_eventType'''
        colors = self.colors
        if colors is None:
            r = None
        elif isinstance(colors, dict):
            r = colors.get(eventType)
        else: # A method
            r = colors(o, eventType, preCompute)
        return r

    def buildTimelineCell(self, date, style, title, content, actions,
                          disableSelect=False):
        '''Called by m_getTimelineCell to build the final XHTML "td" tag
           representing the timeline cell.'''
        style = ' style="%s"' % style if style else ''
        title = ' title="%s"' % title if title else ''
        content = content or ''
        if disableSelect or not actions:
            onClick = css = ''
        else:
            onClick, css = self.getCellSelectParams(date, content)
        return '<td%s%s%s%s>%s</td>' % (onClick, css, style, title, content)

    def getTimelineCell(self, c, o, date, actions):
        '''Gets the content of a cell in a timeline calendar'''
        # Unwrap some variables from the PX context
        date = c.date; other = c.other; render = 'timeline'; cache=c.preComputed
        # Get the events defined at that day, in the current calendar
        events = self.getOtherEventsAt(date, other, c.allEventNames, render,
                                       cache, c.gradients)
        # Compute the cell attributes
        style = title = content = None
        # In priority, get info from layers
        if c.activeLayers:
            # Walk layers in reverse order
            layer = self.layers[-1]
            info = layer.getCellInfo(o, c.activeLayers, date,
                                     other, events, cache)
            if info:
                style, title, content = info
                if not layer.merge:
                    # Exclusively display the layer info, ignoring the base info
                    return self.buildTimelineCell(date, style, title,
                                                  content, actions)
        # Define the cell's style
        style = style or self.getCellStyle(o, date, render, events)
        # If a timeline cell hides more than one event, put event names in the
        # "title" attribute.
        if not title and len(events) > 1:
            title = ', '.join(['%s (%s)' % (\
              c.allEventNames.get(e.event.eventType) or '?', e.event.timeslot) \
              for e in events])
        # Define its content
        disableSelect = False
        if not content:
            if events and c.mayValidate:
                # If at least one event from p_events is in the validation
                # schema, propose a unique checkbox, that will allow to validate
                # or not all validable events at p_date.
                for info in events:
                    if info.event.eventType in other.field.validation.schema:
                        cbId = '%d_%s_%s' % (other.o.iid, other.field.name,
                                             date.strftime('%Y%m%d'))
                        totalRows = 'true' if self.totalRows else 'false'
                        totalCols = 'true' if self.totalCols else 'false'
                        content = '<input type="checkbox" checked="checked" ' \
                          'class="smallbox" id="%s" onclick="onCheckCbCell(' \
                          'this,\'%s\',%s,%s)"/>' % \
                          (cbId, c.hook, totalRows, totalCols)
                        # Disable selection if a validation checkbox is there
                        disableSelect = True
                        break
            elif len(events) == 1:
                # A single event: if not colored, show a symbol. When there are
                # multiple events, a background image is already shown (see the
                # "style" attribute), so do not show any additional info.
                content = events[0].symbol
        return self.buildTimelineCell(date, style, title, content, actions,
                                      disableSelect=disableSelect)

    def getTimelineMonths(self, grid, o, preComputed):
        '''Given the p_grid of dates, this method returns the list of
           corresponding months.'''
        r = []
        for date in grid:
            if not r:
                # Get the month correspoding to the first day in the grid
                m = O(month=date.aMonth(), colspan=1,
                      year=date.year(), first=date)
                r.append(m)
            else:
                # Augment current month' colspan or create a new one
                current = r[-1]
                if date.aMonth() == current.month:
                    current.colspan += 1
                else:
                    m = O(month=date.aMonth(), colspan=1,
                          year=date.year(), first=date)
                    r.append(m)
        # Replace month short names by translated names whose format may vary
        # according to colspan (a higher colspan allow to produce a longer month
        # name).
        for m in r:
            text = '%s %d' % (o.translate('month_%s' % m.month), m.year)
            if m.colspan < 6:
                # Short version: a single letter with an abbr
                m.month = '<abbr title="%s">%s</abbr>' % (text, text[0])
            else:
                m.month = text
            # Allow to customize the name of the month when required
            if self.timelineMonthName:
                self.timelineMonthName(o, m, preComputed)
        return r

    def getAdditionalInfoAt(self, o, date, preComputed):
        '''If the user has specified a method in self.additionalInfo, we call
           it for displaying this additional info in the calendar, at some
           p_date.'''
        info = self.additionalInfo
        return info(o, date, preComputed) if info else None

    def getEventTypes(self, o):
        '''Returns the (dynamic or static) event types as defined in
           self.eventTypes.'''
        types = self.eventTypes
        return types(o) if callable(types) else types

    def getAllowedEventTypes(self, o, eventTypes):
        '''Gets the allowed events types for the currently logged user'''
        allowed = self.allowedEventTypes
        return eventTypes if not allowed else allowed(o, eventTypes)

    def getGradients(self, o):
        '''Gets the gradients possibly defined in addition to p_self.colors'''
        gradients = self.gradients
        return gradients(o) if callable(gradients) else gradients

    def dayIsFull(self, date, events):
        '''In the calendar full at p_date? Defined events at this p_date are in
           p_events. We check here if the main timeslot is used or if all
           others are used.'''
        if not events: return
        for e in events:
            if e.timeslot == 'main': return True
        return len(events) == len(self.timeslots) - 1

    def dateInRange(self, date, startDate, endDate):
        '''Is p_date within the range (possibly) defined for this calendar by
           p_startDate and p_endDate ?'''
        tooEarly = startDate and (date < startDate)
        tooLate = endDate and not tooEarly and (date > endDate)
        return not tooEarly and not tooLate

    def getApplicableEventTypesAt(self, o, date, eventTypes, preComputed,
                                  forBrowser=False):
        '''Returns the event types that are applicable at a given p_date'''
        # More precisely, it returns an object with 2 attributes:
        # * "events" is the list of applicable event types;
        # * "message", not empty if some event types are not applicable,
        #              contains a message explaining those event types are
        #              not applicable.
        if not eventTypes: return # There may be no event type at all
        if not self.applicableEvents:
            # Keep p_eventTypes as is
            message = None
        else:
            eventTypes = eventTypes[:]
            message = self.applicableEvents(o, date, eventTypes, preComputed)
        r = O(eventTypes=eventTypes, message=message)
        if forBrowser:
            r.eventTypes = ','.join(r.eventTypes)
            if not r.message: r.message = ''
        return r

    def getAllSlots(self, o):
        '''Returns tuple (name, slot) for all defined timeslots. Position the
           default one as the first one in the list.'''
        r = []
        for slot in self.timeslots:
            name = o.translate('timeslot_main') if slot.id == 'main' \
                                                else slot.name
            if slot.default:
                r.insert(0, (name, slot))
            else:
                r.append((name, slot))
        return r

    def getFreeSlotsAt(self, date, events, slotIds, slotIdsStr,
                       forBrowser=False):
        '''Gets the free timeslots in this calendar for some p_date. As a
           precondition, we know that the day is not full (so timeslot "main"
           cannot be taken). p_events are those already defined at p_date.
           p_slotIds is the precomputed list of timeslot ids.'''
        if not events: return slotIdsStr if forBrowser else slotIds
        # Remove any taken slot
        r = slotIds[:]
        r.remove('main') # "main" cannot be chosen: p_events is not empty
        for event in events: r.remove(event.timeslot)
        # Return the result
        return ','.join(r) if forBrowser else r

    def getTimeslot(self, id):
        '''Get the timeslot corresponding to p_id'''
        for slot in self.timeslots:
            if slot.id == id: return slot

    def getEventsAt(self, o, date):
        '''Returns the list of events that exist at some p_date (=day). p_date
           can be:
           * a DateTime instance;
           * a tuple (i_year, i_month, i_day);
           * a string YYYYmmdd.
        '''
        if self.name not in o.values: return
        years = getattr(o, self.name)
        if not years: return
        # Get year, month and name from p_date
        if isinstance(date, tuple):
            year, month, day = date
        elif isinstance(date, str):
            year, month, day = int(date[:4]), int(date[4:6]), int(date[6:8])
        else:
            year, month, day = date.year(), date.month(), date.day()
        # Dig into the oobtree
        if year not in years: return
        months = years[year]
        if month not in months: return
        days = months[month]
        if day not in days: return
        return days[day]

    def getEventTypeAt(self, o, date):
        '''Returns the event type of the first event defined at p_day, or None
           if unspecified.'''
        events = self.getEventsAt(o, date)
        return events[0].eventType if events else None

    def standardizeDateRange(self, range):
        '''p_range can have various formats (see m_walkEvents below). This
           method standardizes the date range as a 6-tuple
           (startYear, startMonth, startDay, endYear, endMonth, endDay).'''
        if not range: return
        if isinstance(range, int):
            # p_range represents a year
            return (range, 1, 1, range, 12, 31)
        elif isinstance(range[0], int):
            # p_range represents a month
            year, month = range
            return (year, month, 1, year, month, 31)
        else:
            # p_range is a tuple (start, end) of DateTime instances
            start, end = range
            return (start.year(), start.month(), start.day(),
                    end.year(),   end.month(),   end.day())

    def walkEvents(self, o, callback, dateRange=None):
        '''Walks, on p_o, the calendar value in chronological order for this
           field and calls p_callback for every day containing events. The
           callback must accept 3 args: p_o, the current day (as a DateTime
           instance) and the list of events at that day (the database-stored
           PersistentList instance). If the callback returns True, we stop the
           walk.

           If p_dateRange is specified, it limits the walk to this range. It
           can be:
           * an integer, representing a year;
           * a tuple of integers (year, month) representing a given month
             (first month is numbered 1);
           * a tuple (start, end) of DateTime instances.
        '''
        if self.name not in o.values: return
        yearsDict = getattr(o, self.name)
        if not yearsDict: return
        # Standardize date range
        if dateRange:
            startYear, startMonth, startDay, endYear, endMonth, endDay = \
              self.standardizeDateRange(dateRange)
        # Browse years
        years = list(yearsDict.keys())
        years.sort()
        for year in years:
            # Ignore this year if out of range
            if dateRange:
                if (year < startYear) or (year > endYear): continue
                isStartYear = year == startYear
                isEndYear = year == endYear
            # Browse this year's months
            monthsDict = yearsDict[year]
            if not monthsDict: continue
            months = list(monthsDict.keys())
            months.sort()
            for month in months:
                # Ignore this month if out of range
                if dateRange:
                    if (isStartYear and (month < startMonth)) or \
                       (isEndYear and (month > endMonth)): continue
                    isStartMonth = isStartYear and (month == startMonth)
                    isEndMonth = isEndYear and (month == endMonth)
                # Browse this month's days
                daysDict = monthsDict[month]
                if not daysDict: continue
                days = list(daysDict.keys())
                days.sort()
                for day in days:
                    # Ignore this day if out of range
                    if dateRange:
                        if (isStartMonth and (day < startDay)) or \
                           (isEndMonth and (day > endDay)): continue
                    date = DateTime('%d/%d/%d UTC' % (year, month, day))
                    stop = callback(o, date, daysDict[day])
                    if stop: return

    def getEventsByType(self, o, eventType, minDate=None, maxDate=None,
                        sorted=True, groupSpanned=False):
        '''Returns all the events of a given p_eventType. If p_eventType is
           None, it returns events of all types. p_eventType can also be a
           list or tuple. The return value is a list of 2-tuples whose 1st elem
           is a DateTime instance and whose 2nd elem is the event.

           If p_sorted is True, the list is sorted in chronological order. Else,
           the order is random, but the result is computed faster.

           If p_minDate and/or p_maxDate is/are specified, it restricts the
           search interval accordingly.

           If p_groupSpanned is True, events spanned on several days are
           grouped into a single event. In this case, tuples in the result
           are 3-tuples: (DateTime_startDate, DateTime_endDate, event).
        '''
        # Prevent wrong combinations of parameters
        if groupSpanned and not sorted:
            raise Exception(Calendar.UNSORTED_EVENTS)
        r = []
        if self.name not in o.values: return r
        # Compute "min" and "max" tuples
        if minDate:
            minYear = minDate.year()
            minMonth = (minYear, minDate.month())
            minDay = (minYear, minDate.month(), minDate.day())
        if maxDate:
            maxYear = maxDate.year()
            maxMonth = (maxYear, maxDate.month())
            maxDay = (maxYear, maxDate.month(), maxDate.day())
        # Browse years
        years = getattr(o, self.name)
        for year in years.keys():
            # Don't take this year into account if outside interval
            if minDate and (year < minYear): continue
            if maxDate and (year > maxYear): continue
            months = years[year]
            # Browse this year's months
            for month in months.keys():
                # Don't take this month into account if outside interval
                thisMonth = (year, month)
                if minDate and (thisMonth < minMonth): continue
                if maxDate and (thisMonth > maxMonth): continue
                days = months[month]
                # Browse this month's days
                for day in days.keys():
                    # Don't take this day into account if outside interval
                    thisDay = (year, month, day)
                    if minDate and (thisDay < minDay): continue
                    if maxDate and (thisDay > maxDay): continue
                    events = days[day]
                    # Browse this day's events
                    for event in events:
                        # Filter unwanted events
                        if eventType:
                            if isinstance(eventType, str):
                                keepIt = (event.eventType == eventType)
                            else:
                                keepIt = (event.eventType in eventType)
                            if not keepIt: continue
                        # We have found a event
                        date = DateTime('%d/%d/%d UTC' % (year, month, day))
                        if groupSpanned:
                            singleRes = [date, None, event]
                        else:
                            singleRes = (date, event)
                        r.append(singleRes)
        # Sort the result if required
        if sorted: r.sort(key=lambda x: x[0])
        # Group events spanned on several days if required
        if groupSpanned:
            # Browse events in reverse order and merge them when appropriate
            i = len(r) - 1
            while i > 0:
                currentDate = r[i][0]
                lastDate = r[i][1]
                previousDate = r[i-1][0]
                currentType = r[i][2].eventType
                previousType = r[i-1][2].eventType
                if (previousDate == (currentDate-1)) and \
                   (previousType == currentType):
                    # A merge is needed
                    del r[i]
                    r[i-1][1] = lastDate or currentDate
                i -= 1
        return r

    def hasEventsAt(self, o, date, events):
        '''Returns True if, at p_date, events are exactly of the same type as
           p_events.'''
        if not events: return
        others = self.getEventsAt(o, date)
        if not others: return
        if len(events) != len(others): return
        i = 0
        while i < len(events):
            if not events[i].sameAs(others[i]): return
            i += 1
        return True

    def getOtherEventsAt(self, date, others, eventNames, render, preComputed,
                         gradients=None):
        '''Gets events that are defined in p_others at some p_date. If p_single
           is True, p_others does not contain the list of all other calendars,
           but information about a single calendar.'''
        r = []
        isTimeline = render == 'timeline'
        if isinstance(others, Other):
            others.getEventsInfoAt(r, self, date, eventNames, isTimeline,
                                   preComputed, gradients)
        else:
            for other in utils.IterSub(others):
                other.getEventsInfoAt(r, self, date, eventNames, isTimeline,
                                      preComputed, gradients)
        return r

    def getEventName(self, o, eventType):
        '''Gets the name of the event corresponding to p_eventType as it must
           appear to the user.'''
        if self.eventNameMethod:
            return self.eventNameMethod(o, eventType)
        else:
            return o.translate('%s_event_%s' % (self.labelId, eventType))

    def getAllEvents(self, o, eventTypes, others):
        '''Computes:
           * the list of all event types (from this calendar and p_others);
           * a dict of event names, keyed by event types, for all events
             in this calendar and p_others).'''
        r = [[], {}]
        if eventTypes:
            for et in eventTypes:
                r[0].append(et)
                r[1][et] = self.getEventName(o, et)
        if not others: return r
        for other in utils.IterSub(others):
            eventTypes = other.getEventTypes()
            if eventTypes:
                for et in eventTypes:
                    if et not in r[1]:
                        r[0].append(et)
                        r[1][et] = other.field.getEventName(other.o, et)
        return r

    def getStartDate(self, o):
        '''Get the start date for this calendar if defined'''
        if self.startDate:
            d = self.startDate(o)
            # Return the start date without hour, in UTC
            return DateTime('%d/%d/%d UTC' % (d.year(), d.month(), d.day()))

    def getEndDate(self, o):
        '''Get the end date for this calendar if defined'''
        if self.endDate:
            d = self.endDate(o)
            # Return the end date without hour, in UTC
            return DateTime('%d/%d/%d UTC' % (d.year(), d.month(), d.day()))

    def getDefaultDate(self, o):
        '''Get the default date that must appear as soon as the calendar is
           shown.'''
        default = self.defaultDate
        return default(o) if default else DateTime() # Now

    def checkCreateEvent(self, o, eventType, timeslot, events):
        '''Checks if one may create an event of p_eventType in p_timeslot.
           Events already defined at p_date are in p_events. If the creation is
           not possible, an error message is returned.'''
        # The following errors should not occur if we have a normal user behind
        # the ui.
        for e in events:
            if e.timeslot == timeslot: return Calendar.TIMESLOT_USED
            elif e.timeslot == 'main': return Calendar.DAY_FULL
        if events and (timeslot == 'main'): return Calendar.DAY_FULL
        # Get the Timeslot and check if, at this timeslot, it is allowed to
        # create an event of p_eventType.
        for slot in self.timeslots:
            if slot.id == timeslot:
                # I have the timeslot
                if not slot.allows(eventType):
                    _ = o.translate
                    return _('timeslot_misfit', mapping={'slot': timeslot})

    def mergeEvent(self, eventType, timeslot, events):
        '''If, after adding an event of p_eventType, all timeslots are used with
           events of the same type, we can merge them and create a single event
           of this type in the main timeslot.'''
        # When defining an event in the main timeslot, no merge is needed
        if timeslot == 'main': return
        # Merge is required when all non-main timeslots are used by events of
        # the same type.
        if len(events) != (len(self.timeslots)-2): return
        for event in events:
            if event.eventType != eventType: return
        # If we are here, we must merge all events
        del events[:]
        events.append(Event(eventType))
        return True

    def createEvent(self, o, date, eventType, timeslot='main', eventSpan=None,
                    handleEventSpan=True, log=True, deleteFirst=False):
        '''Create a new event of some p_eventType in the calendar on p_o, at
           some p_date (day) in a given p_timeslot. If p_handleEventSpan is
           True, we will use p_eventSpan to create the same event for successive
           days. If p_deleteFirst is True, any existing event found at p_date
           will be deleted before creating the new event.'''
        req = o.req
        # Get values from parameters
        eventType = eventType or req.eventType
        # Split the p_date into separate parts
        year, month, day = date.year(), date.month(), date.day()
        # Create, on p_o, the calendar data structure if it doesn't exist yet
        yearsDict = o.values.get(self.name)
        if yearsDict is None:
            # 1st level: create a IOBTree whose keys are years
            yearsDict = IOBTree()
            setattr(o, self.name, yearsDict)
        # Get the sub-dict storing months for a given year
        if year in yearsDict:
            monthsDict = yearsDict[year]
        else:
            yearsDict[year] = monthsDict = IOBTree()
        # Get the sub-dict storing days of a given month
        if month in monthsDict:
            daysDict = monthsDict[month]
        else:
            monthsDict[month] = daysDict = IOBTree()
        # Get the list of events for a given day
        if day in daysDict:
            events = daysDict[day]
        else:
            daysDict[day] = events = PersistentList()
        # Delete any event if required
        if events and deleteFirst:
            del events[:]
        # Return an error if the creation cannot occur
        error = self.checkCreateEvent(o, eventType, timeslot, events)
        if error: return error
        # Merge this event with others when relevant
        merged = self.mergeEvent(eventType, timeslot, events)
        if not merged:
            # Create and store the event
            events.append(Event(eventType, timeslot))
            # Sort events in the order of timeslots
            if len(events) > 1:
                timeslots = [slot.id for slot in self.timeslots]
                events.data.sort(key=lambda e: timeslots.index(e.timeslot))
                events._p_changed = 1
        # Span the event on the successive days if required
        suffix = ''
        if handleEventSpan and eventSpan:
            for i in range(eventSpan):
                date = date + 1
                self.createEvent(o, date, eventType, timeslot,
                                 handleEventSpan=False)
                suffix = ', span+%d' % eventSpan
        if handleEventSpan and log:
            msg = 'added %s, slot %s%s' % (eventType, timeslot, suffix)
            self.log(o, msg, date)

    def mayDelete(self, o, events):
        '''May the user delete p_events?'''
        delete = self.delete
        if not delete: return
        return delete(o, events[0].eventType) if callable(delete) else True

    def mayEdit(self, o, raiseError=False):
        '''May the user edit calendar events ?'''
        # Check the security-based condition
        if not o.guard.mayEdit(o, self.writePermission, raiseError=raiseError):
            return
        # Check the field-specific condition
        return self.getAttribute(o, 'editable')

    def deleteEvent(self, o, date, timeslot, handleEventSpan=True, log=True,
                    executeMethods=True):
        '''Deletes an event. If t_timeslot is "main", it deletes all events at
           p_date, be there a single event on the main timeslot or several
           events on other timeslots. Else, it only deletes the event at
           p_timeslot. If p_handleEventSpan is True, we will use
           req.deleteNext to delete successive events, too.'''
        events = self.getEventsAt(o, date)
        if not events: return
        # Execute "beforeDelete"
        if executeMethods and self.beforeDelete:
            r = self.beforeDelete(o, date, timeslot)
            # Abort event deletion when required
            if r is False: return
        daysDict = getattr(o, self.name)[date.year()][date.month()]
        count = len(events)
        eNames = ', '.join([e.getName(o, self, xhtml=False) for e in events])
        if timeslot == 'main':
            # Delete all events; delete them also in the following days when
            # relevant.
            del daysDict[date.day()]
            req = o.req
            suffix = ''
            if handleEventSpan and (req.deleteNext == 'True'):
                nbOfDays = 0
                while True:
                    date = date + 1
                    if self.hasEventsAt(o, date, events):
                        self.deleteEvent(o, date, timeslot,
                                    handleEventSpan=False, executeMethods=False)
                        nbOfDays += 1
                    else:
                        break
                if nbOfDays: suffix = ', span+%d' % nbOfDays
            if handleEventSpan and log:
                msg = '%s deleted (%d)%s.' % (eNames, count, suffix)
                self.log(o, msg, date)
        else:
            # Delete the event at p_timeslot
            i = len(events) - 1
            while i >= 0:
                if events[i].timeslot == timeslot:
                    msg = '%s deleted at slot %s.' % \
                          (events[i].getName(o, self, xhtml=False), timeslot)
                    del events[i]
                    if log: self.log(o, msg, date)
                    break
                i -= 1

    def validate(self, o, date, eventType, timeslot, span=0):
        '''The validation process for a calendar is a bit different from the
           standard one, that checks a "complete" request value. Here, we only
           check the validity of some insertion of events within the
           calendar.'''
        if not self.validator: return
        r = self.validator(o, date, eventType, timeslot, span)
        if isinstance(r, str):
            # Validation failed, and we have the error message in "r"
            return r
        # Return a standard message if the validation fails without producing a
        # specific message.
        return r or o.translate('field_invalid')

    traverse['process'] = 'perm:write'
    def process(self, o):
        '''Processes an action coming from the calendar widget, ie, the creation
           or deletion of a calendar event.'''
        # Refined security check
        self.mayEdit(o, raiseError=True)
        req = o.req
        action = req.actionType
        # Get the date and timeslot for this action
        date = DateTime(req.day)
        eventType = req.eventType
        timeslot = req.timeslot or 'main'
        eventSpan = req.eventSpan or 0
        eventSpan = min(int(eventSpan), self.maxEventLength)
        if action == 'createEvent':
            # Trigger validation
            valid = self.validate(o, date, eventType, timeslot, eventSpan)
            if isinstance(valid, str): return valid
            return self.createEvent(o, date, eventType, timeslot, eventSpan)
        elif action == 'deleteEvent':
            return self.deleteEvent(o, date, timeslot)

    def getColumnStyle(self, o, date, render, today):
        '''What style(s) must apply to the table column representing p_date
           in the calendar? For timelines only.'''
        if render != 'timeline': return ''
        # Cells representing specific days must have a specific background color
        r = ''
        day = date.aDay()
        # Do we have a custom color scheme where to get a color ?
        color = None
        if self.columnColors:
            color = self.columnColors(o, date)
        if not color and (day in Calendar.timelineBgColors):
            color = Calendar.timelineBgColors[day]
        if color: r = 'background-color: %s' % color
        return r

    def getCellStyle(self, o, date, render, events):
        '''Gets the cell style to apply to the cell corresponding to p_date'''
        if render != 'timeline': return # Currently, for timelines only
        if not events: return
        elif len(events) > 1:
            # Return a special background indicating that several events are
            # hidden behing this cell.
            return 'background-image: url(%s/static/appy/angled.png)' % o.siteUrl
        else:
            event = events[0]
            if event.bgColor:
                return event.gradient.getStyle(event.bgColor) if event.gradient\
                       else 'background-color:%s' % event.bgColor

    def getCellClass(self, o, date, render, today):
        '''What CSS class(es) must apply to the table cell representing p_date
           in the calendar?'''
        if render != 'month': return '' # Currently, for month rendering only
        r = []
        # We must distinguish between past and future dates
        r.append('odd' if date < today else 'even')
        # Week-end days must have a specific style
        if date.aDay() in ('Sat', 'Sun'): r.append('cellWE')
        return ' '.join(r)

    def splitList(self, l, sub): return utils.splitList(l, sub)

    def mayValidate(self, o):
        '''May the currently logged user validate wish events ?'''
        valid = self.validation
        return valid.method(o) if valid else None

    def getAjaxData(self, hook, o, **params):
        '''Initializes an AjaxData object on the DOM node corresponding to
           this calendar field.'''
        # If the calendar is used as mode for a search, carry request keys
        # allowing to identify this search.
        req = o.req
        if req.search:
            parent = ",'searchResults'"
            params['resultMode'] = 'calendar'
        else:
            parent = ''
        params = sutils.getStringFrom(params)
        return "new AjaxData('%s/%s/view','POST',%s,'%s'%s)" % \
               (o.url, self.name, params, hook, parent)

    def getAjaxDataTotals(self, o, type, hook):
        '''Initializes an AjaxData object on the DOM node corresponding to
           the zone containing the total rows/cols (depending on p_type) in a
           timeline calendar.'''
        suffix = 'trs' if type == 'rows' else 'tcs'
        return "new AjaxData('%s/%s/pxTotalsFromAjax','GET',{},'%s_%s','%s')" %\
               (o.url, self.name, hook, suffix, hook)

    traverse['validateEvents'] = 'perm:write'
    def validateEvents(self, o):
        '''Validate or discard events from the request'''
        return self.validation.do(o, self)

    def getValidationCheckboxesStatus(self, req):
        '''Gets the status of the validation checkboxes from the request'''
        r = {}
        for status, value in Calendar.validCbStatuses.items():
            ids = req[status]
            if ids:
                for id in ids.split(','): r[id] = value
        return r

    def computeTotals(self, totalType, o, grid, others, preComputed):
        '''Compute the totals for every column (p_totalType == 'row') or row
           (p_totalType == "col").'''
        allTotals = getattr(self, 'total%ss' % totalType.capitalize())
        if not allTotals: return
        # Count other calendars and dates in the grid
        othersCount = 0
        for group in others: othersCount += len(group)
        datesCount = len(grid)
        isRow = totalType == 'row'
        # Initialise, for every (row or col) totals, Total instances
        totalCount = isRow and datesCount or othersCount
        lastCount = isRow and othersCount or datesCount
        r = {}
        for totals in allTotals:
            r[totals.name]= [Total(totals.initValue) for i in range(totalCount)]
        # Get the status of validation checkboxes
        status = self.getValidationCheckboxesStatus(o.req)
        # Walk every date within every calendar
        indexes = {'i': -1, 'j': -1}
        ii = isRow and 'i' or 'j'
        jj = isRow and 'j' or 'i'
        for other in utils.IterSub(others):
            indexes['i'] += 1
            indexes['j'] = -1
            for date in grid:
                indexes['j'] += 1
                # Get the events in this other calendar at this date
                events = other.field.getEventsAt(other.o, date)
                # From info @this date, update the total for every totals
                last = indexes[ii] == lastCount - 1
                # Get the status of the validation checkbox that is possibly
                # present at this date for this calendar
                checked = None
                cbId = '%d_%s_%s' % (other.o.iid, other.field.name,
                                     date.strftime('%Y%m%d'))
                if cbId in status: checked = status[cbId]
                # Update the Total instance for every totals at this date
                for totals in allTotals:
                    total = r[totals.name][indexes[jj]]
                    totals.onCell(o, date, other, events, total, last,
                                  checked, preComputed)
        return r

    def getActiveLayers(self, req):
        '''Gets the layers that are currently active'''
        if 'activeLayers' in req:
            # Get them from the request
            layers = req.activeLayers or ()
            r = layers if not layers else layers.split(',')
        else:
            # Get the layers that are active by default
            r = [layer.name for layer in self.layers if layer.activeByDefault]
        return r

    def getVisibleActions(self, o, dayOne):
        '''Return the visible actions among self.actions'''
        r = []
        for action in self.actions:
            show = action.show
            show = show(o, dayOne) if callable(show) else show
            if show: r.append(action)
        return r

    def onExecuteAction(self, o):
        '''An action has been triggered from the ui'''
        # Find the action to execute
        req = o.req
        name = req.actionName
        monthDayOne = DateTime('%s/01' % req.month)
        action = None
        for act in self.getVisibleActions(o, monthDayOne):
            if act.name == name:
                action = act
                break
        if not action: raise Exception(Calendar.ACTION_NOT_FOUND % name)
        # Get the selected cells
        selected = []
        tool = o.tool
        sel = req.selected
        if sel:
            for elems in sel.split(','):
                id, date = elems.split('_')
                # Get the calendar object from "id"
                calendarObj = tool.getObject(id)
                # Get a DateTime instance from "date"
                calendarDate = DateTime('%s/%s/%s UTC' % \
                                        (date[:4], date[4:6], date[6:]))
                selected.append((calendarObj, calendarDate))
        # Execute the action
        return action.action(o, selected, req.comment)

    def getXmlValue(self, o, value):
        '''Not implemented yet'''
        return

    def store(self, o, value):
        '''Stores this complete p_value on p_o'''
        if not self.persist or value is None: return
        # Data can be a IOBTree
        if isinstance(value, IOBTree):
            super().store(o, value)
            return
        # Data can also be a standard dict. It is the case, for example, for
        # calendar data imported from a distant site.
        for year, sub1 in value.items():
            if not sub1: continue
            for month, sub2 in sub1.items():
                if not sub2: continue
                for day, events in sub2.items():
                    if not events: continue
                    date = DateTime('%d/%d/%d' % (year, month, day))
                    for event in events:
                        self.createEvent(o, date, event.eventType,
                                         timeslot=event.timeslot,
                                         handleEventSpan=False, log=False)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
