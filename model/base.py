#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import persistent

from appy.px import Px
from appy.ui import Iframe
from appy.ui.layout import Layout
from appy.model.fields import Show
from appy.database.lock import Lock
from appy.ui.template import Template
from appy.ui.criteria import Criteria
from appy.model.fields.ref import Ref
from appy.ui.validate import Validator
from appy.model.searches import Search
from appy.model.fields.text import Text
from appy.model.fields.date import Date
from appy.model.utils import Object as O
from appy.database.catalog import Catalog
from appy.xml.marshaller import Marshaller
from appy.model.fields.string import String
from appy.model.fields.action import Action
from appy.model.fields.python import Python
from appy.model.fields.computed import Computed
from appy.model.workflow.history import History
from appy.model.fields.phase import Page, UiPhases
from appy.utils import multicall, MessageException
from appy.model.workflow import standard as workflows
from appy.model.fields.select import Select, Selection
from appy.utils.string import Normalize, produceNiceMessage

# Errors - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
RO_EXPR     = 'This is a read-only property: you cannot set a value for it.'
FIELD_KO    = 'Field "%s" on class "%s" does not exist.'
MISS_CLS    = '"new" called without class name.'
REF_INS_KO  = 'Param "insert" for Ref field %s is None.'
CONT_ERR    = "Container can't be retrieved that way."
INDEX_TEMP  = "A temp object can't be (un)indexed."
CATALOG_KO  = 'Catalog not found for %s instance.'
NO_ID       = 'Call to getObject with no ID.'
NO_STR      = 'Specify the name of the class as a string.'
F_FREEZ_KO  = 'Field "%s" is not (un)freezable.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Base:
    '''Base class for any Appy class'''

    # Make some elements available here
    Lock = Lock
    Search = Search

    # Some elements will be traversed
    traverse = {'history': True, 'Search': True}

    # The default workflow for a class that does not define one
    workflow = workflows.Anonymous

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                             Fields
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # The following fields are base fields that apply to any class, be it a
    # class from the base Appy model or a class (re)defined in the app.

    # Field "searchable" defines an index containing keywords collected from all
    # other object fields having attribute searchable=True.
    def getSearchableText(self):
        '''Collects and returns keywords as defined on every field being
           "searchable".'''
        r = []
        for field in self.class_.fields.values():
            if not field.searchable: continue
            val = field.getIndexValue(self, searchable=True)
            if val:
                r.append(val)
        return ' '.join(r)

    searchableAttributes = {'show': False, 'persist':False, 'indexed':True,
      'default': getSearchableText, 'label':'Base', 'page': None}

    searchable = Text(**searchableAttributes)

    # Attribute "title" is a mandatory field used at various places by default,
    # for displaying base information about an object.
    titleAttributes = {'multiplicity': (1,1), 'show': Show.EX, 'indexed': True,
      'searchable': True, 'filterField': searchable,
      # The following lambda allows to produce an index value suitable for
      # sorting. In the call to m_getShownValue, language 'en' is forced in
      # order to bypass the user language and always have a deterministic value.
      'indexValue': lambda o, v:
         Normalize.sortable(o.getShownValue(language='en')) if v else ''}

    title = String(**titleAttributes)

    # Attribute "creator" gets the login of the user having created the object
    p = {'multiplicity': (1,1), 'show': 'xml', 'indexed': True, 'label': 'Base'}
    creator = Computed(method=lambda o: o.history[-1].login, **p)

    def setCreator(self, login):
        '''Sets p_login as p_self's creator'''
        self.history[-1].login = login

    def getCreator(self, title=True):
        '''Return the User instance (or its p_title) behind p_self.creator'''
        return self.history[-1].getUser(self, title=title)

    # Object's creation and last modification dates
    p['show'] = Show.VE_
    created = Date(default=lambda o: o.history[-1].date, persist=False, **p)
    modified = Date(default=lambda o: o.history.modified, persist=False, **p)

    # "state" is a field deduced from the object history and identifies the
    # object state according to its workflow. It must be a "select" field,
    # because it will be necessary for displaying the translated state name.
    stateAttributes = {
      'validator': Selection(lambda o: o.getWorkflow().listStates(o)),
      'svalidator': Selection(lambda tool, c: c.workflow.listStates(tool)),
      'show': 'result', 'default': lambda o: o.history[0].state,
      'persist': False, 'indexed': True, 'height': 5, 'label':'Base'
    }

    state = Select(**stateAttributes)

    # Field "allowed" defines an index storing the list of roles and users being
    # allowed to view this object. It will be used within catalog searches with
    # attribute "secure" being "True", for filtering objects the user is allowed
    # to see.
    def getAllowed(self):
        '''Returns the list of roles and users which are granted read access to
           this object.'''
        allowedRoles = self.getWorkflow().getRolesFor(self, 'read')
        if self.localRoles.only:
            # The roles will not be mentioned as-is
            r = []
        else:
            r = list(allowedRoles.keys())
        # Add users or groups having, locally, this role on this object
        for id, roles in self.localRoles.items():
            for role in roles:
                if role in allowedRoles:
                    usr = 'user:%s' % id
                    if usr not in r: r.append(usr)
        return r

    allowed = Select(multiplicity=(0, None), show=False, persist=False,
                     indexed=True, default=getAllowed, label='Base')

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                             History
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    recordAttributes = {'method': History.view, 'label':'Base', 'layouts':'f',
      'xml': lambda o, value: o.history,
      'show': lambda o: Show.VX if o.user.hasRole('Manager') else None,
      'page':Page('history', label='Base_page_history',
                  sticky=True, icon='history.svg',
                  show=lambda o: 'view' if o.user.hasRole('Manager') else None)}

    record = Computed(**recordAttributes)

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                        UI Python interpreter
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    interpreter = Python(label='Base', layouts='f',
      page=Page('python', label='Base_page_python', sticky=True,
                show=lambda o: 'view' if o.user.login == 'admin' else None,
                icon='python.svg'))

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                            Properties
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # The following properties are read-only attributes allowing easy access,
    # from any object in the database, to (i) a series of heavily-demanded
    # objects, like the tool or the currently logged user, or (ii) commonly
    # used functions.

    # ~~~ All these properties will have this setter, raising an exception
    def raiseReadOnly(self, v): raise Exception(RO_EXPR)

    # The guard
    guard = property(lambda o: o.H().guard, raiseReadOnly)

    # The currently logged user
    user = property(lambda o: o.H().guard.user, raiseReadOnly)

    # The unique Tool instance
    tool = property(lambda o: o.H().tool, raiseReadOnly)

    # Get the appy.model.meta.Class for this instance
    class_ = property(lambda o: o.getClass(), raiseReadOnly)

    # Get the apps' configuration
    config = property(lambda o: o.H().config, raiseReadOnly)

    # The request and response objects
    req = property(lambda o: o.H().req, raiseReadOnly)
    resp = property(lambda o: o.H().resp, raiseReadOnly)

    # The object (base) URL
    url = property(lambda o: o.H().server.getUrl(o), raiseReadOnly)

    # An access to the developer's cache object, stored on the handler
    cache = property(lambda o: o.H().cache, raiseReadOnly)

    # A potential initiator object
    initiator = property(lambda o: o.getInitiator(), raiseReadOnly)

    # The referer URL
    referer = property(lambda o: o.H().headers['Referer'], raiseReadOnly)

    # The object container
    container = property(lambda o:o.getContainer(objectOnly=True),raiseReadOnly)

    # The app model
    model = property(lambda o: o.H().server.model, raiseReadOnly)

    # The site URL
    siteUrl = property(lambda o: o.config.server.getUrl(o.H()), raiseReadOnly)

    # The path to the app folder
    appPath = property(lambda o: o.H().config.model.appPath, raiseReadOnly)

    # The current traversal
    traversal = property(lambda o: o.H().traversal, raiseReadOnly)

    # The translated name of the current object state
    stateLabel = property(lambda o: o.getLabel(o.state, field=False))

    # The catalog storing indexed data for this object
    traverse['catalog'] = 'Manager'
    catalog = property(lambda o: o.getCatalog(), raiseReadOnly)

    # A reference the the database object
    database = property(lambda o: o.H().server.database, raiseReadOnly)

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                            Base methods
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def getHandler(self):
        '''Returns the current request handler'''
        # Class "Handler" has been injected to class Base in Base.Handler in
        # appy.server.handler in order to avoid circular dependencies.
        return Base.Handler.get()

    # This method is used so often that it deserves a short name
    H = getHandler

    def getClass(self):
        '''Get the appy.model.meta.Class corresponding to p_self'''
        classes = self.H().server.model.classes
        name = self.__class__.__bases__[0].__name__
        return classes.get(name)

    def getWorkflow(self, python=False):
        '''Get the appy.model.meta.Workflow corresponding to p_self, or the True
           Python class if p_python is True)'''
        r = self.getClass().workflow
        return r.python if python else r

    def do(self, name, comment=None, doAction=True, doHistory=True,
           secure=False, doSay=False, data=None):
        '''Programmatically triggers on p_self a transition named p_name'''
        # p_data can be a dict that will be included into the history event.
        # ~~~
        # If p_doSay is True, it will not lead to the UI message being
        # automatically included in the response cookie, but will allow the
        # caller to retrieve it (via the return value) and do what he wants with
        # it.
        transition = self.getWorkflow().transitions.get(name)
        return transition.trigger(self, comment=comment, doAction=doAction,
                     doHistory=doHistory, doSay=doSay, secure=secure, data=data)

    def getPageLayout(self, layout):
        '''Returns the page layout corresponding to p_layout for p_self'''
        # The layout may be forced by request parameter "pageLayout". Useful
        # when displaying an object in a particular context, ie, in a popup.
        req = self.req
        if 'pageLayout' in req:
            pl = req.pageLayout
            if not isinstance(pl, Layout):
                # A string
                if '*' in pl:
                    # A CSS class and alignment are specified
                    pl, css, align = pl.split('*')
                else:
                    css = ''
                    align = 'left'
                pl = Layout(pl, css=css, align=align)
            return pl
        # Retrieve layouts being applicable for p_self
        r = self.class_.getPageLayouts(self)[layout]
        return r if not isinstance(r, str) else Layout(r)

    def getDefaultPage(self, layout):
        '''Get p_self's default page on p_layout'''
        # The defaut page for p_layout may be customized by special methods
        # m_getDefaultViewPage and m_getDefaultEditPage.
        method = 'getDefault%sPage' % layout.capitalize()
        return getattr(self, method)() if hasattr(self, method) else 'main'

    def getCurrentPage(self, req, layout):
        '''Gets the name of the currently shown page for p_self, or a default
           page if no page is defined in the p_req(uest).'''
        # Try to get the page from the request, or return p_self's default
        # page on p_layout.
        return req.page or self.getDefaultPage(layout)

    def getObject(self, id, logMissing=False):
        '''Gets an object given its p_id'''
        if not id: raise Exception(NO_ID)
        return self.database.getObject(self.H(), id, logMissing=logMissing)

    def getRefObject(self):
        '''This method returns the source object, if we are in the context of
           performing some action (like a search) in the context of a Ref.'''
        # Information about such Ref is found in the request
        info = self.req.ref or Criteria.readFromRequest(self.H()).get('_ref')
        if not info: return
        return self.getObject(info.split(':', 1)[0])

    def getPublishedObject(self):
        '''Returns the object being currently published in the UI, if any'''
        traversal = self.traversal
        if not traversal: return
        return traversal.o

    def __repr__(self):
        '''Returns the class name and Appy object ID'''
        return '<%s id=%s>' % (self.getClass().name, self.id)

    def isTemp(self):
        '''Is this object temporary ?'''
        return self.id in self.H().dbConnection.root.temp

    def log(self, message, type='info', noUser=False):
        '''Logs a p_message of some p_type'''
        return self.H().log('app', type, message)

    def say(self, message, fleeting=None):
        '''Adds p_message to the global message returned in the response'''
        self.resp.addMessage(message, fleeting=fleeting)

    def goto(self, url=None, message=None, fromPopup=False):
        '''Return to some p_url or to the referer page. If you want to come back
           from a popup, explicitly set p_fromPopup to True.'''
        self.resp.goto(url, message, fromPopup)

    def gotoSet(self):
        '''Return True if m_goto has already been called and the response code
           is already a 303 "Redirect".'''
        return self.resp.code == 303

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                           Security methods
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def raiseUnauthorized(self, msg=None):
        '''Raise a security-related error'''
        raise self.guard.Error(msg)

    def raiseMessage(self, message):
        '''Raise a nicely-rendered error, without technical details'''
        raise MessageException(message)

    def allows(self, permission='read', raiseError=False):
        '''Check the guard's homonym method'''
        return self.guard.allows(self, permission, raiseError=raiseError)

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                            URL methods
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def buildUrl(self, name='', base=None, ram=False, bg=False):
        '''See doc in appy.server.Server::buildUrl'''
        H = self.H()
        return H.server.buildUrl(H, name=name, base=base, ram=ram, bg=bg)

    def buildSvg(self, name, bg=False):
        '''Variant of m_buildUrl being specific to SVG files. Indeed, SVG files
           are exclusively RAM-cached.'''
        # p_name must not contain the ".svg" file extension
        H = self.H()
        return H.server.buildUrl(H, '%s.svg' % name, ram=True, bg=bg)

    def getUrl(self, sub=None, **params):
        '''See doc in appy.server.Server::getUrl'''
        return self.H().server.getUrl(self, sub=sub, **params)

    def getGotoUrl(self):
        '''Get p_self's URL, at the page and layout as defined by request
           variables "gotoPage" and "gotoLayout".'''
        req = self.req
        return self.getUrl(sub=req.gotoLayout, page=req.gotoPage,
                           nav=req.nav or 'no')

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                            Field methods
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def getField(self, name, className=None, raiseError=False):
        '''Returns the field whose name is p_name. If p_className is there, get
           the field on this class instead of on p_self's class. If p_raiseError
           is True and the field is not found, an exception is raised. Else,
           None is returned.'''
        # The field with this p_name may be an inner field within an outer field
        isInner = '*' in name
        if isInner:
            parts = name.split('*')
            if len(parts) == 2: name, sub = parts
            else:               name, sub, i = parts
        # Get the class where the field definition may be found
        class_ = self.H().server.model.classes[className] if className \
                                                          else self.getClass()
        r = class_.fields.get(name)
        # Get the sub-field when relevant
        if r and isInner: r = r.getField(sub)
        # Raise an error if the field was not found and p_raiseError is True
        if r is None and raiseError:
            raise AttributeError(FIELD_KO % (name, class_.name))
        return r

    def getFields(self, layout, page=None, phase=None, type=None, fields=None):
        '''Returns the list of fields to render on p_layout'''
        r = []
        # Browse p_self's fields, or p_fields if passed
        for field in (fields or self.class_.fields.values()):
            # Ignore fields not being on p_page
            if page and field.pageName != page: continue
            # Ignore fields not being on any page in p_phase
            if phase and (field.page and (field.page.phase != phase)): continue
            # Ignore fields not being of p_type
            if type and field.type != type: continue
            # Ignore fields that can't be rendered on p_layout
            if not field.isRenderable(layout): continue
            # Ignore unshowable fields
            if not field.isShowable(self, layout): continue
            r.append(field)
        return r

    def getGroupedFields(self, page, layout, collect=True, fields=None):
        '''Returns p_self's fields, sorted by group, being part of this p_page,
           to be shown on this p_layout.'''
        # If p_collect is...
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  False  | r_ is a list, each element being a field or a group.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  True   | r_ is a tuple (page, l, css, js, phases):
        #         |  - "page"   repeats the current p_page;
        #         |  - "l"      is the list produced when p_collect is False;
        #         |  - "css"    is a list of CSS files that must be included
        #         |             because used by the returned fields;
        #         |  - "js"     is a list of Javascript files that must be
        #         |             included because used by the returned fields;
        #         |  - "phases" is an ordered dict of the phases and pages that
        #         |             must currently be shown for p_self.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # If p_fields are given, we use them instead of getting all fields
        # defined on p_self's class.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        r = []
        groups = {} # The already encountered groups (UiGroup instances)
        css = js = phases = None # The elements to collect when relevant
        # Browse fields
        config = self.config
        for field in (fields or self.class_.fields.values()):
            if collect and field.page:
                # Collect phases, for all fields, not just for fields that will
                # be selected here.
                if phases is None: phases = UiPhases(page, self, layout)
                phases.addField(field)
            # Ignore fields whose page is not p_page
            if field.pageName != page: continue
            # Ignore fields that must not be shown
            if not field.isRenderable(layout) or \
               not field.isShowable(self, layout): continue
            if collect:
                # Collect JS/CSS files
                if css is None: css = []
                field.getCss(self, layout, css)
                if js is None: js = []
                field.getJs(self, layout, js, config)
            # Insert the field directly in the result if it is not in a group
            if not field.group:
                r.append(field)
            else:
                # Insert it in the right group (if the group exists on p_layout)
                group = field.getGroup(layout)
                if not group:
                    r.append(field)
                else:
                    # Insert the UiGroup instance corresponding to field.group
                    uiGroup = group.insertInto(r, groups, field.page,
                                               self.class_.name)
                    uiGroup.addElement(field)
        # Finalize the data structure storing phases
        if phases: phases.finalize()
        # At this time, we may realize that p_page can't be shown on p_layout.
        # In that case, re-compute everything for the default page.
        if phases and phases.unshowableCurrentPage():
            return self.getGroupedFields(phases.defaultPageName, layout,
                                         collect=collect, fields=fields)
        # Return the appropriate result, depending on p_collect
        return r if not collect else page, r, css, js, phases

    def isEmpty(self, name, value=None, fromParam=False):
        '''Returns True if value of field p_name is considered to be empty
           (or p_value if p_fromParam is True).'''
        field = self.getField(name, raiseError=True)
        if not fromParam:
            value = field.getStoredValue(self, name)
        return field.isEmptyValue(self, value)

    def getLabel(self, name, field=True, language=None):
        '''Gets the translated label for field (if p_field is True) or workflow
           state or transition (if p_field is False) named p_name.'''
        # Translate the name of a field
        if field:
            field = self.getField(name, raiseError=True)
            return self.translate('label', field=field, language=language)
        # Translate the name of a state or transition
        return self.translate('%s_%s' % (self.getWorkflow().name, name),
                              language=language)

    def getValue(self, name, type=None, layout='view', language=None,
                 value=None, bypassDefault=False):
        '''Gets the value of field named p_name on p_self'''
        # In most cases, use the property set on p_self to retrieve this value.
        # For example, for retrieving the value of field named "title" on
        # p_self, use:
        #
        #                          self.title
        #
        # Use m_getValue if you need some variant of the field value. If p_type
        # is:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #    None     | The value as stored in the database will be returned
        #             | (or p_value if not None). If p_bypassDefault is True, in
        #             | the absence of a value, the system allowing to retrieve
        #             | a default value will be bypassed. Note that it has no
        #             | sense to specify a p_value if p_type is None. It is
        #             | useful when specifying one of the 2 following types, in
        #             | order to format an alternate value than the one stored
        #             | on p_self.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # 'formatted' | The "formatted" value, as produced by methods
        #             | <Field>.getFormattedValue, will be returned. For
        #             | example, in the case of a Select field, the formatted
        #             | value is a nice translated name, the database value
        #             | being a short technical term. If this formatting implies
        #             | translating something, it will be done in p_language, or
        #             | in the UI language if not specified. Parameter p_layout
        #             | may also be used, some fields using alternate value
        #             | representations on different layouts. Parameter p_layout
        #             | must be understood as "display the field value as it
        #             | would appear on layout X".
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   'shown'   | A variant of the "formatted" type, taking care of
        #             | multilingual values, as produced by methods
        #             | <Field>.getShownValue. For a multilingual value, the
        #             | "shown" value will be the part corresponding to the UI
        #             | language (or to p_language if specified).
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  'catalog'  | The field value as stored in the database index, as
        #             | produced by methods <Field>.getCatalogValue.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # [Not implemented yet] If p_name refers to an inner field (has the form
        # <fieldName>*<subName>), p_value must be passed ans must be one of
        # the sub-values contained within the outer field. 
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        field = self.getField(name)
        # Get the catalog value
        if type == 'catalog': return field.getCatalogValue(self)
        # All other values are based on the value as stored in the database.
        # Get it, excepted if given in p_value.
        if value is None:
            method = 'getStoredValue' if bypassDefault else 'getValue'
            r = getattr(field, method)(self, name)
        else:
            r = value
        if type is None: return r
        # Get the formatted or shown
        method = getattr(field, 'get%sValue' % type.capitalize())
        return method(self, r, layout, language=language)

    def getShownValue(self, name='title', layout='view', language=None,
                      value=None):
        '''Call field.getShownValue on field named p_name'''
        field = self.getField(name)
        value = field.getValue(self) if value is None else value
        return field.getShownValue(self, value, layout, language=language)

    def countRefs(self, name):
        '''Counts the nb of objects linked to this one via Ref field p_name'''
        tied = self.values.get(name)
        return 0 if tied is None else len(tied)

    def path(self, name):
        '''Returns the absolute file name of file stored in File field p_named
           p_name.'''
        v = getattr(self, name)
        if v: return v.getFilePath(self)

    def getIndexOf(self, name, tied, raiseError=True, notFoundValue=None):
        '''See docstring in the homonym method on appy/model/fields/ref::Ref'''
        return self.getField(name).getIndexOf(self, tied, raiseError=raiseError,
                                              notFoundValue=notFoundValue)

    def getPageIndexOf(self, name, tied):
        '''See docstring in the homonym method on appy/model/fields/ref::Ref'''
        return self.getField(name).getPageIndexOf(self, tied)

    def link(self, name, o, secure=False, executeMethods=True, at=None):
        '''Links p_o (which can be a list of objects) to p_self via Ref field
           p_name.'''
        # For understanding the 3 last params, check Ref's m_linkObject's doc
        field = self.getField(name)
        return field.linkObject(self, o, secure=secure,
                                executeMethods=executeMethods, at=at)

    def unlink(self, name, o, secure=False, executeMethods=True):
        '''Unlinks p_o (which can be a list of objects) from p_self via Ref
           field p_name.'''
        # For understanding the 2 last params, check Ref's m_unlinkObject's doc
        field = self.getField(name)
        return field.unlinkObject(self, o, secure=secure,
                                  executeMethods=executeMethods)

    def sort(self, name, sortKey='title', reverse=False):
        '''Sorts referred elements linked to p_self via Ref field named p_name
           according to a given p_sortKey.'''
        # p_sortKey can be:
        # - an attribute set on referred objects ("title", by default);
        # - a method that will be called on every tied object, will receive
        #   every such object as unique arg and will return a value that will
        #   represent its order among all tied objects. This mimics usage of
        #   the "key" param of the standard list.sort method;
        # - None. If None, default sorting will occur, using the method stored
        #   in field.insert.
        # ~
        # Get the objects tied to p_self via field p_name
        objects = getattr(self, name, None)
        if not objects: return
        if not sortKey:
            # Sort according to field.insert
            field = self.getField(name)
            insertMethod = field.insert
            if not insertMethod:
                raise Exception(REF_INS_KO % name)
            if not callable(insertMethod): insertMethod = insertMethod[1]
            keyMethod = lambda o: insertMethod(self, o)
        elif isinstance(sortKey, str):
            # Sort according to p_sortKey
            field = objects[0].getField(sortKey)
            keyMethod = lambda o: field.getSortValue(o)
        else:
            # Sort according to a custom method
            keyMethod = sortKey
        # Perform the sort
        objects.sort(key=keyMethod, reverse=reverse)

    def freezeField(self, name, template=None, format='pdf', secure=False,
                    freezeOdtOnError=True, value=None):
        '''Freezes, on p_self, the content of a freezable field named p_name'''
        # In the case of a Pod field, a given p_template may be given (indeed,
        # several templates can exist in field.template); the "freeze format"
        # may be passed in p_format ("pdf" by default). If p_value is not None,
        # it is frozen as-is, instead of recomputing the field value.
        field = self.getField(name)
        if not field.freezable:
            raise Exception(F_FREEZ_KO % name)
        # Additional parameters are passed for Pod fields
        if field.type == 'Pod':
            return field.freeze(self, template, format, secure=secure,
                                upload=value, freezeOdtOnError=freezeOdtOnError)
        else:
            return field.freeze(self, value=value)

    def unfreezeField(self, name, template=None, format='pdf', secure=False):
        '''Unfreezes a frozen field'''
        field = self.getField(name)
        if not field.freezable:
            raise Exception(F_FREEZ_KO % name)
        # Additional parameters are passed for Pod fields
        if field.type == 'Pod':
            field.unfreeze(self, template, format, secure=secure)
        else:
            field.unfreeze(self)

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                              Containment
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Attribute "cid" stores identifying information about the object being the
    # container of this one. "cid" stands for "*c*ontainer *id*". An object
    # being tied to another one via a Ref field with attribute "composite" being
    # True defines such a "container relationship" between these objects, one
    # object being the container of the other. In that case, the contained
    # object will have a "cid" storing info about the container object and the
    # Ref field. More precisely, if:
    # 
    #   object X has a composite Ref R storing object Y, with back Ref B,
    #
    # the container ID for Y (Y.cid) will be equal to "<X.iid>_<B.name>"
    #
    # An object may be top-level and have no container. Such an object is named
    # a "root object" and its "cid" will be None.
    # 
    # It is illegal to have the same object being the target of more that one
    # composite Ref.

    def computeCid(self):
        '''Computes the container ID ("cid") for p_self'''
        r = None
        for field in self.class_.fields.values():
            if field.type == 'Ref' and field.isBack and field.back.composite:
                container = getattr(self, field.name, None)
                if container:
                    try:
                        iid = container.iid
                    except AttributeError:
                        iid = container[0].iid
                    r = '%d_%s' % (iid, field.name)
                    break
        # If no container has been found, the object is a root object
        return r

    p['show'] = False
    cid = String(default=computeCid, persist=False, emptyIndexValue=None, **p)

    def getContainer(self, objectOnly=False, orInitiator=True, forward=False):
        '''Returns p_self's container, as a tuple (containerObject, fieldName)
           or the container alone if p_objectOnly is True. If the object is
           root, it returns (None, None) or None. If the container is not found
           and p_orInitiator is True, the initiator (which is probably the
           future container), when present, is returned.'''
        # Manage temp objects, having no container ID
        if self.isTemp():
            # Get the initiator
            initiator = self.getInitiator()
            if not initiator or not orInitiator:
                return None if objectOnly else (None, None)
            if not objectOnly and not forward:
                # In that case we cannot return the name of the back reference,
                # because the initiator gives the name of the forward reference
                # instead.
                raise Exception(CONT_ERR)
            o = initiator.o
            return o if objectOnly else (o, initiator.field.name)
        # Get the container ID
        cid = self.cid
        if cid is None:
            # A root object: it has no container
            return None if objectOnly else (None, None)
        else:
            id, name = cid.rsplit('_', 1)
            container = self.getObject(id)
            if forward and not objectOnly:
                # Get the name of p_name's forward reference
                name = self.getField(name).back.name
            return container if objectOnly else (container, name)

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                          Catalog-related methods
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def search(self, className=None, **kwargs):
        '''Performs a search in the database, for instances of class named
           p_className, or of self's class if not specified.'''
        if className and not isinstance(className, str): raise Exception(NO_STR)
        handler = self.H()
        className = className or self.class_.name
        return self.database.search(handler, className, **kwargs)

    def search1(self, className=None, **kwargs):
        '''Performs a search for a single object'''
        r = self.search(className, maxResults=1, **kwargs)
        return r[0] if r else None

    def count(self, className=None, **kwargs):
        '''Identical to m_search abo, but returns the number of objects matching
           the search instead of returning the objects themselves.'''
        # Use this method instead of writing len(self.search(...))
        return len(self.search(className=className, ids=True, **kwargs))

    def compute(self, className, sortBy=None, context=None, expression=None,
                secure=False, max=None, **fields):
        '''Computes a result based on a search on objects of p_className'''
        # Like m_search and m_count above, this method performs a search on
        # objects of p_className; but in this case, instead of returning a list
        # of matching objects (like m_search) or counting elements (like
        # p_count), it evaluates, on every matching object (possibly restricted
        # to at most p_max objects), a Python p_expression (which may be an
        # expression or a statement), and returns, if needed, a result. The
        # result may be initialized through parameter p_context. p_expression is
        # evaluated with 2 variables in its context: "o" which is the currently
        # walked object, instance of p_className, and "ctx", which is the
        # context as initialized (or not) by p_context. p_context may be used as
        # (1) a variable or instance that is updated on every call to produce a
        #     result;
        # (2) an input variable or instance;
        # (3) both.

        # The method returns p_context, modified or not by evaluation of
        # p_expression on every matching object.

        # When you need to perform an action or computation on a lot of objects,
        # use this method instead of doing things like
           
        #              "for o in self.search(MyClass,...)"
        
        # Initialize the context variable "ctx"
        ctx = context
        i = 0
        for iid in self.search(className, ids=True, sortBy=sortBy, \
                               secure=secure, **fields):
            # Stop if the maximum number of objects has been reached
            if max is not None and i >= max: break
            # Get the object from its ID
            o = self.getObject(iid, logMissing=True)
            # Ignore dead IDs
            if o is None: continue
            i += 1
            # Evaluate the expression
            if expression: exec(expression)
        return ctx

    def reindex(self, **kwargs):
        '''(re-/un-)indexes this object in the catalog corresponding to its
           class. Returns True if at least one change has been actually
           performed in at least one index.'''
        if self.isTemp(): raise Exception(INDEX_TEMP)
        return self.database.reindexObject(self.H(), self, **kwargs)

    def getCatalog(self, class_=None, raiseError=False):
        '''Returns the catalog storing p_self (if indexed) or instances of
           another p_class_, if passed.'''
        class_ = class_ or self.class_
        r = self.H().dbConnection.root.catalogs.get(class_.name)
        if not r and raiseError:
            raise Exception(CATALOG_KO % class_.name)
        return r

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                                Sub-PXs
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # The object preamble is based and reuses the same CSS classes as results's
    # top zone.
    pxPreamble = Px('''
     <div class="sTop"
          var="class_=o.class_;
               nav=req.nav if req.nav != 'no' else None;
               snav=ui.Siblings.get(nav,tool,_ctx_,'iconS') if nav else None">

      <!-- Class name -->
      <div class="pageTitle">
       <x>:_(o.class_.name)</x>

       <!-- The total number of objects, if navigation is there -->
       <x if="snav">
         <span var="css=class_.getCssFor(tool, 'sep')"
               class=":'navSep %s' % css if css else 'navSep'">//</span>
         <span class="btot">:snav.total</span>
       </x>

       <!-- Class-specific colored border (*t*itle *bot*tom) -->
       <div var="css=class_.getCssFor(tool, 'tbot')"
            if="css" class=":'tbot %s' % css"></div>
      </div>

      <!-- The "back" icon -->
      <div if="snav"
           class="pageIcons">::snav.getGotoSource(svg, _, imgCss='iconM')</div>

      <!-- Siblings navigation -->
      <div if="snav" class="snav" style="margin-left:auto"
           var2="gotoSource=False">:snav.pxNavigate</div>

      <!-- Pod templates -->
      <div var="fields=o.getFields('pre', 'main')" style="margin-left:auto">
       <div class="spod" for="field in fields"
            var2="fieldName=field.name">:field.pxRender</div>
      </div>
     </div>''')

    # The header displays, for a given object, its title and breadcrumb
    pxHeader = Px('''
     <div var="breadcrumb=ui.Breadcrumb(o, popup)"
          if="breadcrumb.parts" class=":breadcrumb.css">
      <x if="breadcrumb.sup">::breadcrumb.sup</x>
      <x for="part in breadcrumb.parts"
         var2="link=not loop.part.last and part.view">
       <img if="not loop.part.first" src=":svg('arrowsA')"
            class="iconS" style="transform: rotate(270deg)"/>
       <!-- Display the title or a link to the object -->
       <span if="not link" class="title">::part.title</span>
       <!-- Display a link for parent objects -->
       <a if="link" href=":part.url">::part.title</a>
      </x>
      <x if="breadcrumb.sub">::breadcrumb.sub</x>
     </div>''')

    # The grouped fields to show on a given page
    pxFields = Px('''
     <table width=":table.width | '100%'">
      <tr for="field in grouped"><td>:field.pxRender</td></tr></table>''')

    # PX displaying the content of a single field
    pxField = Px('''
     <div style="padding: 30px"
          var="field=o.getField(req.name);
               layout='view'">:field.pxRender</div>''',
     template=Template.px, hook='content')

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                           Object controls
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    pxControls = Px('''
     <!-- Object phases and pages. pxButtons will be called and inserted into
          the main phase. -->

     <x var="isEdit=layout == 'edit';
             nav=req.nav or 'no';
             current=phases.currentPage;
             compact=popup or config.ui.compact;
             picto='pictoC' if compact else 'picto';
             mayAct=not isEdit and guard.mayAct(o)">:phases.view</x>''')

    # Standard, custom and workflow-related actions
    pxButtons = Px('''
     <x if="phase.name == 'main'">
      <!-- Standard actions -->

      <!-- Save -->
      <div if="isEdit and current.showSave"
           var2="label=o.class_.getSaveText(o)">
       <div>
        <a class="clickable"
           onclick=":'submitAppyForm(%s,%s,%s)' % \
                      (q('save'), q(current.name), q('view'))">
         <img src=":svg('save')" class=":picto"/>
         <div style=":'display:%s' % config.ui.pageDisplay">::label</div>
        </a>
       </div>
      </div>

      <!-- Cancel -->
      <div if="isEdit and current.showCancel" var2="label=_('object_cancel')">
       <div>
        <a class="clickable" name="cancel"
           onclick=":'submitAppyForm(%s,%s,%s)' % \
                      (q('cancel'), q(current.name), q('view'))">
         <img src=":svg('cancel')" class=":picto"/>
         <div style=":'display:%s' % config.ui.pageDisplay">::label</div>
        </a>
       </div>
      </div>

      <!-- Delete -->
      <div if="not isEdit and not popup and guard.mayDelete(o) and \
               not o.Lock.isSet(o, user, page)" var2="label=_('object_delete')">
       <div>
        <a class="clickable" onclick=":'onDeleteObject(%s)' % q(o.iid)">
         <img src=":svg('delete')" class=":picto"/>
         <div style=":'display:%s' % config.ui.pageDisplay">::label</div>
        </a>
       </div>
      </div>

      <!-- Workflow transitions -->
      <x if="mayAct and o.class_.showTransitions(o, layout)"
         var2="workflow=o.getWorkflow()">
       <x var="transitions=workflow.getTransitions(o)" if="transitions">
        <x>:workflow.pxTransitions</x></x>
      </x>
     </x>

     <!-- Fields on layout "buttons". Layout is set as "view" and not "buttons"
          because this latter would render a too minimalistic widget. -->
     <x if="not isEdit"
        var2="fields=o.getFields('buttons', page=req.page or 'main');
              layout='view'">
      <!-- Call PX "buttons", and not "pxRender", to minimize wrapping tags -->
      <x for="field in fields"
         var2="name=field.name; value=field.getValueIf(o, name, layout)">
       <div>:field.buttons</div></x>
     </x>''')

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                         Objet creation method
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def create(self, _name, secure=False, raiseOnWrongAttribute=True,
               executeMethods=True, indexIt=True, initialComment=None,
               initialState=None, **kwargs):
        '''Create a new instance of a Appy class'''
        # If p__name is the name of a field, the created object will be linked
        # to p_self via this field. Else, p__name must correspond to a root
        # class and no link will exist between the created instance and p_self.

        # p_kwargs allow to specify values for object fields. If p_secure is
        # False, security checks will not be performed.

        # If p_raiseOnWrongAttribute is True, if a value from p_kwargs does not
        # correspond to a field on the created object, an AttributeError will be
        # raised. Else, the value will be silently ignored.

        # If p_executeMethods is False, the class's onEdit method, if present,
        # will not be called; any other defined method will not be called
        # neither (ie, Ref.insert, Ref.beforeLink, Ref.afterLink...).

        # p_initialComment will be stored as comment in the initial workflow
        # transition. If p_initialState is given (as a string), it will force
        # the object state instead of setting him to its workflow's initial
        # state.

        # Determine the ID of the object to create
        id = kwargs.pop('id') if 'id' in kwargs else None

        # Must we create an instance of a root class or one via a Ref field ?
        if _name[0].islower():
            # p__name is the name of a Ref field
            field = self.getField(_name)
            className = field.class_.meta.name
            # Check that the user can edit this field
            if secure: field.checkAdd(self)
        else:
            # p_name is the name of a root class
            className = _name
            field = None
        # Create the object
        o = self.database.new(self.H(), className, id=id, secure=secure,
                              initialComment=initialComment,
                              initialState=initialState)
        # Set object attributes
        for name, value in kwargs.items():
            try:
                setattr(o, name, value)
            except AttributeError as ae:
                if raiseOnWrongAttribute: raise ae
        # Call custom early initialization: a hook allowing the app developer to
        # initialise its object before it is linked to its initiator object.
        if executeMethods: multicall(o, 'onEditEarly', False, None)
        # Link the created object to its initiator when relevant
        if field: field.linkObject(self, o, executeMethods=executeMethods)
        # Call custom initialization: a hook allowing the app developer to
        # initialise its object after it's been linked to its initiator object.
        if executeMethods: multicall(o, 'onEdit', False, True)
        # Index the object (when relevant) and return it
        if indexIt and o.class_.isIndexable():
            # p_indexIt may be False if the object is, in a first step, created
            # "empty" and field values are filled afterwards.
            o.reindex()
        return o

    def getCopyValues(self, exclude=(), fields={}):
        '''Returns a dict ~{s_fieldName, fieldValue}~ representing p_self's
           dataset ready-to-be-copied to another object.'''
        # Check m_createFrom below to know more about method args
        # ~
        r = {}
        # Browse field values from p_self and store "copyable" ones in "r"
        for field in self.class_.fields.values():
            # Skip non persistent fields, back references & p_exclude(d) fields
            if not field.persist or field.name in exclude or \
               (field.type == 'Ref' and field.isBack): continue
            # Use the value in p_fields if given
            if field.name in fields:
                value = fields[field.name]
            else:
                value = field.getCopyValue(self)
            if value is not None:
                r[field.name] = value
        return r

    def createFrom(self, _name, other, secure=False, executeMethods=True,
                   exclude=(), keepBase=False, keepHistory=False, fields={}):
        '''Similar to m_create above, excepted that another object (p_other) is
           used as base for filling in data for the object to create.'''
        # p_exclude lists fields (by their names) that will not be copied from
        # p_other. If p_keepBase is True, basic attributes will be kept on the
        # new object: creator and dates "created" and "modified". Else, the new
        # object's creator will be the logged user.

        # Note that this method does not perform a deep copy: objects linked via
        # Ref fields from p_self will be referenced by the clone, but not
        # themselves copied.

        # Get, as a dict, all field values to set from p_other. p_other may not
        # be of the same class as p_self.
        params = other.getCopyValues(exclude, fields)
        # Create the new instance
        r = self.create(_name, secure=secure, raiseOnWrongAttribute=False,
                        executeMethods=executeMethods, **params)
        # Copy p_other's history events as-is if requested
        if keepHistory: r.history.setEvents(other.history)
        # Propagate base attributes if required (which is useless if history has
        # already been cloned in its entirety).
        if not keepHistory and keepBase:
            history = r.history
            # Keep the same creator as p_other
            history[-1].login = other.creator
            # Keep the same creation date
            history[-1].date = other.created
            # Keep the same modification date
            history.modified = other.modified
        return r

    def __copy__(self, memo):
        '''Duplicating an Appy object must be done via m_createFrom'''
        # This disables duplicating an Appy object via copy.copy
        return self

    def __deepcopy__(self, memo):
        '''Duplicating an Appy object must be done via m_createFrom'''
        # This disables duplicating an Appy object via copy.deepcopy
        return self

    def updateFrom(self, other, exclude=(), fields={}):
        '''Updates p_self's field values from this p_other object. Back refs and
           fields listed on p_exclude will not be copied.'''
        # Browse all field values to set on p_other
        for name, value in other.getCopyValues(exclude, fields).items():
            # Has p_self a field named p_name ?
            if self.getField(name):
                self.values[name] = value

    def delete(self, historize=False, executeMethods=True):
        '''Deletes p_self (see homonym method on the database object'''
        return self.database.delete(self, historize, executeMethods)

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # Translation method
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def translate(self, label, mapping=None, language=None, asText=False,
                  field=None, blankOnError=False, noNice=False):
        '''Translates a given p_label with p_mapping'''
        # If p_field is given, p_label does not correspond to a full label name,
        # but to a label type linked to p_field: "label", "descr" or "help".
        # Indeed, in this case, a specific i18n mapping may be available on the
        # field, so we must merge this mapping into p_mapping.
        handler = self.H()
        # In what language must we get the translation ?
        language = language or handler.guard.userLanguage
        # Get the label name, and the field-specific mapping if any
        if field:
            if field.type != 'group':
                fieldMapping = field.mapping[label]
                if fieldMapping:
                    if callable(fieldMapping):
                        fieldMapping = field.callMethod(self, fieldMapping)
                    if not mapping:
                        mapping = fieldMapping
                    else:
                        mapping.update(fieldMapping)
                # Translation may be found on a FieldTranslation instance
                if field.translations:
                    return field.translations.get(label, language, mapping)
            label = getattr(field, '%sId' % label)
        # Get the appropriate Translation object, or, if not found, get the one
        # corresponding to the defined fallback language.
        store = handler.dbConnection.root.objects
        translation = store.get(language) or \
                      store.get(self.config.ui.fallbackLanguage)
        # Get the label from this translation object, or from the fallback
        # language if not found.
        if translation:
            r = translation.get(label, mapping)
            if not r:
                # Try to get a translation in the fallback language
                fallback = self.config.ui.fallbackLanguage
                if fallback in store:
                    # The fallback language may not be among app's languages
                    r = store.get(fallback).get(label, mapping)
        else:
            r = ''
        # If still no result, put a nice name derived from the label instead of
        # a translated message.
        if not r and not blankOnError and not noNice:
            return produceNiceMessage(label.rsplit('_', 1)[-1])
        # Manage carriage returns, depending on the desired format
        return r.replace('<br/>', '\n') if asText else r

    def callOnView(self):
        '''Call "onView" method if present'''
        method = getattr(self, 'onView', None)
        if method: method()

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # XML export
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    traverse['xml'] = 'perm:read'
    def xml(self):
        '''Returns p_self's XML version'''
        self.resp.setContentType('xml')
        return self # p_self will be automatically marshalled by the traversal

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # PXs
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # The object, as shown in a list of referred (tied) objects. In this PX:
    # v_io refers to the source, *i*nitiator object ;
    # v_o  refers to the tied object.
    pxTied = Px('''
     <tr var="io=initiator.o;
              ifield=initiator.field;
              *=ifield.initPx(io, req, _ctx_) if _ctx_.ajaxSingle else None;
              ohook=ifield.getHookFor(o);
              backHook=ohook if layout == 'cell' else None;
              target=ui.LinkTarget(ifield.class_, backHook, ifield.viaPopup);
              objectIndex=ifield.getIndexOf(io, o, raiseError=False);
              cbId='%s_%s' % (hook, currentNumber);
              mayView=guard.mayView(o);
              id=o.iid"
         id=":ohook">
      <x for="col in columns" var2="field=col.field">:col.pxCellRef</x>

      <!-- Store data in this tr node allowing to ajax-refresh it -->
      <script>:ifield.getAjaxDataRow(o, ohook, hook, inPickList,
               currentNumber=currentNumber, cbChecked=cbId, ajaxSingle=True,
               initiator=':%d:%s' % (io.iid, ifield.name))</script>
     </tr>''')

    # The object, as shown in a list of search results
    pxResult = Px('''
     <tr var="id=o.iid; ohook=mode.getHookFor(o); mayView=guard.mayView(o);
              backHook=ohook; cbId='%s_%s' % (mode.checkboxesId, currentNumber)"
         id=":ohook">
      <x for="col in mode.columns" var2="field=col.field">:col.pxCell</x>

      <!-- Store data in this tr node allowing to ajax-refresh it -->
      <script>:mode.getAjaxDataRow(o, ohook, currentNumber=currentNumber,
               cbChecked=cbId)</script></tr>''')

    # Base PX for viewing object fields from a given page
    view = Px('''
     <x var="x=guard.mayView(o, raiseError=True);
             pageLayout=o.getPageLayout(layout);
             page=o.getCurrentPage(req, layout);
             page,grouped,css,js,phases=o.getGroupedFields(page, layout)">
      <x>::ui.Includer.getSpecific(tool, css, js)</x>
      <x if="not req.notGlobal">::ui.Globals.getForms(tool)</x>
      <x var="table=pageLayout;tagId='pageLayout'; tagName=''; tagCss='';
              layoutTarget=o">:table.pxRender</x>
      <x if="not req.notGlobal"
         var="x=o.callOnView()">::ui.Globals.getScripts(tool, q, layout)</x>
     </x>''', template=Template.px, hook='content')

    # The default element computed and returned when an object is reached by a
    # traversal is the "view" PX.
    default = view

    # Base PX for editing object fields from a given page
    edit = Px('''
     <x var="x=guard.mayEdit(o, raiseError=True);
             table=o.getPageLayout(layout);
             page=o.getCurrentPage(req, layout);
             x=o.Lock.set(o, user, page);
             confirmText=req.confirmText;
             page,grouped,css,js,phases=o.getGroupedFields(page, layout);
             x=req.patchFromTemplate(o)">
      <x>::ui.Includer.getSpecific(tool, css, js)</x>
      <x>::ui.Globals.getForms(tool)</x>
      <script>:ui.Validator.getJsErrors(handler)</script>
      <!-- Warn the user that the form should be left via buttons -->
      <script>protectAppyForm()</script>
      <form id="appyForm" name="appyForm" method="post"
            enctype="multipart/form-data" action=":'%s/save' % o.url">
       <input type="hidden" name="action" value=""/>
       <input type="hidden" name="popup" value=":popup"/>
       <input type="hidden" name="page" value=":page"/>
       <input type="hidden" name="nav" value=":req.nav or ''"/>
       <input type="hidden" name="referer"
              value=":req.referer or o.referer or ''"/>
       <input type="hidden" name="_get_" value=":req._get_ or ''"/>
       <input type="hidden" name="gotoPage" value=""/>
       <input type="hidden" name="gotoLayout" value=""/>
       <input type="hidden" name="insert" value=":req.insert or ''"/>
       <input type="hidden" name="confirmed" value="False"/>
       <input type="hidden" name="confirmedData" value=""/>
       <x var="tagId='pageLayout'; tagName=''; tagCss='';
               layoutTarget=o">:table.pxRender</x>
      </form>
      <script if="confirmText">::'askConfirm(%s,%s,%s,null,%d)' % \
        (q('script'), q('postConfirmedEditForm(comment)'), q(confirmText), \
         o.class_.getConfirmPopupWidth(popup))</script>
      <x>::ui.Globals.getScripts(tool, q, layout)</x>
     </x>''',

     js='''
      completeAppyForm = function(f) {
        // Complete Appy form p_f via special form element named "_get_"
        let g = f._get_;
        if (!g.value) return;
        let [source, name, info] = g.value.split(':');
        if (source == 'form') {
          // Complete p_f with form elements coming from another form
          let f2 = getNode(':' + name),
              fields = info.split(','),
              fieldName = fieldValue = null;
          if (!f2) return;
          for (let i=0; i < fields.length; i++) {
            fieldName = fields[i];
            if (fieldName[0] == '*') {
              // Try to retrieve search criteria from the storage if present
              let spars = getSearchInfo(fieldName.substr(1) + '_customSearch');
              fieldValue = ('criteria' in spars)? spars['criteria']: null;
              if (!fieldValue) continue;
              fieldName = 'criteria';
            }
            else {
              fieldValue = f2.elements[fieldName].value;
            }
            addFormField(f, fieldName, fieldValue);
          }
        }
      }

      retrieveContentEditable = function(f) {
        // Copy, in textareas, content stored in content-editable divs
        let divs = f.querySelectorAll('[contenteditable=true]');
        for (const d of divs) {
          if (d.innerHTML && d.innerHTML !== '<div></div>' && d.nextSibling) {
            d.nextSibling.value = d.innerHTML;
          }
        }
      }

      submitAppyForm = function(action, gotoPage, gotoLayout) {
        const f = document.getElementById('appyForm');
        // Complete the form via the "_get_" element if present
        if (action != 'cancel') completeAppyForm(f);
        f.action.value = action;
        if (f.popup.value == 'True') {
          /* Initialize the "close popup" cookie. If set to "no", it is not time
             yet to close it. The timer hereafter will regularly check if the
             popup must be closed. */
          createCookie('closePopup', 'no');
          const popup = getNode('iframePopup', true);
          // Set a timer for checking when we must close the iframe popup
          popup.popupTimer = setInterval(backFromPopup, 700);
        }
        f.gotoPage.value = gotoPage;
        f.gotoLayout.value = gotoLayout;
        retrieveContentEditable(f);
        f.submit(); clickOn(f);
      }

      protectAppyForm = function() {
        window.onbeforeunload = function(event){
        let f = document.getElementById("appyForm");
        if (f.action.value == "") {
          let e = event || window.event;
          if (e) {e.returnValue = warn_leave_form;}
          return warn_leave_form;
          }
        }
      }''', template=Template.px, hook='content', name='edit')

    def getInitiator(self, search=False):
        '''Gets, from the request, information about a potential initiator'''
        # An initiator is an object from which an action is triggered on another
        # object (being p_self). The most obvious example is a target object
        # (p_self) created from a Ref field on a source object (the initiator).
        # The method returns None if there is no initiator.
        req = self.req
        if not search:
            # Try to get a "classic" initiator, from the "[o]nav" key
            nav = req.nav or req.onav
            if not nav or nav == 'no': return
            fieldType, info = nav.split('.', 1)
            field = eval(fieldType.capitalize())
            if field.initiator:
                r = field.initiator(self.tool, req, info)
                if r.isComplete():
                    return r
        else:
            # Try to get the initiator from the current search = a Ref field
            # referenced in key "_ref" or from search criteria.
            ref = req._ref or req.ref
            if not ref:
                criteria = Criteria.readFromRequest(self.H())
                if criteria and '_ref' in criteria: ref = criteria['_ref']
            if ref:
                return self.getObject(ref.split(':')[0])

    def getPopupInitiator(self):
        '''If the UI is currently positioned in the iframe popup, this method
           returns, as an object ~O(o,field)~, the initiator object being
           responsible for the popup opening, in the base window.'''
        req = self.req
        if req.popup in (None, 'False', '0'): return
        if 'search' in req and ',' in req.search:
            id, name, mode = req.search.split(',')
            o = self.getObject(id)
            return O(o=o, field=o.getField(name))

    def getFolder(self, create=False, withRelative=False):
        '''Gets, as a pathlib.Path instance, the folder where binary files
           related to this object are stored on the filesystem.'''
        return self.database.getFolder(self, create, withRelative)

    def cancel(self, initiator=None, popup=False, isTemp=False):
        '''Redirect the user after an object edition has been canceled'''
        self.H().commit = True
        # Render a message for the user. This message (and the url to redirect
        # the user to) may be customized by method m_onCancel.
        req = self.req
        message = url = None
        if hasattr(self, 'onCancel'):
            r = self.onCancel(isTemp)
            if r: message, url = r
        self.say(message or self.translate('object_canceled'))
        # Determine the current page
        page = req.page or 'main'
        if isTemp:
            # Delete the temp object whose creation has been canceled
            self.delete()
        else:
            # Remove the lock set on the current page
            Lock.remove(self, page)
        # If we are in a popup, render a minimalist HTML page that will close it
        if popup: return Iframe.goBack(self, initiator)
        # Determine, if not defined yet, the URL to go back to
        if self.gotoSet(): return
        self.goto(url or (self.req.referer if isTemp else self.getGotoUrl()))

    traverse['save'] = 'perm:write'
    def save(self):
        '''Called when p_self's data coming from the UI must be saved to disk.
           p_self can be a temporary object. In this case, "saving" consists in
           moving it to its "final" place.'''
        req = self.req
        tool = self.tool
        isTemp = self.isTemp()
        popup = req.popup == 'True'
        saveConfirmed = req.confirmed == 'True'
        # If this object is created from an initiator, get info about it
        initiator = self.getInitiator()
        # The precise action can be "save", but also "cancel"
        action = req.action
        if action == 'cancel': return self.cancel(initiator, popup, isTemp)
        # Create a validator: he will manage validation of request data
        validator = self.H().validator = Validator(self, saveConfirmed)
        r = validator.run()
        # If a result is returned, the "edit" page must be shown again:
        # validation failed or a confirmation is required.
        if r: return r
        # Update the object in the database
        text = self.database.update(self, validator, initiator)
        # Recompute cached info on the guard: things may have changed
        guard = self.guard
        guard.cache()
        # If p_self has already been deleted ("text" being None in that case),
        # or if the logged user has lost the right to view it, redirect him to
        # its home page.
        if text is None or not guard.mayView(self):
            if popup:
                if text: self.say(text)
                return Iframe.goBack(self, initiator)
            elif not self.gotoSet():
                self.goto(tool.computeHomePage(), message=text)
            return
        # If we are here, action is "save" and p_self has been updated. Redirect
        # the user to the appropriate page.
        self.say(text)
        # Come back from the popup if we were in it
        if popup and req.gotoLayout == 'view':
            return Iframe.goBack(self, initiator)
        # Go to wherever has been defined, if already defined
        if self.gotoSet(): return
        # Go to the appropriate URL
        if isTemp and initiator:
            # Let the initiator choose the back URL
            url = initiator.getBackUrl(self)
        else:
            # Go to p_self's page and layout as defined in the request
            url = self.getGotoUrl()
        self.goto(url)

    traverse['new'] = True
    def new(self):
        '''Called when a user wants to create a root object or an object via a
           Ref field. A temporary object is created and the "edit" page to it is
           returned.'''
        req = self.req
        className = req.className
        if not className:
            self.log(MISS_CLS, type='error')
            self.raiseUnauthorized()
        # This requires a database commit
        handler = self.H()
        handler.commit = True
        # Create the params to add to the URL leading to the new object's edit
        # page.
        params = {'sub':'edit', 'page':'main', 'nav':'no',
                  'popup': req.popup == 'True'}
        initiator = self.getInitiator()
        if initiator:
            # Transmit initiator information in the next request (as well as
            # special key "_get_" if present). This information is stored in the
            # "nav" request key.
            params['nav'] = req.nav
            g = req._get_
            if g: params['_get_'] = g
            # Is the creation of the new object via the initiator allowed ?
            initiator.checkAllowed(log=True)
            # Let the initiator complete URL parameters when relevant
            initiator.updateParameters(params)
        # Create a temp object
        o = self.database.new(handler, className, temp=True)
        # Populate p_o's edit form fields with a template object if present
        templateId = req.template_
        if templateId: params['template_'] = templateId
        # Call method "onCreate" if available. This method typically sets local
        # roles to the newly created object.
        if hasattr(o, 'onCreate'): o.onCreate()
        # Go to o's "edit" page
        self.goto(o.getUrl(**params))

    traverse['remove'] = 'perm:delete'
    def remove(self):
        '''Deletes p_self and return a message to the UI'''
        # Delete the object from the database. If a text is returned, an error
        # occurred and the deletion was aborted.
        text = self.delete(historize=True)
        # Prepare the back URL. None = the default = the referer page.
        back = None
        gotoSet = self.gotoSet()
        # Return a message to the UI
        handler = self.H()
        if not text:
            # The deletion has been successfully performed
            text = self.translate('action_done')
            # If we were consulting the object itself, return to the home page.
            # Else, return to the referer page (it is the default).
            if not gotoSet and handler.isPublished(self):
                back = self.tool.computeHomePage()
        # If we are called from an Ajax request, simply return the message
        if handler.isAjax():
            self.resp.ungoto()
            return text
        # Go to the "back" URL (if "goto" hasn't been called yet)
        if not gotoSet:
            self.goto(url=back, message=text)

    traverse['unlock'] = 'perm:write'
    def unlock(self):
        '''Unlocks the page whose name is in the request'''
        Lock.remove(self, page=self.req.page, force=True)
        self.goto(message=self.translate('action_done'))
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
