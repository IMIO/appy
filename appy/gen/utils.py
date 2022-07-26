# ------------------------------------------------------------------------------
import re, os, os.path, base64, urllib, types

from appy import Object
from appy.px import Px
from appy.shared import utils as sutils

# Function for creating a Zope object ------------------------------------------
def createObject(folder, id, className, appName, wf=True, noSecurity=False,
                 initialComment='', initialState=None):
    '''Creates, in p_folder, object with some p_id. Object will be an instance
       of p_className from application p_appName. In a very special case (the
       creation of the config object), computing workflow-related info is not
       possible at this time. This is why this function can be called with
       p_wf=False.'''
    exec 'from Products.%s.%s import %s as ZopeClass' % \
         (appName, className, className)
    # Get the tool. It may not be present yet, maybe are we creating it now.
    if folder.meta_type.endswith('Folder'):
        # p_folder is a standard Zope (temp) folder
        tool = getattr(folder, 'config', None)
    else:
        # p_folder is an instance of a gen-class
        tool = folder.getTool()
    # Get the currently logged user
    user = None
    if tool: user = tool.getUser()
    # Checks whether the user may create this object if security is enabled
    if not noSecurity:
        klass = ZopeClass.wrapperClass.__bases__[-1]
        if not tool.userMayCreate(klass, checkInitiator=True):
            from AccessControl import Unauthorized
            raise Unauthorized("User can't create instances of %s" % \
                               klass.__name__)
    # Prevent object creation if "id" refers to an existing object
    if tool and tool.getObject(id, brain=True):
        raise Exception('object with id "%s" already exist.' % id)
    # Create the object
    obj = ZopeClass(id)
    folder._objects = folder._objects + ({'id':id, 'meta_type':className},)
    folder._setOb(id, obj)
    obj = folder._getOb(id) # Important. Else, obj is not really in the folder.
    obj.portal_type = className
    obj.id = id
    # If no user object is there, we are at startup, before default User
    # instances are created.
    userId = user and user.login or 'system'
    obj.creator = userId
    from DateTime import DateTime
    obj.created = DateTime()
    obj.modified = obj.created
    from persistent.mapping import PersistentMapping
    obj.__ac_local_roles__ = PersistentMapping({ userId: ['Owner'] })
    if wf: obj.initializeWorkflow(initialComment, initialState)
    return obj

# ------------------------------------------------------------------------------
upperLetter = re.compile('[A-Z]')
def produceNiceMessage(msg):
    '''Transforms p_msg into a nice msg.'''
    res = ''
    if msg:
        res = msg[0].upper()
        for c in msg[1:]:
            if c == '_':
                res += ' '
            elif upperLetter.match(c):
                res += ' ' + c.lower()
            else:
                res += c
    return res

# ------------------------------------------------------------------------------
class SomeObjects:
    '''Represents a bunch of objects retrieved from a reference or a query in
       the catalog.'''
    DEAD_BRAIN = 'brain removed for missing object@%s.'

    def __init__(self, objects=None, batchSize=None, startNumber=0,
                 noSecurity=False):
        # The objects (more precisely, p_objects start being brains)
        self.objects = objects or []
        # self.objects may only represent a part of all available objects
        self.totalNumber = len(self.objects)
        # self.objects' max length
        self.batchSize = batchSize or self.totalNumber
        # The index of first object in self.objects in the whole list
        self.startNumber = startNumber
        self.noSecurity = noSecurity
        # Some brains may correspond to unexistent objects
        self.deadBrains = None

    def addDeadBrain(self, brain):
        '''Adds p_brain to the list of dead brains. More precisely, p_brain is
           not a brain but a brain's path.'''
        dead = self.deadBrains
        if dead:
            dead.append(brain)
        else:
            self.deadBrains = [brain]

    def removeDeadBrains(self, tool):
        '''Removes dead brains from the catalog'''
        catalog = tool.getPath('/catalog')
        for path in self.deadBrains:
            catalog.uncatalog_object(path)
            tool.log(self.DEAD_BRAIN % path, noUser=True, type='error')
            self.totalNumber -= 1

    def brainsToObjects(self, tool):
        '''self.objects has been populated from catalog's brains, not from true
           objects. This method turns them (or some of them depending on
           batchSize and startNumber) into real objects.

           If self.noSecurity is True, it gets the objects even if the logged
           user does not have the right to get them.'''
        # Browse (a sub-set of) brains
        start = self.startNumber
        total = self.totalNumber
        i = start
        end = start + self.batchSize
        # Prepare data structures
        brains = self.objects
        r = []
        noSecurity = self.noSecurity
        while (i < end) and (i < total):
            brain = brains[i]
            obj = tool.toObject(brain, noSecurity=True)
            if obj is None:
                # A dead brain. Add it to the list: we will remove it
                # afterwards. If we remove dead brains while browsing brains, it
                # produces problems within the list of brains and all brains are
                # not walked.
                self.addDeadBrain(brain.getPath())
            else:
                r.append(obj)
            i += 1
        # Replace brains with (found) objects
        self.objects = r
        if self.deadBrains: self.removeDeadBrains(tool)

