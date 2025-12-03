#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.px import Px
from appy.model.base import Base
from appy.model.utils import Object as O

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from DateTime import DateTime
from persistent import Persistent

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class EventData(Persistent):
    '''Base class used to define objects that will be stored in the "data"
       attribute of a calendar event, being itself an istance of class
       appy.model.field.calendar.Event.'''

    # With a Appy calendar, there are several possibilities regarding the data
    # model to use when storing events. Basically, at every day, a calendar
    # stores a list of events, each one being an instance of class appy.model.
    # calendar.event.Event. For every event, stored attributes are, essentially,
    # the event "type" and slot. The list of possible types and slots for a
    # particular Appy calendar must be defined in, respectively, attributes
    # Calendar.eventTypes and Calendar.timeslots. The notion of "event type" is
    # central and highly abstract: it may represent a plethora of various and
    # complex things. Concretely, every event type must be a short, identifier
    # string.
    #
    # The most basic approach is to define a list of short strings as possible
    # event types that can be stored for every event, like:
    #
    #                      'week', 'weekend', 'dayOff'
    #
    # This allows to define a simple calendar allowing to "qualify" every day as
    # week day, week-end day or day off.
    #
    # If you want to store arbitrary complex data at a given day (& timeslot) in
    # a Appy calendar, another approach is to create Appy objects outside the
    # calendar and refer to these objects by storing, as calendar event types,
    # stringified iids corresponding to these objects. For example, suppose
    # you have a Ref storing Absence objects, each one representing a type of
    # absence, for example: holiday (iid 123), illness (iid 124) and training
    # (iid 125). Then, stored events could have the following types:
    #
    #                          '123', '124', '125'
    #
    # You could also go further and store any combination of object IIDs and/or
    # other custom keys, like:
    #
    #                  'az656*123', 'ah878*124', 'ko878*125'
    #
    # Or whatever you might imagine.
    #
    # This approach may still not be satisfying. Indeed,
    # (a) you could need to refer to external Appy objects via event types
    #     storing object IIDs, but still want to store more attributes on the
    #     event itself. It could be the case, for example, if there are too many
    #     possible combinations of referred Appy objects ;
    # (b) it could also not be possible or desirable to refer to standard Appy
    #     objects in a calendar.
    #
    # At this point, 2 additional approches are proposed.
    #
    # The first one is to define Appy fields in attribute Calendar.eventFields.
    # When such fields are defined, the popup for adding or creating an event,
    # beyond asking for an event type and slot, will render these additional
    # fields. Entered values for these fields will then be stored on a
    # persistent object, stored in attribute event.data; this object will be an
    # instance of this EventData class, or one of its sub-classes if specified
    # in attribute Calendar.dataClass.
    #
    # The second one is to let you completely free to invent your own UI
    # controls. In that case, forget about attributes Calendar.eventFields and
    # Calendar.dataClass. Define your custom sub-class hierarchy based on class
    # EventData; then, create your own forms for creating and updading your
    # events. Use methods on the Event class to create or update your events in
    # your Appy calendar.

    # Note that, if you use this latter approach:
    # - the standard Calendar views will not do much for you to graphically
    #   represent the data, or allow to edit it ;
    # - some standard functions, like merging events of the same day, will
    #   potentially imply losing custom data.

    def __init__(self):
        # The container event
        self.event = None
        # p_self's creation date (will hold a DateTime.DateTime object)
        self.created = None
        # p_self's creator (user login)
        self.creator = None
        # p_self's last modification date (will hold a DateTime.DateTime object)
        self.modified = None
        # p_self's last modifier
        self.modifier = None
        # When event fields are in use, an EventData object must mimic an Appy
        # object. As a consequence, values for event fields will be stored in a
        # persistent dict in p_self.values.
        self.values = None

    def complete(self, o, event):
        '''Fills p_self's base attributes on p_event creation'''
        self.event = event
        self.created = self.modified = DateTime()
        self.creator = self.modifier = o.user.login

    def update(self, o, other):
        '''Updates p_self with data as stored on this p_other data set'''
        self.modified = DateTime()
        self.modifier = o.user.login
        self.values = other.values

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                              I am Appy
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Minimal stuff for mimicking the Base class
    iid = 666 # A dummy object IID
    def H(self): return Base.Handler.get()
    config = property(lambda o: o.H().config, None)
    req = property(lambda o: o.H().req, None)
    database = property(lambda o: o.H().server.database, None)
    def getObject(self, id): return self.database.getObject(self.H(), id)

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                                PXs
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # This PX renders the base EventData attributes, as defined in the
    # hereabove-defined constructor.

    pxBase = Px('''
     <div class="dropdownMenu menuCal" onmouseover="toggleDropdown(this)"
          onmouseout="toggleDropdown(this,'none')">
      <div>☰</div>
      <div class="dropdown fadedIn ddCal" style="display:none">
       <div>
        <b>:_('Base_creator')</b> 
        <x>:user.getTitleFromLogin(data.creator)</x> 
        <x>:_('date_on')</x> 
        <x>:tool.formatDate(data.created, withHour=True)</x>
       </div> 
       <div if="data.modified and data.modified != data.created"
            class="topSpaceS">
        <b>:_('Base_modifier')</b> 
        <x>:user.getTitleFromLogin(data.modifier)</x> 
        <x>:_('date_on')</x> 
        <x>:tool.formatDate(data.modified, withHour=True)</x>
       </div>
      </div>
     </div>''',

     css='''.menuCal { float:left; cursor:help; font-weight:normal;
                       font-style:normal; margin-right:0.2em }
            .ddCal { margin-left:-3em; width:10em;
                     font-size:85% !important }''')

    # The specific fields your sub-class adds may be rendered in the standard
    # Appy calendar views via the PXs you may override in the following static
    # attributes, on your sub-class.
    pxMonth = pxMonthMulti = pxWeek = pxDay = pxDayMulti = None

    # PX that renders fields possibly defined in attribute Calendar.eventFields

    pxEventFields = Px('''
     <div id=":req.hook" class="calSpan"
          var="layout='edit';
               fields=field.getEventFieldsFor(o, req.eventType)">
      <!-- Render these v_fields, if any -->
      <x if="fields"
         var2="fieldName=None;
               page,grouped,css,js,phases=o.getGroupedFields('main', 'edit',
                                                             fields=fields)">
       <!-- If we are editing existing event data, get it and set it as the
            current (mimicked) Appy v_o(bject). -->
       <x var="px=o.pxFields;
               day=field.DateTime(req.day);
               event=field.getEventAt(o, day, req.timeslot);
               o=event.data if event and event.data else o">:px</x>
      </x>
     </div>''')

    def updateContext(self, c, mode):
        '''Override this to complete the PX p_c(ontext) that will be passed to
           s_px.'''

    def render(self, o, calendar, event, mode='Month'):
        '''Render this dataset (p_self) being stored in this p_event within that
           p_calendar, on this p_o(bject).'''
        # Returns a 3-tuple with the 3 parts one may render about p_self:
        # 1· a custom rendering as proposed by an EventData sub-class via its
        #    px{mode};
        # 2· the standard attributes as defined in the EventData constructor;
        # 3· event fields (if any)
        #
        # Define a context for the PXs allowing to render parts 1 to 3: get the
        # current PX context and patch it.
        context = o.traversal.context
        baseO = context.o # Remember the currently walked object
        context.data = self
        context.o = o
        # Let a sub-class update the context
        self.updateContext(context, mode)
        # Get and execute the PXs
        px = getattr(self, f'px{mode}')
        custom = px(context) if px else None
        standard = self.pxBase(context)
        # Render event fields
        if calendar.eventFields:
            fields = calendar.getEventFieldsFor(o, event.eventType)
            if fields:
                # Render these fields
                c = context
                c.fieldName = None
                c.page, c.grouped, c.css, c.js, c.phases = \
                  o.getGroupedFields('main', 'view', fields=fields)
                # p_self plays the role of the current Appy object (v_context.o)
                c.o = self
                fields = o.pxFields(context)
        else:
            fields = None
        # Reset the context
        context.o = baseO
        # Return the result
        return custom, standard, fields
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
