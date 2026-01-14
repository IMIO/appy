#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.px import Px
from appy.utils import bn
from appy.model.fields import Field
from appy.ui.template import Template
from appy.model.utils import Object as O

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Progress:
    '''Implements a progress bar for object actions or workflow transitions that
       last a long time.'''

    # Some elements will be traversable
    traverse = {}

    # How does it work ? If an Action field or a workflow transition will
    # probably take a long time, place, in his "progress" attribute, an instance
    # of this class. Within the code that implements the action or transition,
    # once you have progress-related info, call method m_set on the Progress
    # object. This method must be called with 2 args:

    # 1) an integer number between 1 and 100 that represents the progress
    #    percentage ;
    # 2) a translated text, that will be shown in the user interface.

    def __init__(self, label=None, interval=5):
        # This i18n p_label, if specified, will be used to show the initial text
        # around the progress bar, before the first progress request is made.
        # If p_label is None, a default text will be shown.
        self.label = label or 'progress_init'
        # The interval, in seconds, between 2 client requests for progress
        self.interval = interval

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
        return f'new BarHook(document.currentScript.parentNode, ' \
               f'`${{siteUrl}}/tool/ui/Progress/get?{params}`).' \
               f'setInterval({interval});'

    def getStartJs(self):
        '''Returns the JS code allowing to run the long operation and the first
           status check.'''
        return 'document.currentScript.parentNode.hook.fetch();' \
               'document.querySelector("#bar").hook.fetch()'

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

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                                    PXs
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # The main progress PX

    view = Px('''
     <div id="progress"
          var="o, elem=tool.ui.Progress.getFromRequest(tool);
               progress=elem.progress;
               ongoing=progress.hasPath(o, name)">

      <!-- Display an error message if the action is still ongoing -->
      <div if="ongoing" class="pbError">::_('progress_already')</div>

      <x if="not ongoing" var2="x=progress.init(o, name)">
       <script>::progress.getMainHook(tool)</script>

       <!-- The progress bar -->
       <div id="bar">
         <script>::progress.getBarHook(o, elem)</script>
         <div class="pbAll">
          <!-- The "done" part -->
          <div id="pbDone" style="width:0%">&nbsp;</div>
          <!-- The "to do" part -->
          <div id="pbTodo" style="width:100%">&nbsp;</div>
         </div>
         <div id="pbText">:_(progress.label)</div>
       </div>

       <!-- Launch the action and recurrent status getter -->
       <script>::progress.getStartJs()</script>
      </x>
     </div>''', template=Template.px, hook='content',

     css='''
       .pbAll { border:1px solid black; width:98%;
                margin:1.5em 0 1em 0; display:flex; gap:0 }
       .pbError { margin-top:1em }
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
       #pbTodo { background-color:white; height:1.5em }
     ''',

     js='''
       class BarHook extends Hook {

         // Override m_fetchJson in order to refresh the progress bar
         fetchJson(json) {
           const node = this.node,
                 percentage = json.percentage,
                 done = node.querySelector('#pbDone'),
                 todo = node.querySelector('#pbTodo');
           // Update the "done" part
           if (percentage) {
             done.style.width = `${percentage}%`;
             done.style.borderRight = '1px solid black';
             // Display the percentage in the progress bar if there is space
             if (percentage > 15) done.innerText = done.style.width;
           }
           // Update the "to do" part
           const remain = 100 - percentage;
           if (remain) {
             todo.style.display = 'block';
             todo.style.width = `${remain}%`;
           }
           else todo.style.display = 'none';
           // Update the text
           node.querySelector('#pbText').innerHTML = json.text || '';
         }

         // Continue to fetch status while the main action is not finished
         continueFetch() {
           return !this.node.parentNode.hook.fetched;
         }
       }''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
