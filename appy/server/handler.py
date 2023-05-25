'''A handler is responsible for handling a HTTP request'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from http import HTTPStatus
from http import client as hc
import re, socket, threading, urllib.parse, transaction

from appy.utils import Function
from appy.model.base import Base
from appy.server.guard import Guard
from appy.server.error import Error
from appy.server.static import Static
from appy.server.request import Request
from appy.model.utils import Object as O
from appy.server.response import Response
from appy.server.languages import Languages
from appy.server.traversal import Traversal
from appy.pod.actions import EvaluationError
from appy.utils import asDict, MessageException

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
TRANS_RETRY = 'Conflict occurred (%s). Replay transaction (#%d)...'
TRANS_ERR   = 'Unresolved conflict occurred (%s).'
SOCK_TO     = 'Client socket timeout: %s.'
RQ_LINE_KO  = 'Bad request line "%s".'
HTTP_V_KO   = 'Wrong HTTP version "%s".'
HTTP_V_UNS  = 'Unsupported HTTP version "%s".'
H_METH_KO   = 'Wrong HTTP method "%s".'
HEAD_TOO_LG = 'Line too long: %s...'
HEAD_T_MANY = 'Too many headers: %s...'
T_READ_SOCK = 'Reading request line on rfile...'
T_READ_GOT  = 'Got request line: %s (length: %d)'
T_AL_REG    = 'Thread %d was already in registry.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class MethodsCache(dict):
    '''A dict of method results, used to avoid executing more than once the same
       method, while handling a request. Every handler implements such a
       cache.'''

    def call(self, o, method, class_=None, cache=True):
        '''Call p_method on some p_o(bject). m_method can be an instance method
           on p_o; it can also be a static method. In this latter case, p_o is
           the tool and the static method, defined in p_class_, will be called
           with the tool as unique arg.

           If the method result is already in the cache, it will simply be
           returned. Else, the method will be executed, its result will be
           stored in the cache and returned.

           If p_cache is False, caching is disabled and the method is always
           executed.
        '''
        # Disable the cache for lambda functions
        name = method.__name__
        cache = False if name == '<lambda>' else cache
        # Call the method if cache is not needed
        if not cache: return method(o)
        # If first arg of method is named "tool" instead of the traditional
        # "self", we cheat and will call the method with the tool as first arg.
        # This will allow to consider this method as if it was a static method
        # on the tool.
        cheat = False
        if not class_ and method.__code__.co_varnames[0] == 'tool':
            prefix = o.class_.name
            o = o.tool
            cheat = True
        # Build the unique key allowing to store method results in the cache.
        # The key is of the form
        #                    <object id>:<method name>
        # In the case of a static method, "object id" is replaced with the class
        # name.
        if not cheat:
            prefix = class_.__name__ if class_ else str(o.iid)
            # Prefix the method name with the name of its class. Indeed,
            # p_method may not belong to p_o's class.
            name = Function.getQualifiedName(method)
        key = '%s:%s' % (prefix, name)
        # Return the cached value if present in the method cache
        if key in self: return self[key]
        # No cached value: call the method, cache the result and return it
        r = method(o)
        self[key] = r
        return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Handler:
    '''Abstract handler'''

    # A handler handles an incoming HTTP request. Class "Handler" is the
    # abstract base class for all concrete handlers, as defined hereafter.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #  HttpHandler   | Handles HTTP requests. In the Appy HTTP server, every
    #                | request is managed by a thread. At server startup, a
    #                | configurable number of threads are run and are waiting
    #                | for requests. Every time a request hits the server, it is
    #                | assigned to a thread, that instantiates a handler and
    #                | manages the request.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # VirtualHandler | When the Appy HTTP server starts, it is like if he had to
    #                | handle a virtual request. For that special case, an for
    #                | other similar cases, like scheduler jobs, an instance of
    #                | VirtualHandler is created.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # In the following static attribute, we maintain a registry of the currently
    # instantiated handlers. Every handler is keyed by the ID of the thread that
    # is running it.
    registry = {}

    # Make some names available here
    Guard = Guard
    Static = Static
    Traversal = Traversal

    # Every handler can use a special char allowing to easily identify entries
    # produced from it in log files.
    logChar = ''

    @classmethod
    def add(class_, handler):
        '''Adds a new p_handler into the registry'''
        id = threading.get_ident()
        # If the currently running thread is already in the registry, overwrite
        # the entry with that new p_handler.
        r = id in class_.registry
        class_.registry[id] = handler
        # Return True if the thread was already mentioned in the registry
        # (this should not happen).
        return r

    @classmethod
    def remove(class_):
        '''Remove p_handler from the registry'''
        del class_.registry[threading.get_ident()]

    @classmethod
    def get(class_):
        '''Returns the handler for the currently executing thread'''
        return class_.registry[threading.get_ident()]

    # Make the Language class available in the handler namespace
    Languages = Languages

    def init(self):
        '''Define attributes which are common to any handler'''
        # A lot of object methods are executed while handling a request. Dict
        # "methods" hereafter caches method results: it avoids executing more
        # than once the same method. Only methods without args are cached, like
        # methods defined on field attributes such as "show".
        self.methods = MethodsCache()
        # Appy and apps may use the following object to cache any other element
        self.cache = O()
        # Create a guard, a transient object for managing security
        self.guard = Guard(self)

    def customInit(self):
        '''The app can define a method on its tool, named "initialiseHandler",
           allowing to perform custom initialisation on a freshly created
           handler (ie for caching some highly requested info).'''
        if not hasattr(self.tool, 'initialiseHandler'): return
        self.tool.initialiseHandler(self)

    def clientIP(self):
        '''Gets the IP address of the client'''
        # Check header key X-Forwarded-For first
        return self.headers.get('X-Forwarded-For') or self.clientHost

    # This dict allows, on a concrete handler, to find the data to log
    logAttributes = O(ip='self.clientIP()', port='str(self.clientPort)',
      command='self.command', path='self.path', protocol='self.requestVersion',
      message='message', user='self.guard.userLogin',
      agent='self.headers.get("User-Agent")')

    def log(self, type, level, message=None):
        '''Logs, in the logger determined by p_type, a p_message at some
           p_level, that can be "debug", "info", "warning", "error" or
           "critical". p_message can be empty: in this case, the log entry will
           only contain the predefined attributes as defined by the
           appy.database.log.Config.'''
        server = self.server
        # Add the "log char" to the message when relevant
        if message and self.logChar:
            message = f'{self.logChar} {message}'
        logger = getattr(server.loggers, type)
        cfg = getattr(server.config.log, type)
        # Get the parts of the message to dump
        r = []
        for part in cfg.messageParts:
            try:
                value = eval(getattr(Handler.logAttributes, part))
                if value is not None:
                    r.append(value)
            except AttributeError:
                pass
        # Call the appropriate method on the logger object corresponding to the
        # log p_level.
        getattr(logger, level)(cfg.sep.join(r))

    def isMobile(self):
        '''Was the currently handled HTTP request initiated from a mobile
           device ?'''

    def getSpecial(self, login):
        '''Returns the special User instance having this p_login'''
        try:
            r = self.dbConnection.root.objects.get(login)
        except AttributeError:
            # The DB connection may not have been defined yet
            r = None
        return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Inject class Handler on class Base to avoid circular package dependencies
Base.Handler = Handler

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class HttpHandler(Handler):
    '''Handles incoming HTTP requests'''

    # This is a "real" request handler
    fake = False

    # Store, for every logged user, the date/time of its last access
    onlineUsers = {}

    # Supported HTTP methods
    supportedHttpMethods = asDict(['GET', 'POST'])

    # Regex used to detect a mobile browser from the User-Agent header
    mobileRex = re.compile('Android|iPhone|iPod')

    def __init__(self, clientSocket, server):
        # The global config
        self.config = server.config
        # The request path (will be parsed later, but may be mentioned in some
        # errors before being initialized).
        self.path = '-'
        # The client socket from which the client request will be read
        self.clientSocket = clientSocket
        self.clientHost, self.clientPort = clientSocket.getpeername()
        # A back reference to the Appy server
        self.server = server
        # Create a buffered file for reading data on the socket
        self.rfile = clientSocket.makefile('rb', -1)
        # Create a Response object, used to build the response to send back to
        # the client.
        self.resp = Response(self)
        # Must the client socket be closed after the request has been handled ?
        self.closeSocket = True # Until now
        # The debug level
        self.debugLevel = self.config.server.debugLevel

    def init(self):
        '''Additional initialization, only applicable for dynamic content'''
        # Update the response object with headers being specific to a dynamic
        # response.
        self.resp.initDynamic()
        # An instance of appy.ui.validate.Validator will be created here, when
        # data sent via the ui requires to be validated.
        self.validator = None
        # Search criteria may be cached
        self.criteria = None
        # Must we commit data into the database ?
        self.commit = False
        # Late-initialised objects: the traversal and the guard
        self.traversal = self.guard = None
        # Set here a link to the tool. The handler object will be heavily
        # consulted by a plethora of objects during request handling. This is
        # why it is convenient to define such attributes on it.
        self.tool = self.dbConnection.root.objects.get('tool')
        # Call the base handler's method
        Handler.init(self)

    def finish(self):
        '''Closes p_self.rfile'''
        self.rfile.close()

    def getLayout(self):
        '''Try to deduce the current layout from the traversal, if present'''
        traversal = getattr(self, 'traversal', None)
        if traversal: return getattr(traversal.context, 'layout', None)

    def isAjax(self):
        '''Is this handler handling an Ajax request ?'''
        req = self.req
        return req and req.ajax == 'True'

    def inPopup(self):
        '''Are we "in" the Appy iframe popup ?'''
        req = self.req
        return req and req.popup == 'True'

    def isPublished(self, o):
        '''Is object p_o the currently published object ?'''
        referer = self.headers.get('referer')
        if not referer: return
        # Ensure the referer URL path ends with a slash
        path = urllib.parse.urlparse(referer).path
        if not path.endswith('/'): path = '%s/' % path
        return ('/%s/' % o.id) in path

    def isMobile(self):
        '''Was the currently handled HTTP request initiated from a mobile
           device ?'''
        headers = self.headers
        if not headers: return
        agent = headers.get('User-Agent')
        return False if not agent else bool(HttpHandler.mobileRex.search(agent))

    def complete(self):
        '''Completes p_self's data structures, that were not initialised due to
           an error in one of the base Appy systems, like authentication.'''
        # having a complete handler allows, a.o., to nicely handle errors
        if not self.guard:
            self.guard = Guard(self, user=self.getSpecial('anon'))
        if not self.traversal:
            self.traversal = Traversal(handler=self)

    def manageGuardError(self, resp, traversal, error=None):
        '''A security-related error has occurred: the logged user is not allowed
           to access the desired URL. If the user is anon, redirect him to the
           login page. Else, return an error. p_error may contain the raised
           exception instance.'''
        # Return the response content. In the case of a redirect, None will be
        # returned.
        if self.guard.user.isAnon():
            if resp.contentType == 'html':
                # This is (supposedly) a user behind a browser
                config = self.config
                siteUrl = config.server.getUrl(self)
                gotoUrl = urllib.parse.quote('%s%s' % (siteUrl, self.path))
                resp.goto(url='%s/tool/%s?goto=%s&stay=1' % \
                          (siteUrl, config.ui.home, gotoUrl),
                          message=self.tool.translate('please_authenticate'))
                r = None
            else:
                # Return a 403 error, marshalled
                resp.code = HTTPStatus.FORBIDDEN
                tag = error.__class__.__name__ if error is not None else 'Error'
                r = traversal.marshall(error or '', rootTag=tag)
        else:
            # Log and return a 403 error: forbidden
            resp.code = HTTPStatus.FORBIDDEN
            r = Error.get(resp, traversal, error=error)
        return r

    def manageDatabaseRequest(self):
        '''Manage an HTTP request whose response must imply using the
           database and return the response content as a string.'''
        # Initialise p_self's base data structures
        self.init()
        # Run a traversal
        self.traversal = traversal = Traversal(handler=self)
        resp = self.resp
        try:
            r = traversal.run()
        except Traversal.Error as err:
            resp.code = HTTPStatus.NOT_FOUND # 404
            r = Error.get(resp, traversal)
        except Guard.Error as err:
            r = self.manageGuardError(resp, traversal, error=err)
        except MessageException as msg:
            resp.code = HTTPStatus.OK
            r = Error.get(resp, traversal, error=msg)
        except EvaluationError as err:
            # It can be an exception being re-raised in the context of a PX
            # evaluation error.
            orig = err.originalError
            if isinstance(orig, Guard.Error):
                r = self.manageGuardError(resp, traversal, error=orig)
            elif isinstance(orig, MessageException):
                resp.code = HTTPStatus.OK
                r = Error.get(resp, traversal, error=orig)
            elif orig.__class__ in self.server.database.ConflictErrors:
                # A database conflict error embedded into an evaluation error.
                # Re-raise it as a first class exception: it will be catched and
                # managed by the calling method.
                raise orig
            else:
                resp.code = HTTPStatus.INTERNAL_SERVER_ERROR # 500
                r = Error.get(resp, traversal)
        return r

    def attemptDatabaseRequest(self):
        '''Tries to m_manageDatabaseRequest. Perform several attempts depending 
           on the occurrence of database conflict errors. Returns the content of
           the page to serve, as a string.'''
        maxAttempts = self.config.database.conflictRetries
        attempts = 0
        database = self.server.database
        while True:
            try:
                r = self.manageDatabaseRequest()
                # Perform a database commit when appropriate
                if self.commit: database.commit(self)
            except database.ConflictErrors as err:
                attempts += 1
                # Abort the transaction that could not be committed
                transaction.abort()
                # Return an error if is was the last attempt
                if attempts == maxAttempts:
                    self.log('app', 'error', TRANS_ERR % str(err))
                    self.resp.code = HTTPStatus.SERVICE_UNAVAILABLE # 503
                    r = Error.get(self.resp, self.traversal)
                    break
                else:
                    self.log('app', 'warning',
                             TRANS_RETRY % (str(err), attempts))
            except MessageException as msg:
                self.resp.code = HTTPStatus.OK
                r = Error.get(self.resp, self.traversal, error=msg)
                break
            except Exception as err:
                self.resp.code = HTTPStatus.INTERNAL_SERVER_ERROR # 500
                r = Error.get(self.resp, self.traversal, error=err)
                break
            else:
                break
        return r

    def determineType(self):
        '''Determines the type of the request and split, in p_self.parts, the
           request path into parts.'''
        self.parsedPath = parsed = urllib.parse.urlparse(self.path.strip('/'))
        parts = parsed.path.split('/')
        config = self.config
        # Remove any blank part among self.parts
        i = len(parts) - 1
        while i >= 0:
            if not parts[i]: del parts[i]
            i -= 1
        # No path at all means: dynamic content must be served (with a default
        # object and default method or PX applied on it).
        if not parts:
            self.static = False
        # If the first part of the path corresponds to the root static folder,
        # static content must be served.
        elif parts[0] == config.server.static.root:
            self.static = True
            del parts[0]
        # If the unique part corresponds to a file (ie, any name containing a
        # dot), it is static content, too (favicon.ico, robots.txt...)
        elif len(parts) == 1 and '.' in parts[0]:
            self.static = True
            # Get this file at the place configured in the UI config
            base = config.ui.images.get(parts[0]) or 'appy'
            parts.insert(0, base)
        # In any other case, dynamic content must be served
        else:
            self.static = False
        self.parts = parts
        # Must the client socket be closed after the request has been handled ?
        httpVersion = config.server.httpVersion
        self.closeSocket = httpVersion == 1 or \
                           self.headers.get('Connection') == 'close'

    def handle(self):
        '''Called by m_run to handle a HTTP request'''
        # Determine the type of the request: static or dynamic (boolean
        # self.static). Static content is any not-database-stored-and-editable
        # image, Javascript, CSS file, etc. Dynamic content is any request
        # reading and/or writing to/from the database.
        self.determineType()
        resp = self.resp
        if self.static:
            # Manage static content
            Static.get(self)
        else:
            # Add myself to the registry of handlers
            already = Handler.add(self)
            if already:
                self.log('app', 'warning', T_AL_REG % threading.get_ident())
            # Initialise a database connection
            database = self.server.database
            self.dbConnection = database.openConnection()
            try:
                # Extract parameters and create a Request instance in p_self.req
                self.req = Request.create(self)
                # Compute dynamic content
                r = self.attemptDatabaseRequest()
                # Build the HTTP response (if not done yet)
                resp.build(r)
            finally:
                # Remove myself from the registry (for now)
                Handler.remove()
                # Close the DB connection
                database.closeConnection(self.dbConnection)
        # Log this hit and the response code on the site log
        self.log('site', 'info', str(resp.code.value))

    def parseRequestHeaders(self):
        '''Parses the request line and headers. Returns (None, None) on success
           and (errorCode, message) on failure.'''
        # Split the request line
        stripped = self.requestLine.rstrip(Response.eol)
        parts = stripped.decode(Response.headersEncoding).split()
        count = len(parts)
        if count not in (2, 3):
            return HTTPStatus.BAD_REQUEST, RQ_LINE_KO % stripped
        # Manage the request version
        if count == 3:
            # The version of the HTTP protocol requested by the client
            version = parts.pop()
            if not version.startswith('HTTP/'):
                return HTTPStatus.BAD_REQUEST, HTTP_V_KO % version
            self.requestVersion = version
            if version.count('.') != 1:
                return HTTPStatus.BAD_REQUEST, HTTP_V_KO % version
            try:
                floatVersion = float(version[5:])
                # Currently, HTTP 1.0 and 1.1 are supported
                if floatVersion < 1.0 or floatVersion > 1.1:
                    code = HTTPStatus.HTTP_VERSION_NOT_SUPPORTED
                    return code, HTTP_V_UNS % version
            except ValueError:
                return HTTPStatus.BAD_REQUEST, HTTP_V_KO % version
        else:
            self.requestVersion = self.config.server.getProtocolString()
        # Manage the HTTP method (GET or POST) and path
        self.httpMethod, self.path = parts
        # Parse HTTP headers
        try:
            self.headers = hc.parse_headers(self.rfile, _class=hc.HTTPMessage)
        except hc.LineTooLong as err:
            code = HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE
            return code, HEAD_TOO_LG % str(err)[:15]
        except hc.HTTPException as err:
            code = HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE
            return code, HEAD_T_MANY % str(err)[:15]
        return None, None

    def tlog(self, message, level=1):
        '''Output p_message if the debug level requires it'''
        return self.server.tlog(message, level=level,
                                clientPort=self.clientPort)

    def run(self):
        '''Handles a complete HTTP request'''
        try:
            # Read the request line
            self.tlog(T_READ_SOCK)
            self.requestLine = line = self.rfile.readline(65537)
            length = len(line)
            self.tlog(T_READ_GOT % (line, length))
            # Cancel everything if no data was received
            if not line: return self.finish()
            # The request URI may be too long
            if length > 65536:
                self.resp.buildError(HTTPStatus.REQUEST_URI_TOO_LONG)
                return self.finish()
            # Parse request headers
            errorCode, message = self.parseRequestHeaders()
            if errorCode:
                self.resp.buildError(errorCode, message=message)
                return self.finish()
            # Is the HTTP method supported ?
            method = self.httpMethod
            if method not in HttpHandler.supportedHttpMethods:
                self.resp.buildError(HTTPStatus.NOT_IMPLEMENTED,
                                     message=H_METH_KO % method)
                return self.finish()
            # Handle the request
            self.handle()
        except socket.timeout as e:
            # A read or a write timed out: discard the client socket
            self.log('app', 'error', SOCK_TO % str(e))
        finally:
            self.finish()

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class VirtualHandler(Handler):
    '''Fake handler handling a virtual request: server initialization, scheduler
       job, etc.'''

    # Fake handler attributes
    clientPort = 0
    command = 'GET'
    path = '/'
    requestVersion = 'HTTP/1.1'
    headers = {'User-Agent': 'system'}
    fake = True
    traversal = None

    # Entries logged from a virtual handler will be prefixed with this char
    logChar = '>'

    def __init__(self, server):
        '''Tries to define the same, or fake version of, a standard handler's
           attributes.'''
        # The Appy HTTP server instance
        self.server = server
        self.config = server.config
        # Create fake Request and Response objects
        self.req = Request()
        self.resp = Response(self)
        # Call the base handler's method
        Handler.init(self)
        # Add myself to the registry of handlers
        Handler.add(self)
        # By default, a commit will be performed
        self.commit = True
        # The following attributes will be initialised later
        self.dbConnection = None
        self.tool = None
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -