#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import io
from DateTime import DateTime # Just to have it in the interpreter context
from contextlib import redirect_stdout

from appy.px import Px
from appy.utils import Traceback
from appy.xml.escape import Escape
from appy.model.fields import Field
from appy.utils import string as sutils
from appy.database.operators import or_, and_, in_

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
COMMIT   = 'Committed from %d: %s'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Python(Field):
    '''Through-the-web Python interpreter'''

    # Some elements will be traversable
    traverse = Field.traverse.copy()

    # All layouts produce the same rendering. That being said, in 99% of all
    # situations, only the "view" layout will be used.
    view = cell = buttons = edit = Px('''
     <div class="python"
          var="prefix='%s_%s' % (o.iid, field.name);
               hook='%s_output' % prefix">
      <div id=":hook"></div>
      <div class="prompt">&gt;&gt;&gt;</div>
      <input type="text" id=":'%s_input' % prefix" autocomplete="false"
         onkeydown=":'if (event.keyCode==13) onPyCommand(%s, this)' % q(hook)"/>
      <div class="iactions">
        <input type="checkbox" id=":'%s_commit' % prefix"/>
        <label lfor=":'%s_commit' % prefix">Commit</label>
      </div>
      <script>:"document.getElementById('%s_input').focus();%s" %
               (prefix, field.getAjaxData(hook, o))</script>
     </div>''',

     js='''
       onPyCommand = function(hook, input){
         var command = input.value.trim();
         if (!command) return;
         input.value = '';
         // Misuse the 'exit' command to clear the command history
         if (command == 'exit') {
           document.getElementById(hook).innerHTML = '';
           return;
         }
         // Must a database commit occur ?
         var id = hook.substring(0, hook.length-6) + 'commit',
             cb = document.getElementById(id),
             commit = cb.checked.toString();
         cb.checked = false;
         askAjax(hook, null, {'command':command, 'commit':commit});
       }

       onPyOutput = function(rq, injected) {
         // Scroll to ensure the input field is still visible
         injected.nextSibling.nextSibling.scrollIntoView();
       }

       class CommandHistory {
         constructor(){
           this.commands = []; // Commands already typed in the interpreter
           this.i = -1;        // The currently select command
         }
       }''',

     css='''
      .python { background-color:|pythonBgColor|; color:|brightColor|;
         padding:5px; font-family:monospace; height:40vh; overflow-y:auto }
      .prompt { display:inline; padding-right:10px }
      .python input[type=text] { padding:0; margin:0; border:none;
         color:|brightColor|; font-family:monospace; width:80% }
      .iactions { float:right; padding-bottom:10px }
      .iactions label { color:|brightColor|; padding-right:10px }
      .iactions input { background-color:#eee; opacity:0.6 }
      .commitMsg { font-style:italic; color:|altColor| }
     ''')

    # There is no possibility to render this field on layout "search"
    search = ''

    def __init__(self, show='view', renderable=None, page='main', group=None,
      layouts=None, move=0, readPermission='read', writePermission='write',
      width=None, height=None, colspan=1, master=None, masterValue=None,
      focus=False, mapping=None, generateLabel=None, label=None, view=None,
      cell=None, buttons=None, edit=None, xml=None, translations=None):
        # Call the base constructor
        Field.__init__(self, None, (0,1), None, None, show, renderable, page,
          group, layouts, move, False, True, None, None, False, None,
          readPermission, writePermission, width, height, None, colspan, master,
          masterValue, focus, False, mapping, generateLabel, label, None, None,
          None, None, False, False, view, cell, buttons, edit, xml,
          translations)

    def getAjaxData(self, hook, o):
        '''Initializes an AjaxData object on the DOM node corresponding to this
           field.'''
        params = {'hook': hook}
        params = sutils.getStringFrom(params)
        # Complete params with default parameters
        return "new AjaxData('%s/%s/onCommand', 'GET', %s, '%s', null, null, " \
               "onPyOutput, true)" % (o.url, self.name, params, hook)

    def formatOutput(self, output, fromExpr):
        '''Formats this Python command p_output. p_fromExpr is True if it was
           the result of evaluating a Python expression. p_fromExpr is False in
           any other case: p_output was collected from the redirected stdout, or
           was a no-result following the execution of a Python statement.'''
        if fromExpr:
            # Surround a string with quotes
            if isinstance(output, str):
                r = "'%s'" % output.replace("'", "\\'")
            else:
                # Convert it to a string
                r = repr(output)
        else:
            r = output
        # XHTML-escape it
        return Escape.xhtml(r)

    def doCommit(self, o, mustCommit, command):
        '''If a database commit is required (p_mustCommit is True), do it, log
           if and return a message to the UI.'''
        if mustCommit:
            o.log(COMMIT % (o.iid, command))
            o.H().commit = True
            r = '<div class="commitMsg">Commit done and logged.</div>'
        else:
            r = ''
        return r

    traverse['onCommand'] = 'user:admin'
    def onCommand(self, o):
        '''Evaluates the Python expression entered into the UI'''
        command = o.req.command
        # Redirect stdout to a StringIO
        with io.StringIO() as buf, redirect_stdout(buf):
            try:
                fromExpr = True
                try:
                    r = eval(command)
                    if r is None:
                        # If the result of evaluating the command is None and
                        # something was dumped on stdout, return this output.
                        output = buf.getvalue()
                        if output:
                            r = output
                            fromExpr = False
                except SyntaxError as se:
                    # Try interpreting the command as a statement
                    exec(command)
                    r = ''
                    fromExpr = False
                # Format the result
                r = self.formatOutput(r, fromExpr)
                # Is commit required ?
                commit = o.req.commit == 'true'
            except Exception as e:
                r = Traceback.get(html=True)
                commit = False
        # Manage commit
        message = self.doCommit(o, commit, command)
        # Return the command echoed + the command output
        return '<div>&gt;&gt;&gt; %s</div>%s%s' % \
               (Escape.xhtml(command), r, message)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
