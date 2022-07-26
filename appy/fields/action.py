# ~license~
# ------------------------------------------------------------------------------
try:
    from zExceptions import BadRequest
except ImportError:
    pass # If Zope is not there

import os.path
from appy.fields import Field, Initiator, Layouts
from appy.px import Px
from appy.gen import utils as gutils
from appy.shared import utils as sutils

# Constants --------------------------------------------------------------------
CONFIRM_ERROR = 'When using options, a popup will already be shown, with the ' \
  'possibility to cancel the action, so it has no sense to ask a ' \
  'confirmation via attribute "confirm".'

# ------------------------------------------------------------------------------
class ActionInitiator(Initiator):
    '''Initiator used when an action triggers the creation of an object via
       field "options" (see below).'''

    def manage(self, options):
        '''Executes the action with p_options. Once this has been done,
           p_options becomes useless and is deleted.'''
        # Call the action(s) with p_options as argument (simulate a UI request)
        method = self.field.onUiRequest
        success, msg = method(self.obj.o, self.req, options=options,
                              minimal=True)
        # Remove the "options" transient object
        try:
            options.delete(unindex=False)
        except BadRequest:
            # The object may already have been deleted if the transaction has
            # been aborted by developer's code.
            pass
        # If we are back from a popup, must we force the back URL?
        if self.field.result == 'redirect':
            self.backFromPopupUrl = msg

# ------------------------------------------------------------------------------
class Multi:
    '''Management of muti-actions = actions that execute on a set of objects,
       and not on a single one.'''

    def __init__(self, back, check):
        # The DOM node to ajax-refresh once the multi-action has been executed
        self.back = back
        # The DOM node storing the un/checked objects onto which the
        # multi-action must be executed.
        self.check = check

