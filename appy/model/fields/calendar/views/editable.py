#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import time
from DateTime import DateTime

from appy.px import Px
from appy.ui.criteria import Criteria
from appy.utils import dates as dutils

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Editable:
    '''Mix-in class used by a View class when, via this view, calendar events
       may be created, updated and/or deleted.'''

    def mayAppyCreate(self, c):
        '''Must the "create" button be rendered in the cell corresponding to
           the day at p_c.date, for triggering the creation of a Appy
           object ?'''
        # Do not confuse the creation of an Appy object via a calendar (being
        # enabled by attribute p_field.createObjects) and the creation of
        # calendar events (being determined by field.eventTypes).
        #
        # A calendar event is created within the calendar data structure as
        # stored on the concerned object, while an Appy object is never created
        # in this data structure. It is created in the Appy database as any
        # other Appy object. Creating Appy objects via a calendar view is just
        # proposed as a convenient way to create such objects.
        method = c.field.createObjects
        if not method: return
        # A method is there. Call it.
        o = c.o
        r = method(o, c.date, c.cache)
        if not r: return
        # Get the class for which the "create" button must be rendered
        className, attributes = r
        if not className: return
        # Is the user allowed to create instances of this class ?
        class_ = o.model.classes[className]
        cache = o.cache
        key = f'_may_{className}'
        if key in cache:
            may = cache[key]
        else:
            may = cache[key] = o.guard.mayInstantiate(class_)
        if not may: return
        # Complete, when relevant, attributes with the current day
        dateField = class_.fields.get('date')
        if dateField:
            # Set the hour to the current hour, if the field uses the "hour"
            # part.
            if dateField.format == dateField.WITH_HOUR:
                now = time.localtime()
                hour = f'{str(now.tm_hour).zfill(2)}:{str(now.tm_min).zfill(2)}'
                date = DateTime(f"{c.date.strftime('%Y/%m/%d')} {hour}")
            else:
                date = c.date
            attributes.date = date
        # If we are here, an Appy object may be created. Instead of returning
        # True, return a tuple containing the class name and attributes,
        # marshalled in a string (by reusing class Criteria).
        return className, Criteria.dictAsString(attributes.d())

    def getCellClass(self, date):
        '''What CSS class(es) must apply to the cell representing p_date in the
           current calendar view ?'''
        r = []
        # We must distinguish between past and future dates
        r.append('odd' if date < self.today else 'even')
        # Week-end days must have a specific style
        if date.aDay() in dutils.weekEndDays:
            r.append('cellWE')
        return ' '.join(r)

    def getEventTypeOnChange(self, c):
        '''If p_self.field defines a slot map, configure a JS function that will
           update selectable timeslots in the timeslot selector, everytime an
           event type is selected in the event type selector.'''
        field = self.field
        return 'EventPopup.geT(this).setEventType(-2)' if field.slotMap else ''

    def getSlotsFor(self, eventType):
        '''Returns a comma-separated list of timeslots one may select when
           creating an event of this p_eventType.'''
        slotMap = self.field.slotMap
        if slotMap:
            r = slotMap(self.o, eventType)
            if r:
                return ','.join(r)
        return ''

    def getEventAt(self, events, timeslot):
        '''Return, among these p_events, the one at this p_timeslot'''
        if not events: return
        for event in events:
            if event.timeslot == timeslot:
                return event

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                  The "edit" popup and its components
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # The event type and timeslot selectors

    pxSelectors = Px('''
     <!-- The event filter -->
     <input id="searchET" name="searchET" type="text" size="3" placeholder="…"
            oninput="EventPopup.geT(this).filterEventTypes()"
            onkeyup="EventPopup.geT(this).selectEventType(event)"/>

     <!-- The event type selector -->
     <select name="eventType" required="required"
             onchange=":view.getEventTypeOnChange(_ctx_)" class="calSelect">
      <option value="">:_('choose_a_value')</option>
      <option for="eventType in allowedTypes"
              var2="disabled=eventType not in okTypes.eventTypes"
              selected=":reqType == eventType"
              disabled=":disabled" title=":okTypes.message if disabled else ''"
              data-slots=":view.getSlotsFor(eventType)"
              value=":eventType">:field.getEventName(o, eventType)</option>
     </select>
     <span class="required">*</span>

     <!-- Choose a timeslot -->
     <div if="create and len(timeslots) &gt; 1" id="slotZone">
      <label class="calSpan">:_('timeslot')</label> 
      <select name="timeslot" class="calSelect"
              var="selected=False; selectedSet=False">
       <option for="sname, slot in field.Timeslot.getAllNamed(o, timeslots)"
               var2="enabled=slot.id in freeSlots;
                     @selected=False if selectedSet else enabled;
                     @selectedSet=selectedSet or enabled"
               selected=":(timeslot == slot.id) if timeslot else selected"
               disabled=":not enabled" title=":'' if enabled else '🛇'"
               value=":slot.id">:sname</option>
      </select>
     </div>

     <!-- Store here the timeslot when editing an existing event -->
     <input type="hidden" if="not create" name="timeslot"
            value=":timeslot"/>''')

    # Dynamic, field-specific content of the popup for adding/updating an event

    pxContent = Px('''
     <div id=":hook"
          var="reqType=eventType|None;
               timeslot=timeslot|None;
               create=not reqType;
               view=field.View.get(o, field);
               date=field.DateTime(day);
               hasFields=bool(field.eventFields);
               eventTypes=field.getEventTypes(o);
               timeslots=field.Timeslot.getAll(o, field);
               allowedTypes=field.getAllowedTypes(o, eventTypes);
               cache=field.getCache(o, view);
               okTypes=field.getApplicableEventTypesAt(o, date, allowedTypes,
                                                       cache, True);
               events=field.getEventsAt(o, date);
               freeSlots=field.Timeslot.getFreeAt(o, date, events, timeslots)">

      <!-- Event type and timeslot selectors -->
      <x>:view.pxSelectors</x>

      <!-- Span the event on several days -->
      <div if="create" align="center" class="calSpan" id="spanZone">
       <x>::_('event_span')</x>
       <input type="number" name="eventSpan" size="1"
              min="1" max=":field.maxEventLength"
              onkeypress="return (event.keyCode != 13)"/>
      </div>

      <!-- An optional comment (use a Poor widget) -->
      <div class="calSpan" if="field.useEventComments"
           var2="field=view.Poor(viewCss=None, label='None', width='96%',
                              height='5em', placeholder=_('workflow_comment'));
                 x=field.init(None, 'comment'); name=field.name; value=None;
                 lg=None; inRequest=not create;
                 event=view.getEventAt(events, timeslot);
                 requestValue=getattr(event,'comment',None) if event else None;
                 hostLayout=None">:field.editUni</div>

      <!-- Event fields -->
      <x if="hasFields" var2="hook=f'{hook}Fields'">
       <!-- Create a new event: just set a hook -->
       <div if="create" id=":hook" class="calspan"></div>
       <!-- Update an existing event: render the field(s) if any -->
       <x if="not create">:field.EventData.pxEventFields</x>
      </x>

      <!-- Set the focus on the widget for filtering events -->
      <script>document.getElementById('searchET').focus()</script>
     </div>''')

    # Popup for adding or updating an event

    pxEditPopup = Px('''
     <div var="popupId=f'{hook}_edit'"
          id=":popupId" class="popup" align="center">
      <form id=":f'{popupId}Form'" method="post" data-sub="process">
       <input type="hidden" name="actionType" value="createEvent"/>
       <input type="hidden" name="popupDay"/>

       <!-- Choose an event type -->
       <div align="center" id="newEventLabel">:_(field.createEventLabel)</div>
       <div id="optionChoose" class="hide">:_('choose_a_value')</div>
       <div id="optionNil" class="hide">:_('query_no_result')</div>

       <!-- Form content will be fetched via pxContent -->
       <div id=":f'{popupId}Content'"></div>

       <!-- Save and cancel buttons -->
       <input type="button" value=":_('object_save')" name="saveButton"
              onclick="EventPopup.geT(this).run()"/>
       <input type="button" value=":_('object_cancel')"
              onclick=":f'closePopup(`{popupId}`)'"/>
      </form>
     </div>''')

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                         The "delete" popup
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Popup for removing events

    pxDelPopup = Px('''
     <div var="popupId=f'{hook}_del'"
          id=":popupId" class="popup" align="center">
      <form id=":f'{popupId}Form'" method="post" data-sub="process">
       <input type="hidden" name="actionType" value="deleteEvent"/>
       <input type="hidden" name="timeslot" value="*"/>
       <input type="hidden" name="popupDay"/>
       <div align="center"
            style="margin-bottom: 5px">:_('action_confirm')</div>

       <!-- Delete successive events ? -->
       <div class="discreet" style="margin-bottom:10px"
            id=":f'{hook}_DelNextEvent'"
            var="cbId=f'{popupId}_cb'; hdId=f'{popupId}_hd'">
         <input type="checkbox" name="deleteNext_cb" id=":cbId"
                onClick="toggleCheckbox(this)"/><input
          type="hidden" id=":hdId" name="deleteNext"/>
         <label lfor=":cbId" class="simpleLabel">:_('del_next_events')</label>
       </div>
       <input type="button" value=":_('yes')"
              onClick=":f'EventPopup.geT(this).run()'"/>
       <input type="button" value=":_('no')"
              onclick=":f'closePopup({q(popupId)})'"/>
      </form>
     </div>''')

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                   Render a cell in a standard calendar
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Render events in a particular calendar cell (called by pxCell below)

    pxEvents = Px('''
     <x if="events">
      <div for="event in shownEvents" style="color:grey">

       <!-- Checkbox for validating the event -->
       <input type="checkbox" checked="checked" class="smallbox"
              if="mayValidate and field.validation.isWish(o, event.eventType)"
              id=":'%s_%s_%s' % (date.strftime('%Y%m%d'), event.eventType,
                                 event.getTimeMark())"
              onclick=":f'onCheckCbCell(this,{q(hook)})'"/>

       <!-- The event name -->
       <x>::event.getName(o, field, timeslots, typeInfo)</x>

        <!-- Edit this particular event -->
        <img if="mayEdit and field.editableEvents and event.eventType in \
                  allowedTypes"
             class="calicon iconS" src=":svg('edit')" style="opacity:0"
             onclick=":f'new EventPopup(this,`{hook}`,`{o.iid}`,`{field.name}`,
                        `edit`,`{dayString}`,`{event.timeslot}`,{hasEventFields}
                        ).openEdit(`{event.eventType}`)'"/>

        <!-- Delete this particular event -->
        <img if="mayDelete and not single" class="calicon iconS"
             src=":svg('deleteS')" style="opacity:0"
             onclick=":f'new EventPopup(this,`{hook}`,`{o.iid}`,`{field.name}`,
                        `del`,`{dayString}`,`{event.timeslot}`).openDelete()'"/>
      </div>
     </x>

     <!-- Events from other calendars -->
     <x if="not view.multiple and others"
        var2="otherEvents=field.Other.getEventsAt(field, date, others,
                                                 typeInfo, view, cache)">
      <div for="event in otherEvents"
           style=":f'color:{event.color};font-style:italic'">:event.name</div>
     </x>''')

    # PX rendering a cell in a Calendar field, in views like
    # (a) the individual month view ;
    # (b) the multiple week view.

    pxCell = Px('''
     <td var="events=field.getEventsAt(o, date, typeInfo=typeInfo);
              shownEvents=view.getShownEvents(events);
              single=events and len(events) == 1;
              spansDays=field.hasEventsAt(o, date+1, events);
              spansDaysJs='true' if spansDays else 'false';
              mayCreate=mayEdit and allowedTypes and not field.dayIsFull(o,
                          date, events, timeslots);
              mayDelete=mayEdit and events and field.mayDelete(o, events);
              mayAppyCreate=view.mayAppyCreate(_ctx_);
              okTypes=field.getApplicableEventTypesAt(o, date, allowedTypes,
                        cache, True) if (mayCreate or mayEdit) else None;
              js='itoggle(this)' if mayEdit or mayAppyCreate else '';
              cellWeight='bold' if date.isCurrentDay() else 'normal';
              cellStyle=f'font-weight:{cellWeight}';
              totals=totals|None"
         class=":cssClasses" style=":cellStyle"
         onmouseover=":js" onmouseout=":js">

      <x if="not view.multiple">
       <span>:day</span> 
       <span if="day == 1">:_(f'month_{date.aMonth()}_short')</span>
      </x>

      <!-- Icon for adding an event -->
      <x if="mayCreate">
       <img class="calicon" style="opacity:0"
            if="okTypes and okTypes.eventTypes" src=":url('plus')"
            onclick=":f'new EventPopup(this,`{hook}`,`{o.iid}`,`{field.name}`,
                       `new`,`{dayString}`,null,{hasEventFields}).openEdit()'"/>
      </x>

      <!-- Icon for adding an Appy object -->
      <x if="mayAppyCreate" var2="cname,attrs=mayAppyCreate">
       <img class="calicon" style="opacity:0" src=":url('plus')"
            onclick=":f'postAndClick(`{cname}_add`,`{attrs}`)'"/>
      </x>

      <!-- Icon for deleting event(s) -->
      <img if="mayDelete" class="calicon iconS" style="opacity:0"
           src=":svg('deleteS' if single else 'deleteMany')"
           onclick=":f'new EventPopup(this,`{hook}`,`{o.iid}`,`{field.name}`,
                      `del`,`{dayString}`,`*`).openDelete({spansDaysJs})'"/>

      <!-- Events -->
      <x>:view.pxEvents</x>

      <!-- Additional info -->
      <x var="info=field.getAdditionalInfoAt(o, date, None, 'month', cache)"
         if="info">::info</x>

      <!-- Update totals when relevant -->
      <x if="view.multiple and totals" var2="x=totals.update(_ctx_)"></x>
     </td>''')

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                    Render a cell in a Picker field
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    pxCellPick = Px('''
     <td class=":cssClasses"
         var="exclude=field.mustExclude(o, date, cache);
              onEdit=layout == 'edit'">
      <!-- This day cannot be picked and a message must be rendered -->
      <abbr if="isinstance(exclude, str)" title=":exclude"
            class="pickSB">🚫</abbr>

      <!-- This day can be picked -->
      <x if="not exclude"
         var2="hasEvent=field.hasEventAt(o, date, cache._ci_)">

       <!-- On /edit, render a checkbox -->
       <x if="onEdit" var2="suffix='on' if hasEvent else 'off'">
        <input type="hidden" name=":name" value=":f'{dayString}_{suffix}'"/>
        <input type="checkbox" class="pickCB" name=":f'cb_{name}'"
               id=":dayString" value=":dayString" checked=":hasEvent"
               onchange="updatePicked(this)"/>
       </x>

       <!-- On /view, render a symbol -->
       <span if="not onEdit and hasEvent" class="pickSB">✅</span>
      </x>

      <!-- Show the day number, and month name when relevant -->
      <span>:day</span> 
      <span if="day == 1">:_(f'month_{date.aMonth()}_short')</span>
     </td>''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
