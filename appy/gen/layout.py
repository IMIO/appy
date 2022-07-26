'''This module contains classes used for layouting graphical elements
   (fields, widgets, groups, ...).'''

# A layout defines how a given field is rendered in a given context. Several
# contexts exist:
#  "view"   represents a given page for a given Appy class, in read-only mode.
#  "edit"   represents a given page for a given Appy class, in edit mode.
#  "cell"   represents a cell in a table, like when we need to render a field
#           value in a query result or in a reference table.
#  "search" represents an advanced search screen.

# Layout elements for a class or page ------------------------------------------
#  s - The page summary, containing summarized information about the page or
#      class, workflow information and object history.
#  w - The widgets of the current page/class
#  n - The navigation panel (inter-objects navigation)
#  b - The range of buttons (intra-object navigation, save, edit, delete...)

# Layout elements for a field --------------------------------------------------
#  l -  "label"        The field label
#  d -  "description"  The field description (a description is always visible)
#  h -  "help"         Help for the field (typically rendered as an icon,
#                       clicking on it shows a popup with online help
#  v -  "validation"   The icon that is shown when a validation error occurs
#                       (typically only used on "edit" layouts)
#  r -  "required"     The icon that specified that the field is required (if
#                       relevant; typically only used on "edit" layouts)
#  f -  "field"        The field value, or input for entering a value.
#  c -  "changes"      The button for displaying changes to a field

# For every field of a Appy class, you can define, for every layout context,
# what field-related information will appear, and how it will be rendered.
# class "Layouts" below defines the default layouts for pages and fields and
# alternative layouts.
# 
# How to express a layout? You simply define a string that is made of the
# letters corresponding to the field elements you want to render. The order of
# elements correspond to the order into which they will be rendered.

# ------------------------------------------------------------------------------
from appy.px import Px

# ------------------------------------------------------------------------------
rowDelimiters =  {'-':'middle', '=':'top', '_':'bottom'}
rowDelms = ''.join(rowDelimiters.keys())
cellDelimiters = {'|': 'center', ';': 'left', '!': 'right'}
cellDelms = ''.join(cellDelimiters.keys())

pxDict = {
  # Page-related elements
  's': 'pxHeader', 'w': 'pxFields', 'n': 'pxNavigationStrip', 'b': 'pxButtons',
  # Field-related elements
  'l': 'pxLabel', 'd': 'pxDescription', 'h': 'pxHelp', 'v': 'pxValidation',
  'r': 'pxRequired', 'c': 'pxChanges'}

# ------------------------------------------------------------------------------
class Cell:
    '''Represents a cell in a row in a table'''
    def __init__(self, content, align, isHeader=False):
        self.align = align
        self.width = None
        self.content = None
        self.colspan = 1
        if isHeader:
            self.width = content
        else:
            self.content = [] # The list of widgets to render in the cell
            self.decodeContent(content)

    def __repr__(self):
        return '<Cell %s>' % self.content

    def decodeContent(self, content):
        digits = '' # We collect the digits that will give the colspan
        for char in content:
            if char.isdigit():
                digits += char
            else: # It is a letter corresponding to a macro
                self.content.append(pxDict.get(char, char))
        # Manage the colspan
        if digits:
            self.colspan = int(digits)

    def renderContent(self, value, layoutType, layoutTarget):
        '''Renders p_value (one element among self.content) for a given
           p_layoutTarget (a field or object) on some p_layoutType.'''
        if value == 'f':
            # The name of the PX depends on p_layoutType
            return getattr(layoutTarget, 'px%s' % layoutType.capitalize())
        else: # p_value is the name of a PX
            return getattr(layoutTarget, value)

# ------------------------------------------------------------------------------
class Row:
    '''Represents a row in a table'''
    def __init__(self, content, valign, isHeader=False):
        self.valign = valign
        self.cells = []
        self.decodeCells(content, isHeader)
        # Compute the row length
        length = 0
        for cell in self.cells:
            length += cell.colspan
        self.length = length

    def __repr__(self):
        return '<Row %s (%d)>' % (str(self.cells), self.length)

    def decodeCells(self, content, isHeader):
        '''Decodes the given chunk of layout string p_content containing
           column-related information (if p_isHeader is True) or cell content
           (if p_isHeader is False) and produces a list of Cell instances.'''
        cellContent = ''
        for char in content:
            if char in cellDelimiters:
                align = cellDelimiters[char]
                self.cells.append(Cell(cellContent, align, isHeader))
                cellContent = ''
            else:
                cellContent += char
        # Manage the last cell if any
        if cellContent:
            self.cells.append(Cell(cellContent, 'left', isHeader))

