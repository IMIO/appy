#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from DateTime import DateTime

from appy.px import Px
from appy.utils import iconParts
from appy.model.fields.group import Group
from appy.model.workflow.state import State
from appy.model.workflow import emptyDict, Role

# Errors - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
UN_TRIG  = 'Transition "%s" on %s can\'t be triggered.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Transition:
    '''Represents a workflow transition'''

    # A specific class for transition-related errors
    class Error(Exception): pass

    # Some methods will be traversable
    traverse = {}

    def __init__(self, states, condition=True, preAction=None, action=None,
                 show=True, confirm=False, group=None, icon=None, sicon=None,
                 redirect=None, historizeActionMessage=False, iconOnly=False,
                 iconOut=False, iconCss='iconS', updateModified=False):

        '''A transition instance must be created as a static attribute for a
           Workflow class.'''

        # In its simpler form, p_states is a list of 2 states:
        # (fromState, toState). But it can also be a list of several
        # (fromState, toState) sub-lists. This way, you may define only 1
        # transition at several places in the state-transition diagram. It may
        # be useful for "undo" transitions, for example.
        self.states = self.standardiseStates(states)

        # The p_condition determines if a transition can be triggered. If
        # p_condition is a:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # string  | it represents the name of a role. Only people having this
        #         | role on the related object will be allowed to trigger the
        #         | transition ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # Role    | we are in the same case as the previous one, but with a role
        #         | being passed as a Role instance ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # method  | it represents a custom condition, as a method that must be
        #         | defined on your workflow class. This method must accept the
        #         | target object as unique arg and return True if the
        #         | transition can be triggered.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # list /  | it is a sequence whose elements are any of the hereabove-
        # tuple   | mentioned values. The transition will be triggerable if the
        #         | currently logged user has *at least* one of the listed roles
        #         | and if *all* listed methods return True. If you want to mix
        #         | roles and methods, it is generally preferable to place roles
        #         | before functions in the sequence.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.condition = condition
        if isinstance(condition, str):
            # The condition specifies the name of a role
            self.condition = Role(condition)

        # The p_preAction is a method that will be executed just before a
        # transition is fired. This method must be defined on a workflow class,
        # must accept the target object as unique arg and must return None.
        # p_preAction can also hold a list or tuple of methods. In that case,
        # all these methods will be executed in their sequence order.
        self.preAction = preAction

        # The p_action is a method that will be executed just after a transition
        # has been fired. It means, a.o., that, at this point, the history event
        # representing the workflow action has already been inserted into the
        # target object's history. At this point, the target object is in the
        # transition's target state. This method must be defined on a workflow
        # class and must accept the target object as unique arg. The return
        # value can be a translated text, as a string, ready to be shown in the
        # UI. p_action can also hold a list or tuple of methods. In that case,
        # all these methods will be executed in their sequence order. Their
        # return values, if any, will be concatenated. If there iis no returned
        # text, a standard translated text will be returned in the UI.
        self.action = action

        # If p_show is False, the end user will not be able to trigger the
        # transition. It will only be possible by code.
        self.show = show

        # If True, in the UI, when clicking on the icon or button representing
        # this transition, a confirm popup will show up.
        self.confirm = confirm

        # Transitions can be grouped, just like fields
        self.group = Group.get(group)

        # You can specify an icon for the button or icon representing this
        # transition in the UI. If you want to specify a standard Appy SVG icon
        # or one of your SVG icons being in folder <yourApp>/static, specify the
        # name of the image, ie, "help.svg". If you want to specify one of your
        # non-SVG icons, specify "<yourApp>/<yourImage>". Else, default Appy
        # icon "action.svg" (from appy/ui/static) will be used.
        self.icon, self.iconBase, self.iconRam = iconParts(icon or 'action.svg')

        # You may specify, in attribute "sicon", an alternate icon suitable when
        # rendered as a small icon.
        sicon = sicon or icon or 'action.svg'
        self.sicon, self.siconBase, self.siconRam = iconParts(sicon)

        # If p_redirect is None, once the transition will be triggered, Appy
        # will perform an automatic redirect:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # (a) | if you were on some "view" page, Appy will redirect you to this
        #     | page (thus refreshing it entirely);
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # (b) | if you were in a list of objects, Appy will Ajax-refresh the row
        #     | containing the object from which you triggered the transition.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # Case (b) can be problematic if the transition modifies the list of
        # objects, or if it modifies other elements shown outside this list.
        # If you specify "redirect" being:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "page"     | case (a) will always apply;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "referer"  | the entire page will be refreshed with the referer page.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.redirect = redirect

        # When a transition is triggered, the corresponding event is added in
        # the object's history. If p_historizeActionMessage is True, the message
        # returned by p_self.action (if any) will be appended to this event's
        # comment.
        self.historizeActionMessage = historizeActionMessage

        # If p_iconOnly is True, the transition will be rendered as an icon (and
        # not a button), even on the "buttons" layout.
        self.iconOnly = iconOnly

        # If p_iconOut is True, when the transition is rendered as a
        # "icon + button" (p_iconOnly is False), the icon will be positioned
        # outside the button. Else, it will be integrated as a background-image
        # inside it. Having the icon outside the button allows for more
        # graphical possibilities (ie: the button may have a border that does
        # not include the icon).
        self.iconOut = iconOut

        # The CSS class to apply to the button icon, in "icon out" mode
        self.iconCss = iconCss

        # If p_updateModified is True, triggering this transition is considered
        # as a change on the object: his last modification date will be updated.
        self.updateModified = updateModified

    def init(self, workflow, name):
        '''Lazy initialisation'''
        self.workflow = workflow
        self.name = name
        self.labelId = f'{workflow.name}_{name}'

    def __repr__(self):
        '''String's short representation for p_self'''
        return f'<transition {self.workflow.name}::{self.name}>'

    def standardiseStates(self, states):
        '''Get p_states as a list or a list of lists. Indeed, the user may also
           specify p_states as a tuple or tuple of tuples. Having lists allows
           us to easily perform changes in states if required.'''
        if isinstance(states[0], State):
            return list(states) if isinstance(states, tuple) else states
        return [[start, end] for start, end in states]

    def getEndStateName(self, wf, startStateName=None):
        '''Returns the name of p_self's end state. If p_self is a
           multi-transition, the name of a specific p_startStateName can be
           given.'''
        if self.isSingle():
            return self.states[1].getName(wf)
        else:
            for start, end in self.states:
                if not startStateName:
                    return end.getName(wf)
                else:
                    if start.getName(wf) == startStateName:
                        return end.getName(wf)

    def getUsedRoles(self):
        '''self.condition can specify a role'''
        r = []
        if isinstance(self.condition, Role):
            r.append(self.condition)
        return r

    def isSingle(self):
        '''If this transition is only defined between 2 states, returns True.
           Else, returns False.'''
        return isinstance(self.states[0], State)

    def isShowable(self, o):
        '''Is this transition showable ?'''
        return self.show(self.workflow, o) if callable(self.show) else self.show

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                           Workflow modifiers
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Appy is built with the idea that an app can be further extended or
    # modified by an ext. Consequently, several of the following methods exist
    # only for modifying, at the "ext" level, a wokflow being defined in an app.

    def addAction(self, action):
        '''Adds an p_action in self.action'''
        actions = self.action
        if not actions:
            self.action = action
        elif isinstance(actions, list):
            actions.append(action)
        elif isinstance(actions, tuple):
            self.action = list(actions)
            self.action.append(action)
        else: # A single action is already defined
            self.action = [actions, action]

    def _replaceStateIn(self, oldState, newState, states):
        '''Replace p_oldState by p_newState in p_states'''
        if oldState not in states: return
        i = states.index(oldState)
        del states[i]
        states.insert(i, newState)

    def replaceState(self, oldState, newState):
        '''Replace p_oldState by p_newState in self.states'''
        if self.isSingle():
            self._replaceStateIn(oldState, newState, self.states)
        else:
            for i in range(len(self.states)):
                self._replaceStateIn(oldState, newState, self.states[i])

    def removeState(self, state):
        '''For a multi-state transition, this method removes every state pair
           containing p_state.'''
        if self.isSingle():
            raise WorkflowException('To use for multi-transitions only')
        i = len(self.states) - 1
        while i >= 0:
            if state in self.states[i]:
                del self.states[i]
            i -= 1
        # This transition may become a single-state-pair transition.
        if len(self.states) == 1:
            self.states = self.states[0]

    def setState(self, state):
        '''Configure this transition as being an auto-transition on p_state.
           This can be useful if, when changing a workflow, one wants to remove
           a state by isolating him from the rest of the state diagram and
           disable some transitions by making them auto-transitions of this
           disabled state.'''
        self.states = [state, state]

    def hasState(self, state, isFrom):
        '''If p_isFrom is True, this method returns True if p_state is a
           starting state for p_self. If p_isFrom is False, this method returns
           True if p_state is an ending state for p_self.'''
        stateIndex = 1
        if isFrom:
            stateIndex = 0
        if self.isSingle():
            r = state == self.states[stateIndex]
        else:
            r = False
            for states in self.states:
                if states[stateIndex] == state:
                    r = True
                    break
        return r

    def replaceRoleInCondition(self, old, new):
        '''When self.condition is a tuple or list, this method replaces role
           p_old by p_new. p_old and p_new can be strings or Role instances.'''
        condition = self.condition
        if isinstance(old, Role): old = old.name
        # Ensure we have a list
        if isinstance(condition, tuple): condition = list(condition)
        if not isinstance(condition, list):
            raise WorkflowException('m_replaceRoleInCondition can only be ' \
              'used if transition.condition is a sequence.')
        # Find the p_old role
        i = -1
        found = False
        for cond in condition:
            i += 1
            if isinstance(cond, Role): cond = cond.name
            if cond == old:
                found = True
                break
        if not found: return
        del condition[i]
        condition.insert(i, new)
        self.condition = tuple(condition)

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                    Check conditions and execute actions
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def isTriggerable(self, o, secure=True):
        '''Can this transition be triggered on p_o ?'''
        # Checks that the current state of the object is a start state for this
        # transition.
        state = o.state
        if self.isSingle():
            if state != self.states[0].name: return
        else:
            found = False
            for start, end in self.states:
                if start.name == state:
                    found = True
                    break
            if not found: return
        # Check that the condition is met, excepted if secure is False
        if not secure: return True
        user = o.user
        # We will need the workflow's prototypical instance
        proto = self.workflow.proto
        if isinstance(self.condition, Role):
            # Condition is a role. Transition may be triggered if the user has
            # this role.
            return user.hasRole(self.condition.name, o)
        elif callable(self.condition):
            return self.condition(proto, o)
        elif type(self.condition) in (tuple, list):
            # It is a list of roles and/or functions. Transition may be
            # triggered if user has at least one of those roles and if all
            # functions return True.
            hasRole = None
            for condition in self.condition:
                # "Unwrap" role names from Role instances
                if isinstance(condition, Role): condition = condition.name
                if isinstance(condition, str): # It is a role
                    if hasRole is None:
                        hasRole = False
                    if user.hasRole(condition, o):
                        hasRole = True
                else: # It is a method
                    r = condition(proto, o)
                    if not r:
                        # v_r is False or a No instance. If roles were also
                        # mentioned among p_self.condition, and v_hasRole is
                        # False so far, return False and not the No instance.
                        return False if hasRole is False else r
            if hasRole != False:
                return True
        else:
            return bool(self.condition)

    def executeAction(self, o, pre=False):
        '''Executes the action (or pre-action if p_pre is True) related to this
           transition.'''
        r = ''
        proto = self.workflow.proto
        attr = 'preAction' if pre else 'action'
        action = getattr(self, attr)
        if type(action) in (tuple, list):
            # We need to execute a list of actions
            for act in action:
                text = act(proto, o)
                if text: r += text
        else: # We execute a single action only
            text = action(proto, o)
            if text: r += text
        return r

    def getTargetState(self, o):
        '''Gets the target state for this transition'''
        # For a single transition, a single possibility
        if self.isSingle(): return self.states[1]
        sourceName = o.state
        for source, target in self.states:
            if source.name == sourceName:
                return target

    def trigger(self, o, comment=None, doAction=True, doHistory=True,
                doSay=True, reindex=True, secure=True, data=None,
                forceTarget=None):
        '''Triggers this transition on some p_o(bject)'''

        # If p_doAction is False, the action and pre-action that must normally
        # be executed, respectively, after and before the transition has been
        # triggered, will not be executed.

        # If p_doHistory is False, there will be no trace from this transition
        # triggering in p_o's history. WARNING: in that case, the state change
        # could not be made! Indeed, the current object's state is stored on the
        # last workflow event. So use this with extreme caution.

        # If p_doSay is False, we consider the transition as being triggered
        # programmatically, and no message is returned to the user.

        # If p_reindex is False, object reindexing will be performed by the
        # caller method.

        # If p_data is specified, it is a dict containing custom data that will
        # be integrated into the history event.

        # Is that the special _init_ transition ?
        name = self.name
        isInit = name == '_init_'
        # "Triggerability" and security checks
        if not isInit and not self.isTriggerable(o, secure=secure):
            raise Transition.Error(UN_TRIG % (name, o.url))
        # Identify the target state for this transition
        target = forceTarget or self.getTargetState(o)
        # Remember the source state, it will be necessary for executing the
        # common action.
        fromState = o.state if not isInit else None
        # Execute the pre-action if any
        if doAction and self.preAction:
            self.executeAction(o, pre=True)
        # Add the event in the object history
        history = o.history
        if doHistory:
            event = history.add('Trigger', target.name, transition=name,
                                comment=comment)
        # Update the object's last modification date when relevant
        if self.updateModified:
            history.modified = DateTime()
        # Execute the action that is common to all transitions, if defined. It
        # is named "onTrigger" on the workflow class by convention. This common
        # action is executed before the transition-specific action (if any).
        proto = self.workflow.proto
        if doAction and hasattr(proto, 'onTrigger'):
            proto.onTrigger(o, name, fromState)
        # Execute the transition-specific action
        msg = self.executeAction(o) if doAction and self.action else None
        # Append the action message to the history comment when relevant
        if doHistory and msg and self.historizeActionMessage:
            event.completeComment(msg)
        # Reindex the object if required. Not only security-related indexes
        # (allowed, state) need to be updated here.
        if reindex and not isInit and not o.isTemp() and o.class_.isIndexable():
            o.reindex()
        # Return a message to the user if needed
        if not doSay: return
        return msg or o.translate('object_saved')

    def ui(self, o, mayTrigger):
        '''Return the UiTransition instance corresponding to p_self'''
        return UiTransition(self, o, mayTrigger)

    traverse['fire'] = True
    def fire(self, o):
        '''Executed when a user wants to trigger this transition from the UI'''
        # This requires a database commit
        tool = o.tool
        req = o.req
        handler = o.H()
        handler.commit = True
        # Trigger the transition
        msg = self.trigger(o, req.popupComment, reindex=False)
        # Reindex p_o if required
        if not o.isTemp(): o.reindex()
        # If we are called from an Ajax request, simply return msg
        if handler.isAjax(): return msg
        # If we are viewing the object and if the logged user looses the
        # permission to view it, redirect the user to its home page.
        if msg: o.say(msg)
        # The developer may already have defined an URL to return to
        if o.gotoSet(): return
        # Return to o/view, excepted if the object is not viewable anymore
        if o.guard.mayView(o):
            if self.redirect == 'referer':
                back = handler.headers['Referer']
            else:
                back = o.getUrl(nav=req.nav or 'no', page=req.page or 'main',
                                popup=req.popup)
        else:
            back = tool.computeHomePage()
        o.goto(back)

    def getBack(self):
        '''Returns, in p_self's workflow, the name of the transition that
           "cancels" the triggering of this one and allows to go back to
           p_self's start state.'''
        single = self.isSingle()
        # Browse all transitions and find the one starting at p_self's end
        # state and coming back to p_self's start state.
        for transition in self.workflow.transitions.values():
            if transition == self: continue
            if single:
                if transition.hasState(self.states[1], True) and \
                   transition.hasState(self.states[0], False):
                       return transition.name
            else:
                startOk = endOk = False
                for start, end in self.states:
                    if not startOk and transition.hasState(end, True):
                        startOk = True
                    if not endOk and transition.hasState(start, False):
                        endOk = True
                    if startOk and endOk: return transition.name

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class UiTransition:
    '''Widget that displays a transition'''

    # The button in itself, real or fake
    pxButton = Px('''
     <!-- Real button -->
     <input if="mayTrigger" type="button" class=":css" value=":label"
            var="back=transition.getBackHook(_ctx_)"
            name=":tr.name" style=":transition.getIconUrl(asBG=True)"
            onclick=":'triggerTransition(%s,this.name,%s,%s)' % \
                       (q(formId), q(transition.confirm), back)"/>
     <!-- Fake button -->
     <input if="not mayTrigger" type="button" class=":'%s fake' % css"
            style=":transition.getIconUrl(asBG=True)"
            value=":label" title=":transition.reason"/>''')

    px = Px('''
     <x var="label=transition.title;
             mayTrigger=transition.mayTrigger;
             inSub=layout=='sub';
             tr=transition.transition;
             asIcon=not inSub or tr.iconOnly">

      <!-- As picto or icon -->
      <a if="asIcon" class=":'clickable' if mayTrigger else 'fake'"
         var="back=transition.getBackHook(_ctx_);
              iconAttr='sicon' if inSub else 'icon';
              iconBase='siconBase' if inSub else 'iconBase';
              iconRam='siconRam' if inSub else 'iconRam'"
         name=":tr.name" title=":transition.getIconTitle()"
         onclick=":'triggerTransition(%s,this.name,%s,%s)' % 
                    (q(formId), q(transition.confirm), back) 
                    if mayTrigger else ''">
       <img src=":url(getattr(tr, iconAttr), base=getattr(tr, iconBase),
                      ram=getattr(tr,iconRam))"
            class=":picto|tr.iconCss"/>
       <div style=":'display:%s' % config.ui.pageDisplay"
            if="not inSub">::label</div>
      </a>

      <!-- As button -->
      <x if="not asIcon"
         var2="css=ui.Button.getCss(label, inSub, iconOut=tr.iconOut)">

       <!-- Variant with the icon outside the button -->
       <div if="tr.iconOut" class="iflex1">
        <img src=":transition.getIconUrl()"
             class=":'%s %s'%('clickable' if mayTrigger else 'fake',tr.iconCss)"
             onclick="this.nextSibling.click()"/>
        <x>:transition.pxButton</x>
       </div>

       <!-- Variant with the icon inside the button -->
       <x if="not tr.iconOut">:transition.pxButton</x>
      </x></x>''',

     js='''
      // Function used for triggering a workflow transition
      function triggerTransition(formId, transition, msg, back) {
        var f = document.getElementById(formId);
        f.action = f.dataset.baseurl + '/' + transition + '/fire';
        submitForm(formId, msg, true, back);
      }''')

    def __init__(self, transition, o, mayTrigger):
        self.o = o
        _ = o.translate
        # The tied p_transition
        self.transition = transition
        self.type = 'transition'
        labelId = transition.labelId
        self.title = _(labelId)
        if transition.confirm:
            msg = _('%s_confirm' % labelId, blankOnError=True) or \
                  _('action_confirm')
            self.confirm = msg
        else:
            self.confirm = ''
        # May this transition be triggered via the UI ?
        self.mayTrigger = True
        self.reason = ''
        if not mayTrigger:
            self.mayTrigger = False
            self.reason = mayTrigger.msg
        # Required by the UiGroup
        self.colspan = 1

    def getBackHook(self, c):
        '''If, when the transition has been triggered, we must ajax-refresh some
           part of the page, this method will return the ID of the corresponding
           DOM node. Else (ie, the entire page needs to be refreshed), it
           returns None.'''
        if c.inSub and not self.transition.redirect:
            r = c.q(c.backHook or c.ohook)
        else:
            r = 'null'
        return r

    def getIconTitle(self):
        '''Compute the title of the icon representing the transition, when this
           latter is represented by an icon only.'''
        if not self.mayTrigger:
            r = self.reason
        elif self.transition.iconOnly:
            r = self.title
        else:
            r = ''
        return r

    def getIconUrl(self, pre='s', asBG=False):
        '''Returns the URL to p_self's (s)icon (depending on p_pre(fix)), to be
           used as a background image or not (depending on p_asBG).'''
        tr = self.transition
        # In "icon out" mode, no background image must be present
        if asBG and tr.iconOut: return ''
        # If p_asBG, get the background image dimensions
        bg = '18px 18px' if asBG else False
        return self.o.buildUrl(getattr(tr, '%sicon' % pre),
                               base=getattr(tr, '%siconBase' % pre),
                               ram=getattr(tr, '%siconRam' % pre), bg=bg)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -