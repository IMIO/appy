'''Builds an init script ready to be deployed and configured in /etc/init.d on a
   target machine.'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
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
    '''Creates the content of an init script'''

    def __init__(self, name, short, descr, start, restart, stop, status):
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

    def get(self, asFile=None):
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

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class LO:
    '''Generates an Init instance allowing to define an init script for
       LibreOffice (LO) in server mode.'''

    # Options to pass to the "soffice" executable
    acceptPart = 'socket,host=localhost,port='
    accept = '--accept=%s%%d;urp;' % acceptPart
    options = '--invisible --headless'

    # Name and descriptions
    name = 'lo'
    short = 'Start LibreOffice server'
    descr = 'Start LibreOffice in server mode.'

    @classmethod
    def get(class_, port=2002, user='appy', asFile=True):
        # Compute options to pass to the soffice executable
        options = '%s "%s"' % (class_.options, class_.accept % port)
        # Build the commands
        start = "cd /home/%s\n  su %s -c 'soffice %s&'" % \
                (user, user, options)
        stop = 'pkill -f %s' % class_.acceptPart
        restart = '%s\n  %s' % (stop, start)
        status = 'pgrep -l -f %s' % class_.acceptPart
        init = Init(class_.name, class_.short, class_.descr, start, restart,
                    stop, status)
        return init.get(asFile=asFile)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
