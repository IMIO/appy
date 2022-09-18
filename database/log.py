'''Appy module managing log files'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import logging, sys, pathlib

from appy.px import Px
from appy.model.utils import Object as O

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Config:
    '''Logging-related parameters for your app'''

    # 2 log files exist per Appy site, one for each of the following types.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # "app"  | The *app*lication log stores entries corresponding to app-related
    #        | actions performed by users (or the system itself). Method "log",
    #        | available on any Appy object, outputs log in this file. Appy
    #        | itself also uses this log file for outputting various infos (user
    #        | logins, logouts...), warnings or errors.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # "site" | The site log contains every hit on the site = enery HTTP POST or
    #        | GET request.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    logTypes = ('app', 'site')

    # Available attributes to dump within log entries
    logAttributes = {
      'time': 'asctime', # The current date & time
      'level': 'levelname', # The log level
      'message': 'message' # The message to log, prefixed by the user login
    }

    def __init__(self, siteDateFormat='%Y/%m/%d %H:%M:%S',
                 appDateFormat='%Y/%m/%d %H:%M:%S',
                 siteAttributes=('time', 'message'),
                 appAttributes=('time', 'level', 'message'),
                 # Add "agent" hereafter to get the browser's User-Agent string
                 siteMessageParts=('ip', 'port', 'command', 'protocol',
                                   'path', 'message'),
                 appMessageParts=('user', 'message'),
                 siteSep=' | ', appSep=' | '):
        '''Initializes the logging configuration options.
           - p_siteDateFormat and p_appDateFormat define the format of dates
             dumped in log messages;
           - p_siteAttributes and p_appAttributes store the list of attributes
             that will be dumped in every log entry;
           - p_siteMessageParts and p_appMessageParts store the list of
             attributes contained within composite attribute "message";
           - p_siteSep and p_appSep store the separators that will be inserted
             between attributes.
        '''
        # Create a sub-object for splitting site- and app-related configuration
        # options.
        for type in self.logTypes:
            sub = O(dateFormat=eval('%sDateFormat' % type),# ~pathlib.Path~
                    attributes=eval('%sAttributes' % type),
                    messageParts=eval('%sMessageParts' % type),
                    sep=eval('%sSep' % type))
            setattr(self, type, sub)

    def set(self, siteLogFolder, appLogFolder):
        '''Sets site-specific configuration elements'''
        # self.site.path is the path to the site log file, logging all HTTP
        # traffic on the site.
        self.site.path = pathlib.Path(siteLogFolder)
        # self.app.path is the path to the app-specific log, containing messages
        # dumped by the app and some by Appy itself.
        self.app.path = pathlib.Path(appLogFolder)
        # Typically, the site and app log files have standardized names and are
        # stored in <site>/var, with database-related files:
        # * "siteLogPath"    is <site>/var/site.log
        # * "appLogPath"     is <site>/var/app.log

    def getFormatter(self, type):
        '''Gets a logging.Formatter object for log entries of p_type'''
        sub = getattr(self, type)
        # Define the list of attributes to dump in every log entry
        attributes = []
        for name in sub.attributes:
            attributes.append('%%(%s)s' % Config.logAttributes[name])
        return logging.Formatter(sub.sep.join(attributes),
                                 datefmt=sub.dateFormat)

    def getLogger(self, type, debug=False):
        '''Return the site or app logger instance (depending on p_type), that
           will output log messages to self.siteLogPath or self.appLogPath. If
           p_debug is True, we are in debug mode: an additional handler will be
           defined for producing output on stdout.'''
        logger = logging.getLogger(type)
        # Get the path to the file where to log messages
        sub = getattr(self, type)
        path = sub.path
        # Add a file handler to the logger
        created = not path.is_file()
        path = str(path)
        logger.addHandler(logging.FileHandler(path))
        if debug:
            # Add an additional handler for outputing messages to stdout as well
            logger.addHandler(logging.StreamHandler(sys.stdout))
            level = logging.DEBUG
        else:
            level = logging.INFO
        # Messages under this level will not be dumped
        logger.setLevel(level)
        # Set a formatter for log entries
        formatter = self.getFormatter(type)
        for handler in logger.handlers:
            handler.setFormatter(formatter)
        # Return the created logger
        if created: logger.info('%s created.' % path)
        return logger

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
LOG_T_KO   = 'Unknown log type "%s".'
LOG_M_KO   = 'Unknown log mode "%s".'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Viewer:
    '''Log viewer, available from the UI's admin zone'''

    # Possible modes are the following.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # "tail" | The n last lines of the selected log file are displayed
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    modes = ('tail',)

    # Attributes having sense in "tail" mode
    maxTail     = 500  # Max number of retrieved lines
    defaultTail = 100  # Default number of retrieved lines
    chunkSize   = 1024 # Number of bytes retrieved at a time

    # The main PX
    px = Px('''
     <!-- Controls -->
     <div>
      <img src=":svg('refresh')" class="clickable iconM"
           onclick="refreshLogZone()"/>
     </div>

     <!-- The file content -->
     <pre id="logContent" class="logText">:content</pre>
     <script>:viewer.getAjaxData(_ctx_)</script>
     <script>logToBottom()</script>''',

     js='''
      logToBottom = function() {
        let content=document.getElementById("logContent");
        content.scrollTop = content.scrollHeight;
      }

      // Ajax-refresh the log zone
      refreshLogZone = function() {
        askField('1_logsViewer', siteUrl+'/tool', 'view');
      }''',

     css='''.logText {overflow:auto;width:65vw;height:75vh }''')

    def __init__(self, tool):
        self.tool = tool

    def tail(self, f):
        '''Mimics the unix-like tool "tail" by returning the n last lines from
           file p_f.'''
        # Get the number of lines to retrieve
        req = self.tool.req
        if req.n:
            n = int(req.n)
        else:
            n = Viewer.defaultTail
        n = min(n, Viewer.maxTail)
        # Go to the end of the file
        f.seek(0, 2)
        current = f.tell() # The current position in the file
        remaining = n # The number of lines yet to retrieve
        chunkSize = Viewer.chunkSize
        chunks = [] # Chunks of p_f, each being of this p_chunkSize, in reverse
                    # order starting from the end of the file.
        while remaining > 0 and current > 0:
            if (current - chunkSize) > 0:
                # Read the next chunk
                f.seek((-len(chunks)+1) * chunkSize, 2)
                chunks.append(f.read(chunkSize))
            else:
                # We have reached the beginning of the file, or the file was
                # smaller than the chunk size.
                f.seek(0,0)
                # Read what was not been read yet
                blocks.append(f.read(current))
                break
            # Count how much lines were encountered in the current chunk
            remaining -= chunks[-1].count(b'\n')
            current -= chunkSize
        r = b''.join(reversed(chunks))
        return b'\n'.join(r.splitlines()[-n:]).decode()

    def getContent(self):
        '''Returns the appropriate part of the content corresponding to the
           currently selected log file.'''
        tool = self.tool
        req = tool.req
        # What is the log file for which content must be shown ?
        logType = req.logType or 'app'
        if logType not in Config.logTypes:
            r = LOG_T_KO % logType
        else:
            # What is the view mode ?
            mode = req.mode or 'tail'
            if mode not in Viewer.modes:
                r = LOG_M_KO % mode
            else:
                # Get the log file's configuration object
                cfg = getattr(tool.config.log, logType)
                # Open the log file. If the file is not opened in binary mode,
                # it is not possible to perfom seeks wwith a negative offset
                # being relative to the end of the file.
                with open(cfg.path, 'rb') as f:
                    # Call the method corresponding to the mode
                    r = getattr(self, mode)(f)
        # Call the main PX
        context = O(viewer=self, tool=tool, req=req, svg=tool.buildSvg,
                    content=r)
        return self.px(context)

    def getAjaxData(self, c):
        '''Creates the Ajax data allwing to Ajax-refresh the log zone'''
        return "new AjaxData('%s','GET', null, '1_logsViewer')" % c.tool.url

    @classmethod
    def run(class_, tool):
        '''Create a Viewer instance'''
        return Viewer(tool).getContent()
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
