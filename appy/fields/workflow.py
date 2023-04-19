# ~license~
# ------------------------------------------------------------------------------
import copy

from group import Group
from appy.px import Px
from appy.gen.utils import User
from appy.shared.utils import sequenceTypes

# Default Appy permissions -----------------------------------------------------
r, w, d = ('read', 'write', 'delete')
emptyDict = {}
class WorkflowException(Exception): pass

# ------------------------------------------------------------------------------
class Role:
    '''Represents a role, be it local or global'''
    appyRoles = ('Manager', 'Owner', 'Anonymous', 'Authenticated')
    appyLocalRoles = ('Owner',)
    appyUngrantableRoles = ('Anonymous', 'Authenticated')
    def __init__(self, name, local=False, grantable=True):
        self.name = name
        self.local = local # True if it can be used as local role only.
        # It is a standard Zope role or an application-specific one?
        self.appy = name in self.appyRoles
        if self.appy and (name in self.appyLocalRoles):
            self.local = True
        self.grantable = grantable
        if self.appy and (name in self.appyUngrantableRoles):
            self.grantable = False
        # An ungrantable role is one that is, like the Anonymous or
        # Authenticated roles, automatically attributed to a user.

    def __repr__(self):
        loc = self.local and ' (local)' or ''
        return '<%s%s>' % (self.name, loc)

