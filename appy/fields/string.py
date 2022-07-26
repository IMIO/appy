# -*- coding: utf-8 -*-
# ~license~
# ------------------------------------------------------------------------------
import re, random, sys
from appy.px import Px
from appy.fields import Field
from appy.gen.layout import Table
from appy.shared.diff import HtmlDiff
from appy.shared.data import countries
from appy.shared import utils as sutils
from appy.fields.select import Selection
from appy.gen.indexer import XhtmlTextExtractor, ValidValue
from appy.shared.xml_parser import Escape,XmlParser,XhtmlCleaner,StringCleaner

# ------------------------------------------------------------------------------
digit  = re.compile('[0-9]')
alpha  = re.compile('[a-zA-Z0-9]')
letter = re.compile('[a-zA-Z]')
digits = '0123456789'
letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
emptyTuple = ()

# ------------------------------------------------------------------------------
NOT_IMPLEMENTED = 'This feature is not implemented yet'
WRONG_READONLY = 'A read-only field must have a format being LINE.'
SELECT_MULTILINGUAL = "A selection field can't be multilingual."
PASSWORD_MULTILINGUAL = "A password or captcha field can't be multilingual."
UNPARSABLE = 'Unparsable: %s'

# ------------------------------------------------------------------------------
class String(Field):
    # Some base layouts for Strings
    tLayouts = {'view': 'l-f', 'edit': 'lrv-d-f'} # For TEXT format
    gtLayouts = {'view': Table('fl', width='99%'), # Idem but in a grid group
                 'edit': Table('d2-f;rv=', width='99%')}
    xLayouts = tLayouts # For XHTML format
    xcLayouts = {'view': 'lc-f', 'edit': 'lrv-d-f'} # Idem but with history
    gxLayouts = gtLayouts # Idem but in a grid group
    gxcLayouts = {'view': Table('cl-f', width='99%'),
                  'edit': Table('drv-f', width='99%')} # Idem but with history
    stLayouts = {'view': Table('fl', width=None), # For select strings
                 'edit': Table('d2-f;rv=', width=None)}

    # Javascript files sometimes required by this type. Method String.getJs
    # below determines when the files must be included.
    cdnUrl = '//cdn.ckeditor.com/%s/%s/ckeditor.js'

    # Default custom style, allowing to produce, in POD results, a page break
    # just after the paragraph having this style.
    customStyles = [{'id': 'div', 'element': 'div',
                     'attributes': {'style': 'page-break-after:always'}}]

    # Use this constant to say that there is no maximum size for a string field
    NO_MAX = sys.maxint

    # Some predefined regular expressions that may be used as validators
    c = re.compile
    EMAIL = c('[a-zA-Z][\w\.-]*[a-zA-Z0-9]*@[a-zA-Z0-9][\w\.-]*[a-zA-Z0-9]\.' \
              '[a-zA-Z][a-zA-Z\.]*[a-zA-Z]')
    ALPHANUMERIC = c('[\w-]+')
    URL = c('(http|https):\/\/[a-z0-9]+([\-\.]{1}[a-z0-9]+)*(\.[a-z]{2,5})?' \
            '(([0-9]{1,5})?\/.*)?')

    # Possible values for "format"
    LINE = 0
    TEXT = 1
    XHTML = 2
    PASSWORD = 3
    CAPTCHA = 4

    # Default ways to render multilingual fields
    defaultLanguagesLayouts = {
      LINE:  {'edit': 'vertical',   'view': 'vertical', 'cell': 'vertical'},
      TEXT:  {'edit': 'horizontal', 'view': 'vertical', 'cell': 'vertical'},
      XHTML: {'edit': 'horizontal', 'view': 'horizontal', 'cell': 'vertical'},
    }

    # Python string methods to use to apply a transform
    transformMethods = {'uppercase': 'upper', 'lowercase': 'lower',
                        'capitalize': 'capitalize'}

    # pxView part for formats String.LINE (but that are not selections) and
    # String.PASSWORD (a fake view for String.PASSWORD and no view at all for
    # String.CAPTCHA).
    pxViewLine = Px('''
     <span if="not value" class="smaller">-</span>
     <x if="value">
      <!-- A password -->
      <x if="fmt == 3">********</x>
      <!-- A URL -->
      <a if="(fmt != 3) and isUrl" target="_blank" href=":value">:value</a>
      <!-- Any other value -->
      <x if="(fmt != 3) and not isUrl">::value</x>
     </x>''')

    # pxView part for format String.TEXT
    pxViewText = Px('''
     <span if="not value" class="smaller">-</span><x if="value">::value</x>''')

    # pxView part for format String.XHTML
    pxViewRich = Px('''
     <div if="not mayAjaxEdit" class="xhtml">::value or '-'</div>
     <x if="mayAjaxEdit" var2="name=lg and ('%s_%s' % (name, lg)) or name">
      <div class="xhtml" contenteditable="true"
           id=":'%s_%s_ck' % (zobj.id, name)">::value or '-'</div>
      <script if="mayAjaxEdit">::field.getJsInlineInit(zobj, name, lg)</script>
     </x>''')

    # PX displaying the language code and name besides the part of the
    # multilingual field storing content in this language.
    pxLanguage = Px('''
     <td style=":'padding-top:%dpx' % lgTop" width="25px">
      <span class="language help"
            title=":ztool.getLanguageName(lg)">:lg.upper()</span>
     </td>''')

    pxMultilingual = Px('''
     <!-- Horizontally-layouted multilingual field -->
     <table if="mLayout == 'horizontal'" width="100%"
            class=":(layoutType == 'cell') and 'no' or ''"
            var="count=len(languages)">
      <tr valign="top"><x for="lg in languages"><x>:field.pxLanguage</x>
       <td width=":'%d%%' % int(100.0/count)"
           var="requestValue=requestValue[lg]|None;
                value=value[lg]|emptyDefault">:field.subPx[layoutType][fmt]</td>
      </x></tr></table>

     <!-- Vertically-layouted multilingual field -->
     <table if="mLayout == 'vertical'"
            class=":(layoutType == 'cell') and 'no' or ''">
      <tr valign="top" height="20px" for="lg in languages">
       <x>:field.pxLanguage</x>
       <td var="requestValue=requestValue[lg]|None;
                value=value[lg]|emptyDefault">:field.subPx[layoutType][fmt]</td>
     </tr></table>''')

    pxView = Px('''
     <x var="fmt=field.format; isUrl=field.isUrl;
             languages=field.getAttribute(obj, 'languages');
             multilingual=len(languages) &gt; 1;
             mLayout=multilingual and field.getLanguagesLayout('view');
             inlineEdit=field.getAttribute(obj, 'inlineEdit');
             mayAjaxEdit=(layoutType != 'cell') and not showChanges and \
                         inlineEdit and zobj.mayEdit(field.writePermission)">
      <x if="field.isSelect">
       <span if="not value" class="smaller">-</span>
       <x if="value and not isMultiple">::value</x>
       <ul if="value and isMultiple"><li for="sv in value"><i>::sv</i></li></ul>
      </x>
      <!-- Any other unilingual field -->
      <x if="not field.isSelect and not multilingual"
         var2="lg=None">:field.subPx['view'][fmt]</x>
      <!-- Any other multilingual field -->
      <x if="not field.isSelect and multilingual"
         var2="lgTop=1; emptyDefault='-'">:field.pxMultilingual</x>
      <!-- If this field is a master field -->
      <input type="hidden" if="masterCss" class=":masterCss" value=":rawValue"
             name=":name" id=":name"/></x>''')

    # pxEdit part for formats String.LINE (but that are not selections),
    # String.PASSWORD and String.CAPTCHA.
    pxEditLine = Px('''
     <input var="inputId=not lg and name or '%s_%s' % (name, lg);
                 placeholder=field.getPlaceholder(obj)"
            id=":inputId" name=":inputId" size=":field.getLineWidth()"
            maxlength=":field.maxChars" placeholder=":placeholder"
            value=":field.getInputValue(inRequest, requestValue, value)"
            style=":'text-transform:%s;%s' % \
                    (field.transform, field.getLineWidth(False))"
            type=":(fmt == 3) and 'password' or 'text'"
            readonly=":field.isReadonly(zobj)"/>
     <!-- Display a captcha if required -->
     <span if="fmt == 4">:_('captcha_text', \
                            mapping=field.getCaptchaChallenge(req.SESSION))
     </span>''')

    # pxEdit part for formats String.TEXT and String.XHTML
    pxEditTextArea = Px('''
     <textarea var="inputId=not lg and name or '%s_%s' % (name, lg)"
       id=":inputId" name=":inputId" cols=":field.getTextareaCols()"
       style=":field.getTextareaStyle()"
       rows=":field.height">:field.getInputValue(inRequest, requestValue, value)
     </textarea>
     <script if="fmt == 2">::field.getJsInit(zobj, lg)</script>''')

    pxEdit = Px('''
     <x var="fmt=field.format;
             languages=field.getAttribute(zobj, 'languages');
             multilingual=len(languages) &gt; 1;
             mLayout=multilingual and field.getLanguagesLayout('edit')">
      <select if="field.isSelect"
              var2="possibleValues=field.getPossibleValues(zobj, \
                      withTranslations=True, withBlankValue=True);
                    charsWidth=field.getWidthInChars(False)"
              name=":name" id=":name" class=":masterCss" multiple=":isMultiple"
              onchange=":field.getOnChange(zobj, layoutType)"
              size=":field.getSelectSize(False, isMultiple)"
              style=":field.getSelectStyle(False, isMultiple)">
       <option for="val in possibleValues" value=":val[0]"
               selected=":field.isSelected(zobj, name, val[0], rawValue)"
               title=":val[1]">:ztool.truncateValue(val[1], charsWidth)</option>
      </select>
      <!-- Any other unilingual field -->
      <x if="not field.isSelect and not multilingual"
         var2="lg=None">:field.subPx['edit'][fmt]</x>
      <!-- Any other multilingual field -->
      <x if="not field.isSelect and multilingual"
         var2="lgTop=(fmt!=2) and 3 or 1;
               emptyDefault=''">:field.pxMultilingual</x>
      </x>''')

    pxCell = Px('''
     <x if="field.isUrl" var2="value=field.getValueIf(zobj, name, layoutType)">
      <a href=":value" title=":value" target="_blank">
       <img src=":url('url')"/></a></x>
     <x if="not field.isUrl"
        var2="multipleValues=value and isMultiple">
      <x if="multipleValues">:', '.join(value)</x>
      <x if="not multipleValues">:field.pxView</x>
     </x>''')

    pxSearch = Px('''
     <!-- Show a simple search field for most String fields -->
     <input if="not field.isSelect" type="text" maxlength=":field.maxChars"
            size=":field.swidth" value=":field.sdefault" name=":widgetName"
            style=":'text-transform:%s' % field.transform"/>
     <!-- Show a multi-selection box for fields whose validator defines a list
          of values, with a "AND/OR" checkbox. -->
     <x if="field.isSelect">
      <!-- The "and" / "or" radio buttons -->
      <x if="field.multiplicity[1] != 1"
         var2="operName='o_%s' % name;
              orName='%s_or' % operName;
              andName='%s_and' % operName">
       <input type="radio" name=":operName" id=":orName" checked="checked"
              value="or"/>
       <label lfor=":orName">:_('search_or')</label>
       <input type="radio" name=":operName" id=":andName" value="and"/>
       <label lfor=":andName">:_('search_and')</label><br/>
      </x>
      <!-- The list of values -->
      <select var="preSelected=field.sdefault;
                   charsWidth=field.getWidthInChars(True)"
              name=":widgetName" multiple="multiple"
              size=":field.getSelectSize(True, True)"
              style=":field.getSelectStyle(True, True)"
              onchange=":field.getOnChange(ztool, 'search', className)">
       <option for="v in field.getPossibleValues(ztool, withTranslations=True,\
                                     withBlankValue=False, className=className)"
               selected=":v[0] in preSelected" value=":v[0]"
               title=":v[1]">:ztool.truncateValue(v[1], charsWidth)</option>
      </select>
     </x><br/>''')

    # Widget for filtering object values on query results
    pxFilterSelect = Px('''
     <select var="name=field.name;
                  filterId='%s_%s' % (mode.ajaxHookId, name);
                  charsWidth=field.getWidthInChars(True)"
        id=":filterId" name=":filterId" class="discreet"
          onchange=":'askBunchFiltered(%s,%s)' % (q(mode.ajaxHookId), q(name))">
      <option for="v in field.getPossibleValues(ztool, withTranslations=True,\
        withBlankValue='forced', blankLabel='everything', className=className)"
        selected=":(name in mode.filters) and (mode.filters[name] == v[0])"
        value=":v[0]" title=":v[1]">:ztool.truncateValue(v[1], \
                                                         charsWidth)</option>
     </select>''')

    # Sub-PX to use according to String format
    subPx = {
     'edit': {LINE:pxEditLine, TEXT:pxEditTextArea, XHTML:pxEditTextArea,
              PASSWORD:pxEditLine, CAPTCHA:pxEditLine},
     'view': {LINE:pxViewLine, TEXT:pxViewText, XHTML:pxViewRich,
              PASSWORD:pxViewLine, CAPTCHA:pxViewLine}
    }
    subPx['cell'] = subPx['view']

    # Some predefined functions that may also be used as validators
    @staticmethod
    def _MODULO_97(obj, value, complement=False):
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
    def MODULO_97(obj, value): return String._MODULO_97(obj, value)
    @staticmethod
    def MODULO_97_COMPLEMENT(obj, value):
        return String._MODULO_97(obj, value, True)
    BELGIAN_ENTERPRISE_NUMBER = MODULO_97_COMPLEMENT

    # Prefixes for which the Belgian NISS must be patched (see m_BELGIAN_NISS)
    nissModuloPrefixes = ('0', '1', '2')

    @staticmethod
    def BELGIAN_NISS(obj, value):
        '''Returns True if the NISS in p_value is valid'''
        if not value: return True
        # Remove any non-digit from nrn
        niss = sutils.keepDigits(value)
        # NISS must be made of 11 numbers
        if len(niss) != 11: return False
        # When NRN begins with some prefix, it must be prefixed with number "2"
        # for checking the modulo 97 complement. It is related to the birth
        # year, coded on 2 chars: must 20 considered as 1920 or 2020 ?
        if niss[0] in String.nissModuloPrefixes:
            niss = '2' + niss
        # Check modulo 97 complement
        return String.MODULO_97_COMPLEMENT(None, niss)

    @staticmethod
    def IBAN(obj, value):
        '''Checks that p_value corresponds to a valid IBAN number. IBAN stands
           for International Bank Account Number (ISO 13616). If the number is
           valid, the method returns True.'''
        if not value: return True
        # First, remove any non-digit or non-letter char
        v = ''
        for c in value:
            if alpha.match(c): v += c
        # Maximum size is 34 chars
        if (len(v) < 8) or (len(v) > 34): return False
        # 2 first chars must be a valid country code
        if not countries.exists(v[:2].upper()): return False
        # 2 next chars are a control code whose value must be between 0 and 96.
        try:
            code = int(v[2:4])
            if (code < 0) or (code > 96): return False
        except ValueError:
            return False
        # Perform the checksum
        vv = v[4:] + v[:4] # Put the 4 first chars at the end.
        nv = ''
        for c in vv:
            # Convert each letter into a number (A=10, B=11, etc)
            # Ascii code for a is 65, so A=10 if we perform "minus 55"
            if letter.match(c): nv += str(ord(c.upper()) - 55)
            else: nv += c
        return int(nv) % 97 == 1

    @staticmethod
    def BIC(obj, value):
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
        if not countries.exists(value[4:6].upper()): return False
        # Last chars represent some location within a country (a city, a
        # province...). They can only be letters or figures.
        for c in value[6:]:
            if not alpha.match(c): return False
        return True

    def __init__(self, validator=None, multiplicity=(0,1), default=None,
      defaultOnEdit=None, format=LINE, show=True, page='main', group=None,
      layouts=None, move=0, indexed=False, mustIndex=True, indexValue=None,
      searchable=False, specificReadPermission=False,
      specificWritePermission=False, width=None, height=None, maxChars=None,
      colspan=1, master=None, masterValue=None, focus=False, historized=False,
      mapping=None, generateLabel=None, label=None, sdefault='', scolspan=1,
      swidth=None, sheight=None, persist=True, transform='none',
      placeholder=None, styles=('p','h1','h2','h3','h4'), customStyles=None,
      allowImageUpload=False, spellcheck=False, languages=('en',),
      languagesLayouts=None, inlineEdit=False, toolbar='Standard', view=None,
      cell=None, edit=None, xml=None, translations=None,
      noValueLabel='choose_a_value', readonly=False):
        # According to format, the widget will be different: input field,
        # textarea, inline editor... Note that there can be only one String
        # field of format CAPTCHA by page, because the captcha challenge is
        # stored in the session at some global key.
        self.format = format
        self.isUrl = validator == String.URL
        # ~~~ The following attributes have sense only if format is XHTML ~~~
        # The list of styles that the user will be able to select in the styles
        # dropdown (within CKEditor) is defined hereafter.
        self.styles = styles
        # If you want to add custom, non-standard styles in the above-mentioned
        # dropdown, do not touch attribute "styles", but specify such entries in
        # the following attribute "customStyles". It must be a list or dict of
        # entries; every entry represents a custom style and must be a dict
        # having the following keys and values. Every key and value must be a
        # string.
        # ----------------------------------------------------------------------
        #    "id"    | An identifier for your style, that must be different from
        #            | any standard CKEditor style like h1, h2, p, div, etc;
        # ----------------------------------------------------------------------
        #   "name"   | A translated name for your style, that will appear in the
        #            | dropdown. Do not use any special (ie, accentuated) char
        #            | in the value: prefer the use of an HTML entity for
        #            | defining such char.
        # ----------------------------------------------------------------------
        #  "element" | The HTML tag that will surround the text onto which the
        #            | style will be applied. Do not use "blockquote", it does
        #            | not work. Non-standard tag "address" works well, or any
        #            | standard tag like h1, h2, etc. Note that if you use a
        #            | standard tag, it will work, but if you have also
        #            | activated it in attribute "style" hereabove, you won't be
        #            | able to make the difference in the result between both
        #            | styles because they will produce a similar result.
        # ----------------------------------------------------------------------
        self.customStyles = customStyles or String.customStyles
        # Do we allow the user to upload images in it ?
        self.allowImageUpload = allowImageUpload
        if allowImageUpload: raise Exception(NOT_IMPLEMENTED)
        # Do we run the CK spellchecker ?
        self.spellcheck = spellcheck
        # What toolbar is used ? Possible values are "Standard" or "Simple"
        self.toolbar = toolbar
        # "placeholder", similar to the HTML attribute of the same name, allows
        # to specify a short hint that describes the expected value of the input
        # field. It is shown inside the input field and disappears as soon as
        # the user encodes something in it. Works only for strings whose format
        # is LINE. Does not work with IE < 10. You can specify a method here,
        # that can, for example, return an internationalized value.
        self.placeholder = placeholder
        # If "languages" holds more than one language, the field will be
        # multi-lingual and several widgets will allow to edit/visualize the
        # field content in all the supported languages. The field is also used
        # by the CK spell checker.
        self.languages = languages
        # When content exists in several languages, how to render them? Either
        # horizontally (one below the other), or vertically (one besides the
        # other). Specify here a dict whose keys are layouts ("edit", "view")
        # and whose values are either "horizontal" or "vertical".
        self.languagesLayouts = languagesLayouts
        # ~~~ End of XHTML-related attributes ~~~
        # "transform" below has a direct impact on the text entered by the user.
        # It applies a transformation on it, exactly as does the CSS
        # "text-transform" property. Allowed values are those allowed for the
        # CSS property: "none" (default), "uppercase", "capitalize" or
        # "lowercase".
        self.transform = transform
        # When selecting a value from a "select" widget, the entry representing
        # no value is translated according to this label. The default one is
        # something like "[ choose ]", but if you prefer a less verbose version,
        # you can use "no_value" that simply displays a dash, or your own label.
        self.noValueLabel = noValueLabel
        # If attribute "readonly" is True (or stores a method returning True),
        # the rendered input field, on edit layouts, will have attribute
        # "readonly" set.
        self.readonly = readonly
        # Call the base constructor
        Field.__init__(self, validator, multiplicity, default, defaultOnEdit,
          show, page, group, layouts, move, indexed, mustIndex, indexValue,
          searchable, specificReadPermission, specificWritePermission, width,
          height, maxChars, colspan, master, masterValue, focus, historized,
          mapping, generateLabel, label, sdefault, scolspan, swidth, sheight,
          persist, inlineEdit, view, cell, edit, xml, translations)
        self.isSelect = self.isSelection()
        # If self.isSelect, self.sdefault must be a list of value(s)
        if self.isSelect and not sdefault:
            self.sdefault = []
        # Default width, height and maxChars vary according to String format
        if width is None:
            if format == String.TEXT:    self.width  = 60
            # This width corresponds to the standard width of an Appy page
            elif format == String.XHTML: self.width  = None
            else:                        self.width  = 30
        if height is None:
            if format == String.TEXT:    self.height = 5
            elif format == String.XHTML: self.height  = None
            elif self.isSelect:          self.height = 4
            else:                        self.height = 1
        if maxChars is None:
            if self.isSelect: pass
            elif format == String.LINE: self.maxChars = 256
            elif format == String.TEXT: self.maxChars = String.NO_MAX
            elif format == String.XHTML: self.maxChars = String.NO_MAX
            elif format == String.PASSWORD: self.maxChars = 20
        if self.indexed and (self.format in (String.LINE, String.TEXT)):
            self.filterPx = self.isSelect and 'pxFilterSelect' or 'pxFilterText'
        self.swidth = self.swidth or self.width
        self.sheight = self.sheight or self.height
        self.checkParameters()

    def checkParameters(self):
        '''Ensures this String is correctly defined'''
        error = None
        if self.isMultilingual(None):
            if self.isSelect:
                error = SELECT_MULTILINGUAL
            elif self.format in (String.PASSWORD, String.CAPTCHA):
                error = PASSWORD_MULTILINGUAL
        if self.readonly and (self.format != String.LINE):
            error = WRONG_READONLY
        if error: raise Exception(error)

    def isSelection(self):
        '''Does the validator of this type definition define a list of values
           into which the user must select one or more values?'''
        res = True
        if type(self.validator) in (list, tuple):
            for elem in self.validator:
                if not isinstance(elem, basestring):
                    res = False
                    break
        else:
            if not isinstance(self.validator, Selection):
                res = False
        return res

    def isRenderable(self, layoutType):
        '''A value being an URL is potentially renderable everywhere'''
        if self.isUrl: return True
        return layoutType != 'buttons'

    def isSortable(self, usage):
        '''Can this field be sortable ?'''
        if self.name == 'state': return
        if usage == 'search':
            r = self.indexed and not self.isMultiValued() and \
                not self.isSelection()
        elif usage == 'ref':
            r = (self.format == 0) and not self.isMultilingual(None, True)
        return r

    def isMultilingual(self, obj, dontKnow=False):
        '''Is this field multilingual ? If we don't know, say p_dontKnow.'''
        # In the following case, impossible to know: we say no.
        if not obj:
            if callable(self.languages): return dontKnow
            else: return len(self.languages) > 1
        return len(self.getAttribute(obj, 'languages')) > 1

    def getLineWidth(self, sizeAttr=True):
        '''When p_self is rendered as an input field of type "text", this method
           returns its width as must be defined, either in the "size" attribute,
           (p_sizeAttr is True) or as a CSS "width" attribute (p_sizeAttr is
           False).'''
        # If the field width is expressed as a percentage, the width must be
        # specified via the CSS "width" attribute. In all other cases, it is
        # specified via the "size" tag attribute.
        width = self.width
        isPercentage = width and isinstance(width, str) and width.endswith('%')
        if sizeAttr: # tag attribute "size"
            if isPercentage: return ''
            else: return width
        else: # CSS attribute "width"
            return isPercentage and ('width:%s' % width) or ''

    def getDefaultLayouts(self):
        '''Returns the default layouts for this type. Default layouts can vary
           acccording to format, multiplicity, group or history.'''
        # Is this field in a grid-style group ?
        inGrid = self.inGrid()
        # Defaults layouts depend on format
        if self.format == String.TEXT:
            return inGrid and String.gtLayouts or String.tLayouts
        elif self.format == String.XHTML:
            if self.historized:
                # self.historized can be a method or a boolean. If it is a
                # method, it means that under some condition, historization will
                # be enabled. So we come here also in this case.
                return inGrid and String.gxcLayouts or String.xcLayouts
            else:
                return inGrid and String.gxLayouts or String.xLayouts
        elif self.isSelection() and inGrid:
            return String.stLayouts

    def getLanguagesLayout(self, layoutType):
        '''Gets the way to render a multilingual field on p_layoutType'''
        if self.languagesLayouts and (layoutType in self.languagesLayouts):
            return self.languagesLayouts[layoutType]
        # Else, return a default value that depends of the format.
        return String.defaultLanguagesLayouts[self.format][layoutType]

    def getValue(self, obj, name=None, layout=None, noListIfSingleObj=False):
        # Cheat if this field represents p_obj's state
        if self.name == 'state': return obj.State()
        value = Field.getValue(self, obj, name, layout)
        if not value:
            if self.isMultiValued(): return emptyTuple
            else: return value
        if isinstance(value, basestring) and self.isMultiValued():
            value = [value]
        elif isinstance(value, tuple):
            value = list(value)
        return value

    def getCopyValue(self, obj):
        '''If the value is mutable (ie, a dict for a multilingual field), return
           a copy of it instead of the value stored in the database.'''
        res = self.getValue(obj)
        if isinstance(res, dict): res = res.copy()
        return res

    def valueIsInRequest(self, obj, request, name=None, layoutType='view'):
        # If we are on the search layout, p_obj, if not None, is certainly not
        # the p_obj we want here (can be a home object).
        if layoutType == 'search':
            return Field.valueIsInRequest(self, obj, request, name, layoutType)
        languages = self.getAttribute(obj, 'languages')
        if len(languages) == 1:
            return Field.valueIsInRequest(self, obj, request, name, layoutType)
        # Is is sufficient to check that at least one of the language-specific
        # values is in the request.
        return request.has_key('%s_%s' % (name, languages[0]))

    def getRequestValue(self, obj, requestName=None):
        '''The request value may be multilingual'''
        request = obj.REQUEST
        name = requestName or self.name
        languages = self.getAttribute(obj, 'languages')
        # A unilingual field
        if len(languages) == 1: return request.get(name, None)
        # A multilingual field
        res = {}
        for language in languages:
            res[language] = request.get('%s_%s' % (name, language), None)
        return res

    def isEmptyValue(self, obj, value):
        '''Returns True if the p_value must be considered as an empty value'''
        if not isinstance(value, dict):
            return Field.isEmptyValue(self, obj, value)
        # p_value is a dict of multilingual values. For such values, as soon
        # as a value is not empty for a given language, the whole value is
        # considered as not being empty.
        for v in value.itervalues():
            if not Field.isEmptyValue(self, obj, v): return
        return True

    def isCompleteValue(self, obj, value):
        '''Returns True if the p_value must be considered as complete. For a
           unilingual field, being complete simply means not being empty. For a
           multilingual field, being complete means that a value is present for
           every language.'''
        if not self.isMultilingual(obj):
            return Field.isCompleteValue(self, obj, value)
        # As soon as a given language value is empty, the global value is not
        # complete.
        if not value: return True
        for v in value.itervalues():
            if Field.isEmptyValue(self, obj, v): return
        return True

    def getDiffValue(self, obj, value, language):
        '''Returns a version of p_value that includes the cumulative diffs
           between successive versions. If the field is non-multilingual, it
           must be called with p_language being None. Else, p_language
           identifies the language-specific part we will work on.'''
        res = None
        lastEvent = None
        name = language and ('%s-%s' % (self.name, language)) or self.name
        for event in obj.workflow_history['appy']:
            if event['action'] != '_datachange_': continue
            if name not in event['changes']: continue
            if res is None:
                # We have found the first version of the field
                res = event['changes'][name][0] or ''
            else:
                # We need to produce the difference between current result and
                # this version.
                iMsg, dMsg = obj.getHistoryTexts(lastEvent)
                thisVersion = event['changes'][name][0] or ''
                comparator = HtmlDiff(res, thisVersion, iMsg, dMsg)
                res = comparator.get()
            lastEvent = event
        if not lastEvent:
            # There is no diff to show for this p_language.
            return value
        # Now we need to compare the result with the current version.
        iMsg, dMsg = obj.getHistoryTexts(lastEvent)
        comparator = HtmlDiff(res, value or '', iMsg, dMsg)
        return comparator.get()

    def getUnilingualFormattedValue(self, obj, value, layoutType='view',
          showChanges=False, userLanguage=None, language=None):
        '''If no p_language is specified, this method is called by
           m_getFormattedValue for getting a non-multilingual value (ie, in
           most cases). Else, this method returns a formatted value for the
           p_language-specific part of a multilingual value.'''
        if Field.isEmptyValue(self, obj, value) and not showChanges: return ''
        res = value
        if self.isSelect:
            if isinstance(self.validator, Selection):
                # Value(s) come from a dynamic vocabulary
                val = self.validator
                if self.isMultiValued():
                    return [val.getText(obj, v, self, language=userLanguage) \
                            for v in value]
                else:
                    return val.getText(obj, value, self, language=userLanguage)
            else:
                # Value(s) come from a fixed vocabulary whose texts are in
                # i18n files.
                _ = obj.translate
                if self.isMultiValued():
                    res = [_('%s_list_%s' % (self.labelId, v), \
                             language=userLanguage) for v in value]
                else:
                    res = _('%s_list_%s' % (self.labelId, value), \
                            language=userLanguage)
        elif (self.format == String.XHTML) and showChanges:
            # Compute the successive changes that occurred on p_value
            res = self.getDiffValue(obj, res, language)
        elif self.format == String.TEXT:
            if layoutType in ('view', 'cell'):
                res = Escape.xhtml(res, p=True)
        # If value starts with a carriage return, add a space; else, it will
        # be ignored.
        if isinstance(res, basestring) and \
           (res.startswith('\n') or res.startswith('\r\n')): res = ' ' + res
        return res

    def getFormattedValue(self, obj, value, layoutType='view',
                          showChanges=False, language=None):
        '''Be careful: p_language represents the UI language, while "languages"
           below represents the content language(s) of this field. p_language
           can be used, ie, to translate a Selection value.'''
        languages = self.getAttribute(obj, 'languages')
        if (len(languages) == 1) or isinstance(value, basestring):
            return self.getUnilingualFormattedValue(obj, value, layoutType,
                     showChanges, userLanguage=language)
            # Normally, p_value should not be a string if there is a single
            # language. This can happen in exceptional cases, ie, in a
            # object's history (data change), when an object was transmitted
            # from one App1 to App2, where a field is unilingual in App1 and
            # multilingual in App2.
        # Return the dict of values whose individual, language-specific values
        # have been formatted via m_getUnilingualFormattedValue.
        if not value and not showChanges: return value
        res = {}
        for lg in languages:
            if not value: val = ''
            else: val = value[lg]
            res[lg] = self.getUnilingualFormattedValue(obj, val, layoutType,
                                                       showChanges, language=lg)
        return res

    def getShownValue(self, obj, value, layoutType='view',
                      showChanges=False, language=None):
        '''Be careful: p_language represents the UI language, while "languages"
           below represents the content language(s) of this field. For a
           multilingual field, this method only shows one specific language
           part.'''
        languages = self.getAttribute(obj, 'languages')
        if len(languages) == 1:
            return self.getUnilingualFormattedValue(obj, value, layoutType,
                                             showChanges, userLanguage=language)
        if not value: return value
        # Try to propose the part that is in the user language, or the part of
        # the first content language else.
        lg = obj.getUserLanguage()
        if lg not in value: lg = languages[0]
        return self.getUnilingualFormattedValue(obj, value[lg], layoutType,
                                                showChanges, language=lg)

    def getSearchValue(self, form):
        '''Potentially apply a transform to search value in p_form'''
        r = Field.getSearchValue(self, form)
        if r and self.transform:
            r = self.applyTransform(r)
        return r

    def getSortValue(self, obj):
        '''Return the value of p_self on p_obj that must be used for sorting.
           While the raw p_value may be the value to use in most cases, it is
           not always true. For example, a string like "Gaëtan" could have
           "gaetan" as sort value.'''
        r = self.getValue(obj)
        if self.format == String.LINE:
            # Normalize the value
            r = sutils.normalizeText(r, dash=False, space=False)
        return r

    def getPlaceholder(self, obj):
        '''Returns a placeholder for the field if defined'''
        res = self.getAttribute(obj, 'placeholder') or ''
        if res == True:
            # A placeholder must be set, but we have no value. In this case, we
            # take the field label.
            res = obj.translate(self.labelId)
        return res

    def extractText(self, value, lower=True, dash=False):
        '''Extracts pure text from XHTML p_value'''
        extractor = XhtmlTextExtractor(lower=lower, dash=dash,
                                       raiseOnError=False)
        return extractor.parse('<p>%s</p>' % value)

    def repair(self, obj):
        '''Checks whether this XHTML p_value is SAX-parsable. If not, try to
           remove illegal chars. The method returns True if the field content
           has been repaired.'''
        value = self.getValue(obj)
        if not value: return
        if not StringCleaner.isParsable(value):
            # Remove illegal chars
            new = StringCleaner.clean(value)
            if not StringCleaner.isParsable(new):
                # Still unparsable... try adding an ending p
                anew = new.strip() + '</p>'
                if not StringCleaner.isParsable(anew):
                    raise Exception(UNPARSABLE % new)
                else:
                    new = anew
            setattr(obj, self.name, new)
            return True

    def getIndexValue(self, obj, forSearch=False):
        '''Pure text must be extracted from rich content; multilingual content
           must be concatenated.'''
        # Must we produce an index value?
        if not self.getAttribute(obj, 'mustIndex'):
            return ValidValue.forString(None, forSearch)
        isXhtml = self.format == String.XHTML
        if self.isMultilingual(obj):
            res = self.getValue(obj)
            if res:
                vals = []
                for v in res.itervalues():
                    if isinstance(v, unicode): v = v.encode('utf-8')
                    if isXhtml: vals.append(self.extractText(v))
                    else: vals.append(v)
                res = ' '.join(vals)
        else:
            res = Field.getIndexValue(self, obj, forSearch)
            if res and isXhtml: res = self.extractText(res)
        return ValidValue.forString(res, forSearch)

    def getPossibleValues(self, obj, withTranslations=False,
                          withBlankValue=False, blankLabel=None, className=None,
                          ignoreMasterValues=False):
        '''Returns the list of possible values for this field (only for fields
           with self.isSelect=True). If p_withTranslations is True, instead of
           returning a list of string values, the result is a list of tuples
           (s_value, s_translation). Moreover, p_withTranslations can hold a
           given language: in this case, this language is used instead of the
           user language. If p_withBlankValue is True, a blank value is
           prepended to the list, excepted if the type is multivalued. Used in
           combination with p_withTranslations being True, the i18n label for
           translating the blank value is given in p_blankLabel. If p_className
           is given, p_obj is the tool and, if we need an instance of
           p_className, we will need to use p_obj.executeQuery to find one.'''
        if not self.isSelect: raise Exception('This field is not a selection.')
        # Get the user language for translations, from p_withTranslations
        lg = isinstance(withTranslations, str) and withTranslations or None
        req = obj.REQUEST
        master = self.master
        aobj = obj.appy()
        if not ignoreMasterValues and master and callable(self.masterValue):
            # This field is an ajax-updatable slave. Get the master value...
            if master.valueIsInRequest(obj, req):
                # ... from the request if available
                requestValue = master.getRequestValue(obj)
                masterValues = master.getStorableValue(obj, requestValue,
                                                       complete=True)
            elif not className:
                # ... or from the database if we are editing an object
                masterValues = master.getValue(obj)
            else:
                # We don't have any master value
                masterValues = None
            # Get possible values by calling self.masterValue
            if masterValues:
                values = self.masterValue(aobj, masterValues)
            else:
                values = []
            # Manage parameter p_withTranslations
            if not withTranslations: res = values
            else:
                res = []
                for v in values:
                    res.append((v, self.getFormattedValue(obj,v,language=lg)))
        else:
            # Get the possible values from attribute "validator"
            if isinstance(self.validator, Selection):
                # We need to call self.methodName for getting the (dynamic)
                # values. If methodName begins with _appy_, it is a special Appy
                # method: we will call it on the Mixin (=p_obj) directly. Else,
                # it is a user method: we will call it on the wrapper
                # (p_obj.appy()). Some args can be hidden into p_methodName,
                # separated with stars, like in this example: method1*arg1*arg2.
                # Only string params are supported.
                methodName = self.validator.methodName
                # Unwrap parameters if any.
                if methodName.find('*') != -1:
                    elems = methodName.split('*')
                    methodName = elems[0]
                    args = elems[1:]
                else:
                    args = ()
                # On what object must we call the method that will produce the
                # values?
                if methodName.startswith('tool:'):
                    obj = obj.getTool()
                    methodName = methodName[5:]
                else:
                    # We must call on p_obj. But if we have something in
                    # p_className, p_obj is the tool and not an instance of
                    # p_className as required. So find such an instance.
                    if className:
                        brains = obj.executeQuery(className, maxResults=1,
                                                  brainsOnly=True)
                        if brains:
                            obj = brains[0]._unrestrictedGetObject()
                # Do we need to call the method on the object or on the wrapper?
                if methodName.startswith('_appy_'):
                    exec 'res = obj.%s(*args)' % methodName
                else:
                    exec 'res = obj.appy().%s(*args)' % methodName
                if not withTranslations: res = [v[0] for v in res]
                elif isinstance(res, list): res = res[:]
            else:
                # The list of (static) values is directly given in
                # self.validator.
                res = []
                for value in self.validator:
                    label = '%s_list_%s' % (self.labelId, value)
                    if withTranslations:
                        res.append( (value, obj.translate(label, language=lg)) )
                    else:
                        res.append(value)
        if (withBlankValue == 'forced') or \
           (withBlankValue and not self.isMultiValued()):
            # Create the blank value to insert at the beginning of the list
            if withTranslations:
                label = blankLabel or self.noValueLabel
                blankValue = ('', obj.translate(label, language=lg))
            else:
                blankValue = ''
            # Insert the blank value in the result
            if isinstance(res, tuple):
                res = (blankValue,) + res
            else:
                res.insert(0, blankValue)
        return res

    def validateValue(self, obj, value):
        if self.format == String.CAPTCHA:
            challenge = obj.REQUEST.SESSION.get('captcha', None)
            # Compute the challenge minus the char to remove
            i = challenge['number']-1
            text = challenge['text'][:i] + challenge['text'][i+1:]
            if value != text:
                return obj.translate('bad_captcha')
        elif self.isSelect:
            # Check that the value is among possible values
            possibleValues = self.getPossibleValues(obj,ignoreMasterValues=True)
            if isinstance(value, basestring):
                error = value not in possibleValues
            else:
                error = False
                for v in value:
                    if v not in possibleValues:
                        error = True
                        break
            if error: return obj.translate('bad_select_value')

    def applyTransform(self, value):
        '''Applies a transform as required by self.transform on single
           value p_value.'''
        if self.transform in ('uppercase', 'lowercase'):
            # For those transforms, I will remove any accent, because, most of
            # the time, if the user wants to apply such effect, it is for ease
            # of data manipulation, so I guess without accent.
            value = sutils.normalizeString(value, usage='noAccents')
        # Apply the transform
        method = String.transformMethods.get(self.transform)
        if method:
            exec 'value = value.%s()' % method
        return value

    def getTextareaStyle(self):
        '''When this widget must be rendered as an HTML field of type
           "textarea", get the content of its "style" attribute.'''
        r = 'text-transform:%s' % self.transform
        if isinstance(self.width, str):
            # The field width must be expressed here and we do not use
            # attribute "cols".
            r += ';width:%s' % self.width
        return r

    def getTextareaCols(self):
        '''When this widget must be rendered as an HTML field of type
           "textarea", get the content of its "cols" attribute.'''
        # Use this attribute only if width is expressed as an integer value
        return isinstance(self.width, int) and self.width or ''

    def getUnilingualStorableValue(self, obj, value):
        isString = isinstance(value, basestring)
        isEmpty = Field.isEmptyValue(self, obj, value)
        # Apply transform if required
        if isString and not isEmpty:
           value = self.applyTransform(value)
        # Clean XHTML strings
        if not isEmpty and (self.format == String.XHTML):
            # When image upload is allowed, ckeditor inserts some "style" attrs
            # (ie for image size when images are resized). So in this case we
            # can't remove style-related information.
            try:
                value = XhtmlCleaner().clean(value)
            except XhtmlCleaner.Error, e:
                # Errors while parsing p_value can't prevent the user from
                # storing it.
                pass
        # Clean TEXT strings
        if not isEmpty and (self.format == String.TEXT):
            value = value.replace('\r', '')
        # Truncate the result if longer than self.maxChars
        if isString and self.maxChars and (len(value) > self.maxChars):
            value = obj.getTool().truncateValue(value, width=self.maxChars)
        # Get a multivalued value if required
        if value and self.isMultiValued() and \
           (type(value) not in sutils.sequenceTypes):
            value = [value]
        return value

    def getStorableValue(self, obj, value, complete=False):
        # If no object is passed, assume the field is unilingual
        if obj is None:
            return self.getUnilingualStorableValue(obj, value)
        # Check unilinguality
        languages = self.getAttribute(obj, 'languages')
        if len(languages) == 1:
            return self.getUnilingualStorableValue(obj, value)
        # A multilingual value is stored as a dict whose keys are ISO 2-letters
        # language codes and whose values are strings storing content in the
        # language ~{s_language: s_content}~.
        if not value: return
        for lg in languages:
            value[lg] = self.getUnilingualStorableValue(obj, value[lg])
        return value

    def store(self, obj, value):
        '''Stores p_value on p_obj for this field'''
        languages = self.getAttribute(obj, 'languages')
        if (len(languages) > 1) and value and \
           (not isinstance(value, dict) or (len(value) != len(languages))):
            raise Exception('Multilingual field "%s" accepts a dict whose '\
                            'keys are in field.languages and whose ' \
                            'values are strings.' % self.name)
        Field.store(self, obj, value)

    def storeFromAjax(self, obj):
        '''Stores the new field value from an Ajax request, or do nothing if
           the action was canceled.'''
        rq = obj.REQUEST
        if rq.get('cancel') == 'True': return
        requestValue = rq['fieldContent']
        # Remember previous value if the field is historized
        isHistorized = self.getAttribute(obj, 'historized')
        previousData = None
        if isHistorized: previousData = obj.rememberPreviousData(self)
        if self.isMultilingual(obj):
            if isHistorized:
                # We take a copy of previousData because it is mutable (dict)
                prevData = previousData[self.name]
                if prevData != None: prevData = prevData.copy()
                previousData[self.name] = prevData
            # We get a partial value, for one language only
            language = rq['languageOnly']
            v = self.getUnilingualStorableValue(obj, requestValue)
            getattr(obj.aq_base, self.name)[language] = v
            part = ' (%s)' % language
        else:
            self.store(obj, self.getStorableValue(obj, requestValue))
            part = ''
        # Update the object history when relevant
        if isHistorized and previousData: obj.historizeData(previousData)
        # Update obj's last modification date
        from DateTime import DateTime
        obj.modified = DateTime()
        obj.reindex()
        obj.log('ajax-edited %s%s on %s.' % (self.name, part, obj.id))

    def getIndexType(self):
        '''Index type varies depending on String parameters.'''
        # If String.isSelect, be it multivalued or not, we define a ListIndex:
        # this way we can use AND/OR operator.
        if self.isSelect:
            return 'ListIndex'
        elif self.format == String.TEXT:
            return 'TextIndex'
        elif self.format == String.XHTML:
            return 'XhtmlIndex'
        return Field.getIndexType(self)

    def getJs(self, obj, layoutType, res, config):
        if self.format == String.XHTML and layoutType in ('edit', 'view'):
            # Compute the URL to ckeditor CDN
            ckUrl = String.cdnUrl % (config.ckVersion, config.ckDistribution)
            if ckUrl not in res: res.append(ckUrl)

    def getCaptchaChallenge(self, session, minLength=5, maxLength=9):
        '''Returns a Captcha challenge in the form of a dict. At key "text",
           value is a string that the user will be required to re-type, but
           without 1 character whose position is at key "number". The challenge
           is stored in the p_session, for the server-side subsequent check.'''
        # The challenge the user needs to type (minus one char)
        challenge = sutils.PasswordGenerator.get(minLength=minLength,
                                                 maxLength=maxLength)
        # Compute the position of the char to remove
        number = random.randint(1, len(challenge))
        r = {'text': challenge, 'number': number}
        session['captcha'] = r
        return r

    def generatePassword(self, maxLength=9):
        '''Generates a password (we recycle here the captcha challenge
           generator).'''
        return sutils.PasswordGenerator.get(maxLength=maxLength)

    ckLanguages = {'en': 'en_US', 'pt': 'pt_BR', 'da': 'da_DK', 'nl': 'nl_NL',
                   'fi': 'fi_FI', 'fr': 'fr_FR', 'de': 'de_DE', 'el': 'el_GR',
                   'it': 'it_IT', 'nb': 'nb_NO', 'pt': 'pt_PT', 'es': 'es_ES',
                   'sv': 'sv_SE'}
    def getCkLanguage(self, obj, language):
        '''Gets the language for CK editor SCAYT. p_language is one of
           self.languages if the field is multilingual, None else. If p_language
           is not supported by CK, we use english.'''
        if not language:
            language = self.getAttribute(obj, 'languages')[0]
        if language in self.ckLanguages: return self.ckLanguages[language]
        return 'en_US'

    def getCkParams(self, obj, language):
        '''Gets the base params to set on a rich text field'''
        tool = obj.getTool()
        base = tool.getSiteUrl()
        ckAttrs = {'customConfig': '%s/ui/ckeditor/config.js' % base,
                   'contentsCss': '%s/ui/ckeditor/contents.css' % base,
                   'stylesSet': '%s/ui/ckeditor/styles.js' % base,
                   'toolbar': self.toolbar, 'format_tags':';'.join(self.styles),
                   'scayt_sLang': self.getCkLanguage(obj, language)}
        if self.width: ckAttrs['width'] = self.width
        if self.height: ckAttrs['height'] = self.height
        if self.spellcheck: ckAttrs['scayt_autoStartup'] = True
        # Add custom styles
        if self.customStyles:
            for style in self.customStyles:
                id = style['id']
                ckAttrs['format_%s' % id] = style
                ckAttrs['format_tags'] += ';%s' % id
        if self.allowImageUpload:
            ckAttrs['filebrowserUploadUrl'] = '%s/upload' % obj.absolute_url()
        if not tool.getUser().has_role('Manager'):
            ckAttrs['removeButtons'] = 'Source'
        ck = []
        for k, v in ckAttrs.iteritems():
            if isinstance(v, int): sv = str(v)
            elif isinstance(v, bool): sv = str(v).lower()
            elif isinstance(v, dict): sv = str(v)
            else: sv = '"%s"' % v
            ck.append('%s: %s' % (k, sv))
        return ', '.join(ck)

    def getJsInit(self, obj, language):
        '''Gets the Javascript init code for displaying a rich editor for this
           field (rich field only). If the field is multilingual, we must init
           the rich text editor for a given p_language (among self.languages).
           Else, p_languages is None.'''
        name = not language and self.name or ('%s_%s' % (self.name, language))
        return 'CKEDITOR.replace("%s", {%s})' % \
               (name, self.getCkParams(obj, language))

    def getJsInlineInit(self, obj, name, language):
        '''Gets the Javascript init code for enabling inline edition of this
           field (rich text only). If the field is multilingual, the current
           p_language is given and p_name includes it. Else, p_language is
           None.'''
        id = obj.id
        fieldName = language and name.rsplit('_',1)[0] or name
        lg = language or ''
        return "CKEDITOR.disableAutoInline = true;\n" \
               "CKEDITOR.inline('%s_%s_ck', {%s, on: {blur: " \
               "function( event ) { var content = event.editor.getData(); " \
               "doInlineSave('%s','%s','%s','view',true,content,'%s')}}})" % \
               (id, name, self.getCkParams(obj, language), id, fieldName,
                obj.absolute_url(), lg)

    def isSelected(self, obj, fieldName, vocabValue, dbValue):
        '''When displaying a selection box (only for fields with a validator
           being a list), must the _vocabValue appear as selected? p_fieldName
           is given and used instead of field.name because it may be a a fake
           name containing a row number from a field within a list field.'''
        rq = obj.REQUEST
        # Get the value we must compare (from request or from database)
        if rq.has_key(fieldName):
            compValue = rq.get(fieldName)
        else:
            compValue = dbValue
        # Compare the value
        if type(compValue) in sutils.sequenceTypes:
            return vocabValue in compValue
        return vocabValue == compValue
# ------------------------------------------------------------------------------
