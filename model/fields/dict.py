#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import copy
from persistent.mapping import PersistentMapping

from appy.px import Px
from appy.ui.layout import Layout
from appy.model.utils import Object
from appy.utils.diff import HtmlDiff
from appy.model.fields.list import List

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class SepRow:
    '''Represents a custom row that is a separator but does not represent
       data.'''

    def __init__(self, text, cellCss=None, rowCss=None):
        self.text = text
        # An optional CSS class to apply to the cell containing p_text
        self.cellCss = cellCss
        # An optional CSS class to apply to the row contaning this cell
        self.rowCss = rowCss

    def get(self, field):
        '''Produces the chunk of XHTML code representing this row'''
        rowCss = ' class="%s"' % self.rowCss if self.rowCss else ''
        cellCss = ' class="%s"' % self.cellCss if self.cellCss else ''
        return '<tr valign="top"%s><td colspan="%s"%s>%s</td></tr>' % \
               (rowCss, len(field.fields) + 1, cellCss, self.text)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Dict(List):
    '''A Dict value has the form ~{s_key: Object}~. Keys are fixed and given by
       a method specified in parameter "keys". Values are Object instances,
       whose attributes are determined by parameter "fields" that, similarly to
       the List field, determines sub-data for every entry in the dict. This
       field is build on top of the List field.'''
    SepRow = SepRow

    # As an outer type, a Dict stores persistent mappings
    outerType = PersistentMapping

    # PX for rendering a single row
    pxRow = Px('''
     <!-- Render a separation row -->
     <x if="not rId">::text.get(field)</x>
     <tr if="rId" valign="top" class=":'even' if loop.rId.odd else 'odd'">
      <x>:field.pxFirstCell</x>
      <td class="discreet">::text</td>
      <td for="subName, field in subFields" if="field" align="center"
          var2="fieldName='%s*%s' % (field.name, rowId)">:field.pxRender</td>
     </tr>''')

    # PX for rendering the dict (shared between pxView and pxEdit)
    pxTable = Px('''
     <table var="isEdit=layout == 'edit'" if="isEdit or value"
            id=":'list_%s' % name" class=":field.getTableCss(_ctx_)"
            width=":field.width"
            var2="keys=field.keys(o);
                  subFields=field.getSubFields(o, layout);
                  swidths=field.getWidths(subFields);
                  o=alto|o">
      <!-- Header -->
      <tr valign="bottom">
       <th width=":swidths[0]"></th>
       <th for="subName, sub in subFields" if="sub"
           width=":swidths[loop.subName.nb + 1]">::sub.getListHeader(_ctx_)</th>
      </tr>
      <!-- Rows of data -->
      <x for="rId, text in keys" var2="rowId='-d-%s' % rId">:field.pxRow</x>
     </table>''')

    def __init__(self, keys, fields, validator=None, multiplicity=(0,1),
      default=None, defaultOnEdit=None, show=True, renderable=None, page='main',
      group=None, layouts=None, move=0, readPermission='read',
      writePermission='write', width='', height=None, maxChars=None, colspan=1,
      master=None, masterValue=None, focus=False, historized=False,
      mapping=None, generateLabel=None, label=None, subLayouts=List.Layouts.sub,
      widths=None, view=None, cell=None, buttons=None, edit=None, xml=None,
      translations=None, headerAlign='middle', listCss=None):
        # Call the base constructor
        List.__init__(self, fields, validator, multiplicity, default,
          defaultOnEdit, show, renderable, page, group, layouts, move,
          readPermission, writePermission, width, height, maxChars, colspan,
          master, masterValue, focus, historized, mapping, generateLabel, label,
          subLayouts, widths, view, cell, buttons, edit, xml, translations,
          headerAlign=headerAlign, listCss=listCss)
        # Method in "keys" must return a list of tuples (key, title): "key"
        # determines the key that will be used to store the entry in the
        # database, while "title" will get the text that will be shown in the ui
        # while encoding/viewing this entry.

        # WARNING: a key must be a string and cannot contain char "*". A key is
        # typically an object ID, CONVERTED to a string.

        # For a nice rendering of your dict, some of the tuples returned by
        # method "keys" can be "separator rows". The tuple representing such a
        # row must have the form (None, sepRow). "None" indicates that this is
        # not a row of data; "sepRow" must be a SepRow instance (see hereabove)
        # that will determine content and style for the separator row.
        self.keys = keys

    def getWidths(self, subFields):
        '''Get the widths to appply to these p_subFields'''
        return self.widths or [''] * (len(subFields) + 1)

    def getStorableValue(self, o, value, single=False):
        '''Gets p_value in a form that can be stored in the database'''
        r = PersistentMapping()
        for k, v in value.items():
            r[k] = self.getStorableRowValue(o, v)
        return r

    def getComparableValue(self, o):
        '''Return a (deep) copy of field value on p_o'''
        # Indeed, because a new value does not overwrite but updates the stored
        # value, the comparable value must be a deep copy of the stored value.
        r = getattr(o, self.name, None)
        if r: return copy.deepcopy(r)

    def remove(self, o, key):
        '''Remove entry corresponding to p_key on the value stored on p_o'''
        if self.name not in o.values: return
        val = o.values[self.name]
        if key not in val: return
        del(val[key])
        o.values[self.name] = val

    def store(self, o, value, overwrite=False):
        '''Stores the p_value (produced by m_getStorableValue) on p_o. If some
           entry from p_value already exists in the DB value, it is updated,
           not overwritten.'''
        if not self.persist: return
        dbValue = o.values.get(self.name)
        if dbValue is None or overwrite:
            o.values[self.name] = value
        else:
            # Update the DB value with p_value
            if not value: return
            for key, data in value.items():
                if key not in dbValue:
                    dbValue[key] = data
                else:
                    dbValue[key].update(data)
                    # Force the mapping to take the change into account
                    dbValue[key] = dbValue[key]

    def subValidate(self, o, value, errors):
        '''Validates inner fields'''
        for key, row in value.items():
            for name, subField in self.getSubFields(o):
                message = subField.validate(o, getattr(row, name, None))
                if message:
                    setattr(errors, '%s*%s' % (subField.name, key), message)

    def getDiffSubValue(self, old, new, texts):
        '''Produce a diff between this p_old sub-value and its p_new version.
           p_texts contain precomputed translated texts about the user that
           performed the change.'''
        if old:
            r = HtmlDiff.templateDiv % (HtmlDiff.deleteStyle, texts[1], old)
        else:
            r = ''
        if new:
            r = '%s%s' % (r, HtmlDiff.templateDiv % (HtmlDiff.insertStyle,
                                                     texts[0], new))
        return r

    def getDiffValue(self, o, old, new, texts):
        '''Return a XHTML representation of dict value p_new incorporating the
           differences with this p_old version.'''
        # Return the p_old value as-is, if the p_new version is None
        if not new:
            fake = self.getFakeObject(old, o.req)
            return self.doRender('view', fake)
        # Update the old value by replacing every modified sub-value (w.r.t
        # p_new) with a diff between the old and the new sub-value.
        diff = copy.deepcopy(old)
        for key, sub in old.items():
            # Get the corresponding entry in p_new
            newSub = new.get(key)
            diffSub = diff[key]
            if newSub:
                # Browse sub-values on this row of data
                for name, val in sub.items():
                    # Get the new version of sub-value
                    newVal = getattr(newSub, name, None)
                    if newVal == val: continue
                    # Values are different, produce a diff
                    diffVal = self.getDiffSubValue(val, newVal, texts)
                    setattr(diffSub, name, diffVal)
            else:
                # This complete row has been removed from p_new
                for name, val in sub.items():
                    diffVal = self.getDiffSubValue(val, None, texts)
                    setattr(diffSub, name, diffVal)
        # Produce a fake object containing the diff
        fake = self.getFakeObject(diff, o.req)
        # Render the diff
        return self.doRender('view', o, minimal=True, specific={'alto': fake})

    def getHistoryValue(self, o, value, i, language=None, empty='-'):
        '''For a Dict field, instead of showing the previous p_value in p_o's
           history, show a XHTML diff between p_value, as found at index p_i,
           and a newer version of it in p_o's history before p_i, or, if not
           found, the value as currently stored on p_o.'''
        # Return an empty value if the p_value is inexistent
        if not value: return empty
        # Find the newer version of p_value
        history = o.history
        newer = history.getNewer(self, value, i-1)
        diffTexts = history[i].getDiffTexts(o)
        return self.getDiffValue(o, value, newer, diffTexts)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
