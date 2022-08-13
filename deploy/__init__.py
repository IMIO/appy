'''Deployment system for Appy sites and apps'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import os, sys
from pathlib import Path

from appy.deploy.repository import Repository

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
T_EXEC    = 'Executing :: %s'
T_LIST    = 'Available target(s) for app "%s", from reference site "%s":\n%s'
NO_CONFIG = 'The "deploy" config was not found in config.deploy.'
NO_TARGET = 'No target was found on config.deploy.targets.'
TARGET_KO = 'Target "%s" not found. Available target(s): %s.'
TARGET_NO = 'Please specify a target to run this command.'

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
        # ~~~
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
        # The chosen target (name). If p_targetName is None, the default target
        # (if there is one) will be selected.
        self.targetName = targetName
        self.target = None # Will hold a Target instance
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
        for name, target in self.config.deploy.targets.items():
            suffix = ' [default]' if target.default else ''
            info = '%s. %s - %s%s' % (str(i).zfill(2), name, target, suffix)
            infos.append(info)
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
        '''Performs an update of all software known to the site and coming from
           external sources (app and dependencies) and (re)starts the site.'''
        target = self.target
        # (1) Build the set of commands to update the app, ext and dependencies
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
        # Run those commands as the main SSH user: else, agent forwarding will
        # not be allowed and will prevent to update repositories using public
        # key authentication.
        command = '%s %s' % (Repository.getEnvironment(), ';'.join(commands))
        target.execute(command)
        # (2) Build the command to restart the distant site
        commands = []
        restart = '%s/bin/site restart' % target.sitePath
        commands.append(restart)
        commands.append(self.tail % (100, target.sitePath))
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

    def getTarget(self, targets):
        '''Return the target onto which the command must be applied'''
        name = self.targetName
        r = None
        if name:
            r = targets.get(name)
        else:
            for target in targets.values():
                if target.default:
                    r = target
                    break
        return r

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
        # Get the target
        target = self.target = self.getTarget(targets)
        if not target and self.command not in Deployer.noTargetCommands:
            if self.targetName is None:
                message = TARGET_NO
            else:
                message = TARGET_KO % (self.targetName, ', '.join(targets))
            print(message)
            sys.exit(1)
        getattr(self, self.command)()
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
