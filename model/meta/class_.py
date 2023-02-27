'''Meta-class for a Appy class'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import collections
import persistent
from persistent.mapping import PersistentMapping

from appy.px import Px
import appy.model.meta.class_
from appy.model.meta import Meta
from appy.model.base import Base
from appy.model.page import Page
from appy.model.user import User
from appy.model.tool import Tool
from appy.model.root import Model
from appy.model.group import Group
from appy.ui.layout import Layouts
from appy.model.fields import Field
from appy.model.workflow import Role
from appy.model.fields.ref import Ref
from appy.model.fields.pod import Pod
from appy.model.searches import Search
from appy.utils import string as sutils
from appy.model.fields.text import Text
from appy.model.document import Document
from appy.model.utils import Object as O
from appy.model.fields.phase import Phase
from appy.model.fields.string import String
from appy.model.fields.select import Select
from appy.model.translation import Translation
from appy.model.workflow.history import History
from appy.model.searches.gridder import Gridder
from appy.model.fields.computed import Computed
from appy.model.workflow.localRoles import LocalRoles
from appy.model.fields.phase import Page as FieldPage

# Errors - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
NAME_KO     = 'You have defined a field or search named "%s" on class "%s". ' \
              'This name is not allowed.'
CR_LOC_ROLE = '%s: local role "%s" cannot be used as creator.'
DUP_S_NAME  = '%s: duplicate search "%s".'
S_F_HOM     = '%s: "%s" is both used as search and field name, this is not ' \
              'allowed.'
CUS_ID_KO   = 'The custom ID produced by method "generaeId" must be a string.'
S_FIELD_KO  = 'Field "%s", mentioned as search field on class "%s", not found.'
FILT_ERR    = '%s::%s - Filter error. %s.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Class(Meta):
    '''Represents an Appy class'''

    # Attributes added on Appy classes
    attributes = {'fields': Field}

    # Fields being unwanted on search fields, although being indexed. Field
    # "title" is not really "unsearchable", but in most cases, it is preferable
    # to use field "searchable".
    unsearchableFields = ('title', 'allowed', 'cid')

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # Model-construction-time methods
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # The following set of methods allow to build the model when making an app
    # or when starting the server.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def __init__(self, class_, isBase=False, appOnly=False):
        Meta.__init__(self, class_, appOnly)
        # p_class_ may be of 3 types:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "base" | A class from the base Appy model (from appy.model) that has
        #        | not been overridden by an app's class.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "app"  | An original class from the app, that does not exist in the
        #        | base model.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "over" | A class defined in the app but that overrides a class defined
        #        | in the base Appy model.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.type = 'base' if isBase else 'app'

        # Create the concrete class from which instances will be created.
        # Indeed, In order to bring all Appy functionalities to p_class_, we
        # need to create a new class inheriting from:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   p_class_  | The class defined by the developer or being part of the
        #             | base Appy model.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #    Base*    | Class appy.model.base.Base, the base class for any Appy
        #             | class, or one if its sub-classes, depending on p_class_
        #             | name. For example, if the user defines a class named
        #             | "Invoice", it will inherit from Base (=a class of type
        #             | "app"). If the user defines a class named "User", it
        #             | will inherit from class appy.model.user.User (= a class
        #             | of type "over"): using the name of a base class from
        #             | package appy.model implicitly means that the developer
        #             | wants to extend this class.
        #             |
        #             | Note that for not-overridden classes from appy.model (=
        #             | classes of type "base"), there is no base class: the
        #             | class is already a base class.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  Persistent | Class persistent.Persistent allows to store instances in
        #             | the database (ZODB).
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # Creating the concrete class is not necessary when p_self.appOnly is
        # True.
        if not appOnly:
            # The name of the generated class (tribute to appy.gen)
            genName = 'Gen_%s' % self.name
            if self.type == 'base':
                # The class must only inherit from p_class_ and Persistent
                exec('class %s(class_, persistent.Persistent): pass' % genName)
            else:
                # It must also inherit from a base class or one of its
                # sub-classes.
                base = self.getBaseClass()
                if base != 'Base':
                    # This is an "over" class
                    self.type = 'over'
                exec('class %s(class_, %s, persistent.Persistent): pass' % \
                     (genName, base))
            # This concrete class will have a full name being
            #                appy.model.meta.class_.<genName>
            exec('self.concrete = %s' % genName)
            # Add the class in the namespace of the current package
            # (appy.model.meta.class_). Else, pickle, used by the ZODB to store
            # instances of this class, will not find it.
            setattr(appy.model.meta.class_, genName, self.concrete)
        else:
            self.type = 'over' if self.name in Model.baseClasses else 'app'
        # Fields are grouped into pages, themselves grouped into "phases"
        self.phases = collections.OrderedDict()
        # Read fields and static searches
        self.readFields()
        self.readSearches()
        # The class will be linked to a workflow (later, by the loader)
        self.workflow = None
        # Call the "update" method if present: it allows developers to modify
        # this class. One of the most frequent updates will be to update field
        # "title". If this method must add a new field, or replace an existing
        # field with an alternate version, do not write things like:
        #
        #   @staticmethod
        #   def update(class_):
        #       class_.fields['title'] = Text(...)
        #
        # ... call method m_setField (defined hereafter) instead:
        #
        #   @staticmethod
        #   def update(class_):
        #       title = Text(...)
        #       class_.setField('title', title)
        if self.type == 'over':
            # Execute the "update" method on the base class
            base = eval(self.name)
            if hasattr(base, 'update'):
                base.update(self)
        if hasattr(self.python, 'update'):
            self.python.update(self)

    def getBaseClass(self):
        '''Returns the name of the class being p_self's base class'''
        name = self.name
        return name if name in Model.baseClasses else 'Base'

    def injectProperties(self):
        '''Injects, on p_self.concrete, a property for every field defined on
           this class, in order to get and set its value.'''
        # Other techniques could have been implemented for injecting such
        # virtual attributes, like overriding __getattribute__ and __setattr__,
        # but this should be avoided in conjunction with ZODB and pickle.
        class_ = self.concrete
        # Inject one property for every field
        for name, field in self.fields.items():
            # To get a field value is done via method Field::getValue
            getter = lambda self, field=field: field.getValue(self)    
            # To set a value is done via method Field::store
            if isinstance(field, Ref):
                setter = lambda self, v, field=field: \
                                field.store(self, v, secure=False)
            else:
                setter = lambda self, v, field=field: field.store(self, v)
            setattr(class_, name, property(getter, setter))

    def getFieldClasses(self, class_):
        '''Returns, on p_class_ and its base classes, the list of classes where
           fields may be defined.'''
        # Add p_class_ in itself
        r = [class_]
        # Scan now p_class_'s base class
        if (class_ != self.python) or (self.type == 'base'):
            base = class_.__bases__[0]
        else:
            base = eval(self.getBaseClass())
        if base.__name__ != 'object':
            r  = self.getFieldClasses(base) + r
        return r

    def readPage(self, page):
        '''While browsing a field, a p_page has been encountered. Add it to
           self.phases if not already done.'''
        # Create the phase when appropriate
        name = page.phase
        if name not in self.phases:
            phase = self.phases[name] = Phase(name)
        else:
            phase = self.phases[name]
        # Add the page into it
        if page.name not in phase.pages:
            phase.pages[page.name] = page

    def readFields(self):
        '''Create attribute "fields" as an ordered dict storing all fields
           defined on this class and parent classes.'''
        class_ = self.python
        r = collections.OrderedDict()
        Err = Model.Error
        # Find field in p_class_ and base classes
        for aClass in self.getFieldClasses(class_):
            tfield = sfield = None
            for name, field in aClass.__dict__.items():
                if name.startswith('__'): continue
                if isinstance(field, Field):
                    # Ensure the field name is acceptable
                    self.checkAttributeName(name)
                    if not aClass.__module__.startswith('appy.model') and \
                       Meta.unallowedName(name):
                        raise Err(NAME_KO % (name, self.name))
                    # A field was found.
                    # ~
                    # Special fields "title", "record", "searchable" and "state"
                    # must be duplicated. Else, all app classes will get the
                    # modifications that the developer can apply to it via
                    # "update" methods.
                    if name == 'searchable':
                        field = sfield = Text(**Base.searchableAttributes)
                    elif name == 'title':
                        field = tfield = String(**Base.titleAttributes)
                    elif name == 'record':
                        field = Computed(**Base.recordAttributes)
                        field.page = field.page.clone()
                    elif name == 'state':
                        field = Select(**Base.stateAttributes)
                    # Late-initialize it
                    field.init(self, name)
                    r[name] = field
                    if field.page:
                        self.readPage(field.page)
            # Reify the link betweeen fields "title" and "searchable" on their
            # duplicates for this v_aClass.
            if tfield and sfield: tfield.filterField = sfield
        self.fields = r

    def setField(self, name, field):
        '''Possibly called by p_self.python's m_update method, this method adds,
           to p_self.fields, a new p_field named p_name, or replaces the field
           currently named p_name if the name is already in use.'''
        self.fields[name] = field
        # Late-initialise it
        field.init(self, name)

    def openHistories(self):
        '''Make histories on p_self's objects viewable by anyone having the
           "read" permission on these objects.'''
        # Indeed, by default, object histories are not "open" to object viewers
        # (from the UI): they are viewable by Managers only.
        record = self.fields['record']
        record.show = record.page.show = 'view'

    def readSearches(self):
        '''Create attribute "searches" as an ordered dict storing all static
           searches defined on this class.'''
        class_ = self.python
        r = collections.OrderedDict()
        Err = Model.Error
        if hasattr(class_, 'searches'):
            for search in class_.searches:
                name = search.name
                # Ensure the search name is acceptable
                if Meta.unallowedName(name):
                    raise Err(NAME_KO % (name, self.name))
                # Ensure the search name is unique, also among fields
                if name in r:
                    raise Err(DUP_S_NAME % (self.name, name))
                if name in self.fields:
                    raise Err(S_F_HOM % (self.name, name))
                # Ensure the field name is acceptable
                self.checkAttributeName(name)
                search.init(self)
                r[search.name] = search
        self.searches = r

    def getCreators(self):
        '''Gets the roles allowed to create instances of this class'''
        r = []
        class_ = self.python
        # The info can be defined in a static attribute named "creators"
        creators = getattr(self.python, 'creators', None)
        if not creators: return r
        # Athough a method can be specified in "creators", we can't execute it,
        # so we care about creators only if defined "statically", as a list.
        if not isinstance(creators, list): return r
        # Browse roles
        for creator in creators:
            if isinstance(creator, Role):
                if creator.local:
                    error = CR_LOC_ROLE % (self.name,creator.name)
                    raise Model.Error(error)
                r.append(creator)
            else:
                r.append(Role(creator))
        return r

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                         Instance-creation method
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def new(self, iid, id, login, initialComment=None, initialState=None):
        '''Create and return an instance of the concrete class'''
        o = self.concrete()
        # Set the IDs on the object
        o.iid = iid
        o.id = id
        # Create the object's history
        o.history = History(o)
        # Create a dict storing the object's local roles, and grant role 'Owner'
        # to the user behind this object creation, whose p_login is given.
        o.localRoles = LocalRoles()
        o.localRoles.add(login, 'Owner')
        # Create the dict "values" that will store field values, and set the
        # first values in it.
        o.values = PersistentMapping() # ~{s_fieldName: fieldValue}~
        # Initialise object's history by triggering the _init_ transition
        workflow = self.workflow
        tr = workflow.initialTransition
        # Cheat with the initial state if p_initialState is there
        state = workflow.states[initialState] if initialState else tr.states[1]
        tr.trigger(o, initialComment, doSay=False, forceTarget=state)
        return o

    def generateId(self, o):
        '''A method named "generateId" may exist on p_self.python, allowing the
           app's developer to choose itself an ID for the p_o(bject) under
           creation. This method accepts p_o as unique arg and must return the
           ID as a string, or None.'''
        # Return None if no such method is defined on p_self.python
        if not hasattr(self.python, 'generateId'): return
        r = self.python.generateId(o)
        # If the method return None, a standard ID will be generated by Appy
        if r is None: return
        # Raise an error if the returned ID is not a string
        if not isinstance(r, str):
            raise Exception(CUS_ID_KO)
        return r

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # Run-time methods
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # The following set of methods allow to compute, at run-time,
    # class-dependent elements.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def getListTitle(self, o, nav):
        '''Gets p_o's title as it must appear within lists of objects'''
        if hasattr(self.python, 'listTitle'):
            r = self.python.listTitle(o, nav)
        else:
            r = o.getShownValue()
        return r

    def getPageLayouts(self, o):
        '''Gets the page layouts being applicable to p_o, being an instance of
           p_self.'''
        r = getattr(self.python, 'layouts', None)
        if callable(r): r = r(o)
        return r or Layouts.Page.defaults

    def produceUniqueLinks(self):
        '''When producing links ("a" tags) to instances of this class, must
           these links always be unique ?'''
        return hasattr(self.python, 'uniqueLinks') and self.python.uniqueLinks

    def showTransitions(self, o, layout):
        '''When displaying p_self's instance p_o, must we show, on p_layout, the
           buttons/icons for triggering transitions ?'''
        # Never show transitions on edit pages
        if layout == 'edit': return
        # Use the default value if self does not specify it
        if not hasattr(self.python, 'showTransitions'): return layout == 'view'
        r = self.python.showTransitions
        r = r(o) if callable(r) else r
        # This value can be a single value or a tuple/list of values
        return layout == r if isinstance(r, str) else layout in r

    # Default CSS classes by UI zone
    defaultCssClasses = {
      'list' : 'list', # [class level] The table tag containing a list of this
                       # class' objects (tied objects from a Ref field, results
                       # from a search, etc.)
      'title': None,   # [object level] The "title" "a" tag (or span if
                       # unclickable) referring to an instance of this class,
                       # shown within lists of objects.
      'pside': None  , # [class level] *p*ortlet side: a zone within the
                       # portlet, on the right side, aimed at becoming a
                       # colored strip if desired.
      'tbot' : None  , # [class level] *t*itle *bot*tom: a zone, on search
                       # results, below the search title, aimed at becoming a
                       # colored sub-strip, when desired.
      'sep'  : None  , # [class level] Still on search results, within the row
                       # located under the search title, this zope represents
                       # the *sep*arator between controls and the count of
                       # objects.
      'sub'  : None  , # [object level] The zone displaying an object's actions
                       # on a list of objects, under or besides its title.
      'popup': None,   # [object level] A CSS class to apply to the main popup
                       # tag, when an object is rendered in the iframe popup. It
                       # is useless to define standard CSS class "popup", which
                       # is applied in all cases.
    }

    def getCssFor(self, o, zone, add=None):
        '''Gets the name of the CSS class to use for styling some p_zone on
           instance p_o. If this class does not define a dict or method named
           "styles", a defaut CSS class may be retrieved from
           p_self.defaultCssClasses.'''
        r = getattr(self.python, 'styles', None)
        if r:
            # v_r can be method, a dict or an Object
            r = r(o, zone) if callable(r) else r.get(zone)
        # Get the default CSS for the zone, when relevant
        r = r or Class.defaultCssClasses.get(zone)
        # There may be some CSS class to p_add
        if add:
            r = add if not r else ('%s %s' % (r, add))
        return r

    def getSubCss(self, o, context, index=None, inPickList=False):
        '''Gets the CSS class to apply to the "sub" layout (=object actions on
           a list of objects), in the p_context of a field or search, under or
           besides p_o's title. p_index is o's p_index within the current list
           of objects.'''
        # Within a Ref with render="menus", a specific CSS class must be used
        if isinstance(context, Ref) and index is None and not inPickList:
            # Currently, no custom CSS is possible for menus
            return 'menuActions'
        # For any other case: there is a mandatory standard CSS class + a
        # potential custom class.
        display = context.actionsDisplay
        if display == 'block':
            r = 'object'
        elif display == 'right':
            r = 'aligned'
        else:
            r = 'inline'
        # Complete this standard CSS class with a custom one, if any
        return self.getCssFor(o, 'sub', add='%sActions' % r)

    # Default i18n labels, per zone
    defaultLabels = {
      'deleteConfirm': 'delete_confirm', # Confirmation message when the user
                                         # clicks a "delete" button.
      'save'         : 'object_save'     # Label for the button allowing to
                                         # create or update objects.
    }

    def getTextFor(self, o, zone):
        '''Gets the translated text corresponding to this p_zone'''
        texts = getattr(self.python, 'texts', None)
        r = texts(o, zone) if texts else None
        return r or o.translate(Class.defaultLabels[zone])

    def getDeleteConfirm(self, o, q, back=None):
        '''Return the JS code that executes when someone wants to delete p_o'''
        back = q(back) if back else 'null'
        return 'onDeleteObject(%s,%s,%s)' % \
               (q(o.iid), back, q(self.getTextFor(o, 'deleteConfirm')))

    def getIconsOnly(self):
        '''For base actions (edit, delete, etc), must icons only appear, or
           complete buttons containing an icon + a label ?'''
        # By default, base actions are rendered as simple icons
        return getattr(self.python, 'iconsOnly', True)

    def getCreateVia(self, tool):
        '''How to create instances of this class ? The answer can be: via a
           web form ("form"), via a form pre-filled from a template (a Search
           instance) or programmatically only (None).'''
        # By default, instances are created via an empty web form
        r = getattr(self.python, 'createVia', 'form')
        return r if not callable(r) else r(tool)

    def getCreateLink(self, tool, createVia, formName, sourceField=None,
                      insert=None):
        '''When instances of p_self must be created from a template (from the
           UI), this method returns the link allowing to search such templates
           from a popup.'''
        r = '%s/Search/results?className=%s&search=fromSearch&popup=True&' \
            'fromClass=%s&formName=%s' % \
            (tool.url, createVia.container.name, self.name, formName)
        # When object creation occurs via a Ref field, its coordinates are given
        # in p_sourceField as a string: "sourceObjectId:fieldName".
        if sourceField: r += '&sourceField=%s' % sourceField
        # p_insert is filled when the object must be inserted at a given place
        if insert: r += '&insert=%s' % insert
        return r

    def getCreateExclude(self, o):
        '''When an instance of this class must be created from a template
           object, what fields must not be copied from the template ?'''
        r = getattr(self.python, 'createExclude', ())
        return r(o) if callable(r) else r

    def getConfirmPopupWidth(self, popup):
        '''Gets the width (in pixels, as an integer value), of the confirmation
           popup possibly shown when creating or editing p_self's instances.'''
        return getattr(self.python, 'confirmPopup', 350 if popup else 500)

    def maySearch(self, tool, layout):
        '''May the user search among instances of this class ?'''
        # When editing a form, one should avoid annoying the user with this
        if layout == 'edit': return
        return self.python.maySearch(tool) \
               if hasattr(self.python, 'maySearch') else True

    def getSearchAdvanced(self, tool):
        '''Gets the "advanced" search defined on this class if present'''
        # This Search instance, when present, is used to define search
        # parameters for this class' special searches: advanced, all and live
        # searches.
        r = getattr(self.python, 'searchAdvanced', None)
        return r if not callable(r) else r(tool)

    def maySearchAdvanced(self, tool):
        '''Is advanced search enabled for this class ?'''
        # Get the "advanced" search
        advanced = self.getSearchAdvanced(tool)
        # By default, advanced search is enabled
        if not advanced: return True
        # Evaluate attribute "show" on this Search instance representing the
        # advanced search.
        return advanced.isShowable(tool)

    def isIndexable(self):
        '''Is p_self "indexable" ? In other words: do we need to have a Catalog
           storing index values for instances of this class ?'''
        return getattr(self.concrete, 'indexable', True)

    def getCatalog(self, o):
        '''Returns the catalog tied to p_self, if it exists'''
        if not self.isIndexable(): return
        return o.H().dbConnection.root.catalogs.get(self.name)

    def getIndex(self, o, name):
        '''Returns the index having this p_name, from p_self's catalog, if it
           exists.'''
        catalog = self.getCatalog(o)
        if catalog:
            return catalog.get(name)

    def getListPods(self, tool):
        '''Finds, among p_self's fields, those being Pod fields showable on
           search results.'''
        # r is a dict {p_field: [visibleTemplate]}
        r = {}
        for field in self.fields.values():
            if isinstance(field, Pod) and field.multiObjects:
                show = field.show(tool) if callable(field.show) else field.show
                if show == 'query':
                    visible = field.getVisibleTemplates(tool)
                    if visible:
                        r[field] = visible
        return r

    def getDynamicSearches(self, tool):
        '''Gets the dynamic searches potentially defined on this class'''
        # Stop here if no dynamic search is defined
        if not hasattr(self.python, 'getDynamicSearches'): return
        # Create the cache if it does not exist yet
        handler = tool.H()
        dyn = handler.cache.dynamicSearches
        if dyn is None:
            dyn = handler.cache.dynamicSearches = {}
        # Get the cached searches when present; compute and cache them else
        name = self.name
        if name in dyn:
            r = dyn[name]
        else:
            r = dyn[name] = self.python.getDynamicSearches(tool)
            for search in r: search.init(self)
        return r

    def getSearch(self, name, tool=None):
        '''Returns static or dynamic search whose name is p_name'''
        # Search among static searches
        r = self.searches.get(name)
        if r or (tool is None): return r
        # Search among dynamic searches
        dyn = self.getDynamicSearches(tool)
        if dyn:
            for search in dyn:
                if search.name == name:
                    return search

    def getGroupedSearches(self, tool, ctx):
        '''Returns an object with 2 attributes:
           * "searches" stores the searches defined for this class, as instances
             of the run-time-specific class appy.model.searches.ui.UiSearch;
           * "default" stores the search being the default one.
        '''
        searches = []
        default = None # Also retrieve the default one here
        groups = {} # The already encountered groups
        page = FieldPage('searches') # A dummy page required by class UiGroup
        # Get the statically defined searches from class's "searches" attribute
        for search in self.searches.values():
            # Ignore search that can't be shown
            if not search.isShowable(tool): continue
            searches.append(search)
        # Get the dynamically computed searches
        dyn = self.getDynamicSearches(tool)
        if dyn: searches += dyn
        # Return the grouped list of UiSearch instances
        r = []
        for search in searches:
            # Create the search descriptor
            ui = search.ui(tool, ctx)
            if not search.group:
                # Insert the search at the highest level, not in any group
                r.append(ui)
            else:
                uiGroup = search.group.insertInto(r, groups, page, self.name,
                                                  content='searches')
                uiGroup.addElement(ui)
            # Is this search the default search?
            if search.default: default = ui
        return O(all=r, default=default)

    def getSearchFields(self, tool, refInfo=None):
        '''Returns, as 2-tuple:
           - p_self's searchable fields (some among all indexed fields),
           - CSS files required to render the search fields,
           - Javascript files required to render these fields,
           - a Gridder instance determining how to render the search form.'''
        # We will collect CSS and JS files required for search fields
        fields = []; css = []; js = []
        if refInfo:
            # The search is triggered from a Ref field
            o, ref = Search.getRefInfo(tool, refInfo, nameOnly=False)
            names = ref.queryFields or ()
            cols = ref.queryNbCols
        else:
            # The search is triggered from an app-wide search
            names = getattr(self.python, 'searchFields', None)
            names = names(tool) if callable(names) else names
            cols = getattr(self.python, 'numberOfSearchColumns', 1)
        # Get fields from names
        if names:
            fields = []
            for name in names:
                field = self.fields.get(name)
                if field is None:
                    tool.log(S_FIELD_KO % (name, self.name), type='warning')
                else:
                    fields.append(field)
        else:
            # If fields are not explicitly listed, take all indexed fields,
            # "title" excepted, "searchable" and "title" being mostly redundant.
            fields = [field for field in self.fields.values() \
             if field.indexed and (field.name not in Class.unsearchableFields)]
        # Collect CSS and JS files
        config = tool.config
        for field in fields:
            field.getCss(None, 'edit', css)
            field.getJs(None, 'edit', js, config)
        # Returns a gridder allowing to render the search field
        gridder = Gridder(cols=cols, colsAuto=True,
                         justifyContent='left', gap='1em 3em')
        return fields, css, js, gridder

    def getResultModes(self):
        '''Gets the search result modes for this class'''
        return getattr(self.python, 'resultModes', None)

    def getResultsTop(self, tool, search, mode):
        '''Returns something to display on the results page just before
           displaying search results.'''
        method = getattr(self.python, 'getResultsTop', None)
        return method(tool, search, mode) if method else None

    def mayEditEventComment(self, o, event, user, isManager):
        '''May p_user edit the comment on this p_event, coming from p_o's
           history ?'''
        r = getattr(self.python, 'editHistoryComments', None)
        # Call the potentially defined custom method
        if callable(r): r = r(o, event)
        # The comment may be edited, but not for any event, by any user
        if r:
            # Allow edition if logged user is a Manager (p_isManager is True) or
            # if he is the p_event's author.
            return isManager or user.login == event.login

    def getTitleMode(self):
        '''Gets the "title mode" for instances of this class'''
        # Consult homonym method on class appy.model.searches.UiSearch
        return getattr(self.python, 'titleMode', None)

    def toggleSubTitles(self, tool, from_):
        '''Must the mechanism for toggling sub-titles be enabled on p_self ?'''
        # Sub-titles may appear, within lists or grids of p_self's instances,
        # under the title of every instance.
        # ~
        # p_from may hold a Ref field. In that case, toggling sub-titles occurs
        # in the context of a list of objects being tied via this field.
        # ~
        # Check first if the mechanism is explicitly disabled
        if from_ and from_.toggleSubTitles is not None:
            toggle = from_.toggleSubTitles
        else:
            toggle = getattr(self.python, 'toggleSubTitles', None)
        if callable(toggle): toggle = toggle(tool)
        if toggle is False: return
        # Enable it if the class defines a method named "getSubTitle"
        return hasattr(self.python, 'getSubTitle')

    def getPortletBottom(self, tool):
        '''Is there a custom zone to display at the bottom of the portlet zone
           for this class ?'''
        r = getattr(self.concrete, 'portletBottom', None)
        if r is None: return
        return r if isinstance(r, Px) else r(tool)

    def getListColumns(self, tool):
        '''Return the list of columns to display when rendering p_self's
           instances in a table.'''
        r = getattr(self.python, 'listColumns', ('title',))
        return r if not callable(r) else r(tool)

    def getFilters(self, tool, filters=None):
        '''Extracts, from the request (or from p_filters if passed), filters
           defined on fields belonging to this class.'''
        r = sutils.getDictFrom(filters or tool.req.filters)
        # Apply a potential transform on every filter value
        for name in list(r.keys()):
            # Get the corresponding field
            field = self.fields.get(name)
            if field:
                try:
                    r[name] = field.getFilterValue(r[name])
                except Exception as err:
                    # The encoded value is invalid. Ignore it.
                    tool.log(FILT_ERR % (self.name, name, str(err)),
                             type='warning')
                    del(r[name])
        return r

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                                  PXs
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Icon for creating instances of this class from a template
    pxAddFrom = Px('''
     <!-- The image outside the button, if "iconOut" -->
     <img if="iconOut" src=":field.getIconUrl(url)"
          class=":'clickable %s' % field.iconCss"
          onclick="this.nextSibling.click()"/>

     <!-- The button in itself -->
     <a target="appyIFrame" id=":addFormName + '_from'"
        href=":class_.getCreateLink(tool, createVia, addFormName, sourceField)">
      <input var="css='Small' if fromRef else 'Portlet';
                  cssOut='noIcon ' if iconOut else '';
                  label=_(field.addFromLabel if field else 'object_add_from')"
         type="button" value=":label" onclick="openPopup('iframePopup')"
         class=":'%sbutton%s button' % (cssOut, css)"
         style=":'' if iconOut else svg('add', bg=True)"/>
     </a>''')

    # Style characteristics to apply to the "add" button, depending on its type
    addStyles = {
      # The "add" button as it appears in the portlet
      'portlet': O(css='buttonPortlet button', bgIcon='portletAdd',
                   bgSize=True),
      # The "add" button as it may appear elsewhere (ie, on search results)
      'small'  : O(css='buttonSmall button', bgIcon='add', bgSize='18px 18px'),
      # When using pxAdd from a custom PX, let this latter manage button style
      None     : O(css='', bgIcon=None, bgSize=None)
    }

    # Form for creating instances of this class from the portlet or a search.
    # Input variables:
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # "viaPopup" | (boolean) Indicates if the form must be opened in a popup.
    #            | Can be True only if we are not already in the popup.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # "onClick"  | (optional string) Alternate JS code to execute when clicking
    #            | on the "add" button.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    pxAdd = Px('''
     <form var="createVia=class_.getCreateVia(tool); className=class_.name"
           if="createVia" class="addForm" name=":'%s_add' % className"
           var2="styles=class_.addStyles[buttonType];
                 target=ui.LinkTarget(class_.python, popup=viaPopup);
                 text=_(label or 'object_add');
                 onClick=onClick|None"
           action=":'%s/new' % tool.url" target=":target.target">
      <input type="hidden" name="className" value=":className"/>
      <input type="hidden" name="template_" value=""/>
      <input type="hidden" name="insert" value=""/>
      <input type="hidden" name="nav" value=":nav"/>
      <input type="hidden" name="inav" value=":inav|''"/>
      <input type="hidden" name="popup"
           value=":'True' if (popup or (target.target!='_self')) else 'False'"/>

      <!-- Create from an empty form -->
      <input class=":styles.css" value=":text" title=":text" type="submit"
        style=":svg(styles.bgIcon, bg=styles.bgSize) if styles.bgIcon else ''"
        onclick=":target.getOnClick('searchResults', onClick=onClick)"/>

      <!-- Create from a pre-filled form when relevant -->
      <div if="createVia != 'form'" class="addFrom"
         var2="fromRef=False; sourceField=None; iconOut=False;
               addFormName='%s_add' % className">:class_.pxAddFrom</div>
     </form>''',

     css='''.addFrom input { margin-left:0 }''')

    # PX representing a class-diagram-like box for this class
    pxBox = Px('''
     <table class="small mbox">
      <tr><th>:class_.name</th><th></th></tr>
      <!-- Fields -->
      <x for="field in class_.fields.values()">:field.pxBox</x>
     </table>''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
