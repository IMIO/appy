#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import re, random, sys, time

from appy.px import Px
from appy import utils, n
from appy.data import Countries
from appy.utils.string import Normalize
from appy.xml.cleaner import StringCleaner
from appy.ui.layout import Layouts, Layout
from appy.model.fields import Field, Validator
from appy.database.operators import Operator, in_
from appy.model.fields.multilingual import Multilingual

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
digit  = re.compile('[0-9]')
alpha  = re.compile('[a-zA-Z0-9]')
letter = re.compile('[a-zA-Z]')
digits = '0123456789'
letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class NumberSelect(Validator):
    '''Validator used for validating a selection of numbers encoded as a
       string.'''

    # A typical use of such a validator is for checking field values
    # representing a selection of pages to print for some document. For example,
    # if one wants to print pages 2, 5, 7 to 19 and 56, a string field may hold
    # value "2;5;7-19;56", and validating that such a value is valid may be
    # performed by this NumberSelect class.

    # This class also offers methods for determining if a number is among a
    # range of selected numbers.

    def __init__(self, max, min=1, sep=';', rangeSep='-'):
        # The maximum number one may encode in the field
        self.max = max
        # The minimum number one may encode in the field
        self.min = min
        # The separator to use between individual numbers
        self.sep = sep
        # The separator to use for defining a range of numbers
        self.rangeSep = rangeSep

    def validNumber(self, value):
        '''Return True if p_value corresponds to a valid number'''
        try:
            n = int(value)
            return self.min <= n <= self.max
        except ValueError:
            return

    def validRange(self, value):
        '''Return True if p_value is a valid range of numbers'''
        min, max = value.split(self.rangeSep)
        return self.validNumber(min) and self.validNumber(max) and \
               int(min) < int(max)

    def validate(self, o, value):
        '''Validates that p_value conforms to p_self'''
        # Spit p_value into parts
        for part in value.split(self.sep):
            # v_part can be a number or a range
            sepCount = part.count(self.rangeSep)
            if sepCount == 1:
                # A range
                method = 'validRange'
            elif sepCount > 1:
                return o.translate('number_select_ko', mapping=self.__dict__)
            else:
                method = 'validNumber'
            if not getattr(self, method)(part):
                return o.translate('number_select_ko', mapping=self.__dict__)
        # If we are here, all the parts are valid
        return True

    def getValues(self, value):
        '''Returns value parts from this validated string p_value, as a basis
           for determining if a given number is among a range of selected
           numbers as validated by this NumberSelect object (p_self).'''
        # Indeed, beyond validating values, the NumberSelect class also offers
        # methods allowing to check whether a value is among a range of selected
        # numbers.
        #
        # As a first step towards this objective, m_getValues converts a raw,
        # string p_value into a 2-tuple of sets. The first set contains all the
        # individual numbers as found on p_value, while the second set contains
        # all the ranges found in p_value. Each range is represented as a tuple
        # of the form: (i_min, i_max).
        #
        # p_value is considered to be a valid value according to p_self
        numbers = set()
        ranges = set()
        if value:
            for part in value.split(self.sep):
                if self.rangeSep in part:
                    # A range
                    miN, maX = part.split(self.rangeSep)
                    ranges.add((int(miN), int(maX)))
                else:
                    numbers.add(int(part))
        return numbers, ranges

    def isAmong(self, number, numbers, ranges):
        '''Is this integer p_number among p_numbers or p_ranges ?'''
        # p_numbers and p_ranges must have been computed by p_getValues
        # The easy part: check whether p_number is among p_numbers
        if number in numbers: return True
        # Check if p_number is among one of these p_ranges
        for miN, maX in ranges:
            # Is p_number among (v_miN, v_maX) ?
            if miN <= number <= maX:
                return True

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class String(Multilingual, Field):
    '''Represents a one-line string'''

    class Layouts(Layouts):
        '''String-specific layouts'''
        g  = Layouts(Layout('f;rv=',  width=n))
        gd = Layouts(Layout('f;rv=d', width=n))

    # Use this constant to say that there is no maximum size for a string field
    NO_MAX = sys.maxsize

    # Some predefined regular expressions that may be used as validators
    c = re.compile
    aZ09  = '[a-zA-Z0-9]'
    aZ    = '[a-zA-Z]'
    EMAIL=c(fr'{aZ09}[\w\.-]*{aZ09}*@{aZ09}[\w\.-]*{aZ09}\.{aZ}[a-zA-Z\.]*{aZ}')
    ALPHANUMERIC = c(r'[\w-]+')
    URL = c(r'(http|https):\/\/[a-z0-9]+([\-\.]{1}[a-z0-9]+)*(\.[a-z]{2,5})?' \
            r'(([0-9]{1,5})?\/.*)?')

    # Default ways to render multilingual fields
    defaultLanguagesLayouts = {
      'edit': 'vertical', 'view': 'vertical', 'cell': 'vertical'}

    # Python string methods to use to apply a transform
    transformMethods = {'uppercase': 'upper', 'lowercase': 'lower',
                        'capitalize': 'capitalize'}

    viewUni = Px('''
     <span if="not value" class="smaller">-</span>
     <x if="value" var="isUrl=field.isUrl">
      <x if="isUrl" var2="value=field.getValueIf(o, name, layout)">
       <img src=":url('url')" class="checkAll"/>
       <a target="_blank" href=":value" title=":value">:value</a>
      </x>
      <x if="not isUrl">::value</x>
     </x>
     <input type="hidden" if="masterCss and not multilingual|False"
            class=":masterCss" value=":rawValue" name=":name" id=":name"/>''')

    cellUni = Px('''
     <span if="not value">-</span>
     <x if="value" var="isUrl=field.isUrl">
      <a if="isUrl" var2="value=field.getValueIf(o, name, layout)"
         target="_blank" href=":value" title=":value"><img src=":url('url')"/>
      </a>
      <x if="not isUrl">::value</x>
     </x>''')

    editUni = Px('''
     <input type="text"
       var="inputId=f'{name}_{lg}' if lg else name;
            placeholder=field.getPlaceholder(o)"
       id=":inputId" name=":inputId" size=":field.getInputSize()"
       maxlength=":field.maxChars" placeholder=":placeholder"
       value=":field.getInputValue(inRequest, requestValue, value)"
       style=":field.getWidgetStyle()" readonly=":field.isReadonly(o)"/>''')

    search = Px('''
     <input type="text" maxlength=":field.maxChars" size=":field.swidth"
            value=":field.getAttribute(o, 'sdefault')" name=":widgetName"
            style=":f'text-transform:{field.transform}'"/><br/>''')

    # Some predefined functions that may be used as validators

    @classmethod
    def rightLength(class_, o, rangE, value):
        '''Has p_value the right length? If no, returns a translated message.'''
        # p_rangE must be expressed as a tuple (i_minLength, i_maxLength) or an
        # object having attributes "min" and "max".
        if isinstance(rangE, tuple):
            miN, maX = rangE
        else:
            miN = rangE.min
            maX = rangE.max
        length = len(value)
        if length < miN or length > maX:
            r = o.translate('length_ko', mapping={'min': miN, 'max': maX})
        else:
            r = True
        return r

    @staticmethod
    def _MODULO_97(o, value, complement=False):
        '''p_value must be a string representing a number, like a bank account.
           this function checks that the 2 last digits are the result of
           computing the modulo 97 of the previous digits. Any non-digit
           character is ignored. If p_complement is True, it does compute the
           complement of modulo 97 instead of modulo 97. p_obj is not used;
           it will be given by the Appy validation machinery, so it must be
           specified as parameter. The function returns True if the check is
           successful.'''
        if not value: return True
        # First, remove any non-digit char
        v = ''
        for c in value:
            if digit.match(c): v += c
        # There must be at least 3 digits for performing the check
        if len(v) < 3: return False
        # Separate the real number from the check digits
        number = int(v[:-2])
        checkNumber = int(v[-2:])
        # Perform the check
        if complement:
            return (97 - (number % 97)) == checkNumber
        else:
            # The check number can't be 0. In this case, we force it to be 97.
            # This is the way Belgian bank account numbers work. I hope this
            # behaviour is general enough to be implemented here.
            mod97 = (number % 97)
            if mod97 == 0: return checkNumber == 97
            else:          return checkNumber == mod97

    @staticmethod
    def MODULO_97(o, value): return String._MODULO_97(o, value)

    @staticmethod
    def MODULO_97_COMPLEMENT(o, value): return String._MODULO_97(o, value, True)
    BELGIAN_ENTERPRISE_NUMBER = MODULO_97_COMPLEMENT

    @staticmethod
    def BELGIAN_NISS(o, value):
        '''Returns True if the NISS in p_value is valid'''
        if not value: return True
        # Remove any non-digit from nrn
        niss = Normalize.digit(value)
        # NISS must be made of 11 numbers
        if len(niss) != 11: return False
        # When NRN begins with some prefix, it must be prefixed with number "2"
        # for checking the modulo 97 complement. It is related to the birth
        # year, coded on 2 chars: must 20 be considered as 1920 or 2020 ?
        #
        # Compute the current and niss years (2 last figures)
        year = time.localtime().tm_year % 100
        nissYear = int(niss[:2])
        # If the niss year is above the current year, we consider it is an adult
        # born the previous century. Example: suppose we are in 2025. A niss
        # starting with 39 will supposedly belong to a person born in 1939,
        # while a niss starting with 25 will supposedly belong to a baby born in
        # 2025. In this latter case, the NISS must be prefix with figure 2
        # before computing the module 97 complement.
        prefix = '' if nissYear > year else '2'
        niss = f'{prefix}{niss}'
        # Check modulo 97 complement
        return String.MODULO_97_COMPLEMENT(o, niss)

    @staticmethod
    def EURO_ZIP(o, value, maxChars=n):
        '''Returns True if p_value contains a valid European postal code'''
        # This code validates the minimal set of rules common to all european
        # countries: having at least 4 digits, whose integer value is >1000.
        if not value: return True
        # Remove any non-digit char
        pc = Normalize.digit(value)
        # Postal code must at least be made of 4 chars and must be >1000
        if len(pc) < 4 or int(pc) < 1000:
            return False
        # If p_maxChars is specified, check it
        if maxChars is None:
            r = True
        else:
            r = len(pc) <= maxChars
        return r

    @staticmethod
    def BELGIAN_ZIP(o, value):
        '''Returns True if p_value contains a valid Begian postal code'''
        return String.EURO_ZIP(o, value, maxChars=4)

    @staticmethod
    def IBAN(o, value):
        '''Checks that p_value corresponds to a valid IBAN number. IBAN stands
           for International Bank Account Number (ISO 13616). If the number is
           valid, the method returns True.'''
        if not value: return True
        # First, remove any non-digit or non-letter char
        v = Normalize.alphanum(value)
        # Maximum size is 34 chars
        if not (8 <= len(v) <= 34): return False
        # 2 first chars must be a valid country code
        if not Countries.get().exists(v[:2].upper()): return False
        # 2 next chars are a control code whose value must be between 0 and 96.
        try:
            code = int(v[2:4])
            if not (2 <= code <= 98): return False
        except ValueError:
            return False
        # Perform the checksum
        vv = v[4:] + v[:4] # Put the 4 first chars at the end
        nv = ''
        for c in vv:
            # Convert each letter into a number (A=10, B=11, etc)
            # Ascii code for a is 65, so A=10 if we perform "minus 55"
            if letter.match(c): nv += str(ord(c.upper()) - 55)
            else: nv += c
        return int(nv) % 97 == 1

    @staticmethod
    def BIC(o, value):
        '''Checks that p_value corresponds to a valid BIC number. BIC stands
           for Bank Identifier Code (ISO 9362). If the number is valid, the
           method returns True.'''
        if not value: return True
        # BIC number must be 8 or 11 chars
        if len(value) not in (8, 11): return False
        # 4 first chars, representing bank name, must be letters
        for c in value[:4]:
            if not letter.match(c): return False
        # 2 next chars must be a valid country code
        if not Countries.get().exists(value[4:6].upper()): return False
        # Last chars represent some location within a country (a city, a
        # province...). They can only be letters or figures.
        for c in value[6:]:
            if not alpha.match(c): return False
        return True

    # A Validator sub-class that may be used as validator
    NumberSelect = NumberSelect

    def __init__(self, validator=n, multiplicity=(0,1), default=n,
      defaultOnEdit=n, show=True, renderable=n, page='main', group=n, layouts=n,
      move=0, indexed=False, mustIndex=True, indexValue=n, emptyIndexValue='-',
      searchable=False, sortField=n, filterField=n, readPermission='read',
      writePermission='write', width=n, height=n, maxChars=n, colspan=1,
      master=n, masterValue=n, masterSnub=n, focus=False, historized=False,
      mapping=n, generateLabel=n, label=n, sdefault='', scolspan=1, swidth=n,
      fwidth=10, sheight=n, persist=True, transform='none', placeholder=n,
      languages=('en',), languagesLayouts=n, viewSingle=False, inlineEdit=False,
      view=n, cell=n, buttons=n, edit=n, custom=n, xml=n, translations=n,
      readonly=False, stripped=True, alignOnEdit='left'):
        # Does this field store an URL ?
        self.isUrl = validator == String.URL
        # "placeholder", similar to the HTML attribute of the same name, allows
        # to specify a short hint describing the expected value of the input
        # field. It is shown inside the input field and disappears as soon as
        # the user encodes something in it. You can specify a method here, that
        # can, for example, return an internationalized value.
        self.placeholder = placeholder
        # "transform" below has a direct impact on the text entered by the user.
        # It applies a transformation on it, exactly as does the CSS
        # "text-transform" property. Allowed values are those allowed for the
        # CSS property: "none" (default), "uppercase", "capitalize" or
        # "lowercase".
        self.transform = transform
        # If attribute "readonly" is True (or stores a method returning True),
        # the rendered input field, on edit layouts, will have attribute
        # "readonly" set.
        self.readonly = readonly
        # Must the field content be stripped as soon as it is encoded by the
        # user ?
        self.stripped = stripped
        # On "edit", the alignment of the string encoded in the value can be
        # "left", "right" or "center".
        self.alignOnEdit = alignOnEdit
        # Call the base constructors
        Multilingual.__init__(self, languages, languagesLayouts, viewSingle)
        Field.__init__(self, validator, multiplicity, default, defaultOnEdit,
          show, renderable, page, group, layouts, move, indexed, mustIndex,
          indexValue, emptyIndexValue, searchable, sortField, filterField,
          readPermission, writePermission, width, height, maxChars, colspan,
          master, masterValue, masterSnub, focus, historized, mapping,
          generateLabel, label, sdefault, scolspan, swidth, sheight, persist,
          inlineEdit, view, cell, buttons, edit, custom, xml, translations)
        # Default width, height and maxChars
        if width is None:
            self.width  = 30
        if height is None:
            self.height = 1
        if maxChars is None:
            self.maxChars = 256
        if self.indexed:
            self.filterPx = 'pxFilterText'
        self.swidth = self.swidth or self.width
        self.sheight = self.sheight or self.height
        # The *f*ilter width
        self.fwidth = fwidth

    def isRenderableOn(self, layout):
        '''A value being an URL can be rendered everywhere'''
        if self.isUrl: return True
        return super().isRenderableOn(layout)

    def isSortable(self, inRefs=False):
        '''Can this field be sortable ?'''
        if not inRefs: return Field.isSortable(self)
        return not self.isMultilingual(None, True)

    def getUniFormattedValue(self, o, value, layout='view', showChanges=False,
                             language=n, contentLanguage=n):
        '''Returns the formatted variant of p_value. If p_contentLanguage is
           specified, p_value is the p_contentLanguage part of a multilingual
           value.'''
        return Field.getFormattedValue(self, o, value, layout, showChanges,
                                       language)

    def validateUniValue(self, o, value): return

    def getWidgetStyle(self):
        '''Get the styles to apply to the input widget on the edit layout'''
        r = f'text-transform:{self.transform};text-align:{self.alignOnEdit}'
        size = self.getInputSize(False)
        if size:
            r = f'{r};{size}'
        return r

    @classmethod
    def getRange(class_, value):
        '''If p_value ends with a star, returns a range. Else, it returns
           p_value unchanged.'''
        # Leave the value untouched if already correct
        if isinstance(value, Operator) or not value.endswith('*'): return value
        # Build and return a range
        prefix = value[:-1]
        return in_(prefix, f'{prefix}z')

    @classmethod
    def computeSearchValue(class_, field, req, value=n):
        '''Potentially apply a transform to search value in p_req and possibly
           define an interval of search values.'''
        r = Field.getSearchValue(field, req, value=value).strip()
        if not r: return r
        # Potentially apply a transform to the search value
        if getattr(field, 'transform', None):
            r = field.applyTransform(r)
        # Define a range if the search term ends with a *
        return class_.getRange(r)

    def getSearchValue(self, req, value=n):
        '''See called method's docstring'''
        return String.computeSearchValue(self, req, value=value)

    def getSortValue(self, o):
        '''Return p_self' value on p_o that must be used for sorting'''
        # While the raw field value, as produced by method "getValue", may be
        # the value to use in most cases, it is not always true. For example, a
        # string like "Gaëtan" could have "gaetan" as sort value.
        return Normalize.sortable(self.getValue(o) or '')

    def getPlaceholder(self, o):
        '''Returns a placeholder for the field if defined'''
        r = self.getAttribute(o, 'placeholder') or ''
        if r == True:
            # A placeholder must be set, but we have no value. In this case, we
            # take the field label.
            r = o.translate(self.labelId)
        return r

    def applyTransform(self, value):
        '''Applies a transform as required by self.transform on single
           value p_value.'''
        if self.transform in ('uppercase', 'lowercase'):
            # For those transforms, accents will be removed, because, most
            # of the time, if the user wants to apply such effect, it is for
            # ease of data manipulation, probably without accent.
            value = Normalize.accents(value)
        # Apply the transform
        method = String.transformMethods.get(self.transform)
        if method:
            value = eval(f'value.{method}()')
        return value

    def getUniStorableValue(self, o, value):
        '''Manage a potential string transform and max chars'''
        # Strip this p_value if required
        if value and self.stripped:
            value = value.strip()
        # Remove problematic chars if found
        value = StringCleaner.clean(value)
        # Apply transform if required
        if value:
            value = self.applyTransform(value)
            # Manage maxChars
            max = self.maxChars
            if max and (len(value) > max): value = value[:max]
        return value
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
