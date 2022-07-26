'''PX stands for *P*ython *X*ML. It is a templating engine that reuses the pod
   engine to produce XML (including XHTML) from templates written as a mix of
   Python and XML.'''

# ~license~
# ------------------------------------------------------------------------------
import xml.sax

from appy.pod import Evaluator
from appy.pod.buffers import MemoryBuffer
from appy.px.px_parser import PxParser, PxEnvironment
from appy.shared.xml_parser import xmlPrologue, xhtmlPrologue

# Exception class --------------------------------------------------------------
class PxError(Exception): pass

# ------------------------------------------------------------------------------
class Px:
    '''Represents a (chunk of) PX code'''
    xmlPrologue = xmlPrologue
    xhtmlPrologue = xhtmlPrologue

    def __init__(self, content, isFileName=False, partial=True,
                 template=None, hook=None, prologue=None, unicode=True,
                 css=None, js=None, name=None):
        '''p_content is the PX code, as a string, or a file name if p_isFileName
           is True. If this code represents a complete XML file, p_partial is
           False. Else, we must surround p_content with a root tag to be able
           to parse it with a SAX parser.

           If this PX is based on another PX template, specify the PX template
           in p_template and the name of the p_hook where to insert this PX into
           the template PX.

           If a p_prologue is specified, it will be rendered at the start of the
           PX result.

           By default, a PX's result will be a unicode. If you want to get an
           encoded str instead, use p_unicode=False.

           You can specify, in p_css and p_js, PX-specific CSS styles and
           Javascript code, as strings. These strings will be surrounded by the
           appropriate HTML tag ("style" for p_css and "script" for p_js) and
           dumped just before the PX result. Note that if the PX is executed
           more than once, its corresponding p_css and p_js will only be dumped
           before the first PX result.
        '''
        # Get the PX content
        if isFileName:
            f = file(content)
            self.content = f.read()
            f.close()
        else:
            self.content = content
        # It this content a complete XML file, or just some part of it ?
        self.partial = partial
        # Is this PX based on a template PX ?
        self.template = template
        self.hook = hook
        # Is there some (XML, XHTML...) prologue to dump ?
        self.prologue = prologue
        # Will the result be unicode or str ?
        self.unicode = unicode
        # PX-specific CSS and JS code
        self.css = self.compact(css)
        self.js = self.compact(js)
        # A PX can have a name
        self.name = name
        # A PX can be profiled (see m_profile below)
        self.profiler = None
        # Parse the PX
        self.parse()

    def parse(self):
        '''Parses self.content and create the structure corresponding to this
           PX.'''
        if self.partial:
            # Surround the partial chunk with a root tag: it must be valid XML
            self.content = '<x>%s</x>' % self.content
        # Create a PX parser
        self.parser = PxParser(PxEnvironment(), self)
        # Parses self.content (a PX code in a string) with self.parser, to
        # produce a tree of memory buffers.
        try:
            self.parser.parse(self.content)
        except xml.sax.SAXParseException, spe:
            self.completeErrorMessage(spe)
            raise spe

    def compact(self, s):
        '''Removes single-line comments and unnecessary spaces in p_s,
           representing CSS or JS code.'''
        if not s: return
        r = []
        for line in s.split('\n'):
            line = line.strip()
            if not line.startswith('//'):
                r.append(line)
        return '\n'.join(r)

    def addCssJs(self, code, type):
        '''Adds this p_code, being CSS or JS, depending on p_type'''
        code = self.compact(code)
        existing = getattr(self, type)
        if existing:
            code = '%s\n%s' % (existing, code)
        setattr(self, type, code)

    def addCss(self, css): self.addCssJs(css, 'css')
    def addJs(self, js): self.addCssJs(js, 'js')

    def completeErrorMessage(self, parsingError):
        '''A p_parsingError occurred. Complete the error message with the
           erroneous line from self.content.'''
        # Split lines from self.content
        splitted = self.content.split('\n')
        i = parsingError.getLineNumber() - 1
        # Get the erroneous line, and add a subsequent line for indicating
        # the erroneous column.
        column = ' ' * (parsingError.getColumnNumber()-1) + '^'
        lines = [splitted[i], column]
        # Get the previous and next lines when present.
        if i > 0: lines.insert(0, splitted[i-1])
        if i < len(splitted)-1: lines.append(splitted[i+1])
        parsingError._msg += '\n%s' % '\n'.join(lines)

    def __call__(self, context, applyTemplate=True, isTemplate=False):
        '''Renders the PX.

           If the PX is based on a template PX, we have 2 possibilities.
           1. p_applyTemplate is True. This case corresponds to the initial
              call to the current PX. In this case we call the template with a
              context containing, in the hook variable, the current PX.
           2. p_applyTemplate is False. In this case, we are currently executing
              the PX template, and, at the hook, we must include the current PX,
              as is, without re-applying the template (else, an infinite
              recursion would occur).
        '''
        # Ensure PX-specific keys are in the context
        context['_ctx_'] = context
        context['_eval_'] = Evaluator
        # Include, in the context, variable names for "reserved" PX chars
        context['PIPE'] = '|'
        context['SEMICOLON'] = ';'
        # Also include the PX itself and remember the previously running PX
        px = context.get('_px_')
        if not isTemplate:
            context['_px_'] = self

        # This PX call is probably one among a series of such calls, sharing the
        # same p_context. Within this context, we add a sub-dict at key "rt"
        # (*r*un-*t*ime) for counting the number of times every PX is called.
        # It allows us to include PX-specific CSS and JS code only once.
        if '_rt_' not in context: context['_rt_'] = {}

        if self.hook and applyTemplate:
            # Call the template PX, filling the hook with the current PX
            context[self.hook] = self
            r = self.template(context, isTemplate=True)
        else:
            # Start profiling when relevant
            profiler = self.profiler
            if profiler: profiler.enter(self.name)
            # Create a Memory buffer for storing the result
            env = self.parser.env
            result = MemoryBuffer(env, None)
            # Execute the PX
            env.ast.evaluate(result, context)
            # Get the PX result
            r = result.content
            # Count this call and include CSS and JS code when relevant
            pxId = id(self)
            rt = context['_rt_']
            if pxId in rt:
                rt[pxId] += 1
            else:
                rt[pxId] = 1
                # This is the first time we execute it: include CSS and JS code
                # if present.
                if self.js: r = ('<script>%s</script>\n' % self.js) + r
                if self.css: r = ('<style>%s</style>\n' % self.css) + r
            # Include the prologue and manage encoding
            if self.prologue:
                r = self.prologue + r
            if not self.unicode:
                r = r.encode('utf-8')
            # Stop profiling when relevant
            if profiler: profiler.leave()
        # Restore the previous PX in the context
        if px: context['_px_'] = px
        # Return the result
        return r

    def override(self, content, partial=True):
        '''Overrides the content of this PX with a new p_content (as a
           string).'''
        self.partial = partial
        self.content = content
        # Parse again, with new content
        self.parse()

    def profile(self, name, profiler):
        '''Enables profiling of this PX, that will be named p_name in the
           p_profiler's output.'''
        self.name = name
        self.profiler = profiler

    @staticmethod
    def setBaseVariables(tool, context, obj):
        '''Sets, in p_context, all base variables required to execute standard
           Appy PXs.'''
        # The base object, available everywhere, is the tool
        ztool = tool.o
        # The request object (may be fake)
        req = ztool.REQUEST
        # Are we in the Appy popup ?
        inPopup = req.get('popup') == '1'
        # The currently published object and logged user
        obj = obj or ztool.getHomeObject(inPopup)
        zobj = obj and obj.o or None
        user = tool.user
        # The user language (2-letters ISO code)
        lang = ztool.getUserLanguage()
        # Is this language LTR or RTL ?
        dir = ztool.getLanguageDirection(lang)
        # The root database application object
        app = ztool.getApp()
        # Define the context
        r = {'tool':tool, 'ztool':tool.o, 'req':req, 'resp':req.RESPONSE,
             'obj':obj, 'zobj':zobj, 'inPopup':inPopup, '_':ztool.translate,
             'user':user, 'isAnon':user.login == 'anon', 'q':ztool.quote,
             'app':app, 'appName':ztool.getAppName(), 'appFolder':app.data,
             'url':ztool.getIncludeUrl, 'cfg':ztool.getProductConfig(True),
             'lang':lang, 'dir':dir,
             'dleft':(dir == 'ltr') and 'left' or 'right',
             'dright':(dir == 'ltr') and 'right' or 'left'}
        # Update p_context with the created context
        context.update(r)
        # Set the PX context available on the request object, too
        req.pxContext = context

    # Names of the base variables that must be present in the context of any
    # standard Appy PX.
    contextKeys = ('tool', 'ztool', 'req', 'resp', 'inPopup', '_', 'user',
                   'isAnon', 'q', 'app', 'appName', 'appFolder', 'url', 'cfg',
                   'lang', 'dir', 'dleft', 'dright')

    @classmethod
    def copyBaseVariables(klass, context, other):
        '''Copy base variables whose names are defined in p_klass.contextKeys
           from p_other to p_context.'''
        for key in klass.contextKeys:
            context[key] = other[key]
# ------------------------------------------------------------------------------
