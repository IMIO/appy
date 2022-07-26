# -*- coding: utf-8 -*-

'''Manages accounts-related data in the user interface'''

# ------------------------------------------------------------------------------
from appy.px import Px
from appy.shared.utils import formatNumber

# ~license~
# ------------------------------------------------------------------------------
class Entry:
    '''Abstract base class for any entry'''
    def __init__(self, account, label, style, sep, cellTag):
        # The outer account
        self.account = account
        # The (translated) label for the amount
        self.label = label
        # Some style may be applied to the label entry
        self.style = style
        # A separator line may de drawn just before rendering the row
        self.sep = sep
        # The tag to use for dumping a cell: td or th
        self.cellTag = cellTag

    def renderRow(self, i):
        '''Returns the table row corresponding to this entry, which has index
           p_i in the list.'''
        css = (i % 2) and 'even' or 'odd'
        return '<tr class="%s">%s</tr>' % (css, self.render())

    def renderLabel(self):
        '''Renders the label for this entry'''
        s = self.style
        if s:
            label = '<%s>%s</%s>' % (s, self.label, s)
        else:
            label = self.label
        return '<label>%s</label>' % label

# ------------------------------------------------------------------------------
class Amount(Entry):
    '''Represents one entry in an account, being some positive or negative
       amount.'''

    def __init__(self, account, label, value, positive=True, style=None,
                 unit=None, align='right', sep=False, cellTag='td'):
        # Call the base constructor
        Entry.__init__(self, account, label, style, sep, cellTag)
        # The (float or int) amount (or None)
        self.value = value
        # Must we negate the value ?
        self.positive = positive
        # The unit for this amount
        self.unit = unit or account.defaultUnit
        # Value alignment
        self.align = align

    def renderUnit(self, value, css=None):
        '''Render the "unit" part of this amount'''
        if value is None:
            r = ''
        else:
            r = self.unit or ''
        if r:
            r = '<span class="discreet">%s</span>' % r
        t = self.cellTag
        return '<%s%s>%s</%s>' % (t, css or '', r, t)

    def render(self):
        '''Returns the XHTML table cells corresponding to this entry'''
        # Dump a separator if required
        tdc = self.sep and ' class="accountSep"' or ''
        # Format the value
        value = self.value
        if value is None:
            value = '-'
            sign = ''
        else:
            value = formatNumber(value, tsep=' ')
            sign = not self.positive and '-' or ''
        # Define the unit
        unit = self.renderUnit(value, css=tdc)
        # Produce the complete result
        t = self.cellTag
        return '<%s>%s</%s><%s%s align="center">%s</%s><%s align="%s"%s>%s' \
               '</%s>%s' % (t, self.renderLabel(), t, t, tdc, sign, t, t,
                            self.align, tdc, value, t, unit)

# ------------------------------------------------------------------------------
class Section(Entry):
    '''Entry representing a section'''
    def __init__(self, account, label, style=None, sep=False, cellTag='td'):
        # Call the base constructor
        Entry.__init__(self, account, label, style, sep, cellTag)

    def render(self):
        '''Renders this section'''
        t = self.cellTag
        return '<%s class="accountSub">%s</%s><%s colspan="3"></%s>' % \
               (t, self.renderLabel(), t, t, t)

# ------------------------------------------------------------------------------
class Account:
    '''An "account" is a list of entries, each of them being an amount (positive
       or negative), a total or some specific UI element like a separator.'''

    # Default width for columns: label, sign, value and unit
    defaultColumns = ['185em', '', '70em', '']

    def __init__(self, o, width='100%', css='', columns=None, defaultUnit=None):
        # The object from which data will be collected to create the account
        self.o = o
        # The account entries
        self.entries = []
        # Styles to apply to the resulting XHTML table
        self.width = width
        self.css = css
        self.columns = columns or Account.defaultColumns
        # This default unit, if present, will be shown for every entry for which
        # no unit is defined.
        self.defaultUnit = defaultUnit

    def addAmount(self, field=None, value=None, expression=None, label=None,
                  mapping=None, positive=True, style=None, unit=None,
                  sep=False, fieldValue=None, cellTag='td'):
        '''Adds an entry of type "amount" in the account'''

        # ----------------------------------------------------------------------
        # The label and value of the amount to display can be determined by:
        # ----------------------------------------------------------------------
        # p_field      | it must be the name of a Float or Integer field whose
        #              | value will be retrieved on p_self.o, excepted if
        #              | p_fieldValue is given: it will be used instead;
        # ----------------------------------------------------------------------
        # p_value      | it must be a float or int value. in that case, an i18n
        #              | p_label must be present and will be used (with an
        #              | optional p_mapping) to determine the label for this
        #              | amount;
        # ----------------------------------------------------------------------
        # p_expression | it must be a string containing a Python expression that
        #              | will be evaluated with "o" in its context ("o" being
        #              | p_self.o). The expression must return the float or int
        #              | amount; in that case, similarly to the previous case,
        #              | an i18n p_label must be present, with its optional
        #              | p_mapping.
        # ----------------------------------------------------------------------
        # p_positive is False, the amount will be negated. A specific p_style
        # can be applied to the entry "b" (bold) or "i" (italic).
        o = self.o
        if expression:
            label = o.translate(label, mapping=mapping)
            value = eval(expression)
        elif value is not None:
            label = o.translate(label, mapping=mapping)
        else:
            field = o.getField(field)
            label = o.translate(field.labelId)
            if fieldValue is not None:
                value = fieldValue
            else:
                value = getattr(o, field.name)
        # Create the Amount instance and add it among this account's entries
        amount = Amount(self, label, value, positive=positive, style=style,
                        unit=unit, sep=sep, cellTag=cellTag)
        self.entries.append(amount)

    def addSection(self, label, style=None, sep=False, cellTag='td'):
        '''Adds a section entry'''
        section = Section(self, label, style=style, sep=sep, cellTag=cellTag)
        self.entries.append(section)

    def pop(self):
        '''Removes and return the last entry'''
        return self.entries.pop()

    def getColGroup(self):
        '''Get column specifiers for the main table'''
        cols = []
        for width in self.columns:
            cols.append('<col width="%s"/>' % width)
        return '<colgroup>%s</colgroup>' % ''.join(cols)

    px = Px('''
     <table with=":self.width" class=":self.css" id="account">
      <!-- Column specifiers -->
      <colgroup><col for="width in self.columns" width=":width"/></colgroup>
      <x for="entry in self.entries">::entry.renderRow(loop.entry.nb)</x>
     </table>''',

    css='''
     #account td { padding: 8px }
     .accountSep { border-top: 1px solid black }
     .accountSub { border-bottom: 1px dashed black }
     ''')

    def render(self):
        '''Renders the account as a chunk of XHTML'''
        return Account.px({'self': self})
# ------------------------------------------------------------------------------
