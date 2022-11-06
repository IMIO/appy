#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# This module manages the totals that can be computed from lists of objects
# (List/Dict fields, Search results, etc)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.px import Px
from appy.model.utils import Object as O

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Total:
    '''Represents the computation of a specific total that will be aggregated
       from a series of cells within a list of objects.'''

    def __init__(self, name, field, initValue):
        # The sub-field name
        self.name = name
        # In the case of an inner field, p_field.name is prefixed with the main
        # field name.
        self.field = field
        self.value = initValue

    def __repr__(self):
        return '<Total %s=%s>' % (self.name, str(self.value))

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Totals:
    '''If you want to add rows representing totals computed from lists of
       objects (List rows, Search results...), specify it via Totals instances
       (see doc on the using class).'''

    def __init__(self, id, label, fields, labelPlace, onCell, initValue=0.0,
                 css='total'):
        # p_id must hold a short name or acronym and must be unique within all
        # Totals instances defined on the same container.
        self.id = id
        # p_label is a i18n label that will be used to produce a longer name
        # that will be shown at the start of the total row.
        self.label = label
        # p_fields is a list or tuple of field names for which totals must be
        # computed. When computing totals from an outer field, these fields
        # must be a sub-set from this fields' inner fields. The name of every
        # inner field must be of the form
        #
        #             <outer field name>*<inner field name>
        #
        # , as in this example:
        #
        #                        "expenses*amount"
        self.fields = fields
        # Within the row that will display totals for these p_fields, choose one
        # unused column, where to put p_label. This p_labelPlace must be the
        # name of such a field for which no total will be produced.
        self.labelPlace = labelPlace
        # p_onCell stores a method that will be called every time a cell
        # corresponding to a field listed in p_self.fields is walked in the
        # list of objects. When used by a List field, this method must be
        # defined on the object where the List field is defined; when used by a
        # Search, this method must be defined on the class whose objects are the
        # search results.
        #
        # p_onCell will be called with these args:
        # [* row  ]  [List only] The current "row", as an Object instance. For a
        #            Search, it is useless: the Appy object is already available
        #            via your method's p_self's attribute.
        # * value    The value of the current field on this object or row
        # * total    The Total instance (see above) corresponding to the current
        #            total.
        # * last     A boolean that is True if we are walking the last row.
        self.onCell = onCell
        # "initValue" is the initial value given to created Total instances
        self.initValue = initValue
        # The name of the CSS class that will bbe applied to the "tr" tag
        # corresponding to this Totals instance.
        self.css = css

    @classmethod
    def initialise(class_, container, iterator, columns, isEdit=False):
        '''Create, within a RunningTotals dict, one Total instance for every
           field for which a total must be computed on this p_container.'''
        if isEdit or not container.totalRows: return
        r = RunningTotals(container, iterator, columns)
        for totals in container.totalRows:
            subTotals = O()
            for name in totals.fields:
                to = Total(name, container.getField(name), totals.initValue)
                setattr(subTotals, name, to)
            r[totals.id] = subTotals
        return r

    @classmethod
    def update(class_, totals, o, looped, name, value, loop):
        '''Every time a cell is encountered while rendering a given list entry,
           this method is called, if required, to update p_totals.'''
        if not totals: return
        # In the case of an outer field, the currently walked object, p_looped,
        # is an inner row within this field on p_o. In any other case,
        # o == looped.
        # Browse Totals instances
        for row in totals.container.totalRows:
            # Are there totals to update ?
            total = getattr(totals[row.id], name, None)
            if total:
                last = loop[totals.iterator].last
                if o == looped:
                    row.onCell(o, value, total, last)
                else:
                    row.onCell(o, looped, value, total, last)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class RunningTotals(dict):
    '''Represents a bunch of Total instances being currently computed'''

    # Every key is the ID of a Totals instance. Every value is an object storing
    # one attribute per field whose total must be computed (Totals.fields). So,
    # for each such field, this object stores O.<fieldName> = <Total instance>.

    def __init__(self, container, iterator, columns):
        # The container element from which totals can be computed: a List field,
        # a Search instance,...
        self.container = container
        # The name of the iterator variable used to loop over objects for which
        # totals are being computed.
        self.iterator = iterator
        # Names of all shown columns in the list of objects. This will be used
        # at the end of the process, for rendering total rows.
        self.columns = columns

    def getCellFor(self, running, row, col, _):
        '''Generates, as a complete "td" tag, the cell corresponding to this
           p_col(umn) within this total p_row (=Totals instance).'''
        # This cell may contain :
        # (a) the rows label,
        # (b) a total or
        # (c) an empty string, if the p_col(umn) contains no summable info.
        #
        # Extract the field name from p_col
        if isinstance(col, tuple):
            # The field corresponding to this column may be None if it is not
            # currently showable. In that case, do not dump any cell at all.
            field = col[1]
            if field is None: return ''
            name = field.name
        elif isinstance(col.field, str):
            name = col.field
        else:
            name = col.field.name
        # This field may be the hook for placing the total label
        if name == row.labelPlace:
            r = _(row.label)
            # Force this label to be left-aligned
            style = ' style="text-align:left"'
        else:
            # Try to get a Total instance for this field
            total = running[name]
            r = total.value if total else ''
            style = ''
        return '<td%s>%s</td>' % (style, r)

    # Display total rows at the end of a list of objects
    px = Px('''
     <tr for="row in totals.container.totalRows" class=":row.css"
         var2="total=totals[row.id]">
      <x for="col in totals.columns">::totals.getCellFor(total, row, col, _)</x>
     </tr>''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