# ------------------------------------------------------------------------------
def splitIntoWords(text, ignore=2, ignoreNumbers=False, words=None):
    '''Splits p_text into words. If p_words is None, it returns the set of
       words (no duplicates). Else, it adds one entry in the p_words dict for
       every encountered word.

       Words whose length is <= p_ignore are ignored, excepted, if
       p_ignoreNumbers is False, words being numbers.'''
    # Split p_text into words
    r = text.split()
    # Browse words in reverse order and remove shorter ones
    i = len(r) - 1
    keepIt = None
    while i > -1:
        word = r[i]
        # Keep this word or not ?
        if len(word) <= ignore:
            keepIt = not ignoreNumbers and word.isdigit()
        else:
            keepIt = True
        # Update "r" or "words" accordingly
        if words != None:
            # Add the word to "words" when we must keep it
            if keepIt:
                words[word] = None
        else:
            # Remove the word from "r" if we must not keep it
            if not keepIt:
                del r[i]
        i -= 1
    # Return the result as a set when relevant
    if words == None:
        return set(r)

# ------------------------------------------------------------------------------
class Keywords:
    '''This class allows to handle keywords that a user enters and that will be
       used as basis for performing requests in a TextIndex/XhtmlIndex.'''
    toRemove = '?-+*()'
    def __init__(self, keywords, operator='AND', ignore=2):
        # Clean the p_keywords that the user has entered
        words = sutils.normalizeText(keywords)
        if words == '*': words = ''
        for c in self.toRemove: words = words.replace(c, ' ')
        self.keywords = splitIntoWords(words, ignore=ignore)
        # Store the operator to apply to the keywords (AND or OR)
        self.operator = operator

    def merge(self, other, append=False):
        '''Merges our keywords with those from p_other. If p_append is True,
           p_other keywords are appended at the end; else, keywords are appended
           at the begin.'''
        for word in other.keywords:
            if word not in self.keywords:
                if append:
                    self.keywords.append(word)
                else:
                    self.keywords.insert(0, word)

    def get(self):
        '''Returns the keywords as needed by the TextIndex.'''
        if self.keywords:
            op = ' %s ' % self.operator
            return op.join(self.keywords)+'*'
        return ''

# ------------------------------------------------------------------------------
def getClassName(klass, appName=None):
    '''Generates, from appy-class p_klass, the name of the corresponding
       Zope class. For some classes, name p_appName is required: it is
       part of the class name.'''
    moduleName = klass.__module__
    if (moduleName == 'appy.gen.model') or moduleName.endswith('.wrappers'):
        # This is a model (generation time or run time)
        res = appName + klass.__name__
    elif klass.__bases__ and (klass.__bases__[-1].__module__=='appy.gen.utils'):
        # This is a customized class (inherits from appy.gen.Tool, User,...)
        res = appName + klass.__bases__[-1].__name__
    else: # This is a standard class
        res = klass.__module__.replace('.', '_') + '_' + klass.__name__
    return res

