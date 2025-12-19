'''Global elements to include in HTML pages'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import base64

from appy.px import Px
from appy.ui.js import Quote
from appy.ui.includer import Includer

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Iframe:
    '''Represents the unique Appy iframe popup'''

    view = Px('''
     <div id="iframeMask"></div>
     <div id="iframePopup" class="popup"
          onmousedown="dragStart(event)" onmouseup="dragStop(event)"
          onmousemove="dragIt(event)"
          onmouseover="dragPropose(event)" onmouseout="dragStop(event)">

      <!-- Window icons -->
      <div class="iIcons">

       <!-- Enlarge / restore -->
       <span if="not mobile" class="clickable iMax"
             onclick="Iframe.toggleAppearance(this)"
             data-enlarge=":_('enlarge')" data-restore=":_('restore')"
             data-esymbol="◳" data-rsymbol="□"
             title=":_('enlarge')">◳</span>

       <!-- Close -->
       <img src=":svg('close')" class="clickable iconXS" title=":_('close')"
            onclick="closePopup('iframePopup',null,true)"/>
      </div>

      <!-- Header icon -->
      <img class="iconM popupI" src=":svg('arrows')"/>
      <iframe id="appyIFrame" name="appyIFrame" frameborder="0"></iframe>
     </div>''',

     css='''
      .iMax { font-size:136% }
      .iIcons { display:flex; float:right; color:|altColor|; gap:1em }
     ''',

     js='''class Iframe {

       constructor(popup, w, h, mobile, back) {
         // Interconnect the DOM p_popup and the object under construction
         this.popup = popup;
         popup.appy = this;
         // Get the inner iframe
         this.iframe = document.getElementById('appyIFrame');
         // The popup's standard width and height
         this.w = w;
         this.h = h;
         // Is the client a mobile device ?
         this.mobile = mobile;
         // Set initial dimensions and position for the popup and its iframe
         this.enlarged = false;
         this.setStandard(true);
         // Initialise the back hook, if any
         popup.backHook = back;
         // Show the mask behind the popup
         if (!mobile) this.setMask();
         // Remember the height of the first inner object tag, if any
         this.innerObjectHeight = null;
       }

       // Initialises the popup position
       setPosition(initial) {
         // On a smartphone, it has no sense: it always takes the whole window
         if (this.mobile) return;
         const popup = this.popup;
         /* 2 cases: (a) initial positioning and (b) restore the popup after
            having been enlarged. */
         if (initial) { // (a)
           // (Re)position the popup at the center of the screen
           // The popup is initially positioned at the center of the window
           this.top = popup.style.top = '50%';
           this.left = popup.style.left = '50%';
           this.transform = popup.style.transform = 'translate(-50%,-50%)';
         }
         else { // (b)
           // Restore the dimensions having been saved on the Appy object
           popup.style.top = this.top;
           popup.style.left = this.left;
           popup.style.transform = this.transform;
         }
       }

       // Set the mask preventing clicking around the iframe
       setMask() {
         let mask = document.getElementById('iframeMask');
         mask.style.opacity = 0.7;
         mask.style.zIndex = 99;
       }

       /* Set standard dimensions and positioning for the popup. Its position
          may have been changed by the user (drag and drop). */
       setStandard(initial) {
         const iframe=this.iframe, w=this.w, h=this.h, popup=this.popup;
         // Update v_popup dimensions
         popup.style.width = `${w}px`;
         popup.style.height = `${h}px`;
         // Update v_iframe dimensions
         iframe.style.width = '100%';
         iframe.style.height = '100%';
         // Position the popup
         this.setPosition(initial);
       }

       // Redimension the popup to invade the whole browser window
       setEnlarged() {
         // Remember the current popup position: the user may have changed it
         const popup = this.popup;
         this.top = popup.style.top;
         this.left = popup.style.left;
         this.transform = popup.style.transform;
         // Enlarge the popup
         popup.style.width = '98%';
         popup.style.height = '97%';
         popup.style.transform = 'none';
         popup.style.left = '0px';
         popup.style.top = '0px';
       }

       // Update the toggle icon's symbol and title
       setToggleIcon(icon, name) {
         const letter = name.charAt(0),
               symbol = icon.getAttribute(`data-${letter}symbol`),
               title = icon.getAttribute(`data-${name}`);
         icon.innerText = symbol;
         icon.setAttribute('title', title);
       }

       // Toggle the popup appearance: enlarged <> standard dimensions
       static toggleAppearance(icon) {
         const iframe = document.getElementById('iframePopup').appy;
         let name;
         if (iframe.enlarged) { // Reapply standard dimensions
           iframe.setStandard(false);
           name = 'enlarge';
         }
         else { // Enlarge the popup
           iframe.setEnlarged();
           name = 'restore';
         }
         iframe.setToggleIcon(icon, name);
         iframe.enlarged = !iframe.enlarged;
       }
     }''')

    # HTML page to render for closing the popup
    back = '<!DOCTYPE html>\n<html><head>%s%s</head><body>' \
           '<script>backFromPopup(%d)</script></body></html>'

    @classmethod
    def goBack(class_, o, initiator=None):
        '''Returns a HTML page allowing to close the iframe popup and refresh
           the base page.'''
        # A back URL may be forced by a request key or by an initiator
        back = o.req._back
        if not back and initiator:
            back = initiator.backFromPopupUrl
        # Set the cookie containing information required for closing the popup
        if back:
            close = base64.b64encode(back.encode())
        else:
            close = 'yes'
        resp = o.resp
        resp.setCookie('closePopup', close)
        # Include appy.js and call a Javascript function that will do the job
        version = o.config.server.static.versions['appy.js']
        # If the version of appy.js is not mentioned, it will be impossible to
        # debug inside it. Adding statements like: "console.log" or "debugger"
        # will not work, because the browser will consider "appy.js" not being
        # the effective appy.js. In short, for the browser, appy.js is not
        # appy.js?6.
        return class_.back % (Includer.js(o.buildUrl(f'appy.js?{version}')),
                              Includer.vars(o), o.iid)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
