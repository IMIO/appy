#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import time, uuid
from appy.utils import Traceback

# POD-specific constants - - - - - - - - - - - - - - - - - - - - - - - - - - - -
XHTML_HEADINGS = ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')
XHTML_LISTS    = ('ol', 'ul')

# "para" is a meta-tag representing p, div, blockquote or address
XHTML_PARA_TAGS = XHTML_HEADINGS + ('p', 'div', 'blockquote', 'address', 'para')
XHTML_INNER_TAGS      = ('b', 'i', 'u', 'em', 'span')
XHTML_UNSTYLABLE_TAGS = ('li', 'a')
XHTML_META_TAGS       = {'p': 'para', 'div': 'para',
                         'blockquote': 'para', 'address': 'para'}

# Cell-like tags (including "li")
XHTML_CELL_TAGS = ('th', 'td', 'li')

# Default output formats for POD templates, by template type
formatsByTemplate = {'.odt': ('pdf', 'doc', 'docx', 'odt'),
                     '.ods': ('xls', 'xlsx', 'ods')}

# UI-friendly acronyms for output formats
uiFormats = {'pdf':'PDF', 'doc':'DOC', 'docx':'DOX', 'odt':'ODT',
             'xls':'XLS', 'xlsx':'XLX', 'ods':'ODS', 'csv':'CSV'}

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Evaluator:
    '''Wrapper around the built-in Python function "eval"'''

    @classmethod
    def run(class_, expression, context):
        '''Evaluates p_expression in this p_context'''
        # p_context can be a standard dict or an instance of class
        # appy.model.utils.Object. In this latter case, although it implements
        # dict-like methods, we prefer to unwrap its dict instead of using it
        # directly as context, because it does not raise a KeyError when a key
        # lookup produces no result, but returns None instead.
        context = context if isinstance(context, dict) else context.__dict__
        # Evaluate p_expression
        return eval(expression, context)
        # Note that the "eval" function adds, within p_context, if not already
        # present, the Python built-ins at key '__builtins__'.
        # context['__builtins__'] is similar to the homonym entry in dict
        # globals().

    @classmethod
    def updateContext(class_, context):
        '''This standard evaluator does not need to update the p_context'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class PodError(Exception):
    '''Base pod exception'''

    @staticmethod
    def dumpTraceback(buffer, tb, removeFirstLine):
        # If this error came from an exception raised by pod (p_removeFirstLine
        # is True), the text of the error may be very long, so we avoid having
        # it as error cause + in the first line of the traceback.
        linesToRemove = removeFirstLine and 3 or 2
        i = 0
        for tLine in tb.splitlines():
            i += 1
            if i > linesToRemove:
                buffer.write('<text:p>')
                try:
                    buffer.dumpContent(tLine)
                except UnicodeDecodeError:
                    buffer.dumpContent(tLine.decode('utf-8'))
                buffer.write('</text:p>')

    @staticmethod
    def dump(buffer, message, withinElement=None, removeFirstLine=False,
             dumpTb=True, escapeMessage=True):
        '''Dumps the error p_message in p_buffer or in r_ if p_buffer is None'''
        if withinElement:
            buffer.write('<%s>' % withinElement.OD.nsName)
            for subTag in withinElement.subTags:
                buffer.write('<%s>' % subTag.nsName)
        buffer.write('<office:annotation><dc:creator>POD</dc:creator>' \
          '<dc:date>%s</dc:date><text:p>' % time.strftime('%Y-%m-%dT%H:%M:%S'))
        if escapeMessage:
            buffer.dumpContent(message)
        else:
            buffer.write(message)
        buffer.write('</text:p>')
        if dumpTb:
            # We don't dump the traceback if it is an expression error (it is
            # already included in the error message).
            PodError.dumpTraceback(buffer, Traceback.get(), removeFirstLine)
        buffer.write('</office:annotation>')
        if withinElement:
            subTags = withinElement.subTags[:]
            subTags.reverse()
            for subTag in subTags:
                buffer.write('</%s>' % subTag.nsName)
            buffer.write('</%s>' % withinElement.OD.nsName)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def getUuid(removeDots=False, prefix='f'):
    '''Get a unique ID (ie, for images/documents to be imported into an ODT
       document).'''
    r = uuid.uuid4().hex
    if removeDots: r = r.replace('.', '')
    return '%s%s' % (prefix, r)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
