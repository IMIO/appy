#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy import utils, n
from appy.model.fields.integer import Integer

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
SEP_UNALLOWED = 'Char "%s" is not allowed as decimal separator.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Float(Integer):
    '''Field allowing to store float values'''

    # Allowed chars for being used as decimal separators
    allowedDecimalSeps = ',', '.'

    # Precision of the indexed value, in number of decimals
    indexPrecision = 2

    # The name of the index class storing values of this field in the catalog
    indexType = 'FloatIndex'

    def __init__(self, validator=n, multiplicity=(0,1), default=n,
      defaultOnEdit=n, show=True, renderable=n, page='main', group=n,
      layouts=n, move=0, indexed=False, mustIndex=True, indexValue=n,
      emptyIndexValue=n, searchable=False, readPermission='read',
      writePermission='write', width=5, height=n, maxChars=13, colspan=1,
      master=n, masterValue=n, masterSnub=n, focus=False, historized=False,
      mapping=n, generateLabel=n, label=n, sdefault=('',''), scolspan=1,
      swidth=n, sheight=n, fwidth=3, persist=True, precision=n, sep=(',', '.'),
      tsep=' ', inlineEdit=False, view=n, cell=n, buttons=n, edit=n, custom=n,
      xml=n, translations=n, readonly=False, alignOnEdit='left',
      autoComplete=True):
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
        # Call the base constructor
        super().__init__(validator, multiplicity, default, defaultOnEdit, show,
          renderable, page, group, layouts, move, indexed, mustIndex,
          indexValue, emptyIndexValue, searchable, readPermission,
          writePermission, width, height, maxChars, colspan, master,
          masterValue, masterSnub, focus, historized, mapping, generateLabel,
          label, sdefault, scolspan, swidth, sheight, fwidth, persist,
          inlineEdit, view, cell, buttons, edit, custom, xml, translations,
          readonly, alignOnEdit, autoComplete)
        self.pythonType = float
        self.storableTypes = float, int

    def getFormattedValue(self, obj, value, layout='view', showChanges=False,
                          language=n):
        return utils.formatNumber(value, sep=self.sep[0],
                                  precision=self.precision, tsep=self.tsep)

    def replaceSeparators(self, value):
        '''Replaces, in p_value, separators "sep" and "tsep" in such a way that
           p_value may become a valid Python float literal.'''
        # Remove any tsep within p_value
        r = value.replace(self.tsep, '')
        # Replace sep with the Python decimal separator (the dot)
        for sep in self.sep: r = r.replace(sep, '.')
        return r
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
