# -*- coding: utf-8 -*-

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.px import Px
from appy.xml.cleaner import Cleaner
from appy.model.fields.rich import Rich
from appy.utils import string as sutils
from appy.pod.xhtml2odt import XhtmlPreprocessor

#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class AutoCorrect:
    '''Defines the set of automatic corrections that will occur as you type in a
       poor field.'''

    # Standard replacements: chars being prefixed with a nbsp
    standard = {}

    # Chars that must be prefixed with a non-breakable space
    nbPrefixed = (':', ';', '!', '?', '%')
    for char in nbPrefixed:
        standard[char] = [('text', ' %s' % char)]

    # Replace double quotes by "guillemets" (angle quotes)
    quotes = {'"': {'if':'blankBefore',
                    1: [('text', '« ')],
                    0: [('text', ' »')]}}

    def __init__(self, standard=True, quotes=True):
        '''Produces a specific auto-correct configuration'''
        r = {}
        if standard: r.update(AutoCorrect.standard)
        if quotes:   r.update(AutoCorrect.quotes)
        self.chars = r

    def inJs(self, toolbarId):
        '''Get the JS code allowing to define p_self.chars on the DOM node
           representing the poor toolbar.'''
        return "document.getElementById('%s').autoCorrect=%s;" % \
               (toolbarId, sutils.getStringFrom(self.chars))

# Default AutoCorrect configuration
AutoCorrect.default = AutoCorrect()

#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Icon:
    '''An icon from the toolbar'''

    def __init__(self, name, type, label=None, icon=None, data=None, args=None,
                 shortcut=None):
        # A short, unique name for the icon
        self.name = name
        # The following type of icons exist. Depending on the type, p_data
        # carries a specific type of information.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # p_type      | p_data
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "wrapper"   | the icon corresponds to a portion of text that will be
        #             | wrapped around some tag, using browser function
        #             | document.execCommand. p_data contains the command to
        #             | pass to this function.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "char"      | the icon corresponds to a char to insert into the field.
        #             | p_data is the char to insert.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "action"    | the icon corresponds to some action that is not
        #             | necessarily related to the field content. In that case,
        #             | p_data may be None or its sematincs may be specific to
        #             | the action.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "sentences" | a clic on the icon will display a menu containing
        #             | predefined sentences. Selecting one of them will inject
        #             | it in the target field, where the cursor is currently
        #             | set. In that case, p_data must hold the name of a
        #             | method that must exist on the current object. This
        #             | method will be called without arg and must return a list
        #             | of sentences, each one being a string.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.type = type
        # The i18n label for the icon's tooltip. Should include the keyboard
        # shortcut when present. If None, defaults to "icon_<name>"
        self.label = label or ('icon_%s' % name)
        # The name of the icon image on disk. If None, will be computed as
        # "icon_<name>.png".
        self.icon = icon or ('icon_%s' % name)
        # The data related to this icon, as described hereabove
        self.data = data
        # If p_data refers to a command, its optional args may be defined in
        # p_args.
        self.args = args
        # If a keyboard shortcut is tied to the icon, its key code is defined
        # here, as an integer. See JavasScript keycodes, https://keycode.info.
        self.shortcut = shortcut
        # Precompute this boolean
        self.isSentences = type == 'sentences'

    def asSentences(self, r, o):
        '''For an icon of type "sentences", wraps the icon into a div allowing
           to hook the sub-div containing the sentences, and add this latter.'''
        # For an icon of type "sentences", add a div containing the sentences
        sentences = []
        for sentence in getattr(o, self.data)():
            if not isinstance(sentence, str):
                # We have an additional, custom info to add besides the sentence
                # itself.
                sentence, info = sentence
            else:
                info = ''
            div = '<div class="sentence"><a class="clickable" ' \
                  'onmousedown="injectSentence(event)" ' \
                  'title="%s">%s</a>%s</div>' % \
                  (sentence, Px.truncateValue(sentence, width=65), info)
            sentences.append(div)
        # Add a warning message if no sentence has been found
        if not sentences:
            sentences.append('<div class="legend">%s</div>' % \
                             o.translate('no_sentence'))
        return '<div class="sentenceContainer" ' \
               'onmouseover="toggleDropdown(this) " ' \
               'onmouseout="toggleDropdown(this,\'none\')">%s' \
               '<div class="dropdown" style="display:none; width:350px">' \
               '%s</div></div>' % (r, '\n'.join(sentences))

    def get(self, o):
        '''Returns the HTML chunk representing this icon'''
        shortcut = str(self.shortcut) if self.shortcut else ''
        # Use event "mousedown" and not "onclick". That way, focus is kept on
        # the current poor. Else, if focus must be forced back to the poor, the
        # current position within it will be lost.
        onclick = 'onmousedown' if self.isSentences else 'onclick'
        r = '<img class="iconTB" src="%s" title="%s" name="%s"' \
            ' onmouseover="switchIconBack(this, true)"' \
            ' onmouseout="switchIconBack(this, false)"' \
            ' data-type="%s" data-data="%s" data-args="%s" ' \
            'data-shortcut="%s" %s="useIcon(this)"/>' % \
             (o.buildUrl(self.icon), o.translate(self.label), self.name,
              self.type, self.data or '', self.args or '', shortcut, onclick)
        # Add specific stuff if icon type is "sentences"
        if self.isSentences: r = self.asSentences(r, o)
        return r