# ------------------------------------------------------------------------------
class State:
    '''Represents a workflow state'''
    def __init__(self, permissions, initial=False, phase=None, show=True):
        self.usedRoles = {}
        # Dict "permissions" lists, for every permission managed by a workflow,
        # the roles for which the permission is granted in this state. Standard
        # permissions are 'read', 'write' and 'delete'. p_permissions must be a
        # dict with format
        #            ~{s_permissionName:[s_roleName|Role_role]}~

        # It will be converted by m_standardizeRoles into format
        #            ~{s_permissionName:{s_roleName:Role_role}}~
        self.permissions = permissions
        self.initial = initial
        self.phase = phase
        self.show = show
        # Standardize the way roles are expressed within self.permissions
        self.standardizeRoles()

    def getName(self, wf):
        '''Returns the name for this state in workflow p_wf'''
        for name in dir(wf):
            value = getattr(wf, name)
            if (value == self): return name

    def copyPerms(self):
        '''Gets a deep copy of this state's permissions dict'''
        return copy.deepcopy(self.permissions)

    def getRole(self, role):
        '''p_role can be the name of a role or a Role instance. If it is the
           name of a role, this method returns self.usedRoles[role] if it
           exists, or creates a Role instance, puts it in self.usedRoles and
           returns it else. If it is a Role instance, the method stores it in
           self.usedRoles if it is not in it yet and returns it.'''
        if isinstance(role, basestring):
            if role in self.usedRoles:
                return self.usedRoles[role]
            else:
                theRole = Role(role)
                self.usedRoles[role] = theRole
                return theRole
        else:
            if role.name not in self.usedRoles:
                self.usedRoles[role.name] = role
            return role

    def standardizeRoles(self):
        '''This method converts, within self.permissions, every role to a
           Role instance. Every used role is stored in self.usedRoles.'''
        for permission, roles in self.permissions.iteritems():
            if isinstance(roles, basestring) or isinstance(roles, Role):
                role = self.getRole(roles)
                self.permissions[permission] = {role.name: role}
            elif isinstance(roles, dict):
                for name, role in roles.iteritems():
                    roles[name] = self.getRole(role)
            elif callable(roles):
                # v_roles is a method: it is not possible to standardize it. It
                # will be called at check time.
                pass
            else:
                # "roles" is a list or tuple, or None (nobody may have this
                # permission).
                d = {}
                if roles is not None:
                    for role in roles:
                        role = self.getRole(role)
                        d[role.name] = role
                self.permissions[permission] = d

    def getUsedRoles(self): return self.usedRoles.values()

    def addRoles(self, roles, permissions=()):
        '''Adds p_roles in self.permissions. p_roles can be a role name, a Role
           instance or a list of names and/or Role instances. If p_permissions
           is specified, roles are added to those permissions only. Else, roles
           are added for every permission within self.permissions.'''
        # Standardize parameters
        if type(roles) not in sequenceTypes: roles = (roles,)
        if isinstance(permissions, basestring): permissions = (permissions,)
        for perm, existingRoles in self.permissions.iteritems():
            if permissions and perm not in permissions: continue
            # It is not possible to add p_roles if v_existingRoles is a method
            if callable(existingRoles): continue
            for role in roles:
                # Do nothing if "role" is already among existing roles
                name = isinstance(role, basestring) and role or role.name
                if name in existingRoles: continue
                # Add the role for this permission
                existingRoles[name] = self.getRole(role)

    def removeRoles(self, roleNames, permissions=()):
        '''Removes p_roleNames within dict self.permissions. If p_permissions is
           specified, removal is restricted to those permissions. Else, removal
           occurs throughout the whole dict self.permissions.'''
        if isinstance(roleNames, basestring): roleNames = (roleNames,)
        if isinstance(permissions, basestring): permissions = (permissions,)
        for perm, roles in self.permissions.iteritems():
            if permissions and (perm not in permissions): continue
            for name in roleNames:
                # Remove this role if present in roles for this permission
                if name in roles:
                    del roles[name]

    def setRoles(self, roleNames, permissions=()):
        '''Sets p_rolesNames for p_permissions if not empty, for every
           permission in self.permissions else.'''
        if isinstance(roleNames, basestring): roleNames = (roleNames,)
        if isinstance(permissions, basestring): permissions = (permissions,)
        for perm in self.permissions.iterkeys():
            if permissions and (perm not in permissions): continue
            roles = self.permissions[perm] = {}
            for name in roleNames:
                roles[name] = self.getRole(name)

    def replaceRole(self, oldRoleName, newRoleName, permissions=()):
        '''Replaces p_oldRoleName by p_newRoleName. If p_permissions is
           specified, the replacement is restricted to those permissions. Else,
           replacements apply to the whole dict self.permissions.'''
        if isinstance(permissions, basestring): permissions = (permissions,)
        for perm, roles in self.permissions.iteritems():
            if permissions and (perm not in permissions): continue
            # Find and replace p_oldRoleName with p_newRoleName
            if oldRoleName in roles:
                del roles[oldRoleName]
                roles[newRoleName] = self.getRole(newRoleName)

    def copyRoles(self, sourcePermission, destPermission):
        '''Overrides p_destPermission's roles with (a deep copy of)
           p_sourcePermission's roles.'''
        copiedRoles = copy.deepcopy(self.permissions[sourcePermission])
        self.permissions[destPermission] = copiedRoles

    def isIsolated(self, wf):
        '''Returns True if, from this state, we cannot reach another state. The
           workflow class is given in p_wf. Modifying a workflow for getting a
           state with auto-transitions only is a common technique for disabling
           a state in a workflow.'''
        if self.initial: return
        for tr in wf.__dict__.itervalues():
            if not isinstance(tr, Transition): continue
            # Ignore transitions that do not touch this state
            if not tr.hasState(self, True) and not tr.hasState(self, False):
                continue
            # Transition "tr" has this state as start or end state. If start and
            # end states are different, it means that the state is not
            # isolated.
            if tr.isSingle():
                for state in tr.states:
                    if state != self: return
            else:
                for start, end in tr.states:
                    # Bypass (start, end) pairs having nothing to do with self
                    if (start != self) and (end != self): continue
                    if (start != self) or (end != self): return
        # If we are here, either there was no transition starting from self,
        # either all transitions were auto-transitions: self is then isolated.
        return True

