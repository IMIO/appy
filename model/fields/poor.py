# -*- coding: utf-8 -*-

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.px import Px
from appy.model.fields.rich import Rich

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
        #             | wrapped around a start and end char. p_data contains 2
        #             | chars: the start and end wrapper chars.
        #             | 
        #             | For example, icon "bold" is of type "wrapper", with data
        #             | being "[]". When applied to selected text "hello", it
        #             | becomes "[hello]".
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
                  'onclick="injectSentence(this)" title="%s">%s</a>%s</div>' % \
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
        r = '<img class="iconTB" src="%s" title="%s" name="%s"' \
            ' onmouseover="switchIconBack(this, true)"' \
            ' onmouseout="switchIconBack(this, false)"' \
            ' data-type="%s" data-data="%s" data-args="%s" ' \
            'data-shortcut="%s" onclick="useIcon(this)"/>' % \
             (o.buildUrl(self.icon), o.translate(self.label), self.name,
              self.type, self.data or '', self.args or '', shortcut)
        # Add specific stuff if icon type is "sentences"
        if self.type == 'sentences': r = self.asSentences(r, o)
        return r

# All available icons
Icon.all = [
  Icon('bold',      'wrapper', data='bold',    shortcut=66),
  Icon('italic',    'wrapper', data='italic',  shortcut=73),
  Icon('highlight', 'wrapper', data='hiliteColor', args='yellow', shortcut=72),
  # Insert a non breaking space
  Icon('blank',     'char',    data='code', args=' ', shortcut=32),
  # Insert a non breaking dash
  Icon('dash',      'char',    data='code', args='‑', shortcut=54),
  # Increment the field height by <data>%
  Icon('lengthen',  'action',  data='30',       shortcut=56)
]

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Poor(Rich):
    '''Field allowing to encode XHTML text'''

    # Make some classes available here
    Icon = Icon

    # Unilingual view
    viewUni = cellUni = Px('''
     <x>::field.getInlineEditableValue(o, value or '-', layout, name=name,
                                       language=lg)</x>''')

    # The toolbar
    pxToolbar = Px('''
     <div class="toolbar" id=":tbid|field.name + '_tb'">
      <x for="icon in field.Icon.all">::icon.get(o)</x>
      <!-- Add inline-edition icons when relevant -->
      <x if="hostLayout">:field.pxInlineActions</x>
     </div>''',

     css = '''
      .toolbar { height: 24px; margin: 2px 0 }
      .sentenceContainer { position: relative; display: inline }
      .sentence { padding: 3px 0 }
      .iconTB { padding: 3px; border-width: 1px; border: 1px transparent solid }
      .iconTBSel { background-color: #dbdbdb; border-color: #909090 }
     ''',

     js='''
      getIconsMapping = function(toolbar) {
        // Gets a mapping containing toolbar icons, keyed by their shortcut
        var r = {}, icons=toolbar.getElementsByClassName('iconTB');
        for (var i=0; i<icons.length; i++) {
          var icon=icons[i], key=icon.getAttribute('data-shortcut');
          if (key) r[parseInt(key)] = icon;
        }
        return r;
      }

      linkTextToolbar = function(toolbarId, target) {
        /* Link the toolbar with its target div. Get the target div if not
           given in p_target. */
        if (!target) {
          var targetId=_rsplit(toolbarId, '_', 2)[0];
          target = document.getElementById(targetId + 'P');
        }
        var toolbar=document.getElementById(toolbarId);
        toolbar['target'] = target;
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

      injectString = function(area, s) {
        // Inject some p_s(tring) into the text p_area, where the cursor is set
        var text = area.value,
                   start=area.selectionStart;
        area.value = text.substring(0, start) + s + \
                     text.substring(area.selectionEnd, area.value.length);
        area.selectionStart = area.selectionEnd = start +s.length;
        area.focus();
      }

      injectTag = function(div, tname, content){
        /* Inject, within p_div, a tag this p_tname and p_content. Inject it
           where the cursor is currently positioned. If text is selected, it is
           removed. */
        let sel = window.getSelection(),
            range = sel.getRangeAt(0),
            node;
        // Delete the currently selected text, if any
        if (!range.collapsed) range.deleteContents();
        /* Create and insert the p_tag. If p_tname is "text", insert p_content,
           but not surrounded by any tag. */
        if (tname == 'text') {
          node = document.createTextNode(content);
        }
        else {
          node = document.createElement(tname);
          node.appendChild(document.createTextNode(content));
        }
        range.insertNode(node);
        // Move the cursor after the inserted node
        range.setStartAfter(node);
        range.collapse(true);
        sel.removeAllRanges();
        sel.addRange(range);
      }

      useIcon = function(icon) {
        // Get the linked div (if already linked)
        let div = icon.parentNode['target'];
        if (!div) return;
        let type=icon.getAttribute('data-type'),
            data=icon.getAttribute('data-data'),
            args=icon.getAttribute('data-args') || null;
        if (type == 'wrapper') {
          // Wrap the selected text via the command specified in v_data
          document.execCommand(data, false, args);
        }
        else if (type == 'char') {
          // Insert a (sequence of) char(s) into the text
          injectTag(div, data, args);
        }
        else if (type == 'action') {
          // Actions
          if (icon.name == 'lengthen') lengthenDiv(div, parseInt(data));
        }
      }
      useShortcut = function(event, id) {
        if ((event.ctrlKey) && (event.keyCode in event.target['icons'])) {
          // Perform the icon's action
          useIcon(event.target['icons'][event.keyCode]);
          event.preventDefault();
        }
      }
      injectSentence = function(atag) {
        var area = atag.parentNode.parentNode.parentNode.parentNode['target'];
        if (!area) return;
        // Inject it
        injectString(area, atag.getAttribute('title'));
      }
     ''')

    # Buttons for saving or canceling while inline-editing the field, rendered
    # within its toolbar.

    pxInlineActions = Px('''
      <div var="inToolbar=showToolbar and hostLayout;
                align='left' if inToolbar else 'right';
                fdir='row' if inToolbar else 'column'"
           style=":'float:%s;display:flex;flex-direction:%s' % (align, fdir)">
       <div>
        <img id=":'%s_save' % pid" src=":svg('save')"
             class=":'iconS %s' % ('clickable' if inToolbar else 'inlineIcon')"
             title=":_('object_save')"/></div>
       <div>
        <img id=":'%s_cancel' % pid" src=":svg('cancel')"
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
      <div contenteditable="true" class="xhtmlE" style=":field.getWidgetStyle()"
           onfocus=":field.onFocus(pid, lg, hostLayout)"
           onkeydown="useShortcut(event)"
           id=":'%sP' % pid" >::field.getInputValue(inRequest, requestValue,
                                                    value)</div>

      <!-- The hidden form field -->
      <textarea id=":pid" name=":pid" style="display:none"></textarea>
     </x>''')

    # Do not load ckeditor
    def getJs(self, o, layout, r, config): return

    def getWidgetStyle(self):
        '''Returns style for the main poor tag'''
        return 'width:%s;min-height:%s' % (self.width, self.height)

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
        return "initPoorContent(this);linkTextToolbar('%s_tb', this)" % id

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
#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
