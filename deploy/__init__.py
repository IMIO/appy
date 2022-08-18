'''Deployment system for Appy sites and apps'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import os, sys
from pathlib import Path

from appy.deploy.repository import Repository

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
TG_UPDATE = '\n☉  Updating target "%s" (%d/%d)... ☉\n\n⚠  Once the ' \
            'site\'s log is shown, type Ctrl-C to go to the next target or ' \
            'retrieve terminal prompt. ⚠\n'
T_EXEC    = 'Executing :: %s'
T_LIST    = 'Available target(s) for app "%s", from reference site "%s":\n%s'
NO_CONFIG = 'The "deploy" config was not found in config.deploy.'
NO_TARGET = 'No target was found on config.deploy.targets.'
TARGET_KO = 'Target "%s" not found.'
TARGET_NO = 'Please specify a target to run this command.'
TARGET_VL = 'No valid target was mentioned. Available target(s): %s.'
ALL_RESV  = '\n⚠ Name "ALL" is reserved to update all targets at once. ' \
            'Please rename the target having this name.\n'
SINGLE_TG = 'Command "%s" cannot be run on more than one target.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Target:
    '''Represents an app deployed on a site on a distant machine'''

    def __init__(self, sshHost, sshPort=22, sshLogin='root', sshKey=None,
                 sitePath=None, sitePort=8000, siteApp=None, siteExt=None,
                 siteOwner='appy:appy', siteDependencies=None, default=False):
        # The name of the distant host, for establishing a SSH connection
        self.sshHost = sshHost
        # The port for the SSH connection
        self.sshPort = sshPort
        # The login used to connect to the host in SSH
        self.sshLogin = sshLogin
        # The private key used to connect to the host in SSH
        self.sshKey = sshKey
        # Information about the Appy site on the target
        # ~
        # The path to the site. Typically: /home/appy/<siteName>
        self.sitePath = sitePath
        # The port on which this site will listen
        self.sitePort = sitePort
        # Instances representing the distant repos where the app and ext reside.
        # Must be instances of classes appy.deploy.git.Git or
        # appy.deploy.subversion.Subversion.
        self.siteApp = siteApp
        self.siteExt = siteExt
        # The owner of the distant site. Typically: appy:appy.
        self.siteOwner = siteOwner
        # A list of Python dependencies to install on the distant app, in its
        # "lib" folder. Every dependency must be specified via a Repository
        # instance, from one of the concrete classes as mentioned hereabove (see
        # attributes p_self.siteApp and p_self.siteExt).
        self.siteDependencies = siteDependencies or []
        # Is this target the default target ? It is not mandatory to have a
        # default target. It is useful if you want to launch deployer commands
        # without specfying arg "-t <target>": the default target will be
        # automatically chosen.
        self.default = default

    def __repr__(self):
        '''p_self's string representation'''
        return '<Target %s:%d@%s>' % (self.sshHost, self.sshPort, self.sitePath)

    def execute(self, command):
        '''Executes p_command on this target'''
        r = ['ssh', '%s@%s' % (self.sshLogin, self.sshHost), '"%s"' % command]
        # Determine port
        if self.sshPort != 22: r.insert(1, '-p%d' % self.sshPort)
        # Determine "-i" option (path to the private key)
        if self.sshKey: r.insert(1, '-i %s' % self.sshKey)
        # Build the complete command
        r = ' '.join(r)
        print(T_EXEC % r)
        os.system(r)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Config:
    '''Deployment configuration'''

    def __init__(self):
        # This dict stores all the known targets for deploying this app. Keys
        # are target names, values are Target instances. The default target must
        # be defined at key "default".
        self.targets = {}

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Deployer:
    '''App deployer'''

    # apt command for installing packages non interactively
    apt = 'DEBIAN_FRONTEND=noninteractive apt-get -yq install'

    # OS packages being Appy dependencies
    osDependencies = 'libreoffice git python3-pip apache2 imagemagick'

    # Commands for which a target is not required
    noTargetCommands = ('list',)

    def __init__(self, appPath, sitePath, command, targetName=None):
        # The path to the app
        self.appPath = appPath
        # The path to the reference, local site, containing targets definition
        self.sitePath = sitePath
        # The chosen target(s), as a string (program input). If p_targetName is
        # None and p_command requires a target, the default target(s) will be
        # selected.
        self.targetName = targetName
        # Will hold the list of Target instances corresponding to p_targetName
        self.targets = None
        # Will hold the first (or unique) Target from p_self.target
        self.target = None
        # The command to execute
        self.command = command
        # The app config
        self.config = None

    def quote(self, arg):
        '''Surround p_arg with quotes'''
        r = arg if isinstance(arg, str) else str(arg)
        return "'%s'" % r

    def buildPython(self, statements):
        '''Builds a p_command made of these Python p_statements'''
        return "python3 -c \\\"%s\\\"" % ';'.join(statements)

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                              Commands
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Command for consulting the last lines in a target's app.log file
    tail = 'tail -f -n %d %s/var/app.log'

    def list(self):
        '''Lists the available targets on the config'''
        infos = []
        default = None
        i = 1
        # Make a first round to get the longest target name
        longest = 0
        for name, target in self.config.deploy.targets.items():
            longest = max(len(name), longest)
        # Walk targets
        for name, target in self.config.deploy.targets.items():
            suffix = ' [default]' if target.default else ''
            info = '%s. %s - %s%s' % (str(i).zfill(2), name.ljust(longest),
                                      target, suffix)
            infos.append(info)
            if name == 'ALL':
                # This word is reserved
                print(ALL_RESV)
            i += 1
        infos = '\n'.join(infos)
        print(T_LIST % (self.appPath.name, self.sitePath.name, infos))

    def info(self):
        '''Retrieve info about the target OS'''
        self.target.execute('cat /etc/lsb-release')

    def install(self):
        '''Installs required dependencies on the target via "apt" and "pip3" and
           create special user "appy" on the server.'''
        target = self.target
        commands = [
          # Install required dependencies via Aptitude
          '%s %s' % (self.apt, self.osDependencies),
          # Install Appy and dependencies via pip
          'pip3 install appy -U',
          # Create special user "appy"
          'adduser --disabled-password --gecos appy appy'
        ]
        target.execute(';'.join(commands))

    def site(self):
        '''Creates an Appy site on the distant server'''
        t = self.target
        # Collect commands to be potentially ran on the distant folders where
        # repos will be downloaded.
        configCommands = set()
        # Build args to appy/bin/make
        q = self.quote
        args = [q(t.sitePath), q('-a'), q(t.siteApp.asSpecifier()), q('-p'),
                q(t.sitePort), q('-o'), q(t.siteOwner)]
        t.siteApp.collectIn(configCommands, t.sitePath)
        if t.siteExt:
            args.append(q('-e'))
            args.append(q(t.siteExt.asSpecifier()))
            t.siteExt.collectIn(configCommands, t.sitePath)
        if t.siteDependencies:
            args.append(q('-d'))
            for dep in t.siteDependencies:
                args.append(q(dep.asSpecifier()))
                dep.collectIn(configCommands, t.sitePath)
        # Build the statements to pass to the distant Python interpreter
        statements = [
          'import sys', 'from appy.bin.make import Make',
          "sys.argv=['make.py','site',%s]" % ','.join(args),
          'Make().run()'
        ]
        command = self.buildPython(statements)
        # Execute it
        t.execute(command)
        # Execute the config commands if any
        if configCommands:
            t.execute(';'.join(configCommands))

    def update(self):
        '''Performs, on these p_self.targets, an update of all software known to
           the site and coming from external sources (app and dependencies), and
           (re)starts the site.'''
        targets = self.targets
        # After updating a given target, the last lines of its log file will be
        # shown via a command like:
        #
        #                       tail -f -n 100 app.log
        #
        # Then, when you are tired looking at this log file, type <Ctrl>-C to
        # update the next target or retrieve terminal prompt.
        #
        # If there are several targets, the number of shown lines will be
        # reduced:
        #
        #                        tail -n 30 app.log
        #
        total = len(self.targets)
        tailNb = 100 if total == 1 else 30
        i = 0
        # Browse targets
        for name, target in self.targets.items():
            i += 1
            print(TG_UPDATE % (name, i, total))
            # (1) Build the set of commands to update the app, ext and
            #     dependencies.
            commands = []
            siteOwner = target.siteOwner
            lib = Path(target.sitePath) / 'lib'
            for name in ('App', 'Ext'):
                repo = getattr(target, 'site%s' % name)
                if repo:
                    command, folder = repo.getUpdateCommand(lib)
                    commands.append(command)
                    commands.append('chown -R %s %s' % (siteOwner, folder))
            # Update dependencies
            for repo in target.siteDependencies:
                command, folder = repo.getUpdateCommand(lib)
                commands.append(command)
                commands.append('chown -R %s %s' % (siteOwner, folder))
            # Run those commands as the main SSH user: else, agent forwarding
            # will not be allowed and will prevent to update repositories using
            # public key authentication.
            command = '%s %s' % (Repository.getEnvironment(),
                                 ';'.join(commands))
            target.execute(command)
            # (2) Build the command to restart the distant site and display its
            #     log file.
            commands = []
            restart = '%s/bin/site restart' % target.sitePath
            commands.append(restart)
            commands.append(self.tail % (tailNb, target.sitePath))
            # These commands will be ran with target.siteOwner
            owner = siteOwner.split(':')[0]
            command = "su %s -c '%s'" % (owner, ';'.join(commands))
            target.execute(command)

    def view(self):
        '''Launch a command "tail -f" on the target's app.log file'''
        target = self.target
        target.execute(self.tail % (200, target.sitePath))

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                             Main method
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def getTargets(self, targets):
        '''Return the targets onto which the command must be applied, among all
           p_targets as defined in the config.'''
        names = self.targetName
        notFound = []
        if not names:
            # Collect the default target(s)
            r = {n:t for n,t in targets.items() if t.default}
        else:
            r = {} # Collect the chosen targets ~{s_name:Target}~
            for name in names.split(','):
                if name == 'ALL':
                    # Add all targets
                    for n, t in targets.items():
                        r[n] = t
                elif name in targets:
                    r[name] = targets[name]
                else:
                    notFound.append(name)
                    print(TARGET_KO % name)
        return r, notFound

    def run(self):
        '''Performs p_self.command on the specified p_self.targetName'''
        # Add the relevant paths to sys.path
        for path in (self.sitePath, self.sitePath / 'lib', self.appPath.parent):
            sys.path.insert(0, str(path))
        # Get the config and ensure it is complete
        self.config = __import__(self.appPath.name).Config
        cfg = self.config.deploy
        if not cfg:
            print(NO_CONFIG)
            sys.exit(1)
        targets = cfg.targets
        if not targets:
            print(NO_TARGET)
            sys.exit(1)
        # Get the specified target(s) when relevant
        if self.command not in Deployer.noTargetCommands:
            self.targets, notFound = self.getTargets(targets)
            if not self.targets:
                if self.targetName is None:
                    message = TARGET_NO
                else:
                    message = TARGET_VL % ', '.join(self.targets)
                print(message)
                sys.exit(1)
            # Abord the whole operation if at least one wrong target was found
            if notFound:
                sys.exit(1)
            # The only command accepting more than one target is "update"
            if self.command != 'update':
                # Unwrap the first and unique target in p_self.target
                for target in self.targets.values():
                    self.target = target
                    break
                # Abort if there is more than one target
                if len(self.targets) > 1:
                    print(SINGLE_TG % self.command)
                    sys.exit(1)
        getattr(self, self.command)()
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