# ------------------------------------------------------------------------------
class Table:
    '''Represents a table where to dispose graphical elements'''
    simpleParams = ('style', 'css_class', 'cellpadding', 'cellspacing', 'width',
                    'align')
    derivedRepls = {'view': 'hrvd', 'search': 'hrvd'}

    # Render this Table instance, known in the context as "layout". If the
    # layouted object is a page, the "layout target" (where to look for sub-PXs)
    # will be the object whose page is shown; if the layouted object is a field,
    # the layout target will be this field.

    # Warning: when the layout type is "cell", the cell width and alignment must
    # not be defined by the cell layout, but by the outer column layout.
    pxRender = Px('''
     <table var="layoutCss=layout.css_class;
                 inTd=(layoutType == 'cell') and bool(column)|False"
       cellpadding=":layout.cellpadding"
       cellspacing=":layout.cellspacing"
       width=":not inTd and layout.width or ''"
       align=":not inTd and ztool.flipLanguageDirection(layout.align,dir) or ''"
       class=":tagCss and ('%s %s' % (tagCss, layoutCss)).strip() or layoutCss"
       style=":layout.style" id=":tagId" name=":tagName">
      <!-- The table header row -->
      <tr if="layout.headerRow" valign=":layout.headerRow.valign">
       <th for="cell in layout.headerRow.cells" width=":cell.width"
           align=":ztool.flipLanguageDirection(cell.align, dir)">
       </th>
      </tr>
      <!-- The table content -->
      <tr for="row in layout.rows" valign=":row.valign">
       <td for="cell in row.cells" colspan=":cell.colspan"
           align=":ztool.flipLanguageDirection(cell.align, dir)"
           class=":not loop.cell.last and 'cellGap' or ''">
        <x for="c in cell.content">
         <x>::cell.renderContent(c, layoutType, layoutTarget)</x>
         <img if="not loop.c.last" src=":url('space.gif')"/>
        </x>
       </td>
      </tr>
     </table>''')

    def __init__(self, layoutString=None, style=None, css_class='',
                 cellpadding=0, cellspacing=0, width='100%', align='left',
                 other=None, derivedType=None):
        if other:
            # We need to create a Table instance from another Table instance,
            # given in p_other. In this case, we ignore previous params.
            if derivedType != None:
                # We will not simply mimic p_other. If p_derivedType is:
                # - "view", p_other is an "edit" layout, and we must create the
                #           corresponding "view" layout;
                # - "search", p_derivedFrom is a "view" layout.
                self.layoutString = Table.deriveLayout(other.layoutString,
                                                       derivedType)
            else:
                self.layoutString = other.layoutString
            source = 'other.'
        else:
            source = ''
            self.layoutString = layoutString
        # Initialise simple params, either from the true params, either from
        # the p_other Table instance.
        for param in Table.simpleParams:
            exec 'self.%s = %s%s' % (param, source, param)
        # The following attribute will store a special Row instance used for
        # defining column properties.
        self.headerRow = None
        # The content rows will be stored hereafter.
        self.rows = []
        self.decodeRows(self.layoutString)

    @staticmethod
    def deriveLayout(layout, derivedType):
        '''Returns a layout derived from p_layout'''
        res = layout
        for letter in Table.derivedRepls[derivedType]:
            res = res.replace(letter, '')
        # Strip the derived layout
        res = res.lstrip(rowDelms); res = res.lstrip(cellDelms)
        return res

    def addCssClasses(self, css_class):
        '''Adds a single or a group of p_css_class.'''
        if not self.css_class: self.css_class = css_class
        else:
            self.css_class += ' ' + css_class
            # Ensures that every class appears once
            self.css_class = ' '.join(set(self.css_class.split()))

    def isHeaderRow(self, rowContent):
        '''Determines if p_rowContent specified the table header row or a
           content row.'''
        # Find the first char that is a number or a letter
        for char in rowContent:
            if char not in cellDelimiters:
                if char.isdigit(): return True
                else:              return False
        return True

    def decodeRows(self, layoutString):
        '''Decodes the given p_layoutString and produces a list of Row
           instances.'''
        # Split the p_layoutString with the row delimiters
        rowContent = ''
        for char in layoutString:
            if char in rowDelimiters:
                valign = rowDelimiters[char]
                if self.isHeaderRow(rowContent):
                    if not self.headerRow:
                        self.headerRow = Row(rowContent, valign, isHeader=True)
                else:
                    self.rows.append(Row(rowContent, valign))
                rowContent = ''
            else:
                rowContent += char
        # Manage the last row if any
        if rowContent:
            self.rows.append(Row(rowContent, 'middle'))

    def removeElement(self, elem):
        '''Removes given p_elem from myself'''
        macroToRemove = pxDict[elem]
        for row in self.rows:
            for cell in row.cells:
                if macroToRemove in cell.content:
                    cell.content.remove(macroToRemove)
        if elem in self.layoutString:
            self.layoutString = self.layoutString.replace(elem, '')

    def __repr__(self): return '<Table %s>' % self.layoutString