# ------------------------------------------------------------------------------
class Action(Field):
    '''An action is a Python method that can be triggered by the user on a
       given Appy class. An action is rendered as a button.'''
    # Action-specific initiator class
    initiator = ActionInitiator

    # Getting an action is something special: disable the standard Appy
    # machinery for this.
    customGetValue = True

    # PX for viewing the Action button
    pxView = pxCell = Px('''
     <form var="isFake=field.isFake(zobj, _);
                formId='%s_%s_form' % (zobj.id, name);
                label=_('label', field=field);
                multi=multi|None;
                className=className|zobj.portal_type;
                inputTitle=field.getInputTitle(zobj, label);
                inputLabel=field.getInputLabel(label, layoutType);
                smallButtons=smallButtons|False;
                css=ztool.getButtonCss(label, smallButtons, field.render)"
           id=":formId" action=":field.getFormAction(zobj, ztool)"
           target=":field.options and 'appyIFrame' or '_self'"
           style="display:inline">

      <!-- Form fields for direct action execution -->
      <x if="not field.options and not isFake">
       <input type="hidden" name="fieldName" value=":name"/>
       <input type="hidden" name="popupComment" value=""/>
      </x>

      <!-- Form fields for creating an options instance -->
      <x if="field.options and not isFake">
       <input type="hidden" name="action" value="Create"/>
       <input type="hidden" name="className"
              value=":ztool.getPortalType(field.options)"/>
       <input type="hidden" name="popup" value="1"/>
       <input type="hidden" name="nav"
              value=":'action.%s.%s.%s'% (zobj.id, name, className)"/>
      </x>

      <!-- Form fields for multi-actions -->
      <x if="multi">
       <input type="hidden" name="multi" value="1"/>
       <input type="hidden" name="searchParams"
              value=":field.getSearchParams(req, layoutType)"/>
       <input type="hidden" name="checkedUids"/>
       <input type="hidden" name="checkedSem"/>
       <!-- The parameter starting with a star indicates to collect search
            criteria from the storage when present. -->
       <input type="hidden" name="_get_"
        value=":'form:%s:multi,searchParams,checkedUids,checkedSem,*%s' % \
                (formId, className)"/>
      </x>

      <!-- The button for executing the action -->
      <input if="not isFake" type="button" class=":css" title=":inputTitle"
             value=":inputLabel" style=":url(field.icon, bg=True)"
             onclick=":field.getOnClick(zobj,name,req,layoutType,q,multi)"/>

      <!-- ... or the fake button -->
      <input if="isFake" type="button" class=":'fake %s' % css" title=":isFake"
             value=":inputLabel" style=":url('fake', bg=True)"/>
     </form>''')

    # It is not possible to edit an action, not to search it
    pxEdit = pxSearch = ''

    def __init__(self, validator=None, multiplicity=(1,1), default=None,
      defaultOnEdit=None, show=('view', 'result'), page='main', group=None,
      layouts=None, move=0, specificReadPermission=False,
      specificWritePermission=False, width=None, height=None, maxChars=None,
      colspan=1, action=None, result='computation',
      downloadDisposition='attachment', confirm=False, master=None,
      masterValue=None, focus=False, historized=False, mapping=None,
      generateLabel=None, label=None, icon=None, view=None, cell=None,
      edit=None, xml=None, translations=None, render='button', options=None,
      fake=False):
        # Attribute "action" must hold a method or a list/tuple of methods.
        # In most cases, every method will be called without arg, but there are
        # exceptions (see parameters "options" and "confirm").
        # ----------------------------------------------------------------------
        # If the such method returns...
        # ----------------------------------------------------------------------
        #      None      | The return status is implicitly considered to be a
        #                | success and a standard translated message will be
        #                | shown to the user.
        # ----------------------------------------------------------------------
        #     success    | It is a boolean value representing the status of the
        #                | action: success (True) or failure (False). Depending
        #                | on its status, a different standard message will be
        #                | returned to the user.
        # ----------------------------------------------------------------------
        # (success, msg) | Is is a 2-tuple. The "success" part (a boolean
        #                | value) has exactly the same meaning as the
        #                | hereabove-described "success" case. The "message"
        #                | part is, in most cases (see exceptions below) a
        #                | custom translated message, potentially
        #                | XHTML-formatted, containing human-readable details
        #                | about the action success or failure.
        # ----------------------------------------------------------------------
        # When several methods are specified, their individual results will be
        # merged, ie, to return a concatenated set of messages to the user.
        # ----------------------------------------------------------------------
        self.action = action
        # ----------------------------------------------------------------------
        # Attribute "result" can hold the following values.
        # ----------------------------------------------------------------------
        # "computation"  | (the default case) the action will simply compute
        #                | things and redirect the user to the same page, with
        #                | some status message about execution of the action;
        # ----------------------------------------------------------------------
        #    "file"      | the result is the binary content of a file that the
        #                | user will download. In that case, the "message" part
        #                | of the method result must be an open file handler;
        #                | after the action has been executed, Appy will close
        #                | it;
        # ----------------------------------------------------------------------
        #   "redirect"   | the action will lead to the user being redirected to
        #                | some other page. The URL of this page must be given
        #                | in the "message" part of the method result. If
        #                | "message" is None, we can't determine where to
        #                | redirect and we will fallback to case "computation".
        # ----------------------------------------------------------------------
        self.result = result
        # If self.result is "file", the "disposition" for downloading the file
        # is defined in self.downloadDisposition and can be "attachment" or
        # "inline".
        self.downloadDisposition = downloadDisposition
        # If "confirm" is True, a popup will ask the user if he is really sure
        # about triggering this action. If "confirm" is "comment", the same
        # effect will be achieved, but the popup will contain a field allowing
        # to enter a comment; this comment will be available to self.action's
        # method(s), via a parameter named "comment".
        self.confirm = confirm
        # If no p_icon is specified, "action.png" will be used
        self.icon = icon or 'action'
        Field.__init__(self, None, (0,1), default, defaultOnEdit, show, page,
          group, layouts, move, False, True, None, False,
          specificReadPermission, specificWritePermission, width, height, None,
          colspan, master, masterValue, focus, historized, mapping,
          generateLabel, label, None, None, None, None, False, False, view,
          cell, edit, xml, translations)
        self.validable = False
        # There are various ways to render the action in the ui:
        # "button"   (the default) as a button;
        # "icon"     as an icon on layouts where compacity is a priority
        #            (ie, within lists of objects) but still as a button on the
        #            "view" layout.
        self.render = render
        # An action may receive options: once the user clicks on the action's
        # icon or button, a form is shown, allowing to choose options. In order
        # to achieve this, specify an Appy class in field "options". self.action
        # will then be called with an instance of this class in a parameter
        # named "option". After the action has been executed, this instance will
        # be deleted.
        self.options = options
        # By default, an action is performed on a single object: self.action is
        # an instance method (or a list of instance methods) executing on a
        # single instance of the class defining this action. It is also possible
        # to define an action on a list of objects being results of a search
        # (= a "multi-action"). Here are the steps to follow to define such a
        # multi-action.
        # ----------------------------------------------------------------------
        #  1 | Define an Action field on your class, with its "show" attribute
        #    | being "query" (or a method returning it) in order to tell Appy
        #    | that the action will not be rendered on an object's standard
        #    | layout ("view", "cell"...) but on the "query" layout,
        #    | representing the page displaying search results.
        #    | 
        #    | If you choose to define a method in "show", it must be an
        #    | instance method as usual, but the method will be called with the
        #    | tool as single arg, instead of an instance of your class. In
        #    | order to clearly identify this little cheat, name this first arg
        #    | "tool" instead of "self".
        # ----------------------------------------------------------------------
        #  2 | Defining an action field on the 'query' layout, as explained in
        #    | the previous step, prevents the field from being shown on the
        #    | standard object's layouts, but does not automatically display the
        #    | action on search results from all searches defined in your class.
        #    | In order to "activate" the action on a given search, you must
        #    | explicitly declare it in attribute "actions" of your search.
        #    |
        #    | Here is an example.
        #    |
        #    | Class Invoice:
        #    |    warnClient = Action(show='query', action=lambda...)
        #    |    search = [Search('paid', state='paid'),
        #    |              Search('unpaid', state='unpaid',
        #    |                     actions=(warnClient,))]
        #    |
        #    | In this example, action "warnClient" allowing to send a mail to
        #    | clients having not paid their invoices yet are shown only on
        #    | search results for the search displaying unpaid invoices, but not
        #    | on the one showing paid invoices.
        #    |
        #    | If, conversely, you want to define an action on all searches of a
        #    | given class, here is the recommended technique.
        #    |
        #    | Class A:
        #    |    sendInfo = Action(show='query', action=lambda...)
        #    |    p = {actions: (sendInfo,)}
        #    |    search = [Search('paid', state='paid', **p),
        #    |              Search('unpaid', state='unpaid', **p)]
        #    |    # For advanced and live searches
        #    |    searchAdvanced = Search('advanced', **p)
        #    |
        #    | Finally, if your class defines dynamic searches (via static
        #    | method getDynamicSearches), you have full control on the creation
        #    | of the Search instances: it is up to you to add or not "actions"
        #    | parameters when appropriate. Recall that attribute
        #    | "searchAdvanced" can itself be dynamic: it can be defined as a
        #    | static method accepting the tool as unique arg.
        # ----------------------------------------------------------------------
        #  3 | The method(s) defined in p_self.action will have these
        #    | particularities:
        #    | - as for a "show" method, it will receive the tool as first arg,
        #    |   and not an instance of your class;
        #    | - it will receive a list of objects (= the search results), in an
        #    |   arg that must be named "objects".
        #    | Moreover, if your search is defined with checkboxes=True, your
        #    | method(s) "objects" will contain only objects being checked in
        #    | the UI.
        # ----------------------------------------------------------------------
        # Note that you can use a multi-action having an "options" attribute. In
        # that case, method(s) in parameter "action" must both have args
        # "options" and "objects".
        # ----------------------------------------------------------------------
        # If the action can't be executed, but, instead of not showing the
        # corresponding button at all in the UI, you prefer to show a "fake"
        # button with an explanation about why the action can't be currently
        # performed, place a method in attribute "fake", accepting no arg and
        # returning True when such fake button must be shown.
        self.fake = fake
        # Ensure validity of parameter values
        self.checkParameters()

    def checkParameters(self):
        '''Ensures this Action is correctly defined'''
        # Currently, "result" cannot be "file" if options exist. Indeed, when
        # options are in use, the process of executing and finalizing the action
        # is managed by the object creation mechanism, that has limitations.
        if self.options:
            if self.confirm: raise Exception(CONFIRM_ERROR)

    def getDefaultLayouts(self): return Layouts.Action.b

    def renderLabel(self, layoutType):
        return # Label is rendered directly within the button

    def getFormAction(self, zobj, ztool):
        '''Get the value of the "action" parameter to the "form" tag
           representing the action.'''
        if self.options:
            # Submitting the form will lead to creating an object, in order to
            # retrieve action's options.
            return '%s/do' % ztool.absolute_url()
        else:
            # Submitting the form will really trigger the action
            return '%s/onExecuteAction' % zobj.absolute_url()

    def getOnClick(self, zobj, name, req, layoutType, q, multi):
        '''Gets the JS code to execute when the action button is clicked'''
        # Determine the ID of the form to submit
        formId = '%s_%s_form' % (zobj.id, name)
        # Determine the back hook and check hook (if multi)
        if multi:
            back = multi.back
            check = multi.check
        else:
            back = (layoutType == 'cell') and zobj.id or None
            check = None
        check = check and q(check) or 'null'
        if not self.options:
            # Determine the parameters for executing the action
            showComment = (self.confirm == 'comment') and 'true' or 'false'
            confirmText = self.getConfirmText(zobj)
            back = back and q(back) or 'null'
            # If the action produces a file, the page will not be refreshed. So
            # the action must remain visible: if, as it is done by default, it
            # is replaced with some animation to avoid double-clicks, the
            # original button will not be rendered back once the file will be
            # downloaded.
            visible = (self.result == 'file') and 'true' or 'false'
            js = 'submitForm(%s,%s,%s,%s,%s,%s)' % \
                 (q(formId), q(confirmText), showComment, back, check, visible)
        else:
            # Determine the parameters for creating an options instance
            target = gutils.LinkTarget(klass=self.options,
                                       forcePopup=True, back=back)
            js = '%s; submitForm(%s,null,null,null,%s)' % \
                 (target.onClick, q(formId), check)
        return js

    def getTargetObjects(self, obj, req):
        '''In the context of a multi-action, retrieve the list of target objects
           onto which the action must be applied.'''
        # If semantics indicates that checked objects must be kept, retrieve
        # these objects.
        tool = obj.tool
        ids, unchecked = self.getCheckedInfo(req)
        if not unchecked:
            r = []
            for id in ids:
                cobj = tool.getObject(id)
                if cobj: # The object may have been deleted in the meanwhile
                    r.append(cobj)
            return r
        # Get all the potential target objects, from a Search or Ref
        searchParams = req['searchParams']
        if searchParams:
            # Re-trigger the search
            r = self.getSearchResults(tool.o, req['searchParams'])
        else:
            # Get objets from a ref
            r = getattr(obj, req['fieldName'].split('*',1)[0])
        # Remove those not being checked in the UI
        self.keepCheckedResults(req, r, unchecked=ids)
        return r

    def __call__(self, obj, options=None):
        '''Calls the action on p_obj. Returns a tuple (b_success, s_message)'''
        # Get args to give to method(s) in self.action
        args = {}
        # Is that a multi-action? A multi-action is an action to perform on a
        # list of objects instead of a single object.
        req = obj.request
        multi = req.get('multi') == '1'
        if options: args['options'] = options
        if self.confirm == 'comment':
            args['comment'] = req.get('popupComment')
        if multi:
            args['objects'] = self.getTargetObjects(obj, req)
        # Call method(s) in self.action
        if type(self.action) in sutils.sequenceTypes:
            # There are multiple methods
            res = [True, '']
            for act in self.action:
                actRes = act(obj, **args)
                if type(actRes) in sutils.sequenceTypes:
                    res[0] = res[0] and actRes[0]
                    if self.result.startswith('file'):
                        res[1] = res[1] + actRes[1]
                    else:
                        res[1] = res[1] + '\n' + actRes[1]
                else:
                    res[0] = res[0] and actRes
        else:
            # There is only one method
            actRes = self.action(obj, **args)
            if type(actRes) in sutils.sequenceTypes:
                res = list(actRes)
            else:
                res = [actRes, '']
        # If res is None (ie the user-defined action did not return anything),
        # we consider the action as successfull.
        if res[0] is None: res[0] = True
        # Historize the action when relevant
        if res[0] and self.historized:
            historized = self.getAttribute(obj, 'historized')
            if historized:
                obj.o.addHistoryEvent('_action%s_' % self.name,
                                      comments=args.get('comment'))
        return res

    def getValue(self, obj, name=None, layout=None):
        '''Call the action and return the result'''
        return self(obj.appy())

    # There is no stored value for an action
    def getStoredValue(self, obj, name=None, fromRequest=False): return

    def isShowable(self, obj, layoutType):
        if layoutType == 'edit': return
        return Field.isShowable(self, obj, layoutType)

    def isFake(self, zobj, _):
        '''Must the shown button be a fake button ? If yes, the return value is
           the message to show with the fake button.'''
        if not self.fake: return
        msg = self.getAttribute(zobj.appy(), 'fake')
        if msg and not isinstance(msg, basestring):
            msg = _('action_unexecutable')
        return msg

    def getInputTitle(self, obj, label):
        '''Returns the content of attribute "title" for the "input" field
           corresponding to the action in the ui.'''
        if not self.hasDescr: return label
        return '%s: %s' % (label, obj.translate(self.descrId))

    def getInputLabel(self, label, layoutType):
        '''Returns the label to display on the button corresponding to this
           action = the content of attribute "value" for the "input" field.'''
        # An icon is a button rendered without "value", excepted on the "view"
        # layout, where we still display it.
        if (self.render == 'icon') and (layoutType != 'view'): return ''
        return label

    def getConfirmText(self, zobj):
        '''Get the text to display in the confirm popup'''
        if not self.confirm: return ''
        _ = zobj.translate
        return _(self.labelId + '_confirm', blankOnError=True) or \
               _('action_confirm')

    # Action fields can a priori be shown on every layout, "buttons" included
    def isRenderable(self, layoutType): return True

    def onUiRequest(self, obj, rq, options=None, minimal=False):
        '''This method is called when a user triggers the execution of this
           action from the user interface.'''
        # Execute the action (method __call__)
        actionRes = self(obj.appy(), options=options)
        # Unwrap action results
        success, msg = actionRes
        result = self.result
        if not msg:
            # Use the default i18n messages
            suffix = success and 'done' or 'ko'
            msg = obj.translate('action_%s' % suffix)
            # If we had to redirect the user, we have no URL to do that; so we
            # fall back to a computation.
            if result == 'redirect': result = 'computation'
        elif result == 'file':
            # msg does not contain a message, but a Python file handler
            content = msg.read()
            response = rq.RESPONSE
            if rq.get('popup') == '1':
                # We are serving a file from the popup,that will need to be
                # closed afterwards.
                response.setCookie('closePopup', 'yes', path='/')
                obj.setMessageCookie()
            header = response.setHeader
            header('Content-Type', sutils.getMimeType(msg.name))
            header('Content-Length', len(content))
            header('Content-Disposition', '%s;filename="%s"' % \
                         (self.downloadDisposition, os.path.basename(msg.name)))
            header('Accept-Ranges', 'none')
            response.write(content)
            msg.close()
        # Stop here if p_minimal is True
        if minimal: return success, msg
        if (result == 'computation') or not success:
            # If we are called from an Ajax request, simply return msg
            if hasattr(rq, 'pxContext') and rq.pxContext['ajax']: return msg
            obj.say(msg)
            return obj.goto(obj.getUrl(obj.getReferer()))
        elif result == 'redirect':
            # msg does not contain a message, but the URL where to redirect
            # the user. Redirecting is different if we are in an Ajax request.
            if hasattr(rq, 'pxContext') and rq.pxContext['ajax']:
                rq.RESPONSE.setHeader('Appy-Redirect', msg)
                obj.setMessageCookie()
            else:
                return obj.goto(msg)

    def getMulti(self, back, check):
        '''In the context of a multi-action, create and return a Multi instance
           defining useful info about the action, like the back and check
           hooks.'''
        return Multi(back, check)
# ------------------------------------------------------------------------------