# ------------------------------------------------------------------------------
def callMethod(obj, method, klass=None, cache=True):
    '''This function is used to call a p_method on some Appy p_obj. m_method
       can be an instance method on p_obj; it can also be a static method. In
       this latter case, p_obj is the tool and the static method, defined in
       p_klass, will be called with the tool as unique arg.

       A method cache is implemented on the request object (available at
       p_obj.request). So while handling a single request from the ui, every
       method is called only once. Some method calls must not be cached (ie,
       values of Computed fields). In this case, p_cache will be False.'''
    rq = obj.request
    # Disable cache if the request is fake. Indeed, caching is interesting when
    # we are managing a real ui request.
    if rq.__class__.__name__ == 'Object':
        cache = False
    else:
        # Create the method cache if it does not exist on the request
        if not hasattr(rq, 'methodCache'): rq.methodCache = {}
    # If m_method is a static method or an instance method, unwrap the true
    # Python function object behind it.
    methodType = method.__class__.__name__
    if methodType == 'staticmethod':
        method = method.__get__(klass)
    elif (methodType == 'instancemethod') and \
         (type(method.im_self) != types.ClassType):
        # An instance method. If im_self is a class, it is a classmethod.
        method = method.im_func
    # Disable caching for lambda functions
    funName = method.func_name
    if funName == '<lambda>': cache = False
    # Call the method if cache is not needed
    if not cache: return method(obj)
    # If first arg of method is named "tool" instead of the traditional "self",
    # we cheat and will call the method with the tool as first arg. This will
    # allow to consider this method as if it was a static method on the tool.
    # Every method call, even on different instances, will be cached in a unique
    # key.
    cheat = False
    if not klass and (method.func_code.co_varnames[0] == 'tool'):
        prefix = obj.klass.__name__
        obj = obj.tool
        cheat = True
    # Build the key of this method call in the cache.
    # First part of the key: the p_obj's uid (if p_method is an instance method)
    # or p_className (if p_method is a static method).
    if not cheat:
        if klass:
            prefix = klass.__name__
        else:
            prefix = obj.id
    # Second part of the key: p_method name
    key = '%s:%s' % (prefix, funName)
    # Return the cached value if present in the method cache
    if key in rq.methodCache:
        return rq.methodCache[key]
    # No cached value: call the method, cache the result and return it
    res = method(obj)
    rq.methodCache[key] = res
    return res

# Functions for manipulating the authentication cookie -------------------------
def readCookie(request, onResponse=False):
    '''Returns the tuple (login, password, ctx) read from the authentication
       cookie received in p_request. If no user is logged, its returns
       (None, None, None).'''
    if not onResponse:
        cookie = request.get('_appy_', None)
    else:
        appyCookie = request.RESPONSE.cookies.get('_appy_')
        if appyCookie:
            cookie = appyCookie['value']
        else:
            cookie = None
    if not cookie: return None, None, None
    cookieValue = base64.decodestring(urllib.unquote(cookie))
    if ':' not in cookieValue: return None, None, None
    # Extract the context from the cookieValue
    r, context = cookieValue.rsplit(':', 1)
    # Maintain compatibility with old-style, context-free cookies
    if ':' not in r:
        r = cookieValue
        context = None
    # Extract login and password
    login, password = r.split(':', 1)
    return login, password, context

def writeCookie(login, password, ctx, request):
    '''Encode p_login, p_password and p_ctx into a cookie'''
    res = base64.encodestring('%s:%s:%s' % (login,password,ctx or '')).rstrip()
    request.RESPONSE.setCookie('_appy_', urllib.quote(res), path='/')

def updateCookie(request, ctx, onResponse=False):
    '''Updates the authentication context within the Appy cookie. If
       p_onResponse is True, we get the cookie from the response object instead
       of the request object.'''
    login, password, oldCtx = readCookie(request, onResponse=onResponse)
    if login is None:
        # There is no cookie. When SSO is enabled, cookies are normally not
        # used, excepted if an authentication context comes into play. In that
        # case, the cookie is only used to store this context. In order to
        # represent this fact, set, in the cookie, the user login as "_s_s_o_".
        # Such a cookie means: "this is a special cookie, only used to store the
        # authentication context. Check SSO to get the user login".
        login = '_s_s_o_'
    writeCookie(login, password, ctx, request)

# ------------------------------------------------------------------------------
def initMasterValue(v):
    '''Standardizes p_v as a list of strings, excepted if p_v is a method'''
    if callable(v): return v
    if not isinstance(v, bool) and not v: res = []
    elif type(v) not in sutils.sequenceTypes: res = [v]
    else: res = v
    return [str(v) for v in res]

