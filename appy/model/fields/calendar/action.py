#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.px import Px

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Action:
    '''An action represents a custom method that can be executed, based on
       calendar data. If at least one action is visible, the shown calendar
       cells will become selectable: the selected cells will be available to the
       action.'''

    # Currently, actions can be defined in month, multiple calendars only

    def __init__(self, name, label, action, show=True, valid=None):
        # A short name that must identify this action among all actions defined
        # in this calendar.
        self.name = name
        # A i18n p_label for producing a translated name in the user interface
        self.label = label
        # "labelConfirm" is the i18n label used in the confirmation popup. It
        # is based on self.label, suffixed with "_confirm".
        self.labelConfirm = f'{label}_confirm'
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
        # Must this action be shown or not? p_show can be a boolean or a method.
        # If it is a method, it must accept a unique arg: a DateTime instance
        # being the first day of the currently shown month.
        self.show = show
        # Is the combination of selected events valid for triggering the action?
        self.valid = None

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                             Class methods
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @classmethod
    def getVisibleOn(class_, o, field, dayOne):
        '''Return the visible actions among p_field.actions'''
        actions = field.actions
        if not actions: return
        r = []
        for action in actions:
            show = action.show
            show = show(o, dayOne) if callable(show) else show
            if show: r.append(action)
        return r

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                                  PXs
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # The range of widgets (checkboxes, buttons) allowing to trigger actions
    px = Px('''
      <!-- The view switcher -->
      <div var="others=view.getOthers()" if="others">
       <a for="other, params in others" class="clickable flexg"
          onclick=":view.getAjaxSwitch(hook, other, params)">
        <img src=":o.buildSvg(other)" class="iconM"/>
        <span> ⇢ <x>:_(other)</x></span>
       </a>
      </div>

      <!-- Validate button, with checkbox for automatic checkbox selection -->
      <x if="mayValidate" var2="cbId=f'{hook}_auto'">
       <input if="mayValidate" type="button" value=":_('validate_events')"
              class="buttonSmall button" style=":url('validate', bg=True)"
              onclick=":'CalValidator.setPopup(%s,%s)' % (q(hook),q('block'))"/>
       <input type="checkbox" checked="checked" id=":cbId"/>
       <label lfor=":cbId" class="simpleLabel">:_('select_auto')</label>
      </x>

      <!-- Checkboxes for (de-)activating layers -->
      <x if="field.layers and field.layersSelector">
       <x for="layer in field.layers"
          var2="cbId=f'{hook}_layer_{layer.name}'">
        <input type="checkbox" id=":cbId" checked=":layer.name in activeLayers"
               onclick=":f'switchCalendarLayer({q(hook)},this)'"/>
        <label lfor=":cbId" class="simpleLabel">:_(layer.label)</label>
       </x>
      </x>

      <!-- Custom actions -->
      <x if="actions">
       <input for="action in actions" type="button" value=":_(action.label)"
              var2="js='calendarAction(%s,%s,comment)' %
                        (q(hook), q(action.name))"
              onclick=":'askConfirm(%s,%s,%s,true)' % (q('script'),
                         q(js,False), q(_(action.labelConfirm)))"/>

       <!-- Icon for unselecting all cells -->
       <img src=":url('unselect')" title=":_('unselect_all')" class="calicon"
           onclick=":f'calendarUnselect({q(hook)})'"/>
      </x>''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
