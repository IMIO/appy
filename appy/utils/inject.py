'''Injection of external content into XHTML chunks from Rich/Poor fields'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import re

from appy.xml.escape import Escape
from appy.utils.pretty import PrettyPrinter

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
INJECT_T_KO = 'Wrong injection type "p%s".'
PX_CTX_KO   = 'Cannot render "%s" - PX context is absent or incomplete.'
PX_KO       = 'Error while executing PX "%s": %s'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Injector:
    '''Implements the "injection" mechanism in a Rich/Poor field'''

    # More information on field "inject", defined in class
    # appy.model.fields.rich.Rich.

    # Injector-specific error class
    class Error(Exception): pass

    # Regular expression allowing to identify, within a Rich value, an injection
    # link.
    injectLink = re.compile(r'<a href="(.*?)">p([xy]):\s*(.*?)\s*</a>')

    @classmethod
    def executePx(class_, specifier, o):
        '''Executes the PX denoted by p_specifier'''
        # It is not possible to find the current PX context, if there is no
        # p_o(bject).
        if o is None: return ''
        # It is not possible to execute the PX if the current PX context is
        # absent or incomplete.
        try:
            Px = o.traversal.context.Px
            if Px is None:
                raise class_.Error(PX_CTX_KO % specifier)
        except AttributeError as err:
            raise class_.Error(PX_CTX_KO % specifier)
        # Execute the PX
        try:
            return Px.callFromSpec(specifier, o)
        except Px.Error as err:
            raise class_.Error(PX_KO % (specifier, str(err)))

    @classmethod
    def pxError(class_, message):
        '''Returns this PX-related error m_message, wrapped in a "pre" tag'''
        return '<pre>%s</pre>' % Escape.xhtml(message)

    @classmethod
    def getContent(class_, url, type, specifier, o=None):
        '''A link has been found in a chunk of XHTML code, with this p_url, of
           this p_type ("x" meaning "px:", "y" meaning "py:"), and this
           p_specifier (=the part following "px:" or "py:" in the tag's
           content). This method returns the corresponding content.'''
        if type == 'y':
            # A link to an external Python source code file
            r = PrettyPrinter.getFromUrl(url, specifier, o=o)
        elif type == 'x':
            # p_specifier denotes a PX. Get it and call it.
            try:
                r = class_.executePx(specifier, o)
            except class_.Error as err:
                r = class_.pxError(str(err))
        else:
            r = class_.pxError(INJECT_T_KO % type)
        return r

    @classmethod
    def run(class_, xhtml, o=None):
        '''Perform Rich field injections within this chunk of p_xhtml code'''
        return class_.injectLink.sub(
                 lambda m: class_.getContent(*m.groups(), o=o), xhtml)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