# ------------------------------------------------------------------------------
class ColumnLayout:
    '''A "column layout" dictates the way a table column must be rendered. Such
       a layout is of the form: <name>[*width][,|!|`|`][^].'''
    # --------------------------------------------------------------------------
    #   <name>  | is the name of the field whose content must be shown in
    #           | column's cells ;
    # --------------------------------------------------------------------------
    #   width   | is the width of the column. Any valid value for the "width"
    #           | attribute of the "td" HTML tag is accepted ;
    # --------------------------------------------------------------------------
    #   , | !   | column alignment: respectively, left, centered or right ;
    # --------------------------------------------------------------------------
    #     ^     | if present, indicates that the colmn header must be empty.
    # --------------------------------------------------------------------------

    def __init__(self, layoutString):
        self.layoutString = layoutString

    def get(self):
        '''Returns a list containing the separate elements that are within
           self.layoutString.'''
        consumed = self.layoutString
        lastChar = consumed[-1]
        # Must the column header be empty ?
        if lastChar == '^':
            header = False
            consumed = consumed[:-1]
        else:
            header = True
        # Determine column alignment
        lastChar = consumed[-1]
        if lastChar in cellDelimiters:
            align = cellDelimiters[lastChar]
            consumed = consumed[:-1]
        else:
            align = 'left'
        # Determine name and width
        if '*' in consumed:
            name, width = consumed.rsplit('*', 1)
        else:
            name = consumed
            width = ''
        return name, width, align, header

