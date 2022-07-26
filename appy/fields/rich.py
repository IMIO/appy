# -*- coding: utf-8 -*-
# ~license~

# ------------------------------------------------------------------------------
import sys

from appy.px import Px
from appy.fields import Field
from appy.gen.layout import Layouts
from appy.shared.diff import HtmlDiff
from appy.shared.xml_parser import XhtmlCleaner
from appy.fields.multilingual import Multilingual
from appy.gen.indexer import XhtmlTextExtractor, ValidValue

# ------------------------------------------------------------------------------
NOT_IMPLEMENTED = 'This feature is not implemented yet'

# ------------------------------------------------------------------------------
class Rich(Multilingual, Field):
    '''Field allowing to encode a "rich" text, based on XHTML and external
       editor "ckeditor".'''

    # Required Javascript files
    cdnUrl = '//cdn.ckeditor.com/%s/%s/ckeditor.js'

    # Use this constant to say that there is no maximum size for a string field
    NO_MAX = sys.maxint

    # Default ways to render multilingual fields
    defaultLanguagesLayouts = {
      'edit': 'horizontal', 'view': 'horizontal', 'cell': 'vertical'}

    # Override this dict, defined at the Multilingual level
    lgTop = {'view': 1, 'edit': 1}

    # Default styles to use
    defaultStyles = ('p', 'h1', 'h2', 'h3', 'h4')

    # Default custom style, allowing to produce, in POD results, a page break
    # just after the paragraph having this style.
    customStyles = [{'id': 'div', 'element': 'div',
                     'attributes': {'style': 'page-break-after:always'}}]

    # Unilingual pxView and pxCell
    pxViewUni = pxCellUni = Px('''
     <x var="inlineEdit=field.getAttribute(obj, 'inlineEdit');
             mayAjaxEdit=inlineEdit and (layoutType != 'cell') and not \
                         showChanges and zobj.mayEdit(field.writePermission)">
      <div if="not mayAjaxEdit" class="xhtml">::value or '-'</div>
      <x if="mayAjaxEdit" var2="name=lg and ('%s_%s' % (name, lg)) or name">
       <div class="xhtml" contenteditable="true"
            id=":'%s_%s_ck' % (zobj.id, name)">::value or '-'</div>
       <script if="mayAjaxEdit">::field.getJsInlineInit(zobj, name, lg)</script>
      </x>
     </x>''')

    # Unilingual pxEdit
    pxEditUni = Px('''
     <textarea var="inputId=not lg and name or '%s_%s' % (name, lg)"
       id=":inputId" name=":inputId" cols=":field.getTextareaCols()"
       style=":field.getTextareaStyle()"
       rows=":field.height">:field.getInputValue(inRequest, requestValue, value)
     </textarea>
     <script>::field.getJsInit(zobj, lg)</script>''')

    pxSearch = Px('''
     <input type="text" maxlength=":field.maxChars" size=":field.swidth"
            value=":field.sdefault" name=":widgetName"/>''')

    def __init__(self, validator=None, multiplicity=(0,1), default=None,
      defaultOnEdit=None, show=True, page='main', group=None, layouts=None,
      move=0, indexed=False, mustIndex=True, indexValue=None, searchable=False,
      specificReadPermission=False, specificWritePermission=False, width=None,
      height=None, maxChars=None, colspan=1, master=None, masterValue=None,
      focus=False, historized=False, mapping=None, generateLabel=None,
      label=None, sdefault='', scolspan=1, swidth=None, sheight=None,
      persist=True, styles=defaultStyles, customStyles=None,
      allowImageUpload=False, spellcheck=False, languages=('en',),
      languagesLayouts=None, inlineEdit=False, toolbar='Standard', view=None,
      cell=None, edit=None, xml=None, translations=None):
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
        self.customStyles = customStyles or Rich.customStyles
        # Do we allow the user to upload images in it ?
        self.allowImageUpload = allowImageUpload
        if allowImageUpload: raise Exception(NOT_IMPLEMENTED)
        # Do we run the CK spellchecker ?
        self.spellcheck = spellcheck
        # What toolbar is used ? Possible values are "Standard" or "Simple"
        self.toolbar = toolbar
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
        # Call the base constructor
        Field.__init__(self, validator, multiplicity, default, defaultOnEdit,
          show, page, group, layouts, move, indexed, mustIndex, indexValue,
          searchable, specificReadPermission, specificWritePermission, width,
          height, maxChars, colspan, master, masterValue, focus, historized,
          mapping, generateLabel, label, sdefault, scolspan, swidth, sheight,
          persist, inlineEdit, view, cell, edit, xml, translations)
        # No max chars by default
        if maxChars is None:
            self.maxChars = Rich.NO_MAX

    def getDefaultLayouts(self):
        '''Returns the default layouts for a rich field'''
        # Is this field in a grid-style group ?
        inGrid = self.inGrid()
        if self.historized:
            # self.historized can be a method or a boolean. If it is a method,
            # it means that under some condition, historization will be enabled.
            # So we come here also in this case.
            r = inGrid and 'gc' or 'c'
        else:
            r = inGrid and 'g' or 'b'
        return getattr(Layouts.Rich, r)

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

    def getUniFormattedValue(self, obj, value, layoutType='view',
          showChanges=False, userLanguage=None, language=None):
        '''If no p_language is specified, this method is called by
           m_getFormattedValue for getting a non-multilingual value (ie, in
           most cases). Else, this method returns a formatted value for the
           p_language-specific part of a multilingual value.'''
        if Field.isEmptyValue(self, obj, value) and not showChanges: return ''
        r = value
        if showChanges:
            # Compute the successive changes that occurred on p_value
            r = self.getDiffValue(obj, r, language)
        return r

    def extractText(self, value, lower=True, dash=False):
        '''Extracts pure text from XHTML p_value'''
        extractor = XhtmlTextExtractor(lower=lower, dash=dash,
                                       raiseOnError=False)
        return extractor.parse('<p>%s</p>' % value)

    def getUniIndexValue(self, obj, value, forSearch):
        '''Gets the value to index for unilingual value p_value'''
        return self.extractText(value) or ''

    def getUniStorableValue(self, obj, value):
        '''Gets the p_value as can be stored in the database within p_obj'''
        if not value: return value
        # Clean the value. When image upload is allowed, ckeditor inserts some
        # "style" attrs (ie for image size when images are resized). So in this
        # case we can't remove style-related information.
        try:
            value = XhtmlCleaner().clean(value)
        except XhtmlCleaner.Error, e:
            # Errors while parsing p_value can't prevent the user from storing
            # it.
            pass
        # Manage maxChars
        max = self.maxChars
        if max and (len(value) > max): value = value[:max]
        return value

    def getIndexType(self): return 'XhtmlIndex'

    def getTextareaStyle(self):
        '''On "edit", get the content of textarea's "style" attribute'''
        # If the width is expressed as a string, the field width must be
        # expressed in attribute "style" (so returned by this method) and not
        # via attribute "cols" (returned by m_getTextareaCols below).
        return isinstance(self.width, str) and ('width:%s' % self.width) or ''

    def getTextareaCols(self):
        '''When this widget must be rendered as an HTML field of type
           "textarea", get the content of its "cols" attribute.'''
        # Use this attribute only if width is expressed as an integer value
        return isinstance(self.width, int) and self.width or ''

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

    def getJs(self, obj, layoutType, r, config):
        if layoutType not in ('edit', 'view'): return
        # Compute the URL to ckeditor CDN
        ckUrl = Rich.cdnUrl % (config.ckVersion, config.ckDistribution)
        if ckUrl not in r: r.append(ckUrl)

    def getJsInit(self, obj, language):
        '''Gets the Javascript init code for displaying ckeditor for this field.
           If the field is multilingual, we must init the rich text editor for a
           given p_language (among self.languages). Else, p_languages is
           None.'''
        name = not language and self.name or ('%s_%s' % (self.name, language))
        return 'CKEDITOR.replace("%s", {%s})' % \
               (name, self.getCkParams(obj, language))

    def getJsInlineInit(self, obj, name, language):
        '''Gets the Javascript init code for enabling inline edition of this
           field If the field is multilingual, the current p_language is given
           and p_name includes it. Else, p_language is None.'''
        id = obj.id
        fieldName = language and name.rsplit('_',1)[0] or name
        lg = language or ''
        return "CKEDITOR.disableAutoInline = true;\n" \
               "CKEDITOR.inline('%s_%s_ck', {%s, on: {blur: " \
               "function( event ) { var content = event.editor.getData(); " \
               "doInlineSave('%s','%s','%s','view',true,content,'%s')}}})" % \
               (id, name, self.getCkParams(obj, language), id, fieldName,
                obj.absolute_url(), lg)
# ------------------------------------------------------------------------------
