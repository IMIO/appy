#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from ..px import Px
from ..utils import bn
from .iframe import Iframe
from .template import Template
from ..model.fields import Field
from ..model.utils import Object as O

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Progress:
    '''Implements a progress bar for object actions or workflow transitions that
       last a long time.'''

    # Some elements will be traversable
    traverse = {}

    # How does it work ? If an Action field or a workflow Transition will
    # probably take a long time, place, in his "progress" attribute, an instance
    # of this class. Within the code that implements the action or transition,
    # once you have progress-related info, call method m_setProgress on the
    # Action or Transition object for which a progress bar has been defined.
    # This method must be called with 3 args:

    # 1) the related Appy object;
    # 2) an integer number between 1 and 100 that represents the progress
    #    percentage ;
    # 3) a translated text, that will be shown in the user interface. It can be
    #    raw text or XHTML; if you choose the "append" mode, it MUST be XHTML.

    def __init__(self, label=None, interval=5, append=False, popup=None):
        # This i18n p_label, if specified, will be used to show the initial text
        # around the progress bar, before the first progress request is made.
        # If p_label is None, a default text will be shown.
        self.label = label or 'progress_init'
        # The interval, in seconds, between 2 client requests for progress
        self.interval = interval
        # By default (p_append is False), everytime status information is
        # retrieved from the server, the text that accompanies the progress bar
        # is replaced with the last retrieved one. If you prefer it to be
        # appended to the previous text, set p_append to True.
        self.append = append
        # The progress bar will be shown in the Appy iframe popup. If you want
        # to control iframe characteristics, place here an Iframe object, as
        # found in appy/ui/iframe.py.
        self.popup = popup or Iframe('300px', '300px', resizable=False)

    def getMainHook(self, tool):
        '''Return the JS code allowing to create a Hook object and link it to
           the progress' main DOM node.'''
        path = tool.req.path
        return f'new Hook(document.currentScript.parentNode, ' \
               f'`${{siteUrl}}/{path}`);'

    def getBarHook(self, o, elem):
        '''Return the JS code allowing to create a Hook object and link it to
           the progress bar.'''
        params = f'iid={o.iid}&name={elem.name}'
        # Progress status will be done every v_interval seconds
        interval = elem.progress.interval
        # Must status text be replaced at each status change, or appended ?
        append = '.setAppend(true)' if self.append else ''
        return f'new BarHook(document.currentScript.parentNode, ' \
               f'`${{siteUrl}}/tool/ui/Progress/get?{params}`).' \
               f'setInterval({interval}){append};'

    def getStartJs(self, fg):
        '''Returns the JS code allowing to run the long operation and the first
           status check.'''
        # If the server runs in the foreground, fetching status cannot be done
        fetchS = '' if fg else ';document.querySelector("#bar").hook.fetch();'
        return f'document.currentScript.parentNode.hook.fetch(){fetchS}'

    def getJsData(self):
        '''Returns, in a JS array, popup characteristics as defined by the used
           p_self.popup.'''
        return self.popup.getJsData()

    def getPath(self, o, name):
        '''Get, as a Path object, the absolute path to the temp file where
           progress is dumped.'''
        # Get the OS temp folder where to dump info
        folder = o.database.getTempFolder(sub='progress')
        # Get the name of the file into which to dump the progress
        return folder / f'{o.iid}_{name}'

    def hasPath(self, o, name):
        '''Does a status file exist ?'''
        return self.getPath(o, name).is_file()

    def deletePath(self, o, name):
        '''Deletes the progress status as dumped on disk'''
        path = self.getPath(o, name)
        if path.is_file():
            path.unlink()

    def set(self, o, name, percentage, text=''):
        '''Called by the app/ext to set the progress: a p_percentage between 1
           and 100, and some explanatory p_text about the current status.'''
        # Get the file into which to dump progress
        path = self.getPath(o, name)
        with open(str(path), 'w') as f:
            f.write(f'{percentage}{bn}{text}')

    def init(self, o, name):
        '''Initialise the progress by dumping a status file with 0 percentage'''
        self.set(o, name, 0, o.translate('progress_ongoing'))

    @classmethod
    def getFromRequest(class_, tool):
        '''Get, as a 2-tuple, from the request, the object and field/transition
           being the target of the ongoing progress bar.'''
        # Get the target object
        req = tool.req
        o = tool.getObject(req.iid)
        # Get the target field or transition
        elem = o.getField(req.name) or o.class_.workflow.transitions.get(name)
        return o, elem

    traverse['get'] = True # Strict security will be enforced in the method
    @classmethod
    def get(class_, tool):
        '''Retrieves and returns, as JSON, the current progress status about
           element p_tool.req.name related to object having this
           p_tool.req.iid.'''
        o, elem = class_.getFromRequest(tool)
        # Security check
        if isinstance(elem, Field):
            # A field
            o.allows(elem.readPermission, raiseError=True)
        else:
            # A transition
            if not elem.isTriggerable(o): o.raiseUnauthorized()
        # Result will be JSON
        tool.resp.setContentType('json')
        # Get the file on disk where the progress is dumped
        r = None
        path = elem.progress.getPath(o, elem.name)
        if path.is_file():
            with open(str(path)) as f:
                content = f.read()
                percentage, text = content.split(bn, 1)
                r = O(percentage=int(percentage), text=text)
        else:
            r = O(percentage=0, text=tool.translate('progress_ongoing'))
        return r

    def getFinishedBar(self, text, success=True):
        '''Renders p_self.bar,, forced to 100%, with this final p_text'''
        context = {'progress': self, 'finished': True, 'text':text,
                   'success': success}
        return self.bar(context)

    def getDoneParts(self, finished, success=True):
        '''Returns, as a 3-tuple, elements to be rendered in the "done" part of
           the progress bar.'''
        # The 3 elements are:
        # 1) its width ;
        # 2) the CSS styles to apply to it ;
        # 3) its inner text.
        width = 100 if finished else 0
        widthF = f'{width}%' # The width, formatted
        styles = f'width:{widthF}'
        if finished:
            # Once finished, slow down the CSS animation
            styles = f'{styles};animation-duration:20s'
            text = f'{widthF} 🥳' if success else '😢'
        else:
            text = '&nbsp;'
        return width, styles, text

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                                    PXs
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # The main progress PX

    view = Px('''
     <div id="progress"
          var="o, elem=tool.ui.Progress.getFromRequest(tool);
               progress=elem.progress;
               fg = tool.H().inTheForeground();
               ongoing=progress.hasPath(o, name);
               text=None; finished=False; success=True">

      <!-- Display an error message if the action is still ongoing -->
      <div if="ongoing" class="pbError">::_('progress_already')</div>

      <x if="not ongoing" var2="x=progress.init(o, name)">
       <script>::progress.getMainHook(tool)</script>

       <!-- Display a warning if the server runs in the foreground: because a
            single thread is there, status cannot be fetched in parallel. -->
       <div if="fg" class="pbError">::_('progress_fg')</div>

       <!-- The progress bar -->
       <x>:progress.bar</x>

       <!-- Launch the action and recurrent status getter -->
       <script>::progress.getStartJs(fg)</script>
      </x>
     </div>''', template=Template.px, hook='content',

     css='.pbError { margin-top:1em }',

     js='''
       class BarHook extends Hook {

         // Update the text that accompanies the progress bar
         updateText(json, changed) {
           const text = this.node.querySelector('#pbText');
           if (this.append) {
             /* Append the text only if we are sure we do not retrieve an
                already retrieved status. */
             if (changed) {
               text.innerHTML = `${text.innerHTML}${json.text}`;
             }
           }
           else text.innerHTML = json.text || '';
         }

         // Override m_fetchJson in order to refresh the progress bar
         fetchJson(json) {
           const node = this.node,
                 percent = json.percentage,
                 done = node.querySelector('#pbDone'),
                 todo = node.querySelector('#pbTodo'),
                 changed = (percent && parseInt(done.style.width) != percent);
           // Update the "done" part
           if (percent) {
             if (changed) done.style.width = `${percent}%`;
             done.style.borderRight = '1px solid black';
             // Display the percentage in the progress bar if there is space
             if (percent > 15) done.innerText = done.style.width;
             // Remove a dot in the "to do" part (if some dots are still there)
             if (changed) {
               const dots = todo.innerText;
               if (dots) todo.innerText = dots.slice(0,-1);
             }
           }
           // Update the "to do" part
           const remain = 100 - percent;
           if (remain) {
             todo.style.display = 'block';
             todo.style.width = `${remain}%`;
           }
           else todo.style.display = 'none';
           // Update the text
           this.updateText(json, changed);
         }

         // Continue to fetch status while the main action is not finished
         continueFetch() {
           return !this.node.parentNode.hook.fetched;
         }
       }''')

    # The progress bar
    bar = Px('''
     <div id="bar">

      <!-- The hook allowing to retrieve, in JSON, the progress status -->
      <script if="not finished">::progress.getBarHook(o, elem)</script>

      <!-- Render the bar -->
      <div class="pbAll">

       <!-- The "done" part -->
       <div var="width,styles,dtext=progress.getDoneParts(finished, success)"
            id="pbDone" style=":styles">:dtext</div>

       <!-- The "to do" part -->
       <div if="not finished" id="pbTodo" class="blinkT"
            style="width:100%">···</div>
      </div>

      <!-- The text that accompanies the progress bar -->
      <div id="pbText">::text or _(progress.label)</div>
     </div>''',

     css='''
       .pbAll { border:1px solid black; width:98%;
                margin:1.5em 0 1em 0; display:flex; gap:0 }
       @keyframes animBG {
        0%   { background-position:   0% 50%; }
        50%  { background-position: 100% 50%; }
        100% { background-position:   0% 50%; }
       }
       #pbDone { height:1.5em; text-align:center; transition:width 0.2s;
                 background-image: linear-gradient(-45deg, lightgrey 0%,
                   whitesmoke 25%, lightgrey 51%, whitesmoke 75%,
                   lightgrey 100%);
                 background-size: 400% 400%;
                 animation: animBG 2s ease infinite }
       #pbTodo { background-color:white; height:1.5em; text-align:center }
     ''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
