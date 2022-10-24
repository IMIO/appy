# -*- coding: utf-8 -*-

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import re, random, sys

from appy import utils
from appy.px import Px
from appy.data import Countries
from appy.model.fields import Field
from appy.database.operators import in_
from appy.utils.string import Normalize
from appy.xml.cleaner import StringCleaner
from appy.ui.layout import Layouts, Layout
from appy.model.fields.multilingual import Multilingual

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
digit  = re.compile('[0-9]')
alpha  = re.compile('[a-zA-Z0-9]')
letter = re.compile('[a-zA-Z]')
digits = '0123456789'
letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class String(Multilingual, Field):
    '''Represents a one-line string'''

    class Layouts(Layouts):
        '''String-specific layouts'''
        g  = Layouts(Layout('f;rv=',  width=None))
        gd = Layouts(Layout('f;rv=d', width=None))

    # Use this constant to say that there is no maximum size for a string field
    NO_MAX = sys.maxsize

    # Some predefined regular expressions that may be used as validators
    c = re.compile
    EMAIL = c('[a-zA-Z][\w\.-]*[a-zA-Z0-9]*@[a-zA-Z0-9][\w\.-]*[a-zA-Z0-9]\.' \
              '[a-zA-Z][a-zA-Z\.]*[a-zA-Z]')
    ALPHANUMERIC = c('[\w-]+')
    URL = c('(http|https):\/\/[a-z0-9]+([\-\.]{1}[a-z0-9]+)*(\.[a-z]{2,5})?' \
            '(([0-9]{1,5})?\/.*)?')

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
       var="inputId='%s_%s' % (name, lg) if lg else name;
            placeholder=field.getPlaceholder(o)"
       id=":inputId" name=":inputId" size=":field.getInputSize()"
       maxlength=":field.maxChars" placeholder=":placeholder"
       value=":field.getInputValue(inRequest, requestValue, value)"
       style=":'text-transform:%s;%s' % \
               (field.transform, field.getInputSize(False))"
       readonly=":field.isReadonly(o)"/>''')

    search = Px('''
     <input type="text" maxlength=":field.maxChars" size=":field.swidth"
            value=":field.sdefault" name=":widgetName"
            style=":'text-transform:%s' % field.transform"/><br/>''')

    # Some predefined functions that may also be used as validators
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

    # Prefixes for which the Belgian NISS must be patched (see m_BELGIAN_NISS)
    nissModuloPrefixes = ('0', '1', '2')

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
        # year, coded on 2 chars: must 20 considered as 1920 or 2020 ?
        if niss[0] in String.nissModuloPrefixes:
            niss = '2' + niss
        # Check modulo 97 complement
        return String.MODULO_97_COMPLEMENT(o, niss)

    @staticmethod
    def IBAN(o, value):
        '''Checks that p_value corresponds to a valid IBAN number. IBAN stands
           for International Bank Account Number (ISO 13616). If the number is
           valid, the method returns True.'''
        if not value: return True
        # First, remove any non-digit or non-letter char
        v = Normalize.alphanum(value)
        # Maximum size is 34 chars
        if (len(v) < 8) or (len(v) > 34): return False
        # 2 first chars must be a valid country code
        if not Countries.get().exists(v[:2].upper()): return False
        # 2 next chars are a control code whose value must be between 0 and 96.
        try:
            code = int(v[2:4])
            if (code < 0) or (code > 97): return False
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

    def __init__(self, validator=None, multiplicity=(0,1), default=None,
      defaultOnEdit=None, show=True, renderable=None, page='main', group=None,
      layouts=None, move=0, indexed=False, mustIndex=True, indexValue=None,
      emptyIndexValue='-', searchable=False, filterField=None,
      readPermission='read', writePermission='write', width=None, height=None,
      maxChars=None, colspan=1, master=None, masterValue=None, focus=False,
      historized=False, mapping=None, generateLabel=None, label=None,
      sdefault='', scolspan=1, swidth=None, fwidth=10, sheight=None,
      persist=True, transform='none', placeholder=None, languages=('en',),
      languagesLayouts=None, viewSingle=False, inlineEdit=False, view=None,
      cell=None, buttons=None, edit=None, xml=None, translations=None,
      readonly=False, stripped=True):
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
        # Call the base constructors
        Multilingual.__init__(self, languages, languagesLayouts, viewSingle)
        Field.__init__(self, validator, multiplicity, default, defaultOnEdit,
          show, renderable, page, group, layouts, move, indexed, mustIndex,
          indexValue, emptyIndexValue, searchable, filterField, readPermission,
          writePermission, width, height, maxChars, colspan, master,
          masterValue, focus, historized, mapping, generateLabel, label,
          sdefault, scolspan, swidth, sheight, persist, inlineEdit, view, cell,
          buttons, edit, xml, translations)
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
                             language=None, contentLanguage=None):
        '''Returns the formatted variant of p_value. If p_contentLanguage is
           specified, p_value is the p_contentLanguage part of a multilingual
           value.'''
        return Field.getFormattedValue(self, o, value, layout, showChanges,
                                       language)

    def validateUniValue(self, o, value): return

    @classmethod
    def getRange(class_, value):
        '''If p_value ends with a star, returns a range. Else, it returns
           p_value unchanged.'''
        # Leave the value untouched if already correct
        if isinstance(value, in_) or not value.endswith('*'): return value
        # Build and return a range
        prefix = value[:-1]
        return in_(prefix, prefix + 'z')

    @classmethod
    def computeSearchValue(class_, field, req, value=None):
        '''Potentially apply a transform to search value in p_req and possibly
           define an interval of search values.'''
        r = Field.getSearchValue(field, req, value=value).strip()
        if not r: return r
        # Potentially apply a transform to the search value
        if getattr(field, 'transform', None):
            r = field.applyTransform(r)
        # Define a range if the search term ends with a *
        return class_.getRange(r)

    def getSearchValue(self, req, value=None):
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
            value = eval('value.%s()' % method)
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
