#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from ..px import Px
from .base import Base
from .searches import Search
from .fields.list import List
from ..ui.iframe import Iframe
from ..ui.layout import Layouts
from .fields.group import Group
from .searches.modes import Mode
from .fields.string import String
from .fields.integer import Integer
from .fields.boolean import Boolean
from .workflow.standard import Owner
from .fields.select import Select, Selection
from ..database.operators import Operator, or_

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Query(Base):
    '''Persistent and editable parameters for a Search'''

    workflow = Owner
    indexable = False # Queries are not indexed by default
    listColumns = 'title', 'className', 'states', 'sortBy', 'sortOrder','mode'
    pageListColumns = 'title', 'state'

    # Managers and Publishers may create queries
    creators = ['Manager', 'Publisher']

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                            Main parameters
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Fields in the main page are rendered in a grid group
    mainGroup = Group('main', ['250em', ''], style='grid', hasLabel=False)

    @staticmethod
    def update(class_):
        '''Configures the title'''
        title = class_.fields['title']
        title.layouts = Layouts.g
        title.group = class_.python.mainGroup

    qp = {'label': 'Query', 'group': mainGroup}

    # The name of the root class for which instances are searched
    def listRootClasses(self):
        '''Lists the app's root classes'''
        return [(name, self.translate(f'{name}_plural')) \
                for name in self.config.model.rootClasses]

    className = Select(validator=Selection(listRootClasses),
                       multiplicity=(1,1), **qp)

    # Only objects being in one of the states defined in the hereabove field
    # will be part of the result.

    def listStates(self, className=None):
        '''Lists the states from the workflow tied to the class whose name is
           p_className.'''
        className = className or self.className
        r = []
        if not className: return r
        for state in self.model.classes[className].workflow.states.values():
            r.append((state.name, self.translate(state.labelId)))
        return r

    states = Select(validator=Selection(listStates), multiplicity=(1,None),
                    master=className, masterValue=listStates, render='checkbox',
                    **qp)

    # Technical indexed fields that the user cannot choose
    unselectableIndexes = 'allowed', 'cid'

    # Search parameters, as a List field. Every row represents an indexe field,
    # an operator and a value.

    def listIndexedFields(self, className=None):
        '''Lists, for the class whose name is p_className, the fields being
           indexed.'''
        className = className or self.className
        if not className: return r
        # This may be cached
        key = f'{className}_ifs'
        if key in self.cache: return self.cache[key]
        r = []
        for field in self.model.classes[className].fields.values():
            # Ignore the field if it cannot be chosen
            if field.name in Query.unselectableIndexes: continue
            if field.indexed:
                r.append((field.name, self.translate(field.labelId)))
        # Cache and return the value
        self.cache[key] = r
        return r

    pfp = {'multiplicity': (1,1)}

    # Operators that can be selected for specifying parameter values
    operators = 'equals', 'or', 'in', 'and', 'not'

    pfields = (
      ('name', Select(validator=Selection(listIndexedFields), master=className,
                      masterValue=listIndexedFields, **pfp)),
      ('operator', Select(validator=operators, default='equals', **pfp)),
      ('value', String(**pfp)),
    )

    parameters = List(pfields, **qp)

    # Field used as sort key

    sortBy = Select(validator=Selection(listIndexedFields), multiplicity=(1,1),
                    master=className, masterValue=listIndexedFields, **qp)

    sortOrder = Select(validator=('asc', 'desc'), multiplicity=(1,1), **qp)

    mode = Select(validator=Mode.concrete, multiplicity=(1,1), **qp)

    maxPerPage = Integer(default=30, multiplicity=(1,1), width=2, **qp)

    showPods = Boolean(default=False, **qp)

    showTitle = Boolean(default=False, **qp)

    showNav = Select(validator=('top', 'bottom', 'both', 'none'),
                     default='both', multiplicity=(1,1), render='radio', **qp)

    navAlign = Select(validator=('left', 'center', 'right'),
                     default='center', multiplicity=(1,1), render='radio', **qp)

    showFilters = Boolean(default=True, **qp)

    def validViaPopup(self, value):
        '''Ensure p_value is valid to be stored in field "viaPopup"'''
        value = value.strip()
        # Value can be "False" or can contain pa popup's width and height, in
        # pixels.
        if not value or (value == 'False'): return True
        value = value.split()
        if len(value) > 2: return self.translate('wrong_via_popup')
        for v in value:
            if not v.endswith('px') or not v[:-2].isdigit():
                return self.translate('wrong_via_popup')
        return True

    viaPopup = String(layouts=Layouts.gd, validator=validViaPopup, **qp)

    popupResizable = Boolean(layouts=Boolean.Layouts.gdl, **qp)

    pageLayoutOnView = String(layouts=Layouts.gd, **qp)

    def addParameters(self, search):
        '''Adds p_self.parameters to that p_search object'''
        # Invariant: p_self.parameters is not empty
        class_ = self.model.classes[self.className]
        for info in self.parameters:
            field = class_.fields[info.name]
            if info.operator == 'equals':
                # p_info.value contains a single value
                val = field.getQueryValue(self, info.value)
            else:
                # p_info contains several values
                operClass = Operator.byName[info.operator]
                values = [field.getQueryValue(self, v) \
                          for v in info.value.split(',')]
                val = operClass(*values)
            search.fields[info.name] = val

    def getSearch(self):
        '''Creates the Search object corresponding to this query'''
        # Get the expression related to p_self.states
        states = self.states
        state = states[0] if len(states) == 1 else or_(states)
        # Get the "viaPopup" parameter
        viaPopup = self.viaPopup or ''
        if viaPopup == 'False':
            viaPopup = False
        elif ' ' in viaPopup: # Popup width and height are specified
            viaPopup = viaPopup.split()
            for i in (0, 1): viaPopup[i] = viaPopup[i].strip()
            viaPopup = Iframe(*viaPopup, resizable=self.popupResizable)
        elif viaPopup: # Only the popup width is specified
            viaPopup = viaPopup.strip()
            viaPopup = Iframe(viaPopup, resizable=self.popupResizable)
        # Create the Search object corresponding to p_self's attributes
        className = self.className
        class_ = self.model.classes.get(className)
        r = Search(name=str(self.iid), maxPerPage=self.maxPerPage,
                   translated=self.translate(f'{className}_plural'),
                   sortBy=self.sortBy, sortOrder=self.sortOrder,
                   showPods=self.showPods, showTitle=self.showTitle,
                   showNav=self.showNav, navAlign=self.navAlign,
                   showFilters=self.showFilters, container=class_,
                   viaPopup=viaPopup, pageLayoutOnView=self.pageLayoutOnView,
                   resultModes=(self.mode,), state=state)
        # Add parameters, if any
        if self.parameters:
            self.addParameters(r)
        return r

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                            Main methods
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def validate(self, new, errors):
        '''Ensure parameter values are correct'''
        params = new.parameters
        if not params: return
        class_ = self.model.classes[new.className]
        pField = self.getField('parameters')
        i = -1
        for info in params:
            i += 1
            # Get the field whose value is specified in p_info
            field = class_.fields[info.name]
            error = field.validQueryValue(self, info.value, info.operator)
            if error:
                # The value and/or operator is invalid: v_error contains a
                # translated explanation about the error and the name of the
                # erroneous sub-field (the value or the operator).
                text, name = error
                entry = pField.getEntryName(name, i)
                errors[entry] = text
                return

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                            PX rendering
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Simulate a HTTP GET on a search corresponding to this Query instance
    pxView = Px('''
     <x var="x=setattr(req, 'className', o.className);
             x=setattr(req, 'search', str(o.iid));
             x=Px.injectRequest(_ctx_, req, tool)">:tool.Search.results</x>''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