# ------------------------------------------------------------------------------
class Transition:
    '''Represents a workflow transition'''
    UNTRIGGERABLE = 'Transition "%s" on %s can\'t be triggered.'

    def __init__(self, states, condition=True, action=None, show=True,
                 confirm=False, group=None, icon=None, redirect=None,
                 historizeActionMessage=False):
        # In its simpler form, "states" is a list of 2 states:
        # (fromState, toState). But it can also be a list of several
        # (fromState, toState) sub-lists. This way, you may define only 1
        # transition at several places in the state-transition diagram. It may
        # be useful for "undo" transitions, for example.
        self.states = self.standardiseStates(states)
        self.condition = condition
        if isinstance(condition, basestring):
            # The condition specifies the name of a role
            self.condition = Role(condition)
        self.action = action
        self.show = show # If False, the end user will not be able to trigger
        # the transition. It will only be possible by code.
        self.confirm = confirm # If True, a confirm popup will show up.
        self.group = Group.get(group)
        # The user may specify a specific icon to show for this transition.
        self.icon = icon or 'transition'
        # If redirect is None, once the transition will be triggered, Appy will
        # perform an automatic redirect:
        # (a) if you were on some "view" page, Appy will redirect you to this
        #     page (thus refreshing it entirely);
        # (b) if you were in a list of objects, Appy will Ajax-refresh the row
        #     containing the object from which you triggered the transition.
        # Case (b) can be problematic if the transition modifies the list of
        # objects, or if it modifies other elements shown outside this list.
        # If you specify "redirect" being
        # ----------------------------------------------------------------------
        # "page"     | case (a) will always apply;
        # ----------------------------------------------------------------------
        # "referer"  | the entire page will be refreshed with the referer page.
        # ----------------------------------------------------------------------
        self.redirect = redirect
        # When a transition is triggered, the corresponding event is added in
        # the object's history. If p_historizeActionMessage is True, the message
        # returned by self.action (if any) will be appended to this event's
        # comment.
        self.historizeActionMessage = historizeActionMessage

    def standardiseStates(self, states):
        '''Get p_states as a list or a list of lists. Indeed, the user may also
           specify p_states as a tuple or tuple of tuples. Having lists allows
           us to easily perform changes in states if required.'''
        if isinstance(states[0], State):
            if isinstance(states, tuple): return list(states)
            return states
        return [[start, end] for start, end in states]

    def getName(self, wf):
        '''Returns the name for this state in workflow p_wf'''
        for name in dir(wf):
            value = getattr(wf, name)
            if (value == self): return name

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
        res = []
        if isinstance(self.condition, Role):
            res.append(self.condition)
        return res

    def isSingle(self):
        '''If this transition is only defined between 2 states, returns True.
           Else, returns False.'''
        return isinstance(self.states[0], State)

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
        '''Replace p_oldState by p_newState in p_states.'''
        if oldState not in states: return
        i = states.index(oldState)
        del states[i]
        states.insert(i, newState)

    def replaceState(self, oldState, newState):
        '''Replace p_oldState by p_newState in self.states.'''
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

    def isShowable(self, workflow, obj):
        '''Is this transition showable?'''
        if callable(self.show):
            return self.show(workflow, obj.appy())
        else:
            return self.show

    def hasState(self, state, isFrom):
        '''If p_isFrom is True, this method returns True if p_state is a
           starting state for p_self. If p_isFrom is False, this method returns
           True if p_state is an ending state for p_self.'''
        stateIndex = 1
        if isFrom:
            stateIndex = 0
        if self.isSingle():
            res = state == self.states[stateIndex]
        else:
            res = False
            for states in self.states:
                if states[stateIndex] == state:
                    res = True
                    break
        return res

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

    def isTriggerable(self, obj, wf, noSecurity=False):
        '''Can this transition be triggered on p_obj ?'''
        wf = wf.__instance__ # We need the prototypical instance here
        # Checks that the current state of the object is a start state for this
        # transition.
        objState = obj.State(name=False)
        if self.isSingle():
            if objState != self.states[0]: return False
        else:
            startFound = False
            for startState, stopState in self.states:
                if startState == objState:
                    startFound = True
                    break
            if not startFound: return False
        # Check that the condition is met, excepted if noSecurity is True
        if noSecurity: return True
        user = obj.getTool().getUser()
        if isinstance(self.condition, Role):
            # Condition is a role. Transition may be triggered if the user has
            # this role.
            return user.hasRole(self.condition.name, obj)
        elif callable(self.condition):
            return self.condition(wf, obj.appy())
        elif type(self.condition) in (tuple, list):
            # It is a list of roles and/or functions. Transition may be
            # triggered if user has at least one of those roles and if all
            # functions return True.
            hasRole = None
            for condition in self.condition:
                # "Unwrap" role names from Role instances
                if isinstance(condition, Role): condition = condition.name
                if isinstance(condition, basestring): # It is a role
                    if hasRole is None:
                        hasRole = False
                    if user.hasRole(condition, obj):
                        hasRole = True
                else: # It is a method
                    res = condition(wf, obj.appy())
                    if not res:
                        # v_res is False or a No instance. If roles were also
                        # mentioned among p_self.condition, and v_hasRole is
                        # False so far, return False and not the No instance.
                        if hasRole is False: return
                        return res
            if hasRole != False:
                return True
        else:
            return bool(self.condition)

    def executeAction(self, obj, wf):
        '''Executes the action related to this transition'''
        msg = ''
        obj = obj.appy()
        wf = wf.__instance__ # We need the prototypical instance here
        if type(self.action) in (tuple, list):
            # We need to execute a list of actions
            for act in self.action:
                msgPart = act(wf, obj)
                if msgPart: msg += msgPart
        else: # We execute a single action only
            msgPart = self.action(wf, obj)
            if msgPart: msg += msgPart
        return msg

    def executeCommonAction(self, obj, name, wf, fromState):
        '''Executes the action that is common to any transition, named
           "onTrigger" on the workflow class by convention. The common action is
           executed before the transition-specific action (if any).'''
        obj = obj.appy()
        wf = wf.__instance__ # We need the prototypical instance here
        wf.onTrigger(obj, name, fromState)

    def trigger(self, name, obj, wf, comment, doAction=True, doHistory=True,
                doSay=True, reindex=True, noSecurity=False, data=None):
        '''This method triggers this transition (named p_name) on p_obj. If
           p_doAction is False, the action that must normally be executed after
           the transition has been triggered will not be executed. If
           p_doHistory is False, there will be no trace from this transition
           triggering in p_obj's history. If p_doSay is False, we consider
           the transition as being triggered programmatically, and no message is
           returned to the user. If p_reindex is False, object reindexing will
           be performed by the caller method. If p_data is specified, it is a
           dict containing custom data that will be integrated into the history
           event. Be careful: if keys in this dict correspond to standard event
           keys ("action", "time"...) they will override it.'''
        # "Triggerability" and security checks
        isInit = name == '_init_'
        if not isInit and not self.isTriggerable(obj, wf,noSecurity=noSecurity):
            raise WorkflowException(self.UNTRIGGERABLE % \
                                    (name, obj.absolute_url()))
        # Create the workflow_history dict if it does not exist
        if not hasattr(obj.aq_base, 'workflow_history'):
            from persistent.mapping import PersistentMapping
            obj.workflow_history = PersistentMapping()
        # Create the event list if it does not exist in the dict. The
        # overstructure (a dict with a key 'appy') is only there for historical
        # reasons and will change in Appy 1.0
        if not obj.workflow_history: obj.workflow_history['appy'] = ()
        # Identify the target state for this transition
        if self.isSingle():
            targetState = self.states[1]
            targetStateName = targetState.getName(wf)
        else:
            startState = obj.State(name=False)
            for sState, tState in self.states:
                if startState == sState:
                    targetState = tState
                    targetStateName = targetState.getName(wf)
                    break
        # Add the event in the object history
        action = name
        if isInit:
            action = None
            fromState = None
        else:
            fromState = obj.State() # Remember the "from" (=start) state
        if not doHistory:
            comment = '_invisible_'
            if data: data['actor'] = 'system'
            else:    data = {'actor': 'system'}
        if not data: data = emptyDict
        event = obj.addHistoryEvent(action, review_state=targetStateName,
                                    comments=comment, **data)
        # Execute the action that is common to all transitions, if defined
        if doAction and hasattr(wf, 'onTrigger'):
            self.executeCommonAction(obj, name, wf, fromState)
        # Execute the related action (if any)
        msg = ''
        if doAction and self.action: msg = self.executeAction(obj, wf)
        # Append the action message to the history event when relevant
        if doHistory and msg and self.historizeActionMessage:
            if not comment: comment = msg
            else: comment = '%s<br/><br/>%s' % (comment, msg)
            event['comments'] = comment
            obj.workflow_history['appy'] = obj.workflow_history['appy'][:-1] + \
                                           (event,)
        # Reindex the object if required. Not only security-related indexes
        # (Allowed, State) need to be updated here.
        if reindex and not isInit and not obj.isTemporary(): obj.reindex()
        # Return a message to the user if needed
        if not doSay: return
        if not msg: msg = obj.translate('object_saved')
        return msg

    def onUiRequest(self, obj, wf, name, req):
        '''Executed when a user wants to trigger this transition from the UI'''
        tool = obj.getTool()
        # Trigger the transition
        msg = self.trigger(name, obj, wf, req.get('popupComment', ''),
                           reindex=False)
        # Reindex obj if required
        if not obj.isTemporary(): obj.reindex()
        # If we are called from an Ajax request, simply return msg
        if hasattr(req, 'pxContext') and req.pxContext['ajax']: return msg
        # If we are viewing the object and if the logged user looses the
        # permission to view it, redirect the user to its home page.
        if msg: obj.say(msg)
        # Return to obj/view, excepted if the object is not viewable anymore
        if obj.mayView():
            if self.redirect == 'referer':
                back = req['HTTP_REFERER']
            else:
                back = obj.getUrl(nav=req.get('nav', 'no'),
                                  page=req.get('page', 'main'),
                                  inPopup=req.get('popup', '0') == '1')
        else:
            back = tool.getHomePage()
        tool.goto(back)

    @staticmethod
    def getBack(workflow, transition):
        '''Returns the name of the transition (in p_workflow) that "cancels" the
           triggering of p_transition and allows to go back to p_transition's
           start state.'''
        # Get the end state(s) of p_transition
        transition = getattr(workflow, transition)
        # Browse all transitions and find the one starting at p_transition's end
        # state and coming back to p_transition's start state.
        for trName, tr in workflow.__dict__.iteritems():
            if not isinstance(tr, Transition) or (tr == transition): continue
            if transition.isSingle():
                if tr.hasState(transition.states[1], True) and \
                   tr.hasState(transition.states[0], False): return trName
            else:
                startOk = False
                endOk = False
                for start, end in transition.states:
                    if (not startOk) and tr.hasState(end, True):
                        startOk = True
                    if (not endOk) and tr.hasState(start, False):
                        endOk = True
                    if startOk and endOk: return trName