# ------------------------------------------------------------------------------
class No:
    '''When you write a workflow condition method and you want to return False
       but you want to give to the user some explanations about why a transition
       can't be triggered, do not return False, return an instance of No
       instead. When creating such an instance, you can specify an error
       message.'''
    def __init__(self, msg): self.msg = msg
    def __nonzero__(self): return False
    def __repr__(self): return '<No: %s>' % self.msg

class MessageException(Exception): pass

# ------------------------------------------------------------------------------
class Model: pass
class Tool(Model):
    '''Subclass me to extend or modify the Tool class'''
class User(Model):
    '''Subclass me to extend or modify the User class'''

# ------------------------------------------------------------------------------
class Collapsible:
    '''Represents a chunk of HTML code that can be collapsed/expanded via
       clickable icons.'''
    # Various sets of icons can be used. Each one has a CSS class in appy.css
    iconSets = {'expandCollapse': Object(expand='expand', collapse='collapse'),
                'showHide': Object(expand='show', collapse='hide'),
                'showHideInv': Object(expand='hide', collapse='show')}

    # Icon allowing to collapse/expand a chunk of HTML
    px = Px('''
     <img var="coll=collapse; icons=coll.icons"
          id=":'%s_img' % coll.id" align=":coll.align" class=":coll.css"
          onclick=":'toggleCookie(%s,%s,%s,%s,%s)' % (q(coll.id), \
                    q(coll.display), q(coll.default), \
                    q(icons.expand), q(icons.collapse))"
       src=":coll.expanded and url(icons.collapse) or url(icons.expand)"/>''')

    def __init__(self, id, request, default='collapsed', display='block',
                 icons='expandCollapse', align='left'):
        '''p_display is the value of style attribute "display" for the XHTML
           element when it must be displayed. By default it is "block"; for a
           table it must be "table", etc.'''
        self.id = id # The ID of the collapsible HTML element
        self.request = request # The request object
        self.default = default
        self.display = display
        self.align = align
        # Must the element be collapsed or expanded ?
        self.expanded = request.get(id, default) == 'expanded'
        self.style = 'display:%s' % (self.expanded and self.display or 'none')
        # The name of the CSS class depends on the set of applied icons
        self.css = icons
        self.icons = self.iconSets[icons]

# ------------------------------------------------------------------------------
class LinkTarget:
    '''Represents information about the target of an HTML "a" tag'''

    def __init__(self, klass=None, back=None, forcePopup=False):
        '''The HTML "a" tag must lead to a page for viewing or editing an
           instance of some p_klass. If this page must be opened in a popup
           (depends on attribute p_klass.popup), and if p_back is specified,
           when coming back from the popup, we will ajax-refresh a DOM node
           whose ID is specified in p_back.'''
        # The link leads to a instance of some p_klass
        self.klass = klass
        # Does the link lead to a popup ?
        if forcePopup:
            toPopup = True
        else:
            toPopup = klass and hasattr(klass, 'popup')
        # Determine the target of the "a" tag
        self.target = toPopup and 'appyIFrame' or '_self'
        # If the link leads to a popup, a "onClick" attribute must contain the
        # JS code that opens the popup.
        if toPopup:
            # Create the chunk of JS code to open the popup
            size = getattr(klass, 'popup', '350px')
            if isinstance(size, basestring):
                params = "%s,null" % size[:-2] # Width only
            else: # Width and height
                params = "%s,%s" % (size[0][:-2], size[1][:-2])
            # If p_back is specified, included it in the JS call
            if back: params += ",'%s'" % back
            self.onClick = "openPopup('iframePopup',null,%s)" % params
        else:
            self.onClick = ''

    def getOnClick(self, back):
        '''Gets the "onClick" attribute, taking into account p_back DOM node ID
           that was unknown at the time the LinkTarget instance was created.'''
        # If we must not come back from a popup, return an empty string
        r = self.onClick
        if not r: return r
        return r[:-1] + ",'%s')" % back

    def __repr__(self):
        return '<LinkTarget for=%s,target=%s,onClick=%s>' % \
               (self.klass.__name__, self.target, self.onClick or '-')
# ------------------------------------------------------------------------------
