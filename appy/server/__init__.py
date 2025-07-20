'''Appy HTTP server'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import os, sys, time, socket, logging, pathlib, selectors, threading, platform

from appy.px import Px
from appy import utils, version
from appy.model.root import Model
from appy.database import Database
from appy.utils import url as uutils
from appy.utils import executeCommand
from appy.server.pool import ThreadPool
from appy.utils.path import getShownSize
from appy.model.utils import Object as O
from appy.server.scheduler import Scheduler
from appy.server.static import Config as StaticConfig
from appy.server.handler import HttpHandler, VirtualHandler

# Constants  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
START_CLASSIC = ':: Starting server ::'
START_CLEAN   = ':: Starting clean mode%s ::'
CLEAN_RISH    = ' ("rise file from the ashes" method=%s)'
START_RUN     = ':: Starting run mode (%s) ::'
READY         = '%s:%s ready (process ID %d).'
RUNNING_APP   = 'Running app::%s'
STOP_CLASSIC  = ':: %s:%s stopped ::'
STOP_CLEAN    = ':: Clean end ::'
STOP_RUN      = ':: Run end ::'
APPY_VERSION  = 'Appy is "%s".'
RAM_LOAD      = '%d CSS + %d SVG files loaded in RAM (%s).'
POLLING       = 'Polling (registered client sockets = %d)...'
NEW_CLI       = 'Server socket accepted new client %s::%s'
DB_C_ERR      = 'Error on closing database. %s.'

# Errors - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
CONN_RESET    = 'Connection reset by peer (client port %d).'
BROKEN_PIPE   = 'Broken pipe (client port %d).'
MIN_THR_KO    = 'At least one thread must be in use.'
THR_LIMITS_KO = 'killThreadLimit (%d) should be > hungThreadLimit (%d)'
SPAWN_IF_KO   = 'spawnIfUnder (%d) should be < than the number of threads (%d)'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
bn = '\n'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Config:
    '''HTTP server configuration for a Appy site'''

    # A warning to those using non-free software
    NONFREE_WARN = 'Using proprietary software reduces your freedom, makes ' \
                   'you depend on companies whose growth may cause ethical ' \
                   'problems and endanger your privacy as well as the world ' \
                   'balance.'

    def __init__(self):
        # The server address
        self.address = '0.0.0.0'
        # The server port
        self.port = 8000
        # The protocol in use. Valid values are "http" or "https"
        self.protocol = 'http'
        # The public domain name under which this server is known. Can be
        # useful, in combination with p_self.protocol, to generate site URLs
        # when the server is not solicited by a browser. Indeed, in that case,
        # request info (containing host and port) is absent. This can happen,
        # ie, when a job or a night method is ran. Note that the domain may
        # already include a leading path, ie: www.my.domain.be/leading/path.
        self.domain = None
        # The version of HTTP in use, as a float value. Currently, 1.0 and 1.1
        # are supported.
        self.httpVersion = 1.1
        # Encoding for the HTTP headers
        self.headersEncoding = 'iso-8859-1'
        # Header key storing the host name = the domain name or address under
        # which the server running this site is known. The standard one is
        # "Host", but, when reverse proxies are in the way between the browser
        # and the Appy server, another key may be used, such as X-Forwarded-Host
        # or X-Forwarded-Server. For determining the host name, being the basis
        # for generating all absolute URLs in pages returned to the browser,
        # Appy will first try to retrieve it from the HTTP header key mentioned
        # in p_self.hostKey. If this key is not found, Appy will retrieve it
        # from standard key 'Host'.
        self.hostKey = 'X-Forwarded-Host'
        # The value of the "SameSite" attribute for cookies. Can be "Lax" or
        # "Strict". More info on https://developer.mozilla.org/en-US/docs/Web/
        #                         HTTP/Headers/Set-Cookie/SameSite
        self.sameSite = 'Lax'
        # The size of the queue as defined on the server socket, passed as
        # parameter to the "listen" method.
        self.queueSize = 5
        # The "poll interval", in seconds. After having entered his infinite
        # loop, the server, while waiting for incoming connections or data on
        # these connections, will be interrupted every "pollInterval" seconds.
        # Avoid setting this value to 0.0: the Appy server would take 100% CPU
        # in that case. A value of 0.1 second seems reasonable for production
        # environments. Higher values are useful for debugging (see attribute
        # "debugLevel" below).
        self.pollInterval = 0.1
        # If attribute "debugLevel" is > 0, additional debug info will be
        # produced. If debug level is...
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # 1 | For every database-related request, 2 entries are dumped in the
        #   | site log for every hit: one when the hit is done, one when the
        #   | response is returned.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # 2 | For every request (including static requests, being excluded from
        #   | debugLevel=1), 2 entries are dumped in the
        #   | site log for every hit: one when the hit is done, one when the
        #   | response is returned.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # 3 | app log is added before and after reading requests lines on client
        #   | sockets (to check if there is no I/O block there) ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # 4 | app log is added in the server's infinite loop (every
        #   | "pollInterval" seconds), to check if the server is not blocked
        #   | somewhere. At this level, log also occurs everytime the server
        #   | socket accepts a new client connection.
        #   |
        #   | When using this debug level, set a poll interval being higher (2
        #   | seconds or more). It will slow down the server but will produce
        #   | less verbose output.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.debugLevel = 0
        # If you want to log HTTP headers for some incoming requests, set a
        # regular expression (produced via the re.compile function) in one or
        # all of the 2 following attributes. Static requests are requests for
        # static content, like CSS, JS files or images; dynamic requests are
        # those requiring updating or getting content via a database connection.
        # These regular expressions will be applied to URL request paths (ie,
        # everything that is found after the domain name. For example, for URL
        # https://appyframe.work/su/ck?s=true, the regular expression will be
        # applied on the "/su/ck?s=true" part.
        # These 2 attributes will be RAM-editable by a Manager via the web
        # intertace (admin-zone, page "Log"). In a production environment, avoid
        # hard-coding values for these attributes in your app or ext' config
        # file; instead, set a value through the web interface, only during a
        # limited period of time. This can be convenient for observing HTTP
        # headers within incoming web service calls.
        self.logHeadersStatic = None
        self.logHeadersDynamic = None
        # Configuration for static content (set by m_set below)
        self.static = None
        # Traversers. A "traverser" is a name that can be used at the root of a
        # URL path, to traverse something else than an object. Indeed, the
        # standard traversal is based on database objects. For instance,
        #
        #                      <appUrl>/666
        #
        # requires 666 to be the iid of a database object;
        #
        #                      <appUrl>/something
        #
        # requires "something" to point to an object stored in the database
        # under that name in database dict root.objects.
        # If you want to use starting URL paths not being database objects,
        # define a traverser as an entry in the following dict.
        # - The key is the name to be used in the URL path;
        # - The value is a Python expression, receiving the tool as variable
        #   "tool" in its context.
        # Take care of security when defining traversers.
        self.traversers = {}
        # The path to the site. Will be set by m_set below.
        self.sitePath = None
        #
        # Options for the pool of threads
        #
        # The initial number of threads to run
        self.threads = 5
        # The maximum number of requests a worker thread will process before
        # dying (and replacing itself with a new worker thread).
        self.maxRequests = 100
        # The number of seconds a thread can work on a task before it is
        # considered hung (stuck).
        self.hungThreadLimit = 30
        # The number of seconds a thread can work before you should kill it
        # (assuming it will never finish).
        self.killThreadLimit = 600 # 10 minutes
        # The length of time after killing a thread that it should actually
        # disappear. If it lives longer than this, it is considered a "zombie".
        # Note that even in easy situations killing a thread can be very slow.
        self.dyingLimit = 300 # 5 minutes
        # If there are no idle threads and a request comes in, and there are
        # less than this number of *busy* threads, then add workers to the pool.
        # Busy threads are threads that have taken less than "hungThreadLimit"
        # seconds so far. So if you get *lots* of requests but they complete in
        # a reasonable amount of time, the requests will simply queue up (adding
        # more threads probably wouldn't speed them up). But if you have lots of
        # hung threads and one more request comes in, this will add workers to
        # handle it.
        self.spawnIfUnder = 5
        # If there are more zombies than the following number, just kill the
        # process. This is only good if you have a monitor that will
        # automatically restart the server. This can clean up the mess.
        self.maxZombieThreadsBeforeDie = 0 # Disabled
        # Every X requests (X being the number stored in the following
        # attribute), check for hung threads that need to be killed, or for
        # zombie threads that should cause a restart.
        self.hungCheckPeriod = 100
        # On server shutdown, threads may still be busy. Determine here the
        # maximum number of seconds the server will wait for all threads to
        # terminate, before brutally killing them. By default, wait 10 seconds.
        # Set it to a higher value if your app frequently performs longer
        # transactions and you want to give more chances to these latters to end
        # up gracefully.
        self.maxWait = 10

    def isIPv6(self):
        '''Is IP v6 in use ?'''
        host = self.address
        return host.count(':') > 1  or '[' in host

    def set(self, appFolder, sitePath):
        '''Sets site-specific configuration elements'''
        self.sitePath = pathlib.Path(sitePath)
        appPath = pathlib.Path(appFolder)
        self.static = StaticConfig(appPath)

    def getHost(self, handler, withPort=True):
        '''Gets this server's hostname'''
        # In order to determine the host name, use, in that order, HTTP header
        # key mentioned in p_self.hostKey or "Host".
        headers = handler.headers
        r = headers.get(self.hostKey) or headers.get('Host')
        if r:
            # v_r may contain the port. Remove it if it is present and
            # p_withPort is False.
            if not withPort and ':' in r:
                r = r.split(':', 1)[0]
        elif self.domain:
            # Use p_self.domain and ignore p_withPort
            r = self.domain
        else:
            # Use p_self.address as base
            r = self.address
            if withPort and self.port != 80:
                r = f'{r}:{self.port}'
        return r

    def getUrl(self, handler, relative=False):
        '''Returns the base URL for URLs produced by this Appy server'''
        headers = handler.headers
        if relative:
            base = ''
        else:
            host = self.getHost(handler)
            # Get protocol from header key "X-Forwarded-Proto" when present
            protocol = headers.get('X-Forwarded-Proto') or self.protocol
            # Build the base of the URL
            base = f'{protocol}://{host}'
        # Add a potential path prefix to URLs
        prefix = headers.get('X-Forwarded-Prefix')
        prefix = f'/{prefix}' if prefix else ''
        return f'{base}{prefix}'

    def getProtocolString(self):
        '''Returns the string representing the HTTP protocol version'''
        # For HTTP 1.0 and HTTP 1.1, return always HTTP 1.1
        version = self.httpVersion
        nb = str(version) if version > 1.1 else '1.1'
        return f'HTTP/{nb}'

    def inUse(self):
        '''Returns True if (self.address, self.port) is already in use'''
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Set option "Reuse" for this socket. This will prevent us to get a
        # "already in use" error when TCP connections are left in TIME_WAIT
        # state.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((self.address, self.port))
        except socket.error as e:
            if e.errno == 98:
                return True
        s.close()

    def check(self, messages):
        '''Ensure this config is valid'''
        # At least one thread must be specified
        assert (self.threads > 1), MIN_THR_KO
        # Ensure limits are consistent
        kill = self.killThreadLimit
        hung = self.hungThreadLimit
        assert (not kill or (kill >= hung)), (THR_LIMITS_KO % (kill, hung))
        # Ensure number of threads are consistent
        spawnIf = self.spawnIfUnder
        threads = self.threads
        assert spawnIf <= threads, (SPAWN_IF_KO % (spawnIf, threads))

    def getOsInfo(self):
        '''Returns, as a chunk of XHTML, info about the OS running the current
           Appy server.'''
        r = platform.system()
        if r == 'Linux':
            distro = ''
            if hasattr(platform, 'freedesktop_os_release'):
                # Add details and info about the distro
                try:
                    distro = platform.freedesktop_os_release()
                    # Get distro info as a sub-table
                    rows = []
                    for name, val in distro.items():
                        row = f'<tr><th>{name}</th><td>{val}</td></tr>'
                        rows.append(row)
                    distro = f'<table class="small discreet topSpace">' \
                             f'{bn.join(rows)}</table>'
                except OSError:
                    pass
            r = f'<div>{r}</div><div class="discreet">{platform.platform()}' \
                f'</div>{distro}'
        else:
            # Add a warning
            r = f'<div>{r}</div><div class="discreet topSpace">⚠️ ' \
                f'{self.NONFREE_WARN}</div>'
        return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Server:
    '''Appy HTTP server'''

    # Make some names available gere
    platform = platform

    # Some elements will be traversable
    traverse = {}

    def __init__(self, config, mode, method=None, ext=None):
        # p_config is the main app config
        self.config = config
        self.appyVersion = version.verbose
        # Tell clients the server name and version
        self.nameForClients = f'Amnesiac/1.0 Python/{sys.version.split()[0]}'
        # If an ext is there, load it
        if ext:
            __import__(ext.name)
            config.model.extPath = ext
        # Ensure the config is valid
        warnings = config.check()
        # p_mode can be:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "fg"     | Server start, in the foreground (debug mode)
        # "bg"     | Server start, in the background
        # "clean"  | Special mode for cleaning the database
        # "run"    | Special mode for executing a single p_method on the
        #          | application tool.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # Modes "clean" and "run" misuse the server to perform a specific task.
        # In those modes, the server is not really started (it does not listen
        # to a port) and is shutdowned immediately after the task has been
        # performed.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.mode = mode
        self.classic = mode in ('fg', 'bg')
        # Write, when appropriate, a file containing the server's process ID
        if mode == 'bg':
            path = config.database.getPidPath()
            with path.open('w') as f: f.write(str(os.getpid()))
        # The following attributes will be initialized afterwards
        self.socket = None   # The server socket
        self.selector = None # The selector object
        self.registered = 0  # The number of client sockets currently registered
                             # in the selector.
        # Initialise the loggers
        cfg = config.log
        self.loggers = O(site=cfg.getLogger('site'),
                         app=cfg.getLogger('app', mode != 'bg'))
        self.logStart(method)
        # Now that we have loggers, log configuration warnings, if any
        logger = self.loggers.app
        for warning in warnings:
            logger.warn(warning)
        try:
            # Load the application model. As a side-effect, the app's po files
            # were also already loaded.
            self.model, poFiles = config.model.get(config, logger)
            # Initialise the HTTP server
            cfg = config.server
            self.pool = None
            if self.classic:
                self.init(cfg)
                # Start the pool of threads when relevant
                if mode == 'bg':
                    self.pool = ThreadPool(self, cfg)
            # Create the initialisation handler
            handler = VirtualHandler(self)
            # Initialise the database. More precisely, it connects to it and
            # performs the task linked to p_self.mode.
            config.database.getDatabase(self, handler, poFiles, method=method)
            # Initialise the static configuration
            counts = cfg.static.init(config.ui)
            logger.info(RAM_LOAD % (counts.css, counts.svg,
                                    getShownSize(counts.size)))
            # Unregister the virtual handler
            VirtualHandler.remove()
        except (Model.Error, Database.Error) as err:
            self.abort(err)
        except Exception:
            self.abort()
        # The current user login
        self.user = 'system'
        # Create the scheduler instance
        self.scheduler = Scheduler(self)
        # The server is ready
        if self.classic:
            # Explain what app (and, possibly, ext) is loaded on this site
            logger.info(RUNNING_APP % config.model.getAppExt())
            logger.info(READY % (cfg.address, cfg.port, os.getpid()))

    def init(self, config):
        '''Initialise the server socket'''
        family = socket.AF_INET6 if config.isIPv6() else socket.AF_INET
        sock = self.socket = socket.socket(family, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((config.address, config.port))
        sock.listen(config.queueSize)

    def logStart(self, method):
        '''Logs the appropriate "ready" message, depending on p_self.mode'''
        # Uncomment this line to get more debug info from the pool of threads
        #self.loggers.app.setLevel(logging.DEBUG)
        if self.classic:
            text = START_CLASSIC
        elif self.mode == 'clean':
            part = CLEAN_RISH % method if method else ''
            text = START_CLEAN % part
        elif self.mode == 'run':
            text = START_RUN % method
        logger = self.loggers.app
        logger.info(text)
        logger.info(APPY_VERSION % version.verbose)

    def logShutdown(self):
        '''Logs the appropriate "shutdown" message, depending on p_self.mode'''
        if self.classic:
            cfg = self.config.server
            text = STOP_CLASSIC % (cfg.address, cfg.port)
        elif self.mode == 'clean':
            text = STOP_CLEAN
        elif self.mode == 'run':
            text = STOP_RUN
        self.loggers.app.info(text)

    def logTraceback(self):
        '''Logs a traceback'''
        self.loggers.app.error(utils.Traceback.get().strip())

    def tlog(self, message, level=3, clientPort=None):
        '''Output p_message if the debug level requires it'''
        # "tlog" means "thread log" because every p_message produced by this
        # method will be prefixed with the name of the currently running thread.
        #
        # Do not log anything if the debug level is not appropriate
        if self.config.server.debugLevel < level: return
        # Get the name of the currently running thread
        name = threading.current_thread().getName()
        # Output the p_message on stdout, prefixed with the thread name and the
        # client port number when available.
        port = f'{clientPort} :: ' if clientPort else ''
        self.loggers.app.info(f'{name} :> {port}{message}')

    def shutdown(self):
        '''Normal server shutdown'''
        # Shutdown the pool of threads
        if self.pool:
            self.pool.shutdown()
        # Close the server socket if it is there
        if self.socket: self.socket.close()
        # Shutdown the database
        database = self.database
        if database:
            try:
                database.close()
            except Exception as err:
                self.loggers.app.error(DB_C_ERR % str(err))
                self.logTraceback()
        # Logs the shutdown
        self.logShutdown()
        # Shutdown the loggers
        logging.shutdown()
        # -= Warning =- hereafter, we enter a "blind" zone :: No log
        if self.mode == 'bg':
            # Delete the "pid" file when it exists
            pidFile = self.config.database.getPidPath()
            if pidFile.exists():
                try:
                    pidFile.unlink()
                except Exception as err:
                    pass
        sys.exit(0)

    def abort(self, error=None):
        '''Server shutdown following an error'''
        # Close the server socket if it is there
        if self.socket: self.socket.close()
        # Log the error, or the full traceback if requested
        if error:
            self.loggers.app.error(error)
        else:
            self.logTraceback()
        # Shutdown the loggers
        logging.shutdown()
        # If the database was already there, close it
        if hasattr(self, 'database'): self.database.close()
        # Exit
        sys.exit(1)

    def processClientRequest(self, clientSocket):
        '''Processes an incoming request on this p_clientSocket. In debug mode,
           this method is run in the main, unique thread; in multi-threaded
           mode, it is run from a thread from the pool.'''
        # After handling the request, the p_clientSocket may be closed... or not
        closeSocket = True
        # Create a Handler to handle this request
        try:
            handler = HttpHandler(clientSocket, self)
            handler.run()
            closeSocket = handler.closeSocket
        except ConnectionResetError:
            clientPort = clientSocket.getpeername()[1]
            self.loggers.app.error(CONN_RESET % clientPort)
        except BrokenPipeError:
            clientPort = clientSocket.getpeername()[1]
            self.loggers.app.error(BROKEN_PIPE % clientPort)
        except OSError as err:
            # The following exception may be raised, indicating that
            # p_clientSocket is not bound to a client anymore.
            #
            #         [Errno 107] Transport endpoint is not connected
            if err.errno == 107:
                pass # The socket will be closed
            else:
                raise err
        except Exception:
            self.logTraceback()
        finally:
            if closeSocket:
                # Shut down the client socket
                try:
                    # Perform an explicit shudown before closing the socket.
                    # Indeed, socket.close merely releases the socket and waits
                    # for GC to perform the actual close.
                    clientSocket.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
                clientSocket.close()
            else:
                # p_clientSocket will (probably) be reused for subsequent
                # requests. Register it again on the selector.
                self.selector.register(clientSocket, selectors.EVENT_READ,
                                       self.manageClientRequest)

    def manageClientRequest(self, clientSocket, mask):
        '''Request data has been sent by a client on via its p_clientSocket.
           Read this data and manage the request.'''
        # Unregister now this p_clientSocket from the selector. Indeed, when
        # threads are used to manage requests, the main loop may re-select it
        # before the assigned thread has finished to handle the request.
        self.selector.unregister(clientSocket)
        # Depending on the server mode, manage the request in the main thread or
        # in a thread from the pool.
        if self.pool is None or self.mode == 'fg':
            # In debug mode, process the request in the single, main thread
            self.processClientRequest(clientSocket)
        else:
            # Use the pool of threads. Queue the request to be processed by one
            # of the threads from the pool.
            self.pool.addTask(lambda: self.processClientRequest(clientSocket))

    def acceptClient(self, socket, mask):
        '''A new client has declared itself. p_socket is the server socket. Get
           the corresponding client socket and add it among polled sockets.'''
        clientSocket, clientAddress = socket.accept()
        self.selector.register(clientSocket, selectors.EVENT_READ,
                               self.manageClientRequest)
        self.tlog(NEW_CLI % clientAddress, level=4)

    def serveForever(self):
        '''Defines the server's infinite loop'''
        # Define the Selector class to use
        Selector = getattr(selectors, 'PollSelector', 'SelectSelector')
        config = self.config.server
        with Selector() as selector:
            # Tell the selector to monitor the server socket for reading
            self.selector = selector
            selector.register(self.socket, selectors.EVENT_READ,
                              self.acceptClient)
            while True:
                # This log will be produced every config.pollInterval seconds:
                # quite verbose, but interesting if you want to check that the
                # server is not blocked.
                self.registered = len(selector.get_map()) - 1
                self.tlog(POLLING % self.registered, level=4)
                try:
                    events = selector.select(timeout=config.pollInterval)
                except (KeyboardInterrupt, InterruptedError) as ie:
                    self.shutdown()
                    break
                if events:
                    for key, mask in events:
                        #- - - - - - - - - - - - - - - - - - - - - - - - - - - -
                        # "key.fileobj" can be the server socket or a client
                        # socket. If the socket type is:
                        #- - - - - - - - - - - - - - - - - - - - - - - - - - - -
                        # server | a new client connection must be established
                        #        | and added among polled connections;
                        #- - - - - - - - - - - - - - - - - - - - - - - - - - - -
                        # client | data is ready to be read on a client socket.
                        #- - - - - - - - - - - - - - - - - - - - - - - - - - - -
                        key.data(key.fileobj, mask)
                # Perform scheduled jobs, if any
                self.scheduler.scanJobs()

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                          URL-related methods
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def buildUrl(self, handler, name='', base=None, ram=False, bg=False):
        '''Builds the full URL of a static resource, like an image, a Javascript
           or a CSS file, named p_name. If p_ram is True, p_base is ignored and
           replaced with the RAM root. If p_bg is True, p_name is an image that
           is meant to be used in a "style" attribute for defining the
           background image of some XHTML tag.'''
        # Unwrap the server part of the config
        config = self.config
        cfg = config.server
        # Complete the name when appropriate
        if name:
            # If no extension is found in p_name, we suppose it is a PNG image
            name = name if '.' in name else f'{name}.png'
            if base is None and not ram:
                # Get the base folder containing the resource
                base = config.ui.images.get(name) or 'appy'
            name = f'/{name}'
        else:
            base = base or 'appy'
        # Patch p_base if the static resource is in RAM
        if ram: base = cfg.static.ramRoot
        r = f'{cfg.getUrl(handler)}/{cfg.static.root}/{base}{name}'
        if not bg: return r
        suffix = f';background-size:{bg}' if isinstance(bg, str) else ''
        return f'background-image:url({r}){suffix}'

    def getUrlParams(self, params):
        '''Return the URL-encoded version of dict p_params as required by
           m_getUrl.'''
        # Manage special parameter "unique"
        if 'unique' in params:
            if params['unique']:
                params['_hash'] = f'{time.time():.6f}'
            del params['unique']
        return uutils.encode(params, ignoreNoneValues=True)

    def getUrl(self, o, sub=None, relative=False, **params):
        '''Gets the URL of some p_o(bject)'''
        # Parameters are as follows.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # sub      | If specified, it denotes a part that will be added to the
        #          | object base URL for getting one of its specific sub-pages,
        #          | like "view" or "edit".
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # relative | If True, the base URL <protocol>://<domain> will not be
        #          | part of the result.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # params   | Every entry in p_params will be added as-is as a parameter
        #          | to the URL, excepted if the value is None or key is
        #          | "unique": in that case, its value must be boolean: if
        #          | False, the entry will be removed; if True, it will be
        #          | replaced with a parameter whose value will be based on
        #          | time.time() in order to obtain a link that has never been
        #          | visited by the browser.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # The presence of parameter "popup=True" in the URL will open the
        # corresponding object-related page in the Appy iframe, in a
        # minimalistic way (ie, without portlet, header and footer).
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # The base app URL
        r = self.config.server.getUrl(o.H(), relative=relative)
        # Add the object ID
        r = f'{r}/{o.id}'
        # Manage p_sub
        r = f'{r}/{sub}' if sub else r
        # Manage p_params
        if not params: return r
        return f'{r}?{self.getUrlParams(params)}'

    def patchUrl(self, url, **params):
        '''Modifies p_url and injects p_params into it. They will override their
           homonyms that would be encoded within p_url.'''
        if not params: return url
        # Extract existing parameters from p_url and update them with p_params
        r, parameters = uutils.split(url)
        if parameters:
            parameters.update(params)
        else:
            parameters = params
        return f'{r}?{self.getUrlParams(parameters)}'

    def getLoVersion(self):
        '''Gets the version of LibreOffice being installed on the server I am
           currently running.'''
        out, err = executeCommand(('soffice', '--version'))
        return err or out or '?'

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                                 PXs
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    view = Px('''
     <x var="cfg=config.server; server=handler.server; info=server.platform">
      <h2>Server configuration</h2>
      <table class="small">
       <tr><th>Name</th><td>:info.node()</td></tr>
       <tr><th>Address</th><td>:cfg.address</td></tr>
       <tr><th>Port</th><td>:cfg.port</td></tr>
       <tr><th>Protocol</th><td>:cfg.protocol</td></tr>
       <tr><th>Mode</th><td>:server.mode</td></tr>
       <tr><th>Registered client sockets</th><td>:server.registered</td></tr>
       <tr var="level=config.server.debugLevel;
                baseUrl=f'{tool.url}/Server/updateDebugLevel?delta'">
        <th>Log level</th>
        <td><x>:level</x>
         <!-- Increment / decrement the log level -->
         <div style="display:inline-flex;float:right;gap:1em;font-weight:bold">
          <a if="level &lt; 4" title="Increment" href=":f'{baseUrl}=1'"> + </a>
          <a if="level &gt; 0" title="Decrement" href=":f'{baseUrl}=-1'"> - </a>
         </div>
        </td>
       </tr>
      </table>

      <h2>Hardware and software</h2>
      <table class="small">
       <tr><th>Hardware</th>
        <td>:f'{info.machine()} ({" · ".join(info.architecture())})'</td></tr>
       <tr><th>OS</th><td>::cfg.getOsInfo()</td></tr>
       <tr><th>Python</th><td>:info.python_version()</td></tr>
       <tr><th>ZODB</th><td>:config.database.getZodbVersion()</td></tr>
       <tr><th>Appy</th><td>:server.appyVersion</td></tr>
       <tr><th>LibreOffice</th><td>:server.getLoVersion()</td></tr>
      </table>

      <x if="server.pool">
       <h2>Threads status (initial number of threads=<x>:cfg.threads</x>).</h2>
       <x>::server.pool.getTracked(handler)</x>
      </x>
      <h2>HTTP headers for the current request</h2>
      <table class="grid">
       <tr for="name,value in handler.headers.items()" valign="top">
        <th>:name.replace('-','‑')</th>
        <td>::' ↲&lt;br/&gt;'.join(value.split(','))</td>
       </tr>
      </table>
     </x>''')

    traverse['updateDebugLevel'] = 'Manager'
    @classmethod
    def updateDebugLevel(class_, tool):
        '''This method RAM-updates the config-defined debug level'''
        delta = int(tool.req.delta) # May be negative
        val = tool.config.server.debugLevel + delta
        if 0 <= val <= 4:
            tool.config.server.debugLevel = val
            tool.goto(message=f'Debug level set to {val}.')
        else:
            tool.goto(message=f'Aborted :: Wrong delta.')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