class UiTransition:
    '''Represents a widget that displays a transition'''
    pxView = Px('''
     <x var="label=transition.title;
             inButtons=layoutType == 'buttons';
             css=ztool.getButtonCss(label, inButtons)">

      <!-- Real button -->
      <input if="transition.mayTrigger" type="button" class=":css"
             var="back=transition.getBackHook(zobj, inButtons, q, backHook)"
             name=":transition.name" style=":url(transition.icon, bg=True)"
             value=":label"
             onclick=":'triggerTransition(%s,this.name,%s,%s)' % \
                        (q(formId), q(transition.confirm), back)"/>

      <!-- Fake button, explaining why the transition can't be triggered -->
      <input if="not transition.mayTrigger" type="button"
             class=":'fake %s' % css" style=":url('fake', bg=True)"
             value=":label" title=":transition.reason"/></x>''')

    def __init__(self, name, transition, obj, mayTrigger):
        self.name = name
        self.transition = transition
        self.type = 'transition'
        self.icon = transition.icon
        label = obj.getWorkflowLabel(name)
        self.title = obj.translate(label)
        if transition.confirm:
            msg = obj.translate('%s_confirm' % label, blankOnError=True) or \
                  obj.translate('action_confirm')
            self.confirm = msg
        else:
            self.confirm = ''
        # May this transition be triggered via the UI?
        self.mayTrigger = True
        self.reason = ''
        if not mayTrigger:
            self.mayTrigger = False
            self.reason = mayTrigger.msg
        # Required by the UiGroup
        self.colspan = 1

    def getBackHook(self, obj, inButtons, q, backHook=None):
        '''If, when the transition has been triggered, we must ajax-refresh some
           part of the page, this method will return the ID of the corresponding
           DOM node. Else (ie, the entire page needs to be refreshed), it
           returns None.'''
        if inButtons and not self.transition.redirect:
            return q(backHook or obj.id)
        return 'null'

