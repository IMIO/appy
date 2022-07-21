#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy import utils
from appy.model.fields.integer import Integer

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
SEP_UNALLOWED = 'Char "%s" is not allowed as decimal separator.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Float(Integer):
    # Allowed chars for being used as decimal separators
    allowedDecimalSeps = (',', '.')

    # Precision of the indexed value, in number of decimals
    indexPrecision = 2

    # The name of the index class storing values of this field in the catalog
    indexType = 'FloatIndex'

    def __init__(self, validator=None, multiplicity=(0,1), default=None,
      defaultOnEdit=None, show=True, renderable=None, page='main', group=None,
      layouts=None, move=0, indexed=False, mustIndex=True, indexValue=None,
      emptyIndexValue=None, searchable=False, readPermission='read',
      writePermission='write', width=5, height=None, maxChars=13, colspan=1,
      master=None, masterValue=None, focus=False, historized=False,
      mapping=None, generateLabel=None, label=None, sdefault=('',''),
      scolspan=1, swidth=None, sheight=None, fwidth=3, persist=True,
      precision=None, sep=(',', '.'), tsep=' ', inlineEdit=False, view=None,
      cell=None, buttons=None, edit=None, xml=None, translations=None,
      readonly=False, alignOnEdit='left', autoComplete=True):
        # The precision is the number of decimal digits. This number is used
        # for rendering the float, but the internal float representation is not
        # rounded.
        self.precision = precision
        # The decimal separator can be a tuple if several are allowed, ie
        # ('.', ',')
        self.sep = sep if type(sep) in utils.sequenceTypes else (sep,)
        # Check that the separator(s) are among allowed decimal separators
        for sep in self.sep:
            if sep not in Float.allowedDecimalSeps:
                raise Exception(SEP_UNALLOWED % sep)
        self.tsep = tsep
        Integer.__init__(self, validator, multiplicity, default, defaultOnEdit,
          show, renderable, page, group, layouts, move, indexed, mustIndex,
          indexValue, emptyIndexValue, searchable, readPermission,
          writePermission, width, height, maxChars, colspan, master,
          masterValue, focus, historized, mapping, generateLabel, label,
          sdefault, scolspan, swidth, sheight, fwidth, persist, inlineEdit,
          view, cell, buttons, edit, xml, translations, readonly, alignOnEdit,
          autoComplete)
        self.pythonType = float

    def getFormattedValue(self, obj, value, layout='view', showChanges=False,
                          language=None):
        return utils.formatNumber(value, sep=self.sep[0],
                                  precision=self.precision, tsep=self.tsep)

    def replaceSeparators(self, value):
        '''Replaces, in p_value, separators "sep" and "tsep" in such a way that
           p_value may become a valid Python float literal.'''
        for sep in self.sep: value = value.replace(sep, '.')
        return value.replace(self.tsep, '')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
