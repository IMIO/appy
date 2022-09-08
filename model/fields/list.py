#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import copy
from persistent.list import PersistentList

from appy.px import Px
from appy.model.fields import Field
from appy.model.totals import Totals
from appy.model.utils import Object as O
from appy.ui.layout import Layout, Layouts

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
RC_NO_OS  = 'Class "%s", mentioned in attribute "rowClass", must be a sub-' \
            'class of class appy.model.utils.Object.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class List(Field):
    '''A list, stored as a list of Object instances ~[Object]~. Every object in
       the list has attributes named according to the sub-fields defined in this
       List.'''
    Totals = Totals

    # List is an "outer" field, made of inner fields
    outer = True

    class Layouts(Layouts):
        '''List-specific layouts'''
        # No label on "edit" (*e*dit *m*inimalist)
        em = Layouts(edit=Layout('f;rv=', width=None))
        g = Layouts(edit=em['edit'], view='fl')
        gd = Layouts(edit=Layout('d;v=f;', width=None), view='fl')
        # Default layouts for sub-fields
        sub = Layouts(Layout('frv', width=None))

        @classmethod
        def getDefault(class_, field):
            '''Default layouts for this List p_field'''
            return class_.g if field.inGrid() else super().getDefault(field)

    # A 1st invisible cell containing a virtual field allowing to detect this
    # row at server level.
    pxFirstCell = Px('''<td style="display: none">
     <table var="rid='%s*-row-*%s' % (field.name, rowId)"
            id=":'%d_%s' % (o.iid, rid)">
      <tr><td><input type="hidden" id=":rid" name=":rid"/></td></tr>
     </table></td>''')

    # PX for rendering a single row
    pxRow = Px('''
     <tr valign="top" style=":'display:none' if rowId == -1 else ''"
         class=":'odd' if loop.row.odd else 'even'">
      <x if="not isCell">:field.pxFirstCell</x>
      <td for="name, field in subFields" if="field"
          var2="minimal=isCell;
                fieldName='%s*%d' % (field.name, rowId)">:field.pxRender</td>
      <!-- Icons -->
      <td if="isEdit" align=":dright">
       <img class="clickable iconS" src=":svg('deleteL')"
            title=":_('object_delete')"
            onclick=":field.jsDeleteConfirm(_ctx_)"/>
       <img class="clickable iconS" src=":svg('arrow')"
            style="transform: rotate(180deg)" title=":_('move_up')"
            onclick=":'moveRow(%s,%s,%s,this)' %
                       (q('up'), q(tableId), q(tagId))"/>
       <img class="clickable iconS" src=":svg('arrow')"
            title=":_('move_down')"
            onclick=":'moveRow(%s,%s,%s,this)' %
                       (q('down'), q(tableId), q(tagId))"/>
       <input class="clickable" type="image" tabindex="0"
              src=":url('addBelow')" title=":_('object_add_below')"
              onclick=":'insertRow(%s,%s,this);
                         return false' % (q(tableId), q(tagId))"/>
      </td></tr>''')

    # PX for rendering the list (shared between pxView, pxEdit and pxCell)
    pxTable = Px('''
     <table var="isEdit=layout == 'edit';
                 isCell=layout == 'cell';
                 tableId='list_%s' % name" if="isEdit or value"
            id=":tableId" width=":field.width"
            class=":'grid' if isEdit else 'small'"
            var2="Totals=field.Totals;
                  subFields=field.getSubFields(o, layout);
                  swidths=field.getWidths(subFields);
                  totals=Totals.initialise(field, 'row', subFields, isEdit)">
      <!-- Header -->
      <thead>
       <tr valign="middle">
        <th for="name, sub in subFields" if="sub"
            width=":swidths[loop.name.nb]">
         <x var="field=sub">::field.getListHeader(_ctx_)</x></th>
        <!-- Icon for adding a new row -->
        <th if="isEdit">
         <img class="clickable" src=":url('plus')" title=":_('object_add')"
              onclick=":'insertRow(%s,%s)' % (q(tableId), q(tagId))"/>
        </th>
       </tr>
      </thead>

      <!-- Template row (edit only) -->
      <x var="rowId=-1" if="isEdit">:field.pxRow</x>

      <!-- Rows of data -->
      <x var="rows=field.getInputValue(inRequest, requestValue, value)"
         for="row in rows" var2="rowId=loop.row.nb">:field.pxRow</x>

      <!-- Totals -->
      <x if="totals">:totals.px</x>
     </table>''')

    view = cell = buttons = Px('''<x>:field.pxTable</x>''')
    edit = Px('''<x>
     <!-- This input makes Appy aware that this field is in the request -->
     <input type="hidden" name=":name" value=""/><x>:field.pxTable</x>
    </x>''',

     js='''
       updateRowNumber = function(tagId, row, rowIndex, action) {
         /* Within p_row, we must find tables representing fields. Every such
            table has an id of the form [objectId]_[field]*[subField]*[i].
            Within this table, for every occurrence of this string, the "[i]"
            must be replaced with an updated index. If p_action is 'set',
            p_rowIndex is this index. If p_action is 'add', the index must
            become [i] + p_rowIndex. */

         // Browse elements representing fields
         let fields = row.querySelectorAll('[id^="'+tagId+'"]'),
             newIndex = -1, id, old, elems, new_, val, w, oldIndex,
             tagTypes = ['a', 'script'], widgets=null;

         // Patch fields
         for (let i=0; i<fields.length; i++) {
           // Extract, from the table ID, the field identifier
           id = fields[i].id;
           if ((!id) || (id.indexOf('_') == -1)) continue;
           // Extract info from the field identifier
           old = id.split('_')[1];
           elems = old.split('*');
           /* Get "old" as a regular expression: we may need multiple
              replacements. */
           old = new RegExp(old.replace(/\\*/g, '\\\\*'), 'g');
           // Compute the new index (if not already done) and new field ID
           if (newIndex == -1) {
             oldIndex = parseInt(elems[2]);
             newIndex = (action == 'set')? rowIndex: oldIndex + rowIndex;
           }
           new_ = elems[0] + '*' + elems[1] + '*' + newIndex;
           // Replace the table ID with its new ID
           fields[i].id = fields[i].id.replace(old, new_);
           // Find widgets mentioning v_old and replace it with v_new_
           val = w = null;
           widgets = fields[i].querySelectorAll('[id^="'+elems[0]+'\*"]');
           for (let j=0; j<widgets.length; j++) {
             w = widgets[j];
             // Patch id
             val = w.id;
             if (val) w.id = val.replace(old, new_);
             // Patch name
             val = w.name;
             if (val) w.name = val.replace(old, new_);
           }
           // Find other sub-tags and perform a similar replacement
           for (let k=0; k<tagTypes.length; k++){
             widgets = fields[i].getElementsByTagName(tagTypes[k]);
             for (var l=0; l<widgets.length; l++) {
               w = widgets[l];
               // Patch href
               if ((w.nodeName == 'A') && w.href)
                 { w.href = w.href.replace(old, new_); }
               // Patch (and reeval) script
               if (w.nodeName == 'SCRIPT') {
                 w.text = w.text.replace(old, new_);
                 eval(w.text);
               }
             }
           }
         }
       }

       insertRow = function(tableId, tagId, previous) {
         /* Add a new row in table with ID p_tableId, after p_previous row or at
            the end if p_previous is null. */
         var table = document.getElementById(tableId),
             body = table.tBodies[0],
             rows = table.rows,
             newRow = rows[1].cloneNode(true),
             next = (previous)? \
                    previous.parentNode.parentNode.nextElementSibling : null;
         newRow.style.display = 'table-row';
         if (next) {
           var newIndex = next.rowIndex;
           // We must insert the new row before it
           body.insertBefore(newRow, next);
           // The new row takes the index of "next" (- the 2 unsignificant rows)
           updateRowNumber(tagId, newRow, newIndex-2, 'set');
           // Row numbers for "next" and the following rows must be incremented
           for (var i=newIndex+1; i < rows.length; i++) {
             updateRowNumber(tagId, rows[i], 1, 'add');
           }
         }
         else {
           // We must insert the new row at the end
           body.appendChild(newRow);
           // Within newRow, incorporate the row nb within field names and ids
           updateRowNumber(tagId, newRow, rows.length-3, 'set');
         }
       }

       deleteRow = function(tableId, tagId, deleteImg, ask, rowIndex) {
         var table = document.getElementById(tableId),
             rows = table.rows,
             row = (deleteImg)? deleteImg.parentNode.parentNode: rows[rowIndex];
             rowIndex = row.rowIndex;
         // Must we ask the user to confirm this action ?
         if (ask) {
             askConfirm('script',
                'deleteRow("'+tableId+'","'+tagId+'",null,false,'+rowIndex+')');
             return;
         }
         // Decrement higher row numbers by 1 because of the deletion
         for (var i=rowIndex+1; i < rows.length; i++) {
           updateRowNumber(tagId, rows[i], -1, 'add');
         }
         table.deleteRow(rowIndex);
       }

       moveRow = function(direction, tableId, tagId, moveImg) {
         var row = moveImg.parentNode.parentNode,
             body = document.getElementById(tableId).tBodies[0], sibling;
         // Move up or down
         if (direction == 'up') {
           sibling = row.previousElementSibling;
           if (sibling && sibling.style.display != 'none') {
             updateRowNumber(tagId, row, -1, 'add');
             updateRowNumber(tagId, sibling, 1, 'add');
             body.insertBefore(row, sibling);
           }
         }
         else if (direction == 'down') {
           sibling = row.nextElementSibling;
           if (sibling) {
             updateRowNumber(tagId, row, 1, 'add');
             updateRowNumber(tagId, sibling, -1, 'add');
             // If sibling is null, row will be added to the end
             sibling = sibling.nextElementSibling;
             body.insertBefore(row, sibling);
           }
         }
       }''')

    search = ''

    def __init__(self, fields, validator=None, multiplicity=(0,1), default=None,
      defaultOnEdit=None, show=True, renderable=None, page='main', group=None,
      layouts=None, move=0, readPermission='read', writePermission='write',
      width='', height=None, maxChars=None, colspan=1, master=None,
      masterValue=None, focus=False, historized=False, mapping=None,
      generateLabel=None, label=None, subLayouts=Layouts.sub, widths=None,
      view=None, cell=None, buttons=None, edit=None, xml=None,
      translations=None, deleteConfirm=False, totalRows=None, rowClass=O):
        # Call the base constructor
        Field.__init__(self, validator, multiplicity, default, defaultOnEdit,
         show, renderable, page, group, layouts, move, False, True, None, None,
         False, None, readPermission, writePermission, width, height, None,
         colspan, master, masterValue, focus, historized, mapping,
         generateLabel, label, None, None, None, None, True, False, view, cell,
         buttons, edit, xml, translations)
        self.validable = True
        # Tuple of elements of the form (name, Field instance) determining the
        # format of every element in the list. It can also be a method returning
        # this tuple. In that case, however, no i18n label will be generated for
        # the sub-fields: these latters must be created with a value for
        # attribute "translations".
        self.fields = fields
        # Force some layouting for sub-fields, if p_subLayouts are passed. If
        # you want freedom to tune layouts at the field level, you must specify
        # p_subLayouts=None.
        self.subLayouts = subLayouts
        # One may specify the width of every column in the list. Indeed, using
        # widths and layouts at the sub-field level may not be sufficient.
        self.widths = widths
        # Initialize sub-fields, if statically known
        if not callable(fields):
            self.initSubFields(fields)
        # When deleting a row, must we display a popup for confirming it ?
        self.deleteConfirm = deleteConfirm
        # If you want to specify additional rows representing totals, set, in
        # "totalRows", a list of appy.model.totals::Totals instances.
        self.totalRows = totalRows
        # By default, every row of data that is stored in a List value is an
        # instance of class Object, from package appy.model.utils. You can
        # choose an alternate class, by defining it in attribute p_rowClass
        # hereafter. The class you specify in p_rowClass must be a sub-class of
        # class appy.model.utils.Object. Use this at your own risk. Take a close
        # look at class appy.model.utils.Object, because the way you define your
        # class could lead to Appy malfunctions.
        self.rowClass = rowClass
        self.checkParameters()

    def initSubFields(self, subFields):
        '''Initialises sub-fields' attributes'''
        # Initialise sub-layouts
        subLayouts = self.subLayouts
        if subLayouts:
            for name, field in subFields:
                field.layouts = Layouts.getFor(self, subLayouts)

    def lazyInitSubFields(self, subFields, class_):
        '''Lazy-initialise sub-fields, when known'''
        # It can be at server startup, if sub-fields are statically defined, or
        # everytime a List field is solicited, if sub-fields are dynamically
        # computed.
        for sub, field in subFields:
            fullName = '%s_%s' % (self.name, sub)
            field.init(class_, fullName)
            field.name = '%s*%s' % (self.name, sub)

    def init(self, class_, name):
        '''List-specific lazy initialisation'''
        Field.init(self, class_, name)
        subs = self.fields
        if not callable(subs):
            self.lazyInitSubFields(subs, class_)

    def checkParameters(self):
        '''Ensures this List is correctly defined'''
        if not issubclass(self.rowClass, O):
            raise Exception(RC_NO_OS % self.rowClass)

    def getWidths(self, subFields):
        '''Get the widths to appply to these p_subFields'''
        return self.widths or [''] * len(subFields)

    def getField(self, name):
        '''Gets the field definition whose name is p_name'''
        for n, field in self.fields:
            if n == name: return field

    def getSubFields(self, o, layout=None):
        '''Returns the sub-fields, as a list of tuples ~[(s_name, Field)]~,
           being showable, among p_self.fields on this p_layout. Fields that
           cannot appear in the result are nevertheless present as a tuple
           (s_name, None). This way, it keeps a nice layouting of the table.'''
        fields = self.fields
        if callable(fields):
            # Dynamically computed fields: get and completely initialise them
            fields = self.getAttribute(o, 'fields') # Involves caching
            self.initSubFields(fields)
            self.lazyInitSubFields(fields, o.class_)
        # Stop here if no p_layout is passed
        if layout is None: return fields
        # Retain only sub-fields being showable on this p_layout
        r = []
        for n, field in fields:
            f = field if field.isShowable(o, layout) else None
            r.append((n, f))
        return r

    def getRequestValue(self, o, requestName=None):
        '''Concatenates the list from distinct form elements in the request'''
        req = o.req
        name = requestName or self.name # A List may be into another List (?)
        prefix = name + '*-row-*' # Allows to detect a row of data for this List
        r = {}
        isDict = True # We manage both List and Dict
        for key in req.keys():
            if not key.startswith(prefix): continue
            # I have found a row: get its index
            row = self.rowClass()
            rowId = key.split('*')[-1]
            if rowId == '-1': continue # Ignore the template row
            for subName, subField in self.getSubFields(o):
                keyName = '%s*%s*%s' % (name, subName, rowId)
                if keyName + subField.getRequestSuffix() in req:
                    v = subField.getRequestValue(o, requestName=keyName)
                    setattr(row, subName, v)
            if rowId.isdigit():
                rowId = int(rowId)
                isDict = False
            else:
                # Remove the -d- prefix
                rowId = rowId[3:]
            r[rowId] = row
        # Produce a sorted list (List only)
        if not isDict:
            keys = list(r.keys())
            keys.sort()
            r = [r[key] for key in keys]
        # I store in the request this computed value. This way, when individual
        # subFields will need to get their value, they will take it from here,
        # instead of taking it from the specific request key. Indeed, specific
        # request keys contain row indexes that may be wrong after row deletions
        # by the user.
        if r: req[name] = r
        return r

    def setRequestValue(self, o):
        '''Sets in the request, the field value on p_o in its "request-
           carriable" form.'''
        value = self.getValue(o)
        if value is not None:
            req = o.req
            name = self.name
            i = 0
            for row in value:
                req['%s*-row-*%d' % (name, i)] = ''
                for n, v in row.d().items():
                    key = '%s*%s*%d' % (name, n, i)
                    req[key] = v
                i += 1

    def getStorableRowValue(self, o, requestValue):
        '''Gets a ready-to-store Object instance representing a single row,
           from p_requestValue.'''
        r = self.rowClass()
        for name, field in self.getSubFields(o):
            if not hasattr(requestValue, name) and \
               not field.isShowable(o, 'edit'):
                # Some fields, although present on "edit", may not be part of
                # the p_requestValue (ie, a "select multiple" with no value at
                # all will not be part of the POST HTTP request). If we want to
                # know if the field was in the request or not, we must then
                # check if it is showable on layout "edit".
                continue
            subValue = getattr(requestValue, name, None)
            try:
                setattr(r, name, field.getStorableValue(o, subValue))
            except ValueError:
                # The value for this field for this specific row is incorrect.
                # It can happen in the process of validating the whole List
                # field (a call to m_getStorableValue occurs at this time). We
                # don't care about it, because later on we will have sub-field
                # specific validation that will also detect the error and will
                # prevent storing the wrong value in the database.
                setattr(r, name, subValue)
        return r

    def getStorableValue(self, o, value, single=False):
        '''Gets p_value in a form that can be stored in the database'''
        r = PersistentList()
        for v in value:
            r.append(self.getStorableRowValue(o, v))
        return r

    def getCopyValue(self, o):
        '''Return a (deep) copy of field value on p_o''' 
        r = getattr(o, self.name, None)
        if r: return copy.deepcopy(r)

    def getCss(self, o, layout, r):
        '''Gets the CSS required by sub-fields if any'''
        for name, field in self.getSubFields(o, layout):
            if field:
                field.getCss(o, layout, r)

    def getJs(self, o, layout, r, config):
        '''Gets the JS required by sub-fields if any'''
        for name, field in self.getSubFields(o, layout):
            if field:
                field.getJs(o, layout, r, config)

    def jsDeleteConfirm(self, c):
        '''Gets the JS code to call when the user wants to delete a row'''
        confirm = 'true' if self.deleteConfirm else 'false'
        q = c.q
        return "deleteRow(%s,%s,this,%s)" % (q(c.tableId), q(c.tagId), confirm)

    def subValidate(self, o, value, errors):
        '''Validates inner fields'''
        i = -1
        for row in value:
            i += 1
            for name, subField in self.getSubFields(o):
                message = subField.validate(o, getattr(row, name, None))
                if message:
                    setattr(errors, '%s*%d' % (subField.name, i), message)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