# ------------------------------------------------------------------------------
class Permission:
    '''If you need to define a specific read or write permission for some field
       on a gen-class, you use the specific boolean attrs
       "specificReadPermission" or "specificWritePermission". When you want to
       refer to those specific read or write permissions when
       defining a workflow, for example, you need to use instances of
       "ReadPermission" and "WritePermission", the 2 children classes of this
       class. For example, if you need to refer to write permission of
       attribute "t1" of class A, write: WritePermission("A.t1") or
       WritePermission("x.y.A.t1") if class A is not in the same module as
       where you instantiate the class.

       Note that this holds only if you use attributes "specificReadPermission"
       and "specificWritePermission" as booleans. When defining named
       (string) permissions, for referring to it you simply use those strings,
       you do not create instances of ReadPermission or WritePermission.'''

    def __init__(self, fieldDescriptor):
        self.fieldDescriptor = fieldDescriptor

    def getName(self, wf, appName):
        '''Returns the name of this permission'''
        className, fieldName = self.fieldDescriptor.rsplit('.', 1)
        if className.find('.') == -1:
            # The related class resides in the same module as the workflow
            fullClassName= '%s_%s' % (wf.__module__.replace('.', '_'),className)
        else:
            # className contains the full package name of the class
            fullClassName = className.replace('.', '_')
        # Read or Write ?
        if self.__class__.__name__ == 'ReadPermission': access = 'Read'
        else: access = 'Write'
        return '%s: %s %s %s' % (appName, access, fullClassName, fieldName)

