#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import urllib.parse

from appy.px import Px

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Message:
    '''Manages the "message zone" allowing to display messages coming from the
       Appy server to the end user.'''

    @classmethod
    def consumeAll(class_, handler, unlessRedirect=False):
        '''Returns the list of messages to show to a web page'''
        # Do not consume anything if p_unlessRedirect is True and we are
        # redirecting the user.
        if unlessRedirect and ('Appy-Redirect' in handler.resp.headers): return
        # Try to get messages from the 'AppyMessage' cookie
        message = handler.req.AppyMessage
        if message:
            # Dismiss the cookie
            handler.resp.setCookie('AppyMessage', 'deleted')
            return urllib.parse.unquote(message)

    @classmethod
    def hasValidationErrors(class_, handler):
        '''Returns True if there are validaton errors collected by the
           (handler.)validator.'''
        return handler.validator and handler.validator.errors

    # The message zone
    px = Px('''
     <div id="appyMessage"
          var="validErrors=ui.Message.hasValidationErrors(handler)"
          style=":'display:none' if not validErrors else 'display:block'">
      <script>Message.init(appyMessage)</script>

      <!-- The icon for closing the message -->
      <img src=":svg('close')" class="clickable iconS popupI"
           onclick="this.parentNode.style.display='none'" align=":dright"/>

      <!-- The message content -->
      <div id="appyMessageContent">:validErrors and _('validation_error')</div>
      <div if="validErrors"
           var2="validator=handler.validator">:handler.validator.pxErrors</div>
     </div>
     <script var="messages=ui.Message.consumeAll(handler)"
             if="messages">::'Message.show(%s)' % q(messages)</script>''',

     css='''
      .message { position: fixed; bottom: 30px; right: 0px;
                 background-color: |fillColor|; color: |brightColor|;
                 padding: 10px; z-index: 15; font-weight: bold }
      .message a { color:|messageLinkColor| }
      .messageP { width: 80%; top: 35% }

      @keyframes fade {
        0% { opacity: 0 }
        10% { opacity: 0.9 }
        80% { opacity: 0.6 }
        100% { opacity: 0; display: none; visibility: hidden }
      }
      .fadedOut { animation: fade |messageFadeout| 1;
                  animation-fill-mode: forwards }''',

     # The Fader allows to manage the "fade out" effect on the message box
     js='''
       class Fader {

         constructor(node){ /* Cross-link the fader and its anchor node */
           node.fader = this;
           this.node = node;
         }

         stop(restart) {
           /* Resetting the "fade out" animation can only be performed by
              replacing the target node with a clone. */
           var node=this.node,
               clone=node.cloneNode(true);
           /* Configure the clone */
           Message.init(clone, !restart);
           node.parentNode.replaceChild(clone, node);
           return clone;
         }
       }

       // Static methods for managing the message zone
       class Message {

         // Initialises the DOM node representing the "message" zone
         static init(node, noAnim) {
           new Fader(node);
           node.className = 'message';
           if (!noAnim) {
             node.className += ' fadedOut';
             node.addEventListener('mouseenter',
               function(event) {event.target.fader.stop()});
           }
           else node.onmouseenter = null;
         }

         // Display the message zone
         static show(message) {
           var zone = getNode('appyMessageContent');
           zone.innerHTML = message;
           zone.parentNode.style.display = 'block';
         }
       }
       ''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
