# -*- coding: utf-8 -*-
# ~license~
# ------------------------------------------------------------------------------
from appy.px import Px
from appy.fields import Field
from appy.gen.indexer import ValidValue

# ------------------------------------------------------------------------------
INVALID_MULTILINGUAL_VALUE = 'Multilingual field "%s" accepts a dict whose ' \
  'keys are in field.languages and whose values are strings.'

# ------------------------------------------------------------------------------
class Multilingual:
    '''Mixin class injected into any Field whose content can be multilingual'''

    # Default values to render when field values are empty
    emptyDefault = {'view': '-', 'edit': '', 'cell': ''}
    # Default top space (in pixels) to apply in pxLanguage
    lgTop = {'view': 1, 'edit': 3, 'cell': 3}

    # Note that multilinguality is a dynamic feature: field values can be
    # unilingual or multilingual, depending on some condition on the container
    # object itself, or on some site-specific configuration.

    # PX displaying the language code and name besides the part of the
    # multilingual field storing content in this language.
    pxLanguage = Px('''
     <td style=":'padding-top:%dpx' % field.lgTop[layoutType]" width="25px">
      <span class="language help"
            title=":ztool.getLanguageName(lg)">:lg.upper()</span>
     </td>''')

    # PX acting as a substitute for the field pxView. This PX determines if the
    # field content is multilingual or not. If the field is unilingual, it
    # simply calls a PX named "px<layoutType>Uni" on the field. Else, it renders
    # such a PX for every supported language, calling "px<layoutType>Uni" for
    # every language, and assembling the result according to the "languages
    # layout". The "Uni-" PX receives the current language as variable "lg". If
    # the field is unilingual, the received "lg" variable is None.
    pxView = pxEdit = pxCell = Px('''
     <x var="languages=field.getAttribute(obj, 'languages');
             multilingual=len(languages) &gt; 1;
             pxUni=getattr(field, 'px%sUni' % layoutType.capitalize())">

      <!-- Display the uni-lingual version of the field -->
      <x if="not multilingual" var2="lg=None">:pxUni</x>

      <!-- Display the multi-lingual version of the field -->
      <x if="multilingual"
         var2="languageLayout=field.getLanguagesLayout(layoutType)">

       <!-- Horizontally-layouted multilingual field -->
       <table if="languageLayout == 'horizontal'" width="100%"
              class=":(layoutType == 'cell') and 'no' or ''"
              var="count=len(languages)">
        <tr valign="top"><x for="lg in languages"><x>:field.pxLanguage</x>
         <td width=":'%d%%' % int(100.0/count)"
             var="requestValue=requestValue[lg]|None;
                  value=value[lg]|field.emptyDefault[layoutType]">:pxUni</td>
        </x></tr></table>

       <!-- Vertically-layouted multilingual field -->
       <table if="languageLayout == 'vertical'"
              class=":(layoutType == 'cell') and 'no' or ''">
        <tr valign="top" height="20px" for="lg in languages">
         <x>:field.pxLanguage</x>
         <td var="requestValue=requestValue[lg]|None;
                  value=value[lg]|field.emptyDefault[layoutType]">:pxUni</td>
       </tr></table>
      </x>
     </x>''')

    def __init__(self, languages, languagesLayouts):
        '''Inject multilingual-specific attributes on p_self'''
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

    def isMultilingual(self, obj, dontKnow=False):
        '''Is this field multilingual ? If we don't know, say p_dontKnow'''
        if not obj:
            if callable(self.languages):
                # In that case, it is impossible to know
                return dontKnow
            else: return len(self.languages) > 1
        return len(self.getAttribute(obj, 'languages')) > 1

    def getLanguagesLayout(self, layoutType):
        '''Gets the way to render a multilingual field on p_layoutType.'''
        if self.languagesLayouts and (layoutType in self.languagesLayouts):
            return self.languagesLayouts[layoutType]
        # Else, return a default value that depends of the format
        return self.defaultLanguagesLayouts[layoutType]

    def getCopyValue(self, obj):
        '''A value being multilingual is stored in a dict. For such a value,
           standard method Field.getCopyValue must return a distinct copy of the
           value as stored on p_obj.'''
        r = self.getValue(obj)
        if isinstance(r, dict): r = r.copy()
        return r

    def valueIsInRequest(self, obj, request, name=None, layoutType='view'):
        '''Multilingual values are stored in specific input fields with
           specific names.'''
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
        r = {}
        for language in languages:
            r[language] = request.get('%s_%s' % (name, language), None)
        return r

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

    def getFormattedValue(self, obj, value, layoutType='view',
                          showChanges=False, language=None):
        '''The multilingual and unilingual variants of p_value's formatted
           version differ.'''
        # Note that p_language represents the UI language, while variable
        # "languages" below represents the content language(s) of this field.
        languages = self.getAttribute(obj, 'languages')
        uni = self.getUniFormattedValue
        if (len(languages) == 1) or isinstance(value, basestring):
            # Normally, p_value should not be a string if there is a single
            # language. This can happen in exceptional cases, ie, in a
            # object's history (data change), when an object was transmitted
            # from one App1 to App2, where a field is unilingual in App1 and
            # multilingual in App2.
            return uni(obj, value, layoutType,
                       showChanges, userLanguage=language)
        # Return the dict of values whose individual, language-specific values
        # have been formatted via m_getUniFormattedValue.
        if not value and not showChanges: return value
        r = {}
        for lg in languages:
            if not value: val = ''
            else: val = value[lg]
            r[lg] = uni(obj, val, layoutType, showChanges, language=lg)
        return r

    def getShownValue(self, obj, value, layoutType='view',
                      showChanges=False, language=None):
        '''For a multilingual field, this method only shows one specific
           language part.'''
        # Be careful: p_language represents the UI language, while variable
        # "languages" below represents the content language(s) of this field.
        languages = self.getAttribute(obj, 'languages')
        uni = self.getUniFormattedValue
        if len(languages) == 1:
            return uni(obj, value, layoutType,
                       showChanges, userLanguage=language)
        if not value: return value
        # Try to propose the part that is in the user language, or the part of
        # the first content language else.
        lg = obj.getUserLanguage()
        if lg not in value: lg = languages[0]
        return uni(obj, value[lg], layoutType, showChanges, language=lg)

    def getIndexValue(self, obj, forSearch=False):
        '''Multilingual content must be concatenated into a single value to be
           indexed.'''
        # Must we produce an index value?
        if not self.getAttribute(obj, 'mustIndex'):
            return ValidValue.forString(None, forSearch)
        # Get the field value on p_obj
        r = self.getValue(obj)
        # Possibly transform the value
        if self.indexValue: r = self.indexValue(obj.appy(), r)
        # Manage multilinguality
        if isinstance(r, dict):
            r = ' '.join([self.getUniIndexValue(obj, v, forSearch) \
                          for v in r.itervalues()])
        else:
            r = self.getUniIndexValue(obj, r, forSearch)
        return ValidValue.forString(r, forSearch)

    def getStorableValue(self, obj, value, complete=False):
        languages = self.getAttribute(obj, 'languages')
        if len(languages) == 1:
            return self.getUniStorableValue(obj, value)
        # A multilingual value is stored as a dict whose keys are ISO 2-letters
        # language codes and whose values are strings storing content in the
        # language ~{s_language: s_content}~.
        if not value: return
        for lg in languages:
            value[lg] = self.getUniStorableValue(obj, value[lg])
        return value

    def store(self, obj, value):
        '''Stores p_value on p_obj for this field'''
        languages = self.getAttribute(obj, 'languages')
        if (len(languages) > 1) and value and \
           (not isinstance(value, dict) or (len(value) != len(languages))):
            raise Exception(INVALID_MULTILINGUAL_VALUE % self.name)
        Field.store(self, obj, value)

    def storeValueFromAjax(self, obj, value, previousData):
        '''Stores p_value on p_obj, taking care of multilinguality'''
        # Call the base method if p_self is not multilingual
        if not self.isMultilingual(obj):
            return Field.storeValueFromAjax(self, obj, value, previousData)
        # Manage a multilingual field
        if previousData is not None:
            # Take a copy of previousData because it is mutable (dict)
            prevData = previousData[self.name]
            if prevData is not None: prevData = prevData.copy()
            previousData[self.name] = prevData
        # We get a partial value, for one language only
        language = obj.REQUEST['languageOnly']
        v = self.getUniStorableValue(obj, value)
        getattr(obj.aq_base, self.name)[language] = v
        return ' (%s)' % language
# ------------------------------------------------------------------------------
