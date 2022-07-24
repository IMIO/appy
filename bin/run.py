'''Runs a site'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import os, sys, subprocess, signal, time

from appy.bin import Program
from appy.server import Server

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
HELP_ACT  = 'Action can be "start" (start the site), "stop" (stop it), ' \
            '"restart" (stop it and directly restart it), "fg" (start it in ' \
            'the foreground), "clean" (clean temporary objects, pack the ' \
            'database, detect missing files on the filesystem, remove ' \
            'phantom files) or "run" (execute a specific method).'
HELP_METH = 'When action in "run", you must specify the name of the method ' \
            'to execute on your app\'s tool. When action is "start" or "fg", ' \
            'you may also specify such a method: it will be executed just ' \
            'after standard method "onInstall", if defined on the app\'s tool.'
HELP_WAIT = '(do not use this, this is for Appy internal use only) When ' \
            'action is "stop" or "restart", "run" will wait WAIT seconds ' \
            'before sending the SIGINT signal to the Appy server. In this ' \
            'mode, no output at all is echoed on stdout.'
ACT_KO    = 'Unknown action "%s".'
METH_KO   = 'Specify a method name via option "-m".'
PORT_USED = 'Port %d is already in use.'
PID_EX    = 'Existing pid file removed (server not properly shut down).'
PID_NF    = "The server can't be stopped."
S_START   = 'Started as process %s.'
S_STOP    = 'Server stopped.'
S_NRUN    = 'Server was not running (probably abnormally stopped).'
WAIT_M    = "Max %d'' until stop..."

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Run(Program):

    # Run-specific exception class
    class Error(Exception): pass

    # Other constants
    allowedActions = ('start', 'stop', 'restart', 'fg', 'bg', 'clean', 'run')

    def defineArguments(self):
        '''Define the allowed arguments for this program'''
        parser = self.parser
        parser.add_argument('action', help=HELP_ACT)
        parser.add_argument('-m', '--method', type=str, help=HELP_METH)
        parser.add_argument('-w', '--wait', type=int, help=HELP_WAIT)

    def analyseArguments(self):
        '''Check arguments'''
        # Check that the specified action is valid
        action = self.args.action
        if action not in Run.allowedActions:
            self.exit(ACT_KO % action)
        # Get other args
        method = self.args.method
        wait = None
        if action == 'run':
            if method is None:
                self.exit(METH_KO)
        elif action in ('restart', 'stop'):
            wait = self.args.wait
        self.action = action
        self.method = method
        self.wait = wait

    def say(self, something, cr=True):
        '''Display p_something on stdout by using the standard print function'''
        # When the Appy server (SV) wants to restart himself (ie, after a
        # backup or some other job), he does it by forking, via
        # subprocess.Popen, a subprocess (SUB) that launches this command:
        #
        #            <site_path>/bin/site restart -w <seconds>
        #
        # In this mode, it is useless for the "run" script (in SUB) to print
        # anything on stdout: there is nobody to see this. Worse: using the
        # "print" standard function in SUB with attribute flush=True may block
        # the communication between SUB and SV and prevent the Appy server from
        # restarting.
        if self.wait: return
        if cr: # End with a *c*arriage *r*eturn
            print(something)
        else:
            print(something, end='', flush=True)

    def checkStart(self, exitIfInUse=False):
        '''Checks that the server can be started in "start" mode'''
        # Check if the port is already in use or not
        config = self.config
        if config.server.inUse():
            message = PORT_USED % config.server.port
            if exitIfInUse:
                self.say(message)
                sys.exit(1)
            else:
                raise self.Error(message)
        # If a "pid" file is found, it means that the server was not properly
        # stopped. Remove the file and issue a warning.
        pid = config.database.getPidPath()
        if pid.exists():
            self.say(PID_EX)
            pid.unlink()

    def checkStop(self, pidFile, restart=False):
        '''Checks that the server can be stopped and returns the process ID
           (pid) of the running server.'''
        # Check that the pid file exists
        if not pidFile.exists():
            self.say(PID_NF)
            if not restart:
                sys.exit(1)
            else:
                return
        with pidFile.open() as f: r = f.read().strip()
        return int(r)

    def start(self, exitIfInUse=True):
        '''Starts the server'''
        self.checkStart(exitIfInUse=exitIfInUse)
        # Spawn a child process and run the server in it, in "bg" mode
        args = [sys.argv[0], 'bg']
        if self.method:
            args.append('-m')
            args.append(self.method)
        # Start the server in the background, in another process
        pid = subprocess.Popen(args, stdin=None, stdout=None, stderr=None).pid
        # Create a file storing the process ID, besides the DB file
        self.say(S_START % pid)
        sys.exit(0)

    def waitStopped(self, pidFile, pid):
        '''Wait until p_pidFile has been deleted by the server process'''
        maxWait = self.config.server.maxWait
        self.say(WAIT_M % maxWait, cr=False)
        time.sleep(0.3)
        while pidFile.is_file() and maxWait > 0:
            time.sleep(2)
            maxWait -= 2
            self.say('.', cr=False)
        # Kill brutally if the process is still there
        if pidFile.is_file():
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass # The process is not there anymore
            try:
                pidFile.unlink()
            except Exception as err:
                pass

    def isRunning(self, pid):
        '''Is process with this process p_pid running ?'''
        try:
            os.kill(pid, 0)
            r = True
        except OSError:
            # The process is not running
            r = False
        return r

    def stop(self, restart=False):
        '''Stops the server. If p_restart is True, the server will be
           immediately restarted afterwards.'''
        pidFile = self.config.database.getPidPath()
        pid = self.checkStop(pidFile, restart=restart)
        wasRunning = True
        if pid is not None and self.isRunning(pid):
            # Wait first, if required
            if self.wait: time.sleep(self.wait)
            # Stop the server
            try:
                os.kill(pid, signal.SIGINT)
            except ProcessLookupError:
                self.say(S_NRUN)
                wasRunning = False
            if wasRunning:
                # Wait until we are sure the server is stopped
                self.waitStopped(pidFile, pid)
        if not restart and wasRunning:
            self.say(S_STOP)

    def run(self, site, app, ext=None):
        '''Runs the web server'''
        # Get the configuration
        config = self.config = __import__(app.name).Config
        action = self.action

        # Execute the appropriate action
        if action in ('fg', 'bg', 'clean', 'run'):
            #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
            #  "fg"     | The user executed command "./site fg" : we continue
            #           | and run the server in this (parent, unique) process.
            #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
            #  "bg"     | The user executed command "./site start", the runner
            #           | in the parent process spawned a child process with
            #           | command "./site bg". We continue and run the server in
            #           | this (child) process.
            #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
            #  "clean", | Theses cases are similar to the "fg" mode hereabove;
            #  "run"    | they misuse the server to execute a single command and
            #           | return, without actually running the server.
            #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
            classic = action in ('fg', 'bg')
            if action == 'fg':
                # For "bg", the check has already been performed
                self.checkStart()
            # Create a Server instance
            server = Server(config, action, self.method, ext=ext)
            # In classic modes "fg" or "bg", run the server
            if action in ('fg', 'bg'):
                server.serveForever()
            else:
                # Everything has been done during server initialisation
                server.shutdown()
            sys.exit(0)

        elif action == 'start':
            self.start()

        elif action == 'stop':
            self.stop()

        elif action == 'restart':
            self.stop(restart=True)
            time.sleep(1)
            try:
                self.start(exitIfInUse=False)
            except self.Error as e:
                # The server is probably not stopped yet
                time.sleep(1)
                self.start()
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
