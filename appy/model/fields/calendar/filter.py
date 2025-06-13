#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.px import Px
from appy.ui.layout import Layouts
from appy.model.fields.select import Select

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Filter:
    '''Abstract base class representing a filter allowing to view only a
       selection of all the events in a calendar view.'''

    def __init__(self, name, label, validator, showEvent, show=True):
        # A short name that must identify this filter among all filters defined
        # in this calendar.
        self.name = name
        # A i18n p_label for producing a translated name in the user interface
        self.label = label
        # The p_validator, as for a Field, determines the values that can be
        # selected via the filter. It depends on the concrete Filter class. For
        # example, a SelectFilter will define a validator as the list of
        # possible values one may select in the filter. For an IntegerFilter,
        # the validator will define the range of acceptable integer values.
        self.validator = validator
        # p_showEvent determines if this filter (p_self) permits an event to be
        # shown. It must be a method accepting, as args, (1) one of the events
        # that should be rendered in the calendar and (2) the list of currently
        # applied filter values. It must return True if the filter allows to
        # render the event, False else.
        self.showEvent = showEvent
        # Must this filter be shown or not? p_show can be a boolean or a method.
        # If it is a method, it must accept, as unique arg, a DateTime object
        # being the first (or sole) day of the current calendar view.
        self.show = show
        # Every concrete filter will create, in the following field, an instance
        # of the Field sub-class that will be resused as basis for rendering the
        # filter.
        self.field = None
        # Was p_self.field late-initialised ?
        self.lateInit = False

    def init(self, o, calendar):
        '''Late-initialise p_self.field'''
        # Do it only if not done yet
        if self.lateInit: return
        # Do not set an inner-field-like name for the filter, of the form
        # <outer_field>*<inner_field>. Appy has expectations about outer values
        # being in the request, that do not correspond to the reality of filter
        # fields within calendar fields.
        fullName = f'{calendar.name}{self.name}'
        self.field.init(calendar.container, fullName)
        # Add p_self.field to p_calendar.filterFields
        ffields = calendar.filterFields
        if ffields is None:
            calendar.filterFields = ffields = {}
        ffields[self.name] = self.field

    def getWidgetType(self):
        '''Which HTML widget is used to render this filter ?'''
        # To be overridden by sub-classes

    def patchRequest(self, req, values):
        '''Adds, in the p_req(uest), attributes required by p_self.field, based
           on filter p_values parsed from the request.'''
        # Indeed, rendering a calendar filter is done by (mis- or re-)using a
        # standard Appy field (p_self.field). If this field must display the
        # currently selected filter values, these latters must be expressed in a
        # way that conforms to what the Appy field expects, which is not the
        # case of filter p_values. Consequently, this method has the
        # responsibility to extract, from p_values, filter values being related
        # to p_self.field and reexpress it as appropriate attributes on p_req.
        #
        # To be overridden by child classes: it depends on the type of
        # p_self.field.

    def hides(self, o, event, values):
        '''Does this filter, having these currently applied p_values, hide this
           p_event ?'''
        return not self.showEvent(o, event, values)

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                             Class methods
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @classmethod
    def getVisibleOn(class_, o, field):
        '''Returns, as a dict keyed by their name, the filters that must be
           shown on this calendar p_field for this p_o(bject).'''
        filters = field.filters
        if not filters: return
        r = {}
        for filteR in filters:
            show = filteR.show
            show = show(o) if callable(show) else show
            if show:
                # By the way, late-initialise p_filteR.field if not done yet
                filteR.init(o, field)
                r[filteR.name] = filteR
        return r

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                                  PXs
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    px = Px('''
     <!-- Repeat the current object title: it could not be visible when
          scrolling. -->
     <div class="preF">::o.getShownValue()</div>
     <div for="filteR in view.filters.values()"
          var2="fname=filteR.name; ftype=filteR.getWidgetType()">
      <!-- Filter name, with actions -->
      <div class="titleF">
       <div>::_(filteR.label)</div>
       <div onClick=":f'Filters.askOne(this,`{fname}`,`{ftype}`)'"
            class="clickable actFL" title=":_('filter_apply')">⮂</div>
       <div onClick=":f'Filters.cleanOne(this,`{fname}`,`{ftype}`)'"
            class="clickable" title=":_('filter_clean')">☓</div>
      </div>
      <!-- The filter in itself -->
      <x var="field=filteR.field; layout='edit'">:field.pxRender</x>
     </div>
     <!-- Global actions; apply or clean all filters -->
     <div if="len(view.filters) &gt; 1" class="allF" var="text=_('everything')">
      <div onclick=":f'Filters.askAll(this)'" class="clickable"
           title=":_('filter_apply')"><x>:text</x> ⮂</div>
      <div onclick=":f'Filters.cleanAll(this)'" class="clickable cleanF"
           title=":_('filter_clean')"><x>:text</x> ☓</div>
     </div>''',

     css='''.titleF { display:flex; gap:0.5em; margin-bottom: 0.3em;
                      border-bottom:2px solid |phaseBgColor|; padding:0.2em }
            .preF { margin-top:0.6em; font-size:95%; color:grey }
            .actFL { margin-left:auto }
            .allF { display:flex; gap:0.6em; justify-content:center;
                    margin-top: 0.5em }
            .allF > div { padding: 0 0.5em; font-size:90%;
                          border: 1px solid |phaseBgColor|;
                          background-color:|lightBgColor| }
            .allF > div.cleanF { background-color:|brightColor| }
     ''')

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class SelectFilter(Filter):
    '''Filter allowing to select values from a list of values'''

    def __init__(self, name, label, validator, acceptEvent, show=True,
                 multiple=True):
        '''SelectFilter constructor'''
        # Call the base constructor. p_validator must be a Selection object.
        super().__init__(name, label, validator, acceptEvent, show)
        # May a single value or multiple values be selected in the filter ?
        self.multiple = multiple
        # Use a Select field to render the filter
        maxMult = None if multiple else 1
        self.field = Select(multiplicity=(0, maxMult), validator=validator,
                            render=self.getWidgetType(), layouts=Layouts.f,
                            height='15em')

    def getWidgetType(self):
        '''Which HTML widget is used to render this filter ?'''
        return 'checkbox' if self.multiple else 'select'

    def patchRequest(self, req, values):
        '''Patch the p_req(uest) with p_self.field-specific values, extracted
           from these parsed filter p_values.'''
        vals = values.get(self.name)
        if not vals: return
        req[self.field.name] = vals

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Add sub-classes as attributes of the abstract class
Filter.Select = SelectFilter
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
