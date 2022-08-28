'''Builds an init script ready to be deployed and configured in /etc/init.d on a
   target machine.'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import os

from appy.utils.string import Variables
from appy.utils.path import getTempFileName

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
init = '''#! /bin/sh
### BEGIN INIT INFO
# Provides: *name*
# Required-Start: $syslog $remote_fs
# Required-Stop: $syslog $remote_fs
# Should-Start: $remote_fs
# Should-Stop: $remote_fs
# Default-Start: 2 3 4 5
# Default-Stop: 0 1 6
# Short-Description: *short*
# Description: *descr*
### END INIT INFO
case "$1" in
 start)
  *start*
  ;;

 restart|reload|force-reload)
  *restart*
  ;;

 stop)
  *stop*
  ;;

 status)
  *status*
  ;;

 *)
  echo "Usage: $0 start|restart|stop|status" >&2
  exit 3
  ;;
esac
exit 0
'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Init:
    '''Represents an init script to be created and deployed on some target'''

    # Name of the folder where to store init script on Debian systems
    debianFolder = '/etc/init.d'

    def __init__(self, target, path, name, short, descr, start, restart, stop,
                 status):
        # The target onto which the script will be deployed
        self.target = target
        # The absolute path, on p_target, to the init script
        self.path = path
        # The name of the script
        self.name = name
        # A short description
        self.short = short
        # A longer description
        self.descr = descr
        # The "start" command
        self.start = start
        # The "restart" command
        self.restart = restart
        # The "stop" command
        self.stop = stop
        # The "status" command
        self.status = status

    def get(self, asFile=True):
        '''Creates the content of an init.d script. If p_asFile is True, the
           content is dumped in a temp file and the method returns the path to
           this temp file. Else, the content is returned, as a string.'''
        r = Variables.replace(init, self, stars=True)
        # Return the result as a string
        if not asFile: return r
        # Dump the result in a temp file and return its path
        path = getTempFileName()
        with open(path, 'w') as f: f.write(r)
        return path

    def deploy(self):
        '''Creates an init script and deploys it (copy + configure) on
           p_self.target.'''
        target = self.target
        initFolder = Init.debianFolder
        # Generate the init script locally, in a temp file
        tempFilePath = self.get(asFile=True)
        # Copy the script in /etc/init.d on the target
        target.copy(tempFilePath, self.path)
        breakpoint()
        # Configure it to be run at boot
        commands = ['cd %s' % initFolder, 'chmod a+x %s' % self.name,
                    'update-rc.d %s defaults' % self.name]
        target.execute(';'.join(commands))
        # Delete the locally-generated init script
        os.remove(tempFilePath)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class LO(Init):
    '''Represents an init script for controlling LibreOffice (LO) in server
       mode, on some target.'''

    # Options to pass to the "soffice" executable
    acceptPart = 'socket,host=localhost,port='
    accept = '--accept=%s%%d;urp;' % acceptPart
    options = '--invisible --headless'

    # Name and descriptions
    name = 'lo'
    short = 'Start LibreOffice server'
    descr = 'Start LibreOffice in server mode.'

    def __init__(self, target):
        '''LO's specific constructor'''
        # Compute options to pass to the soffice executable
        options = '%s "%s"' % (LO.options, LO.accept % target.loPort)
        # Build the commands
        user = target.siteUser
        start = "cd /home/%s\n  su %s -c 'soffice %s&'" % (user, user, options)
        stop = 'pkill -f %s' % LO.acceptPart
        restart = '%s\n  %s' % (stop, start)
        status = 'pgrep -l -f %s' % LO.acceptPart
        # The path to the LO init.d script on the target
        initPath = '%s/%s' % (Init.debianFolder, LO.name)
        super().__init__(target, initPath, LO.name, LO.short, LO.descr, start,
                         restart, stop, status)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Site(Init):
    '''Represents an init script for controlling an Appy site's init script on
       some target.'''

    # Init script descriptions
    short = 'Start %s'
    descr = 'Start the Appy site named %s.'

    def __init__(self, target):
        '''Site's specific constructor'''
        # The name of the init script will be equal to the name of the folder
        # where the app resides on the target site.
        name = target.siteName
        controlPath = target.sitePath + '/bin/site'
        initPath = '%s/%s' % (Init.debianFolder, name)
        # Build the commands
        user = target.siteUser
        template = 'su %s -c "%s %%s"' % (user, controlPath)
        start   = template % 'start'
        restart = template % 'restart'
        stop    = template % 'stop'
        status = ''
        super().__init__(target, initPath, name, Site.short % name,
                         Site.descr % name, start, restart, stop, status)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
