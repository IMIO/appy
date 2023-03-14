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
        if unlessRedirect and 'Appy-Redirect' in handler.resp.headers:
            return None, 'null'
        # Try to get messages from the 'AppyMessage' cookie
        message = handler.req.AppyMessage
        if message:
            # Must it be fleeting or not ?
            if message.startswith('*'):
                fleeting = 'true' # JS-encoded
                message = message[1:]
            else:
                fleeting = 'false' # JS-encoded
            # Dismiss the cookie
            handler.resp.setCookie('AppyMessage', 'deleted')
            r = urllib.parse.unquote(message), fleeting
        else:
            r = None, 'null'
        return r

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
      <script>Message.init(appyMessage,true)</script>

      <!-- The icon for closing the message -->
      <img src=":svg('close')" class="clickable iconS popupI"
           onclick="this.parentNode.style.display='none'" align=":dright"/>

      <!-- The message content -->
      <div id="appyMessageContent">:validErrors and _('validation_error')</div>
      <div if="validErrors"
           var2="validator=handler.validator">:handler.validator.pxErrors</div>
     </div>
     <script var="messages,fleeting=ui.Message.consumeAll(handler)"
             if="messages">::'Message.show(%s,%s)' % (q(messages), fleeting)
     </script>''',

     css='''
      .message { position: fixed; bottom: 30px; right: 0px;
                 background-color: |fillColor|; color: |brightColor|;
                 padding: 10px; z-index: 15; font-weight: bold }
      .message a { color:|messageLinkColor| }
      .messageP { width: 80%; top: 35% }
      @media only screen and (hover:none) and (pointer:coarse) {
        .message { width:100%; bottom:0; text-align:center; padding:2em 0;
                   font-size:160% }
        .message img { margin:0 1em 0 0; width:2em }
      }

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

         // Enable the fader
         static enableFader(node) {
           node.className += ' fadedOut';
           node.addEventListener('mouseenter',
             function(event) {event.target.fader.stop()});
         }

         // Initialises the DOM node representing the "message" zone
         static init(node, noAnim) {
           // Always create a Fader objet, even if not be directly used
           new Fader(node);
           node.className = 'message';
           if (!noAnim) Message.enableFader(node);
           else node.onmouseenter = null;
         }

         // Display the message zone
         static show(message, fleeting) {
           let zone = getNode('appyMessageContent'),
               parent = zone.parentNode;
           // Enable the fader if the p_message must be p_fleeting
           if (fleeting) Message.enableFader(parent);
           // Display the p_message
           zone.innerHTML = message;
           parent.style.display = 'block';
         }
       }
       ''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