# ------------------------------------------------------------------------------
class Layouts:
    '''A series of predefined layouts you can use on your Appy fields or pages.
       * First-level static attributes are general layouts applicable to any
         field;
       * default field layouts are in the Field subclass;
       * field-specific layouts are defined on sub-classes whose names
         correspond to Field subclasses;
       * page layouts (the default and others) are defined on the Page
         subclass.'''
    # The following naming conventions apply.
    # "b"  base layout
    # "d"  description (for layouts displaying the field's description)
    # "h"  help (for layouts displaying the field's help icon)
    # "n"  narrow (for non-100%-wide layouts)
    # "w"  wide
    # "g"  group (for layouts applicable to fields in groups with style="grid")
    # "c"  centered
    b = 'lrv-f'
    c = b + '|'
    d = 'lrv-d-f'
    dc = d + '|'
    h = 'lhrv-f'
    n = Table(b, width=None)
    nd = Table(d, width=None)
    w = Table(b, width='100%')
    g = {'edit': 'frvl', 'search': 'l-f'}
    # The *d*escription is visible, even on the *v*iew layout
    dv = {'edit': d, 'view': 'l-d-f'}
    # "Grid" group-related layouts
    gn = {'edit': Table('f;rvl=', width=None), 'search': 'l-f'}
    gd = {'edit': Table('frvl-d', width='99%'), 'search': 'l-f'}
    gdn = Table('d2-f;rvl=', width=None) # "n" for "*n*ot wide"
    gh = 'fhrvl'
    gdh = 'fhrvl-d'

    # ~~~ Default cell layout ~~~
    # Layouts for a field do not contain any entry for layout type "cell".
    # Indeed, rendering a field on such layout is, implicitly, simply rendering
    # its value ("f"). Moreover, rendering a layout renders a complete XHTML
    # table, even if it contains a single cell, like for "f". So we avoid doing
    # this for performance and conciseness reasons. But we can't complelety
    # forget cell layouts, because they are needed for inline-editing (or maybe
    # other Ajax-like functionalities in the future). Indeed, the machinery for
    # ajax-editing the field is inlaid in the XHTML table corresponding to the
    # layout. In such case, we will use a standard cell layout defined here.
    cell = Table('f|', align='center', css_class='no')

    # ~~~ Default layouts for fields ~~~
    class Field:
        defaults = {'normal': {True: 'lrv-f', False: 'lv-f'},
                    'grid':   {True:  {'edit': 'frvl', 'search': 'l-f'},
                               False: {'edit': 'fvl', 'search': 'l-f'}}}

    @classmethod
    def defaults(klass, field):
        '''Returns the default layouts for fields. Depends on:
           - the fact that a field is required or not;
           - the type of group into which the field is.

           If Type-subclass-specific default layouts are defined in
           SubType.getDefaultLayouts, they will override default ones as
           computed here. For every field, the user can also use other
           frequently used layouts that are defined hereabove.'''
        key = field.inGrid() and 'grid' or 'normal'
        return klass.Field.defaults[key][field.required]

    # ~~~ Field-specific layouts ~~~
    class Action:
        b = {'view': 'lf', 'edit': 'lf'}
        c = {'view': 'f|'}

    class Boolean:
        d = {'view': 'lf', 'edit': Table('flrv;=d', width=None)}
        h = {'view': 'lf', 'edit': Table('flhv', width=None)}
        gd = {'view': 'fl', 'edit': Table('f;dv-', width=None)}
        # The "long" version of the previous layout (if the description is
        # long), with vertical alignment on top instead of middle.
        gdl = {'view': 'fl', 'edit': Table('f;dv=', width=None)}
        # Description, renderes as *r*adio buttons
        gdr = {'view': 'fl', 'edit': Table('d-fv=', width=None)}
        rld = {'view': 'lf', 'edit': 'l-d-f'}

    class Calendar:
        b = {'edit': 'f', 'view': 'l-d-f'}
        n = Table('l-f', width=None)

    class Custom:
        # A custom field is not showable by default, except on layout "xml"
        b = 'f'

    class Computed:
        # Wide layout, with content only (no label). Useful for displaying
        # computed warning messages.
        wf = {'view': Table('f', width='100%')}

    class File:
        b = {'view': 'l-f','edit': 'lrv-f'}
        bg = {'view': 'fl','edit': 'frvl'}

    class Info:
        # We specify "edit": that way, "view" inherits from it, and all these
        # layouts are ready in case an info must be shown on an "edit" layout.
        b = {'edit': 'l'}
        d = {'edit': Table('l-d', width=None),
             'view': Table('l-d', width=None)}
        do = {'edit': 'f', 'view': 'd'} # Description only
        c = {'edit': 'l|'} # Centered
        dc = {'edit': 'l|-d|'}
        vdc = {'view': 'l|-d|'}

    class Pod:
        # Right-aligned layouts, convenient for pod fields exporting search
        # results or multi-template pod fields.
        r = {'view': Table('fl!', css_class='podTable')} # "r"ight
        rf = {'view': Table('f!', css_class='podTable')} # "r"ight, no label
        l = {'view': Table('fl;', css_class='podTable')} # "l"eft
        # "r"ight "m"ulti-template (where the global field label is not used
        rm = {'view': Table('f!', css_class='podTable')}

    class Ref:
        # Wide layout for a Ref is a bit different than Layout.d: it must be
        # 100% wide on result, too.
        w = {'view': Table('lrv-f', width='100%')}
        # "d" stands for "description": a description label is added, on view
        wd = {'view': Table('l-d-f', width='100%')}
        # Wide, but not on edit
        w_e = {'edit': Table('lrv-f', width=None),
               'view': Table('lrv-f', width='100%')}
        # "cell" layout varies from the default
        cell = Table('f|', width='100%', css_class='no')

    class String:
        g = {'edit': Table('f;rv=', width=None), 'search': 'l-f'}
        gd = {'edit': Table('f;rv=d', width=None), 'search': 'l-f'}

    class Text:
        b = {'view': 'l-f', 'edit': 'lrv-d-f'}
        g = {'view': Table('fl', width='99%'),
             'edit': Table('d2-f;rv=', width='99%')}

    class Rich:
        b = {'view': 'l-f', 'edit': 'lrv-d-f'}
        c = {'view': 'lc-f', 'edit': 'lrv-d-f'} # Idem but with history
        g = {'view': Table('fl', width='99%'),
             'edit': Table('d2-f;rv=', width='99%')}
        gc = {'view': Table('cl-f', width='99%'),
              'edit': Table('drv-f', width='99%')} # Idem but with history

    class Select:
        d = Table('d2-l-f;rv=', width=None)
        g = {'view': Table('fl', width=None),
             'edit': Table('f;rv=', width=None)}
        gd = {'view': Table('fl', width=None),
              'edit': Table('d2-f;rv=', width=None)}

    class List:
        g = {'view': 'fl', 'edit': Table('f;rv=', width=None), }
        gd = {'view': 'fl', 'edit': Table('d;v=f;', width=None)}

    # ~~~ Layouts for pages ~~~
    class Page:
        # The default layouts
        defaults = {'view': Table('w-b'), 'edit': Table('w-b', width=None)}
        # With the page summary
        summary = {'view': Table('s-w-b'), 'edit': Table('w-b', width=None)}
        # Wide
        wide = {'view': Table('w-b'), 'edit': Table('w-b')}
        # Wide + summary
        wideSummary = {'view': Table('s-w-b'), 'edit': Table('w-b')}
        # Centered
        centered = {'view': Table('w|-b|', align='center'),
                    'edit': Table('w|-b|', width=None, align='center')}
# ------------------------------------------------------------------------------
