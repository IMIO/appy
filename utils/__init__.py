'''Utility modules and functions for Appy'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from persistent.list import PersistentList
import traceback, mimetypes, subprocess, types

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def asDict(seq):
    '''Returns a dict whose keys are elements from p_seq ad values are None'''
    return {elem: None for elem in seq}

# Global variables - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
sequenceTypes = (list, tuple, PersistentList)
commercial = False

# On these layouts, using a gobal selector and switching from one option to the
# other is not allowed: it would reload the entire page. Examples are: the
# language selector, or the authentication context selector.
noSwitchLayouts = asDict(('edit', 'search'))

# MIME-related stuff - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
od = 'application/vnd.oasis.opendocument'
ms = 'application/vnd.openxmlformats-officedocument'
ms2 = 'application/vnd.ms'

mimeTypes = {'odt':  '%s.text' % od,
             'ods':  '%s.spreadsheet' % od,
             'doc':  'application/msword',
             'docx': '%s.wordprocessingml.document' % ms,
             'rtf':  'text/rtf',
             'pdf':  'application/pdf'
             }

mimeTypesExts = {
    '%s.text' % od:        'odt',
    '%s.spreadsheet' % od: 'ods',
    'application/msword':  'doc',
    'text/rtf':            'rtf',
    'application/pdf':     'pdf',
    'image/png':           'png',
    'image/jpeg':          'jpg',
    'image/pjpeg':         'jpg',
    'image/gif':           'gif',
    '%s.wordprocessingml.document' % ms: 'docx',
    '%s.spreadsheetml.sheet' % ms: 'xlsx',
    '%s.presentationml.presentation' % ms: 'pptx',
    '%s-excel' % ms2:      'xls',
    '%s-powerpoint' % ms2: 'ppt',
    '%s-word.document.macroEnabled.12' % ms2: 'docm',
    '%s-excel.sheet.macroEnabled.12' % ms2: 'xlsm',
    '%s-powerpoint.presentation.macroEnabled.12' % ms2: 'pptm'}

def getMimeType(fileName, default='application/octet-stream'):
    '''Tries to guess mime type from p_fileName'''
    res, encoding = mimetypes.guess_type(fileName)
    if not res:
        if fileName.endswith('.po'):
            res = 'text/plain'
            encoding = 'utf-8'
    if not res: return default
    if not encoding: return res
    return '%s;;charset=%s' % (res, encoding)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class CommercialError(Exception):
    '''Raised when some functionality is called from the commercial version but
       is available only in the free, open source version.'''
    MSG = 'This feature is not available in the commercial version. It is ' \
          'only available in the free, open source (GPL) version of Appy.'
    def __init__(self): Exception.__init__(self, self.MSG)

class MessageException(Exception):
    '''User-friendly exception'''
    # Message exceptions are raised when, due to some problem while handling a
    # browser request, the current traversal must be interrupted, but we don't
    # want a "technical" error to be raised (500). We don't want technical
    # details to be logged nor rendered to the UI, such as a Python traceback:
    # we simply want to display nice, translated info about the problem in a 200
    # response.

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class No:
    '''When you write a workflow condition method and you want to return False
       but you want to give to the user some explanations about why a transition
       can't be triggered, do not return False, return an instance of No
       instead. When creating such an instance, you can specify an error
       message.'''
    def __init__(self, msg): self.msg = msg
    def __bool__(self): return False
    def __repr__(self): return '<No: %s>' % self.msg

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def initMasterValue(v):
    '''Standardizes p_v as a list of strings, excepted if p_v is a method'''
    if callable(v): return v
    if not isinstance(v, bool) and not v: res = []
    elif type(v) not in sequenceTypes: res = [v]
    else: res = v
    return [str(v) for v in res]

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def encodeData(data, encoding=None):
    '''Applies some p_encoding to string p_data, but only if an p_encoding is
       specified.'''
    if not encoding: return data
    return data.encode(encoding)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def copyData(data, target, targetMethod, type='string', encoding=None,
             chunkSize=1024):
    '''Copies p_data to a p_target, using p_targetMethod. For example, it copies
       p_data which is a string containing the binary content of a file, to
       p_target, which can be a HTTP connection or a file object.

       p_targetMethod can be "write" (files) or "send" (HTTP connections) or ...
       p_type can be "string" or "file". In the latter case, one may, in
       p_chunkSize, specify the amount of bytes transmitted at a time.

       If an p_encoding is specified, it is applied on p_data before copying.

       Note that if the p_target is a Python file, it must be opened in a way
       that is compatible with the content of p_data, ie open('myFile.doc','wb')
       if content is binary.'''
    dump = getattr(target, targetMethod)
    if not type or (type == 'string'): dump(encodeData(data, encoding))
    elif type == 'file':
        while True:
            chunk = data.read(chunkSize)
            if not chunk: break
            dump(encodeData(chunk, encoding))

# List/dict manipulations  - - - - - - - - - - - - - - - - - - - - - - - - - - -
def splitList(l, sub):
    '''Returns a list that was build from list p_l whose elements were
       re-grouped into sub-lists of p_sub elements.

       For example, if l = [1,2,3,4,5] and sub = 3, the method returns
       [ [1,2,3], [4,5] ].'''
    res = []
    i = -1
    for elem in l:
        i += 1
        if (i % sub) == 0:
            # A new sub-list must be created
            res.append([elem])
        else:
            res[-1].append(elem)
    return res

class IterSub:
    '''Iterator over a list of lists'''
    def __init__(self, l):
        self.l = l
        self.i = 0 # The current index in the main list
        self.j = 0 # The current index in the current sub-list

    def __iter__(self): return self

    def __next__(self):
        # Get the next ith sub-list
        if (self.i + 1) > len(self.l): raise StopIteration
        sub = self.l[self.i]
        if (self.j + 1) > len(sub):
            self.i += 1
            self.j = 0
            return self.__next__()
        else:
            elem = sub[self.j]
            self.j += 1
            return elem

def getElementAt(l, cyclicIndex):
    '''Gets the element within list/tuple p_l that is at index p_cyclicIndex
       (int). If the index out of range, we do not raise IndexError: we continue
       to loop over the list until we reach this index.'''
    return l[cyclicIndex % len(l)]

def flipDict(d, byChar=False):
    '''Flips dict p_d: keys become values, values become keys. p_d is left
       untouched: a new, flipped, dict is returned.'''
    # If p_byChar is True, p_d's values must be strings, and, for every entry
    # of the form
    #                           'k': 'abcd'
    # the following entries are created:
    #               'a': 'k', 'b': 'k', 'c': 'k', 'd': 'k'
    r = {}
    # Browse dict p_d
    for k, v in d.items():
        if byChar:
            for char in v:
                r[char] = k
        else:
            r[v] = k
    return r

def addPair(name, value, d=None):
    '''Adds key-value pair (name, value) to dict p_d. If this dict is None, it
       returns a newly created dict.'''
    if d: d[name] = value
    else: d = {name: value}
    return d

def addListValue(d, key, value):
    '''p_d is supposed to be a dict whose values are lists. If a list already
       exists at this p_key, p_value is appended to it. Else, [value] is added
       at this p_key in p_d.'''
    if key in d:
        d[key].append(value)
    else:
        d[key] = [value]

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Traceback:
    '''Dumps the last traceback into a string'''

    @staticmethod
    def get(last=None, html=False):
        '''Gets the traceback as a string. If p_last is given (must be an
           integer value), only the p_last lines of the traceback will be
           included. It can be useful for pod/px tracebacks: when an exception
           occurs while evaluating a complex tree of buffers, most of the
           traceback lines concern uninteresting buffer/action-related recursive
           calls.'''
        r = traceback.format_exc(last)
        if html:
            from appy.xml.escape import Escape
            r = Escape.xhtml(r)
        return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def executeCommand(cmd, stdin=None, env=None, shell=False):
    '''Executes command p_cmd and returns a tuple (s_stdout, s_stderr)
       containing the data output by the subprocesss on stdout and stderr. p_cmd
       should be a list of args (the 1st arg being the command in itself, the
       remaining args being the parameters), but it can also be a string, too
       (see subprocess.Popen doc).'''
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=stdin,
                            stderr=subprocess.PIPE, env=env, shell=shell)
    out, err = proc.communicate()
    if isinstance(out, bytes):
        out = out.decode()
    if isinstance(err, bytes):
        err = err.decode()
    return out, err

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class ImageMagick:
    '''Allows to perform command-line calls to ImageMagick'''

    # The wrapper around any error message
    error = 'Error while executing ImageMagick command: %s. %s'

    @classmethod
    def run(class_, command):
        '''Executes this ImageMagick p_command, passed a list'''
        out, err = executeCommand(command)
        if err: raise Exception(class_.error % (' '.join(command), err))
        return out

    @classmethod
    def convert(class_, path, options):
        '''Calls the "convert" executable to apply some transform to an image
           whose p_path is passed.'''
        # p_options can be a list, or a string containing blank-separated
        # options.
        options = options.split() if isinstance(options, str) else options
        # Build the command. p_path could be a Pathlib.Path instance.
        path = str(path) if not isinstance(path, str) else path
        cmd = ['convert', path] + options
        cmd.append(path)
        # Execute it
        return class_.run(cmd)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def formatNumber(n, sep=',', precision=2, tsep=' ', removeTrailingZeros=False):
    '''Returns a string representation of number p_n, which can be a float
       or integer. p_sep is the decimal separator to use. p_precision is the
       number of digits to keep in the decimal part for producing a nice rounded
       string representation. p_tsep is the "thousands" separator.'''
    if n is None: return ''
    # Manage precision
    if precision is None:
        res = str(n)
    else:
        format = '%%.%df' % precision
        res = format % n
    # Use the correct decimal separator
    res = res.replace('.', sep)
    # Insert p_tsep every 3 chars in the integer part of the number
    splitted = res.split(sep)
    res = ''
    if len(splitted[0]) < 4: res = splitted[0]
    else:
        i = len(splitted[0])-1
        j = 0
        while i >= 0:
            j += 1
            res = splitted[0][i] + res
            if (j % 3) == 0:
                res = tsep + res
            i -= 1
    # Add the decimal part if not 0
    if len(splitted) > 1:
        try:
            decPart = int(splitted[1])
            if decPart != 0:
                res += sep + splitted[1]
            if removeTrailingZeros: res = res.rstrip('0')
        except ValueError:
            # This exception may occur when the float value has an "exp"
            # part, like in this example: 4.345e-05
            res += sep + splitted[1]
    return res

def roundNumber(n, base=5):
    '''Rounds an integer number p_n to an integer value being p_base'''
    return int(base * round(float(n)/base))

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def multicall(o, name, block, *args):
    '''Via multiple inheritance, method named p_name may exist, for instance
       p_o, on its base class from the framework AND on its base class from the
       app. This method may execute both methods, only one of them or does
       nothing if method name p_name is not defined at any level.'''
    # ~~~
    # This is typically used to call framework methods like "onEdit": the method
    # first calls the base method provided by the framework, then the method
    # defined in the app.
    # ~~~
    # If p_block is True, if the framework method returns False or equivalent,
    # the app method is not called.
    # ~~~
    # (block mode only) The method returns the result of the last called method,
    # or True if no method was called at all.
    # ~~~
    r = True if block else None
    bases = o.__class__.__bases__
    for i in (1, 0):
        if hasattr(bases[i], name):
            res = getattr(bases[i], name)(o, *args)
            if block:
                if i == 1 and not res: return
                r = res
            else:
                # If not in "block" mode, don't lose string results
                if isinstance(res, str):
                    if not isinstance(r, str):
                        r = res
                    else:
                        r += res
                elif not isinstance(r, str):
                    r = res
    return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def iconParts(icon):
    '''Retrieve the <app> and <name> parts for this p_icon'''
    if '/' in icon:
        base, icon = icon.split('/', 1)
    else:
        base = None
    return icon, base, icon.endswith('.svg')

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def termColorize(s, color='2'):
    '''Returns the colorized version of p_s, formatted to be rendered in a Unix
       terminal.'''
    return '\x1b[3%sm%s\x1b[0m' % (color, s)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
METH_KO = 'Method named "%s" does not exist on this %s instance.'

class Function:
    '''Utility methods for functions or methods'''

    @classmethod
    def getQualifiedName(class_, fun):
        '''Returns the name of p_fun (which is function or a method), prefixed
           with the name of its class.'''
        fun = fun if isinstance(fun, types.FunctionType) else fun.__func__
        return fun.__qualname__

    @classmethod
    def scall(class_, o, spec, raiseOnError=False):
        '''Calls a method on this p_o(bject)'''
        # p_spec is a method "specifier", of the form:
        #
        #            <method_name>:<arg1>:<arg2>:...
        #
        # Args are optional. Char ":" is interpreted as an arg specifier: it
        # cannot appear *within* an arg. All such args will be passed as strings
        # to the method.
        parts = spec.split(':')
        name = parts[0]
        args = parts[1:]
        # Execute the method, if it exists on p_o
        if hasattr(o, name):
            r = getattr(o, name)(*args)
        else:
            message = METH_KO % (name, o.class_.name)
            if raiseOnError: raise Exception(message)
            o.log(message, type='warning')
            r = None
        return r
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