# All available icons
Icon.all = [
  Icon('bold',      'wrapper', data='bold', shortcut=66),
  Icon('italic',    'wrapper', data='italic', shortcut=73),
  Icon('highlight', 'wrapper', data='hiliteColor', args='yellow', shortcut=72),
  Icon('unformat',  'wrapper', data='removeFormat', shortcut=77),
  # Insert a non-breaking space
  Icon('blank',     'char',    data=' ', shortcut=32),
  # Insert a non breaking dash
  Icon('dash',      'char',    data='‑', shortcut=54),
  Icon('bulleted',  'wrapper', data='insertUnorderedList'),
  Icon('sub',       'wrapper', data='subscript'),
  Icon('sup',       'wrapper', data='superscript'),
  # Increment the field height by <data>%
  Icon('lengthen',  'action',  data='30', shortcut=56)
]

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Poor(Rich):
    '''Field allowing to encode XHTML text'''

    # Make some classes available here
    Icon = Icon
    AutoCorrect = AutoCorrect

    # Unilingual view
    viewUni = cellUni = Px('''<div style=":field.getWidgetStyle(False)"
     class=":field.getAttribute(o, 'viewCss')">::field.getInlineEditableValue(o,
       value or '-', layout, name=name, language=lg)</div>''')

    # The toolbar
    pxToolbar = Px('''
     <x var="tbId=tbid|field.name + '_tb'">
      <div class="toolbar" id=":tbId">
       <x for="icon in field.Icon.all">::icon.get(o)</x>
       <!-- Add inline-edition icons when relevant -->
       <x if="hostLayout">:field.pxInlineActions</x>
      </div>
      <!-- Configure auto-correct -->
      <script if="field.autoCorrect">::field.autoCorrect.inJs(tbId)</script>
      <script>var nonCharCodes=[0,8,9,13,16,18,20,33,34,35,36,37,38,39,40,46,
                                219,225,229,255];</script>
     </x> ''',

     css = '''
      .toolbar { height: 24px; margin: 2px 0 }
      .sentenceContainer { position: relative; display: inline }
      .sentence { padding: 3px 0 }
      .iconTB { padding: 3px; border-width: 1px; border: 1px transparent solid }
      .iconTBSel { background-color: #dbdbdb; border-color: #909090 }
     ''',

     js='''
      class Surgeon {
        // Performs various DOM triturations

        static wrapNodes(nodes) {
          // Wrap this array of p_nodes into a "div" tag
          let r = document.createElement('div');
          for (const node of nodes) r.appendChild(node);
          return r;
        }

        static cutAt(range) {
          // Cut and return the tail of the current selection
          let current = range.startContainer, r=[];
          if (current.nodeType == Node.TEXT_NODE) {
            // Cut a TextNode in 2 pieces
            let i = range.startOffset,
                tail = current.substring(i);
            if (tail) {
              r.push(document.createTextNode(tail));
              current.data = current.data.substring(0, i);
            }
            current = current.parentNode;
          }
          else {
            // Cut a container tag whose child nodes are probably TextNodes
            let children = current.childNodes,
                i = children.length - 1,
                j = range.startOffset, child;
            while (i >= j) {
              child = current.removeChild(children[i]);
              r.unshift(child);
              i = i-1;
            }
          }
          // Position the cursor after the cut element
          range.setStartAfter(current);
          range.collapse(true);
          return r;
        }

        static insertAt(selection, range, node, moveAfter) {
          /* Inserts p_node at the position indicated by p_selection and
             p_range. If p_moveAfter is true, the cursor is moved to the end of
             the inserted node. */
          range.insertNode(node);
          if (moveAfter) range.setStartAfter(node);
          // Reinitialise the range
          range.collapse(true);
          selection.removeAllRanges();
          selection.addRange(range);
        }

        static inject(type, content, outer) {
          /* Inject, within the currently selected poor, an element of this
             p_type, with this p_content. Inject it where the cursor is
             currently positioned. If text is selected, it is removed. If
             p_outer is true, one or several paragraphs are inserted. */
          let sel = window.getSelection(),
              range = sel.getRangeAt(0),
              many = false, node;
          // Delete the currently selected text, if any
          if (!range.collapsed) range.deleteContents();
          // Create, when relevant, the element to insert
          if (type == 'text') { // Insert string p_content as a TextNode
            node = document.createTextNode(content);
          }
          else if (type == 'node') { // Insert the node passed in p_content
            node = content;
          }
          else if (type == 'array') { // Insert p_content = an array of nodes
            node = content;
            many = true;
          }
          else { // Create the node named p_type, with this p_content
            node = document.createElement(type);
            node.appendChild(document.createTextNode(content));
          }
          // Insert the element(s)
          node = (many)? node : [node];
          let first = true, paraTail;
          for (const nod of node) {
            if (first) {
              if (outer) {
                /* Cut the remaining of the current paragraph: it will be
                   reinserted after all nodes will have been inserted. */
                paraTail = Surgeon.cutAt(range);
              }
              first = false;
            }
            Surgeon.insertAt(sel, range, nod, true);
          }
          // Reinsert v_paraTail if present
          if (paraTail) {
            Surgeon.insertAt(sel, range, Surgeon.wrapNodes(paraTail), false);
          }
        }
      }

      getIconsMapping = function(toolbar) {
        // Gets a mapping containing toolbar icons, keyed by their shortcut
        var r = {}, icons=toolbar.getElementsByClassName('iconTB'), key;
        for (const icon of icons) {
          key = icon.getAttribute('data-shortcut');
          if (key) r[parseInt(key)] = icon;
        }
        return r;
      }

      linkToolbar = function(toolbarId, target) {
        /* Link the toolbar with its target div. Get the target div if not
           given in p_target. */
        if (!target) {
          var targetId=_rsplit(toolbarId, '_', 2)[0];
          target = document.getElementById(targetId + 'P');
        }
        var toolbar=document.getElementById(toolbarId);
        toolbar['target'] = target;
        target['toolbar'] = toolbar;
        target['icons'] = getIconsMapping(toolbar);
      }

      switchIconBack = function(icon, selected) {
        icon.className = (selected)? 'iconTB iconTBSel': 'iconTB';
      }

      lengthenDiv = function(div, percentage) {
        // Lengthen this p_div by some p_percentage
        var rate = 1 + (percentage / 100),
            height = parseInt(div.style.minHeight);
        // Apply the rate
        height = Math.ceil(height * rate);
        // Reinject the new height to the correct area property
        div.style.minHeight = String(height) + 'px';
      }

      useIcon = function(icon) {
        // Get the linked div (if already linked)
        let div = icon.parentNode['target'];
        if (!div) return;
        div.focus();
        let type=icon.getAttribute('data-type'),
            data=icon.getAttribute('data-data'),
            args=icon.getAttribute('data-args') || null;
        if (type == 'wrapper') {
          // Wrap the selected text via the command specified in v_data
          document.execCommand(data, false, args);
        }
        else if (type == 'char') {
          // Insert a (sequence of) char(s) into the text
          Surgeon.inject('text', data);
        }
        else if (type == 'action') {
          // Actions
          if (icon.name == 'lengthen') lengthenDiv(div, parseInt(data));
        }
      }

      setCaret = function(div) {
        // Ensure the caret is correctly positioned before encoding text
        let sel = window.getSelection(),
            range = sel.getRangeAt(0),
            current = range.startContainer;
        if (current == div) {
          /* Structural problem: an empty para must be created and the caret
             must be positioned inside it. As a preamble, remove any silly br
             that would be present. */
          let child;
          for (let i=div.childNodes.length-1; i>=0; i--) {
            child = div.childNodes[i];
            if (child.tagName === 'BR') div.removeChild(child);
          }
          let para = document.createElement('div'),
              text = para.appendChild(document.createTextNode(''));
          div.appendChild(para);
          range.setStart(text, 0);
          range.collapse(true);
          sel.removeAllRanges();
          sel.addRange(range);
        }
      }

      blankBefore = function(div) {
        /* Returns true if there is a blank (or nothing) before the currently
           selected char within p_div. */
        const sel = window.getSelection(),
              range = sel.getRangeAt(0),
              offset = range.startOffset;
        if (offset == 0) return true;
        let container = range.startContainer, prev;
        if (container.nodeType == Node.TEXT_NODE) {
          prev = container.textContent[offset-1];
        }
        else {
          prev = container.childNodes[offset-1].data.slice(-1);
        }
        return (prev === ' ') || (prev === ' '); // Breaking and non-breaking
      }

      applyAutoCorrect = function(div, nodes) {
        /* Apply an auto-correction by injecting these p_nodes into p_div, at
           the current cursor position. */
        if ('if' in nodes) {
          // The replacement to choose depends on a condition
          let condition = eval(nodes['if'])(div),
              key = (condition)? 1: 0;
          applyAutoCorrect(div, nodes[key]);
        }
        else {
          for (const node of nodes) Surgeon.inject(node[0], node[1]);
        }
      }

      // Triggered when the user hits a key in a poor
      onPoorKeyDown = function(event) {
        // Block change observation and manage this change ourselves
        let div = event.target;
        if (event.ctrlKey || (event.altKey && event.keyCode == 32)) {
          /* Manage keyboard shortcuts. Key "alt" is allowed as alternative to
             "ctrl" when hitting "space" (32) (for Mac users). */
          if (event.keyCode in div['icons']) {
            // Perform the icon's action
            setCaret(div);
            useIcon(div['icons'][event.keyCode]);
            event.preventDefault();
          }
        }
        else {
          if (!nonCharCodes.includes(event.keyCode)) {
            // Ensure the caret is at a correct place for inserting text
            setCaret(div);
            // Perform auto-correction when relevant
            let autoCorrect = div['toolbar'].autoCorrect;
            if (autoCorrect && event.key in autoCorrect) {
              // Insert the replacement nodes instead of this char
              applyAutoCorrect(div, autoCorrect[event.key]);
              event.preventDefault();
            }
            else if (!event.isComposing) {
              Surgeon.inject('text', event.key);
              event.preventDefault();
            }
          }
        }
      }

      injectSentence = function(event) {
        let tag = event.target;
        // Close the dropdown
        let dropdown = tag.parentNode.parentNode;
        dropdown.style.display = 'none';
        // Find the corresponding poor
        let div = dropdown.parentNode.parentNode['target'];
        if (!div) return;
        div.focus();
        // Inject the sentence in it
        Surgeon.inject('text', tag.title);
        event.preventDefault();
      }

      // Insert pasted data into a poor field
      getPastedData = function(event) {
        // Prevent data to be directly injected
        event.stopPropagation();
        event.preventDefault();
        // Get pasted data via the clipboard API
        let clipboardData = event.clipboardData || window.clipboardData,
            pastedData = clipboardData.getData('Text');
        if (!pastedData) return;
        // Split v_pastedData into paragraphs
        let paras = pastedData.split('\\n'),
            para = paras.shift();
        /* For the first paragraph, if we are at the root of the (empty)
           contenteditable zone, wrap it in a paragraph. Else, inject text in
           the current paragraph. */
        console.log('Contenteditable ? ' + event.target.getAttribute('contenteditable'));
        if (event.target.getAttribute('contenteditable') === 'true') {
            setCaret(event.target);
        }
        Surgeon.inject('text', para);
        // Insert the next lines as "div" tags
        if (paras.length > 0) {
          // Replace every paragraph with a "div" tag
          for (let i=0; i < paras.length; i++) {
            para = document.createElement('div');
            para.appendChild(document.createTextNode(paras[i]));
            paras[i] = para;
          }
          Surgeon.inject('array', paras, true);
        }
      }''')

    # Buttons for saving or canceling while inline-editing the field, rendered
    # within its toolbar.

    pxInlineActions = Px('''
      <div var="inToolbar=showToolbar and hostLayout;
                align='left' if inToolbar else 'right';
                fdir='row' if inToolbar else 'column'"
           style=":'float:%s;display:flex;flex-direction:%s' % (align, fdir)">
       <div>
        <img id=":'%s_save' % pid" src=":svg('saveS')"
             class=":'iconS %s' % ('clickable' if inToolbar else 'inlineIcon')"
             title=":_('object_save')"/></div>
       <div>
        <img id=":'%s_cancel' % pid" src=":svg('cancelS')"
             class=":'iconS %s' % ('clickable' if inToolbar else 'inlineIcon')"
             title=":_('object_cancel')"/></div>
      </div>
      <script>:'prepareForAjaxSave(%s,%s,%s,%s)' % \
               (q(name), q(o.iid), q(o.url), q(hostLayout))</script>''')

    # Unilingual edit
    editUni = Px('''
     <x var="pid='%s_%s' % (name, lg) if lg else name;
             tbid='%s_tb' % pid;
             x=hostLayout and o.Lock.set(o, user, field=field);
             showToolbar=field.showToolbar(ignoreInner=hostLayout)">

      <!-- Show the toolbar when relevant -->
      <x if="showToolbar">:field.pxToolbar</x>

      <!-- Add buttons for inline-edition when relevant -->
      <x if="not showToolbar and hostLayout">:field.pxInlineActions</x>

      <!-- The poor zone in itself -->
      <div contenteditable="true" class="xhtmlE"
           style=":field.getWidgetStyle(True)"
           onfocus=":field.onFocus(pid, lg, hostLayout)"
           onpaste="getPastedData(event)" onkeydown="onPoorKeyDown(event)"
           id=":'%sP' % pid" >::field.getInputValue(inRequest, requestValue,
                                                    value)</div>
      <!-- The hidden form field -->
      <textarea id=":pid" name=":pid" style="display:none"></textarea>
     </x>''')

    def __init__(self, validator=None, multiplicity=(0,1), default=None,
      defaultOnEdit=None, show=True, renderable=None, page='main', group=None,
      layouts=None, move=0, indexed=False, mustIndex=True, indexValue=None,
      searchable=False, filterField=None, readPermission='read',
      writePermission='write', width=None, height=None, maxChars=None,
      colspan=1, master=None, masterValue=None, focus=False, historized=False,
      mapping=None, generateLabel=None, label=None, sdefault='', scolspan=1,
      swidth=None, fwidth=10, sheight=None, persist=True, documents=False,
      languages=('en',), languagesLayouts=None, viewSingle=False,
      inlineEdit=False, view=None, cell=None, buttons=None, edit=None,
      xml=None, translations=None, inject=False, valueIfEmpty='',
      viewCss='xhtmlV', autoCorrect=AutoCorrect.default, font=None):
        # Call the base constructor
        super().__init__(validator, multiplicity, default, defaultOnEdit,
          show, renderable, page, group, layouts, move, indexed, mustIndex,
          indexValue, searchable, filterField, readPermission, writePermission,
          width, height, maxChars, colspan, master, masterValue, focus,
          historized, mapping, generateLabel, label, sdefault, scolspan, swidth,
          fwidth, sheight, persist, None, None, documents, None,
          languages, languagesLayouts, viewSingle, inlineEdit, 'Standard',
          view, cell, buttons, edit, xml, translations, inject, valueIfEmpty,
          viewCss)
        # As-you-type replacements are defined by placing an Autocorrect object
        # in this attribute.
        self.autoCorrect = autoCorrect
        # If you want to use a specific font shipped with Appy, set its name in
        # attribute "font". Currently, there is only a single font being
        # available:
        #                          NimbusSans-NBV
        #
        # It is a variant of the open soure font "Nimbus Sans", but whose
        # *N*on-*B*reaking chars are made *V*isible, the same way they are in
        # word processors, when mode "Show formatting marks" is enabled.
        #
        # WARNING
        #
        # In order to be loaded by the browser, the font as defined here must
        # also be defined in the UI config, within list config.ui.customFonts.
        self.font = font

    # Do not load ckeditor
    def getJs(self, o, layout, r, config): return

    def getWidgetStyle(self, edit):
        '''Returns style for the main poor tag'''
        # Potentially use a specific font shipped with Appy
        font = 'font-family:"%s",sans-serif' % self.font if self.font else None
        if edit:
            r = 'width:%s;min-height:%s' % (self.width, self.height)
            if font:
                r = '%s;%s' % (r, font)
        else:
            r = font if font else ''
        return r

    def onFocus(self, pid, lg, hostLayout):
        '''Returns the Javascript code to execute when the poor widget gets
           focus, in order to (a) initialise its data (if empty) and (b) link it
           with the toolbar.'''
        if hostLayout:
            # We are inline-editing the (sub-)field: it has its own toolbar
            id = pid
        else:
            # For inner fields, there is a unique global toolbar
            id = '%s_%s' % (self.name, lg) if lg else self.name
        return "linkToolbar('%s_tb', this)" % id

    def getListHeader(self, c):
        '''When used as an inner field, the toolbar must be rendered only once,
           within the container field's header row corresponding to this
           field.'''
        # Inject the toolbar when appropriate
        if c.layout == 'edit' and self.showToolbar(ignoreInner=True):
            bar = self.pxToolbar(c)
        else:
            bar = ''
        return '%s%s' % (super().getListHeader(c), bar)

    def showToolbar(self, ignoreInner=False):
        '''Show the toolbar if the field is not inner. Indeed, in that latter
           case, the toolbar has already been rendered in the container field's
           headers.'''
        # Do not show the toolbar if the field is an inner field, provided this
        # check must be performed.
        return True if ignoreInner else not self.isInner()

    def getXhtmlCleaner(self):
        '''Returns a Cleaner instance tailored to p_self'''
        # More strict cleaning than the Rich
        tagsToIgnore = Cleaner.tagsToIgnoreWithContentStrict
        return Cleaner(attrsToAdd=Cleaner.attrsToAddStrict,
                       propertiesToKeep=Cleaner.propertiesToKeepStrict,
                       tagsToIgnoreWithContent=tagsToIgnore)

    def validateUniValue(self, o, value):
        '''As a preamble, ensure p_value is XHTML'''
        value = XhtmlPreprocessor.preprocess(value, html=True, pre=False,
                                             paraTag='div')
        return super().validateUniValue(o, value)

    def getUniStorableValue(self, o, value):
        '''Gets the p_value as can be stored in the database within p_o'''
        if not value or value == '<br>': return
        # Ensure p_value is XHTML
        value = XhtmlPreprocessor.preprocess(value, html=True, pre=False,
                                             root='x', paraTag='div')
        return super().getUniStorableValue(o, value, wrap=False)
#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
