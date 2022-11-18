'''Global elements to include in HTML pages'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.ui.iframe import Iframe

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Globals:
    '''Global elements to inject in most or all pages'''

    # Translated messages computed in Javascript variables in most pages
    variables = ('no_elem_selected', 'action_confirm', 'save_confirm',
                 'warn_leave_form', 'workflow_comment')

    @classmethod
    def getVariables(class_, tool):
        '''Returns Javascript variables storing translated texts used in forms
           and popups.'''
        r = ['var wrongTextInput="%s none";' % tool.config.ui.wrongTextColor]
        for label in class_.variables:
            r.append('var %s="%s";' % (label, tool.translate(label)))
        return '<script>%s</script>' % '\n'.join(r)

    # Popups must be present in every page
    popups = '''%s
     <!-- Popup for confirming an action -->
     <div id="confirmActionPopup" class="popup">
      <img class="iconM popupI" src="%s"/>
      <form id="confirmActionForm" method="post">
       <div align="center">
        <p id="appyConfirmText"></p>
        <input type="hidden" name="actionType"/>
        <input type="hidden" name="action"/>
        <input type="hidden" name="visible"/>
        <div id="commentArea" align="%s">
         <div id="appyCommentLabel"></div>
         <textarea name="popupComment" id="popupComment"
                   cols="30" rows="3"></textarea>
        </div>
        <div class="topSpace">
         <input type="button" onclick="doConfirm()" value="%s"/>
         <input type="button" value="%s"
                onclick="closePopup('confirmActionPopup', 'comment')"/>
        </div>
       </div>
      </form>
     </div>
     <!-- Popup for uploading a file in a pod field -->
     <div id="uploadPopup" class="popup" align="center">
      <form id="uploadForm" name="uploadForm" enctype="multipart/form-data"
            method="post">
       <input type="hidden" name="objectId"/>
       <input type="hidden" name="fieldName"/>
       <input type="hidden" name="template"/>
       <input type="hidden" name="podFormat"/>
       <input type="hidden" name="action" value="upload"/>
       <input type="file" name="uploadedFile"/><br/><br/>
       <input type="button" onclick="this.form.submit()" value="%s"/>
       <input type="button" onclick="closePopup('uploadPopup')" value="%s"/>
      </form>
     </div>
     <!-- Popup for displaying an error message -->
     <div id="alertPopup" class="popup">
      <img class="iconM popupI" src="%s"/>
      <div align="center" id="appyAlertText"></div>
      <div align="center" class="topSpace">
       <input type="button" onclick="closePopup('alertPopup')" value="%s"/>
      </div>
     </div>%s'''

    @classmethod
    def getPopups(class_, tool, svg, _, dleft, dright, popup):
        '''Returns the popups to include in every page'''
        # The "iframe" popup must not be included if we are already in a popup
        if popup:
            iframe = ''
        else:
            iframe = Iframe.view % (svg('close'), svg('arrows'))
        # Define variables, per popup
        vars = (
         # Global Javascript variables
         class_.getVariables(tool),
         # confirmActionPopup
         svg('arrows'), dleft, _('yes'), _('no'),
         # uploadPopup
         _('object_save'), _('object_cancel'),
         # alertPopup
         svg('warning'), _('appy_ok'),
         # iframePopup
         iframe
        )
        return class_.popups % vars

    # Forms must be present on some pages, like view, edit and search.
    forms = '''
     <!-- Global form for generating/freezing a document from a pod template -->
     <form id="podForm" name="podForm" method="post">
      <input type="hidden" name="template"/>
      <input type="hidden" name="podFormat"/>
      <input type="hidden" name="queryData"/>
      <input type="hidden" name="criteria"/>
      <input type="hidden" name="customParams"/>
      <input type="hidden" name="crumb"/>
      <input type="hidden" name="checkedIds"/>
      <input type="hidden" name="checkedSem"/>
      <input type="hidden" name="freezeAction"/>
      <input type="hidden" name="mailing"/>
      <input type="hidden" name="mailText"/>
     </form>'''

    @classmethod
    def getForms(class_, tool):
        '''Returns the forms to include in most pages, as well as translated
           Javascript messages.'''
        return class_.forms

    @classmethod
    def getScripts(class_, tool, q, layout):
        '''Get the scripts that must be run on most pages'''
        return '<script>initSlaves(%s,%s)</script>' % (q(tool.url), q(layout))
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