class ReadPermission(Permission): pass
class WritePermission(Permission): pass

# Standard workflows -----------------------------------------------------------
class WorkflowAnonymous:
    '''One-state workflow allowing anyone to consult and Manager to edit'''
    ma = 'Manager'
    o = 'Owner'
    everyone = (ma, 'Anonymous', 'Authenticated')
    active = State({r:everyone, w:(ma, o), d:(ma, o)}, initial=True)

class WorkflowAuthenticated:
    '''One-state workflow allowing authenticated users to consult and Manager
       to edit.'''
    ma = 'Manager'
    o = 'Owner'
    authenticated = (ma, 'Authenticated')
    active = State({r:authenticated, w:(ma, o), d:(ma, o)}, initial=True)

class WorkflowOwner:
    '''Workflow allowing only manager and owner to consult and edit'''
    ma = 'Manager'
    o = 'Owner'
    # States
    active = State({r:(ma, o), w:(ma, o), d:ma}, initial=True)
    inactive = State({r:(ma, o), w:ma, d:ma})
    # Transitions
    def doDeactivate(self, obj):
        '''Prevent user "admin" from being deactivated'''
        if isinstance(obj, User) and (obj.login == 'admin'):
            raise WorkflowException('Cannot deactivate admin.')
    deactivate = Transition( (active, inactive), condition=ma,
                             action=doDeactivate)
    reactivate = Transition( (inactive, active), condition=ma)
# ------------------------------------------------------------------------------
