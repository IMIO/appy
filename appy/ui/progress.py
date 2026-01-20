#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from DateTime import DateTime

from ..px import Px
from .iframe import Iframe
from ..utils import bn, br
from .template import Template
from ..model.fields import Field
from ..model.utils import Object as O

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
PC_KO    = 'Progress for %s:%s:: Ignoring status with wrong percentage (%d%%).'
PATH_KO  = 'The progress file does not exist.'
PATH_DEL = 'Progress information about %s:%s has been cleaned.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Progress:
    '''Implements a progress bar for object actions or workflow transitions that
       last a long time.'''

    # The confirmation message when cleaning a status file
    CLEAN_TEXT = f'You are about to delete status info for this operation.' \
                 f'{br}{br}Do it only if you are stuck with it.{br}{br}' \
                 'Proceed ?'

    # Some elements will be traversable
    traverse = {}

    # How does it work ? If an Action field or a workflow Transition will
    # probably take a long time, place, in his "progress" attribute, an instance
    # of this class. Within the code that implements the action or transition,
    # once you have progress-related info, call method m_setProgress on the
    # Action or Transition object for which a progress bar has been defined.
    # This method must be called with 3 args:

    # 1) the related Appy object;
    # 2) an integer number between 0 and 100 that represents the progress
    #    percentage ;
    # 3) a translated text, that will be shown in the user interface. It can be
    #    raw text or XHTML; if you choose the "append" mode, it MUST be XHTML.

    def __init__(self, label=None, interval=5, append=False, popup=None,
                 exclusive=False):
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
        # A long action may slow down the entire site and potentially be
        # troubled by other database commits. If you want to block any other
        # long action and database commit while performing the action tied to
        # this Progress object, set p_exclusive to True.
        # ⚠️ Use this with caution: its sets the entire database in read-only
        #    mode. This is violent and can be problematic for all the other
        #    users. Moreover, if your operation crashes, the database may be
        #    left in read-only mode; a manual operation via the admin-zone is
        #    required to set the database in read/write mode again.
        self.exclusive = exclusive

        # For a given progress, every status dumped at the server side via
        # m_setProgress will get a number. The first one will get number 1. If
        # the browser fetches a status, but not server status has yet been
        # dumped, it will get a virtual status with number 0.

        # ⚠️ Important note. Depending on the browser's status fetch pace,
        #    defined by p_interval, and the pace at which the server code
        #    produces statuses via m_setProgress, the browser may retrieve
        #    several times the same server status; or, inversely, a server
        #    status may never be fetched by the browser, because too quickly
        #    replaced with a new one.

    def getMainHook(self, tool):
        '''Return the JS code allowing to create a Hook object and link it to
           the progress' main DOM node.'''
        path = tool.req.path
        append = '.setAppend(true)' if self.append else ''
        r = f'new ProgressHook(document.currentScript.parentNode, ' \
            f'`${{siteUrl}}/{path}`){append}'
        # By the way, disable the iframe "close" button: the operation can't be
        # aborted at this time.
        disableClose = 'getNode(":iframePopup").appy.setClosable(false)'
        return f'{r};{disableClose}'

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

    def set(self, o, name, percentage, text='', check=True):
        '''Called by the app/ext to set, in the temp file whose path is computed
           by m_getPath, the progress status: a p_percentage between 1 and 100,
           and some explanatory p_text about the current status.'''
        # Ensure the percentage is correct
        if check and (percentage < 0 or percentage > 100):
            o.log(PC_KO % (o.iid, name, percentage), type='error')
            return
        # Get the file into which to dump progress. Check m_getPathInfo to have
        # an idea of the structure of the data being dumped in such files.
        path = self.getPath(o, name)
        if path.is_file():
            # A status file already exists. Before overwriting it, read its
            # start, in order to retrieve the user login, the date of file
            # creation and the file number.
            with open(str(path)) as f:
                login = f.readline().strip()
                created = f.readline().strip()
                nb = int(f.readline().strip())
        else:
            login = o.user.login
            created = str(DateTime())
            nb = -1
        # Increment the file number
        nb += 1
        with open(str(path), 'w') as f:
            f.write(f'{login}{bn}{created}{bn}{nb}{bn}{percentage}{bn}{text}')

    def init(self, o, name):
        '''Initialise the progress by dumping a status file with 0 percentage'''
        text = self.divTranslate(o, 'progress_ongoing')
        self.set(o, name, 0, text, check=False)
        # Put the database in read-only mode when relevant
        if self.exclusive:
            o.database.setReadOnly(True)

    def finalize(self, o, text, success=True):
        '''Finalizes the long operation and returns p_self.bar, rendered at
           100%, with this final p_text.'''
        # Set the database in read/write mode again, if the operation was
        # exclusive.
        if self.exclusive:
            o.database.setReadOnly(False)
        # Renders the progress bar, forced to 100%
        context = {'progress': self, 'finished': True, 'text':text,
                   'success': success, 'o': o, 'svg': o.buildSvg}
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

    def divTranslate(self, o, label=None):
        '''Translates this p_label and put the result in a div tag'''
        r = o.translate(label or self.label)
        return f'<div>{r}</div>'

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #    Class methods related to a specific ongoing long-running operation
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

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
        progress = elem.progress
        path = progress.getPath(o, elem.name)
        if path.is_file():
            r = progress.getPathInfo(path)
        else:
            r = O(percentage=0, login=tool.user.login, created=None, nb=0,
                  text=progress.divTranslate(o, 'progress_ongoing'))
        return r

    @classmethod
    def getPathInfo(class_, path):
        '''Extracts an object with info as dumped in the the status file having
           this p_path.'''
        r = O()
        # The info dumped in the file is made of the following lines:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # 1 | the login of the user performing the action ;
        # 2 | the date of file creation ;
        # 3 | the file number: an integer number starting at 1, that is
        #   | incremented every time the status is updated ;
        # 4 | the percentage, as an integer number between 0 and 100 ;
        # 5 | the text, that may span several lines.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        with open(str(path)) as f:
            r.login = f.readline().strip()
            r.created = DateTime(f.readline().strip())
            r.nb = int(f.readline().strip())
            r.percentage = int(f.readline().strip())
            r.text = f.read() # The remaining of the file is the text
        return r

    traverse['clean'] = 'Manager'
    @classmethod
    def clean(class_, tool):
        '''Deletes the status file about the progress whose parameters are in
           the request.'''
        # Get progress info from the request
        o, elem = class_.getFromRequest(tool)
        # Get the file to delete
        path = elem.progress.getPath(o, elem.name)
        if path.is_file():
            # Delete the fle
            path.unlink()
            text = PATH_DEL % (o.iid, elem)
        else:
            text = PATH_KO
        # No need to commit: it's just about deleting a file on disk
        tool.say(text, fleeting=False)
        tool.goto()

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #      Class methods related to all ongoing long-running operations
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @classmethod
    def listAll(class_, tool):
        '''Returns info about all currently ongoing long-running operations'''
        r = []
        # Walk the temp folder into wich progress operations dump their status
        folder = tool.database.getTempFolder('progress')
        for path in folder.iterdir():
            # Ignore files whose name would not conform to a status file
            name = path.name
            if name.count('_') != 1 or name.count('.'): continue
            # Extract info from the file name: object iid and field/transition
            # name.
            iid, name = name.split('_')
            # Collect, from the file name and content, info in an Object and
            # add it to v_r.
            info = class_.getPathInfo(path)
            info.iid = iid
            info.name = name
            r.append(info)
        return r

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
               readOnly=tool.database.readOnly;
               text=None; finished=False; success=True">

      <!-- Display an error message if the action is already ongoing or the
           database is in read-only mode. -->
      <div if="ongoing or readOnly" class="pbError">::_('progress_already' 
        if ongoing else 'progress_read_only')</div>

      <x if="not ongoing and not readOnly" var2="x=progress.init(o, name)">
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

     # The JS progress hook is customized, via JS class ProgressHook. The
     # objective is to retrieve, in "append" mode, the cumulated text at the end
     # of the process, and integrate it in the final message.

     # The bar hook is extended via JS class BarHook in order to handle json
     # status fetches.

     js='''
       class ProgressHook extends Hook {
         fetchXhtml(xhtml) {
           let chunk = xhtml;
           // If we are in "append" mode, retrieve the cumulated text
           if (this.append) {
             const text = this.node.querySelector('#pbText').innerHTML;
             if (text) {
               chunk = `${chunk}<div class="discreet topSpace">${text}</div>`;
             }
           }
           // Call the base method
           super.fetchXhtml(chunk);
           // Enable the iframe "close" button, that was disabled
           const iframe = getNode(':iframePopup').appy;
           iframe.setClosable(true);
           // When closing the popup, reload the caller (page or hook)
           iframe.backReload = true;
         }
       }

       // Create a BarHook class for handling json status fetches
       class BarHook extends Hook {

         // Custom initialisation: remember the last status number
         init() {
           /* If we haven't retrieve any server status yet, the last status is
              -1. If we have fetched a status but no server status has yet been
              dumped, the last status is 0. In any other case, the last status
              is the number of the last fetched server status. */
           this.lastStatus = -1;
         }

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
                 changed = json.nb != this.lastStatus;
           // Update the "done" part
           if (percent) {
             if (changed) done.style.width = `${percent}%`;
             done.style.borderRight = '1px solid black';
             // Display the percentage in the progress bar if there is space
             if (percent > 10) done.innerText = done.style.width;
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
           // Update last status number
           this.lastStatus = json.nb;
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
            id="pbDone" style=":styles">::dtext</div>

       <!-- The "to do" part -->
       <div if="not finished" id="pbTodo" class="blinkT"
            style="width:100%">···</div>
      </div>

      <!-- A button allowing to close the popup -->
      <div class="pbClose">
       <input if="finished" type="button" class="buttonFixed button"
              onclick="Iframe.close(this)" value=":o.translate('close')"
              style=":svg('close', bg='12px 12px')"/>
      </div>

      <!-- The text that accompanies the progress bar -->
      <div id="pbText">::text or progress.divTranslate(o)</div>
     </div>''',

     css='''
       .pbAll { border:1px solid black; width:98%;
                margin:1.5em 0 1em 0; display:flex; gap:0 }
       .pbClose { text-align:center; margin-bottom:0.5em }
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

    viewAll = Px('''
     <x var="Progress=tool.ui.Progress;
             progs=Progress.listAll(tool)">

      <!-- There is currently no progress action -->
      <div if="not progs" class="discreet">:_('progress_nil')</div>

      <!-- Info about ongoing actions -->
      <table if="progs" class="small">

       <!-- Headers -->
       <tr>
        <th>Object</th><th>Action or transition</th><th>By</th>
        <th>Created</th><th>Status #</th><th>%</th><th></th>
       </tr>
       <!-- Data -->
       <x for="prog in progs">
        <!-- A first row for main data -->
        <tr var="iid=prog.iid; name=prog.name; target=tool.getObject(iid)">
         <td>
          <x>:iid</x> · 
          <x>:(target.getShownValue() or target.id) if target else '?'</x>
         </td>
         <td>:name</td>
         <td>:prog.login</td>
         <td>:tool.formatDate(prog.created)</td>
         <td>:prog.nb</td>
         <td>:prog.percentage</td>

         <!-- Allow to delete the status file -->
         <td>
          <img src=":svg('delete')" class="clickable iconS"
             var="url=f'{tool.url}/ui/Progress/clean?iid={iid}&amp;name={name}'"
            onclick=":f'askConfirm(%s,%s,%s)' %
                        (q('url'), q(url),q(Progress.CLEAN_TEXT))"/></td>
        </tr>
        <!-- A second row for text -->
        <tr>
         <td colspan="7">::prog.text or '-'</td>
        </tr>
       </x>
      </table>
     </x>''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
