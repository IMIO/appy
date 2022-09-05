#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import os.path
from appy.px import Px
from appy import utils
from appy.ui import LinkTarget
from appy.ui.layout import Layouts
from appy.model.searches import Search
from appy.model.fields import Field, Initiator, Show

# Constants  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
CONF_ERR  = 'When using options, a popup will already be shown, with the ' \
            'possibility to cancel the action, so it has no sense to ask a ' \
            'confirmation via attribute "confirm".'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class ActionInitiator(Initiator):
    '''Initiator used when an action triggers the creation of an object via
       field "options" (see below).'''

    def manage(self, options):
        '''Executes the action with p_options. Once this has been done,
           p_options becomes useless and is deleted.'''
        # Call the action(s) with p_options as argument
        field = self.field
        msg = field.perform(self.o, options=options, minimal=True)
        # Remove the "options" transient object
        try:
            options.delete()
        except KeyError:
            # The object may already have been deleted if the transaction has
            # been aborted by developer's code.
            pass
        # If we are back from a popup, must we force the back URL ?
        if field.result == 'redirect':
            self.backFromPopupUrl = msg
            r = None
        else:
            r = msg
        return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Multi:
    '''Management of muti-actions = actions that execute on a set of objects,
       and not on a single one.'''

    def __init__(self, back, check):
        # The DOM node to ajax-refresh once the multi-action has been executed
        self.back = back
        # The DOM node storing the un/checked objects onto which the
        # multi-action must be executed.
        self.check = check

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Action(Field):
    '''An action is a Python method that can be triggered by the user on a
       given Appy class. An action is rendered as a button or icon.'''

    # Some methods will be traversable
    traverse = Field.traverse.copy()

    # Action-specific initiator class
    initiator = ActionInitiator

    # Getting an action is something special: disable the standard Appy
    # machinery for this.
    customGetValue = True

    class Layouts(Layouts):
        '''Action-specific layouts'''
        b = Layouts(edit='lf', view='lf')
        c = Layouts(view='f|')

        @classmethod
        def getDefault(class_, field):
            '''Default layouts for this Action p_field'''
            return class_.b

    # The button allowing to trigger the action
    pxButton = Px('''
     <!-- Real button -->
     <input if="not isFake" type="button" class=":css" title=":inputTitle"
            value=":inputLabel" style=":field.getIconUrl(url, asBG=True)"
            onclick=":field.getOnClick(_ctx_)"/>

     <!-- Fake button -->
     <input if="isFake" type="button" class=":'%s fake' % css"
            title=":isFake" value=":inputLabel"
            style=":field.getIconUrl(url, asBG=True)"/>''')

    # PX for viewing the Action button
    view = cell = buttons = query = Px('''
     <form var="isFake=field.isFake(o, _);  
                formId='%d_%s_form' % (o.iid, name);
                label=_('label', field=field);
                multi=multi|None;
                className=className|o.class_.name;
                inputTitle=field.getInputTitle(o, label);
                inputLabel=field.getInputLabel(label, layout);
                onCell=layout in field.cellLayouts;
                picto=picto|'pictoB';
                asPicto=not onCell and (picto != 'pictoB');
                css=ui.Button.getCss(label, onCell, field.render,
                                     iconOut=field.iconOut)"
        id=":formId" action=":field.getFormAction(o, tool, layout)"
        target=":field.options and 'appyIFrame' or '_self'"
        method="post" class="inline">

      <!-- Form fields for direct action execution -->
      <x if="not field.options and not isFake">
       <input type="hidden" name="popupComment" value=""/>
      </x>

      <!-- Form fields for creating an options instance -->
      <x if="field.options and not isFake">
       <input type="hidden" name="className" value=":field.options.__name__"/>
       <input type="hidden" name="popup" value="True"/>
       <input type="hidden" name="nav"
              value=":'action.%d.%s.%s' % (o.iid, name, className)"/>
      </x>

      <!-- Form fields for multi-actions -->
      <x if="multi">
       <input type="hidden" name="multi" value="True"/>
       <input type="hidden" name="searchParams"
              value=":tool.Search.encodeForReplay(req, layout)"/>
       <input type="hidden" name="checkedIds"/>
       <input type="hidden" name="checkedSem"/>
       <!-- The parameter starting with a star indicates to collect search
            criteria from the storage when present. -->
       <input type="hidden" name="_get_"
        value=":'form:%s:multi,searchParams,checkedIds,checkedSem,*%s' % \
                (formId, className)"/>
      </x>

      <!-- As picto -->
      <a if="asPicto" class=":'help fake' if isFake else 'clickable'"
         title=":isFake if isFake else ''"
         onclick=":field.getOnClick(_ctx_) if not isFake else ''">
       <img src=":url(field.icon, base=field.iconBase, ram=field.iconRam)"
            class=":picto"/>
       <div style=":'display:%s' % config.ui.pageDisplay">::inputTitle</div>
      </a>

      <!-- As button -->
      <x if="not asPicto">

       <!-- Variant with the icon outside the button -->
       <div if="field.iconOut" class="iflex1">
        <img src=":field.getIconUrl(url)" onclick="this.nextSibling.click()"
             class=":'clickable %s' % field.iconCss" title=":label"/>
        <x>:field.pxButton</x>
       </div>

       <!-- Variant with the icon inside the button -->
       <x if="not field.iconOut">:field.pxButton</x>
      </x>
     </form>''')

    # It is not possible to edit an action, not to search it
    edit = search = ''

    def __init__(self, validator=None, multiplicity=(1,1), default=None,
      defaultOnEdit=None, show=Show.TR, renderable=None, page='main',
      group=None, layouts=None, move=0, readPermission='read',
      writePermission='write', width=None, height=None, maxChars=None,
      colspan=1, action=None, result='computation',
      downloadDisposition='attachment', confirm=False, master=None,
      masterValue=None, focus=False, historized=False, mapping=None,
      generateLabel=None, label=None, icon=None, sicon=None, view=None,
      cell=None, buttons=None, edit=None, xml=None, translations=None,
      render='button', iconOut=False, iconCss='iconS', iconSize=None,
      options=None, fake=False):
        # Attribute "action" must hold a method or a list/tuple of methods.
        # In most cases, every method will be called without arg, but there are
        # exceptions (see parameters "options" and "confirm").
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # If the such method returns...
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #      None      | The return status is implicitly considered to be a
        #                | success and a standard translated message will be
        #                | shown to the user.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #     success    | It is a boolean value representing the status of the
        #                | action: success (True) or failure (False). Depending
        #                | on its status, a different standard message will be
        #                | returned to the user.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # (success, msg) | Is is a 2-tuple. The "success" part (a boolean
        #                | value) has exactly the same meaning as the
        #                | hereabove-described "success" case. The "message"
        #                | part is, in most cases (see exceptions below) a
        #                | custom translated message, potentially
        #                | XHTML-formatted, containing human-readable details
        #                | about the action success or failure.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # When several methods are specified, their individual results will be
        # merged, ie, to return a concatenated set of messages to the user.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.action = action

        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # Attribute "result" can hold the following values.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "computation"  | (the default case) the action will simply compute
        #                | things and redirect the user to the same page, with
        #                | some status message about execution of the action;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #    "file"      | the result is the binary content of a file that the
        #                | user will download. In that case, the "message" part
        #                | of the method result must be an open file handler;
        #                | after the action has been executed, Appy will close
        #                | it;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   "redirect"   | the action will lead to the user being redirected to
        #                | some other page. The URL of this page must be given
        #                | in the "message" part of the method result. If
        #                | "message" is None, we can't determine where to
        #                | redirect and we will fallback to case "computation".
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
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

        # If you want to use a specific (SVG) icon for this action, store it in
        # folder <yourApp>/static and set its name (ie "myimage.svg") in
        # parameter "icon". Optimized SVG images are recommended. You can use
        # another image format (ie, PNG); in that case, though, you must prefix
        # the image name with you app name. For example, if your app is named
        # "MyApp" and your icon is MyApp/static/myimage.png, attribute "icon"
        # must hold "MyApp/myimage.png". If you do not specify any image,
        # default icon action.svg will be used (it is stored in appy/ui/static).
        icon = icon or 'action.svg'
        self.icon, self.iconBase, self.iconRam = utils.iconParts(icon)

        # You may specify, in attribute "sicon", an alternate icon suitable when
        # rendered as a small icon. Optimized SVG images are recommended.
        sicon = sicon or icon or 'action.svg'
        self.sicon, self.siconBase, self.siconRam = utils.iconParts(sicon)

        # Call the base constructor
        Field.__init__(self, None, (0,1), default, defaultOnEdit, show,
          renderable, page, group, layouts, move, False, True, None, None,
          False, None, readPermission, writePermission, width, height, None,
          colspan, master, masterValue, focus, historized, mapping,
          generateLabel, label, None, None, None, None, False, False, view,
          cell, buttons, edit, xml, translations)
        self.validable = False

        # There are various ways to render the action in the ui:
        # "button"   (the default) as a button (icon included);
        # "icon"     as an icon on layouts where compacity is a priority
        #            (ie, within lists of objects) but still as a button on the
        #            "view" layout.
        self.render = render

        # If p_iconOut is True, when the action is rendered as a "icon + button"
        # (p_render is "button"), the icon will be positioned outside the
        # button. Else, it will be integrated as a background-image inside it.
        # Having the icon outside the button allows for more graphical
        # possibilities (ie: the button may have a border that does not include
        # the icon).
        self.iconOut = iconOut

        # The CSS class to apply to the button icon, in "icon out" mode
        self.iconCss = iconCss

        # The icon size, in "icon in" mode, where the image is inlaid as
        # background.
        self.iconSize = iconSize or '18px 18px'

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
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
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
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  2 | Defining an action field on the "query" layout, as explained in
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
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  3 | The method(s) defined in p_self.action will have these
        #    | particularities:
        #    | - as for a "show" method, it will receive the tool as first arg,
        #    |   and not an instance of your class;
        #    | - it will receive a list of objects (= the search results), in an
        #    |   arg that must be named "objects".
        #    | Moreover, if your search is defined with checkboxes=True, your
        #    | method(s) "objects" will contain only objects being checked in
        #    | the UI.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # Note that you can use a multi-action having an "options" attribute. In
        # that case, method(s) in parameter "action" must both have args
        # "options" and "objects".
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # If the action can't be executed, but, instead of not showing the
        # corresponding button at all in the UI, you prefer to show a "fake"
        # button with an explanation about why the action can't be currently
        # performed, place a method in attribute "fake", accepting no arg and
        # returning the explanation as a string, or True if you simply want a
        # standard message to appear.
        self.fake = fake

        # Ensure validity of parameter values
        self.checkParameters()

    def checkParameters(self):
        '''Ensures this Action is correctly defined'''
        # Currently, "result" cannot be "file" if options exist. Indeed, when
        # options are in use, the process of executing and finalizing the action
        # is managed by the object creation mechanism, that has limitations.
        if self.options:
            if self.confirm: raise Exception(CONF_ERR)

    def renderLabel(self, layoutType):
        return # Label is rendered directly within the button

    def getFormAction(self, o, tool, layout):
        '''Get the value of the "action" parameter to the "form" tag
           representing the action.'''
        if self.options:
            # Submitting the form will lead to creating an object, in order to
            # retrieve action's options.
            return '%s/new' % tool.url
        else:
            # Submitting the form will really trigger the action. Add the name
            # of the class in the path if p_self is a multi-action.
            part = '@%s/' % self.container.name if layout == 'query' else ''
            return '%s/%s%s/perform' % (o.url, part, self.name)

    def getOnClick(self, ctx):
        '''Gets the JS code to execute when the action button is clicked'''
        # Determine the ID of the form to submit
        o = ctx.o
        q = ctx.q
        formId = '%d_%s_form' % (o.iid, ctx.name)
        # Determine the back hook and check hook (if multi)
        multi = ctx.multi
        if multi:
            back = multi.back
            check = multi.check
        else:
            back = ctx.ohook if ctx.layout == 'cell' else None
            check = None
        check = q(check) if check else 'null'
        if not self.options:
            # Determine the parameters for executing the action
            showComment = 'true' if self.confirm == 'comment' else 'false'
            confirmText = self.getConfirmText(o)
            back = q(back) if back else 'null'
            # If the action produces a file, the page will not be refreshed. So
            # the action must remain visible: if, as it is done by default, it
            # is replaced with some animation to avoid double-clicks, the
            # original button will not be rendered back once the file will be
            # downloaded.
            if self.result == 'file':
                visible = 'true'
                back = 'null'
            else:
                visible = 'false'
            js = 'submitForm(%s,%s,%s,%s,%s,%s)' % \
                 (q(formId), q(confirmText), showComment, back, check, visible)
        else:
            # Determine the parameters for creating an options instance
            target = LinkTarget(class_=self.options, forcePopup=True, back=back)
            js = '%s; submitForm(%s,null,null,null,%s)' % \
                 (target.onClick, q(formId), check)
        return js

    def getTargetObjects(self, o, req):
        '''In the context of a multi-action, retrieve the list of target objects
           onto which the action must be applied.'''
        # If semantics indicates that checked objects must be kept, retrieve
        # these objects.
        tool = o.tool
        ids, unchecked = Search.getCheckedInfo(req)
        if not unchecked:
            r = []
            for iid in ids:
                cobj = tool.getObject(iid)
                if cobj: # The object may have been deleted in the meanwhile
                    r.append(cobj)
            return r
        # Get all the potential target objects, from a Search or Ref
        searchParams = req.searchParams
        if searchParams:
            # Replay the search to get the list of objects
            r = Search.replay(tool, searchParams)
        else:
            # Get objets from a ref
            r = getattr(o, req.fieldName.split('*',1)[0])
        # Remove those not being checked in the UI
        Search.keepCheckedResults(req, r, unchecked=ids)
        return r

    def execute(self, o, options=None):
        '''Execute the action on p_o. Returns a tuple (b_success, s_message)'''
        # Get args to give to method(s) in self.action
        args = {}
        req = o.req
        if options: args['options'] = options
        if self.confirm == 'comment':
            args['comment'] = o.req.popupComment
        # Is that a multi-action ? A multi-action is an action to perform on a
        # list of objects instead of a single object.
        if req.multi:
            args['objects'] = self.getTargetObjects(o, req)
        # Call method(s) in self.action
        if type(self.action) in utils.sequenceTypes:
            # There are multiple methods
            r = [True, '']
            for act in self.action:
                res = act(o, **args)
                if type(res) in utils.sequenceTypes:
                    r[0] = r[0] and res[0]
                    if self.result.startswith('file'):
                        r[1] = r[1] + res[1]
                    else:
                        r[1] = r[1] + '\n' + res[1]
                else:
                    r[0] = r[0] and res
        else:
            # There is only one method
            res = self.action(o, **args)
            if type(res) in utils.sequenceTypes:
                r = list(res)
            else:
                r = [res, '']
        # If res is None (ie the user-defined action did not return anything),
        # we consider the action as successfull.
        if r[0] is None: r[0] = True
        # Historize the action when relevant
        if r[0] and self.historized:
            historized = self.getAttribute(o, 'historized')
            if historized:
                o.history.add('Action', action=self.name,
                              comment=args.get('comment'))
        return r

    def getValue(self, o, name=None, layout=None, single=None):
        '''Call the action and return the result'''
        return self(o)

    # There is no stored value for an action
    def getStoredValue(self, o, name=None, fromRequest=False): return

    def isShowable(self, o, layout):
        '''Never show actions on an "edit" p_layout'''
        return False if layout == 'edit' else super().isShowable(o, layout)

    def isFake(self, o, _):
        '''Must the shown button be a fake button ? If yes, the return value is
           the message to show with the fake button.'''
        if not self.fake: return
        msg = self.getAttribute(o, 'fake')
        if msg and not isinstance(msg, str):
            msg = _('action_unexecutable')
        return msg

    def getInputTitle(self, o, label):
        '''Returns the content of attribute "title" for the "input" field
           corresponding to the action in the ui.'''
        if not self.hasDescr: return label
        return '%s: %s' % (label, o.translate(self.descrId))

    def getIconUrl(self, url, pre='s', asBG=False):
        '''Returns the URL to p_self's (s)icon (depending on p_pre(fix)), to be
           used as a background image or not (depending on p_asBG).'''
        # In "icon out" mode, no background image must be present
        if asBG and self.iconOut: return ''
        # If p_asBG, get the background image dimensions
        bg = self.iconSize if asBG else False
        return url(getattr(self, '%sicon' % pre),
                   base=getattr(self, '%siconBase' % pre),
                   ram=getattr(self, '%siconRam' % pre), bg=bg)

    def getInputLabel(self, label, layout):
        '''Returns the label to display on the button corresponding to this
           action = the content of attribute "value" for the "input" field.'''
        # An icon is a button rendered without "value", excepted on the "view"
        # layout, where we still display it.
        if self.render == 'icon' and layout != 'view': return ''
        return label

    def getConfirmText(self, o):
        '''Get the text to display in the confirm popup'''
        if not self.confirm: return ''
        _ = o.translate
        return _(self.labelId + '_confirm', blankOnError=True) or \
               _('action_confirm')

    def isRenderableOn(self, layout):
        '''Action fields can be rendered on "button" but not on "top" layouts'''
        return layout not in Layouts.topLayouts

    traverse['perform'] = 'perm:write'
    def perform(self, o, options=None, minimal=False):
        '''Called when the action is triggered from the UI'''
        result = self.result
        # Most actions will update the database
        handler = o.H()
        handler.commit = result != 'file'
        resp = o.resp
        # Execute the action
        success, msg = self.execute(o, options=options)
        if not msg:
            # Use the default i18n message, if no message has been dumped yet on
            # the response object.
            if not resp.message:
                suffix = 'done' if success else 'ko'
                msg = o.translate('action_%s' % suffix)
            # If we had to redirect the user, we have no URL to do that; so we
            # fall back to a computation.
            result = 'computation' if result == 'redirect' else result
            r = msg
        elif result == 'file':
            # v_msg does not contain a message, but a Python file handler
            r = msg.read()
            # If we are serving a file from the popup, close it afterwards
            if o.req.popup: resp.setCookie('closePopup', 'yes')
            header = resp.setHeader
            header('Content-Type', utils.getMimeType(msg.name))
            header('Content-Disposition', '%s;filename="%s"' % \
                   (self.downloadDisposition, os.path.basename(msg.name)))
            msg.close()
        else:
            r = msg
        # Stop here if p_minimal is True
        if minimal: return r
        if result == 'computation' or not success:
            # If we are called from an Ajax request, simply return msg
            if handler.isAjax():
                r = msg
            else:
                # The object may have been deleted by the action
                exists = o.getObject(o.id)
                url = o.tool.computeHomePage() if not exists else None
                r = o.goto(url=url, message=msg)
            return r
        elif result == 'redirect':
            # msg does not contain a message, but the URL where to redirect
            # the user. Redirecting is different if we are in an Ajax request.
            if handler.isAjax():
                o.resp.setHeader('Appy-Redirect', msg)
            else:
                return o.goto(msg)
        else:
            return r

    def getMulti(self, back, check):
        '''In the context of a multi-action, create and return a Multi instance
           defining useful info about the action, like the back and check
           hooks.'''
        return Multi(back, check)

    def setTraversable(self, allow='perm:read'):
        '''By default, the URL allowing to trigger an action (/perform) is
           accessible only to those having permission 'write' on the
           corresponding object. This method allows to update this and open the
           action to anyone having this p_allow condition.'''
        self.traverse = t = Action.traverse.copy()
        t['perform'] = t['storeFromAjax'] = allow
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
