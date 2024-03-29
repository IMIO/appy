# ~license~
# ------------------------------------------------------------------------------
import os, os.path, md5, shutil
from appy.shared.utils import getOsTempFolder, FolderDeleter, cleanFolder, \
                              executeCommand

# ------------------------------------------------------------------------------
debianInfo = '''Package: python-appy%s
Version: %s
Architecture: all
Maintainer: Gaetan Delannay <gaetan.delannay@geezteem.com>
Installed-Size: %d
Depends: python (>= %s)%s
Section: python
Priority: optional
Homepage: http://appyframework.org
Description: Appy builds simple but complex web Python apps.
'''
appCtl = '''#! /usr/lib/zope2.12/bin/python
import sys
from appy.bin.zopectl import ZopeRunner
args = ' '.join(sys.argv[1:])
sys.argv = [sys.argv[0], '-C', '/etc/%s.conf', args]
ZopeRunner().run()
'''
appRun = '''#! /bin/sh
exec "/usr/lib/zope2.12/bin/runzope" -C "/etc/%s.conf" "$@"
'''
loStart = '#! /bin/sh\nsoffice --invisible --headless --nofirststartwizard ' \
          '"--accept=socket,host=localhost,port=2002;urp;"'
zopeConf = '''# Zope configuration.
%%define INSTANCE %s
%%define DATA %s
%%define LOG %s
%%define HTTPPORT %s
%%define ZOPE_USER zope

instancehome $INSTANCE
effective-user $ZOPE_USER
%s
<eventlog>
  level info
  <logfile>
    path $LOG/event.log
    level info
  </logfile>
</eventlog>
<logger access>
  level WARN
  <logfile>
    path $LOG/Z2.log
    format %%(message)s
  </logfile>
</logger>
<http-server>
  address $HTTPPORT
</http-server>
<zodb_db main>
  <filestorage>
    path $DATA/Data.fs
  </filestorage>
  mount-point /
</zodb_db>
<zodb_db temporary>
  <temporarystorage>
   name temporary storage for sessioning
  </temporarystorage>
  mount-point /temp_folder
  container-class Products.TemporaryFolder.TemporaryContainer
</zodb_db>
'''
# initScript below will be used to define the scripts that will run the
# app-powered Zope instance and OpenOffice in server mode at boot time.
initScript = '''#! /bin/sh
### BEGIN INIT INFO
# Provides:          %s
# Required-Start:    $syslog $remote_fs
# Required-Stop:     $syslog $remote_fs
# Should-Start:      $remote_fs
# Should-Stop:       $remote_fs
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Start %s
# Description:       %s
### END INIT INFO

case "$1" in
  start)
    %s
    ;;
  restart|reload|force-reload)
    %s
    ;;
  stop)
    %s
    ;;
  *)
    echo "Usage: $0 start|restart|stop" >&2
    exit 3
    ;;
esac
exit 0
'''

class Debianizer:
    '''This class allows to produce a Debian package from a Python (Appy)
       package.'''

    def __init__(self, app, out, appVersion='0.1.0',
                 pythonVersions=('2.6',), zopePort=8080,
                 depends=('zope2.12', 'openoffice.org', 'imagemagick'),
                 sign=False):
        # app is the path to the Python package to Debianize.
        self.app = app
        self.appName = os.path.basename(app)
        self.appNameLower = self.appName.lower()
        # Must we sign the Debian package? If yes, we make the assumption that
        # the currently logged user has a public/private key pair in ~/.gnupg,
        # generated with command "gpg --gen-key".
        self.sign = sign
        # out is the folder where the Debian package will be generated.
        self.out = out
        # What is the version number for this app ?
        self.appVersion = appVersion
        # On which Python versions will the Debian package depend?
        self.pythonVersions = pythonVersions
        # Port for Zope
        self.zopePort = zopePort
        # Debian package dependencies
        self.depends = depends
        # Zope 2.12 requires Python 2.6
        if 'zope2.12' in depends: self.pythonVersions = ('2.6',)

    def run(self):
        '''Generates the Debian package.'''
        curdir = os.getcwd()
        j = os.path.join
        tempFolder = getOsTempFolder()
        # Create, in the temp folder, the required sub-structure for the Debian
        # package.
        debFolder = j(tempFolder, 'debian')
        if os.path.exists(debFolder):
            FolderDeleter.delete(debFolder)
        # Copy the Python package into it
        srcFolder = j(debFolder, 'usr', 'lib')
        for version in self.pythonVersions:
            libFolder = j(srcFolder, 'python%s' % version)
            os.makedirs(libFolder)
            destFolder = j(libFolder, self.appName)
            shutil.copytree(self.app, destFolder)
            # Clean dest folder (.svn/.bzr files)
            cleanFolder(destFolder, folders=('.svn', '.bzr'))
        # When packaging Appy itself, everything is in /usr/lib/pythonX. When
        # packaging an Appy app, we will generate more files for creating a
        # running instance.
        if self.appName != 'appy':
            # Create the folders that will collectively represent the deployed
            # Zope instance.
            binFolder = j(debFolder, 'usr', 'bin')
            os.makedirs(binFolder)
            # <app>ctl
            name = '%s/%sctl' % (binFolder, self.appNameLower)
            f = file(name, 'w')
            f.write(appCtl % self.appNameLower)
            os.chmod(name, 0744) # Make it executable by owner.
            f.close()
            # <app>run
            name = '%s/%srun' % (binFolder, self.appNameLower)
            f = file(name, 'w')
            f.write(appRun % self.appNameLower)
            os.chmod(name, 0744) # Make it executable by owner.
            f.close()
            # startlo
            name = '%s/startlo' % binFolder
            f = file(name, 'w')
            f.write(loStart)
            f.close()
            os.chmod(name, 0744) # Make it executable by owner.
            # /var/lib/<app> (will store Data.fs, lock files, etc)
            varLibFolder = j(debFolder, 'var', 'lib', self.appNameLower)
            os.makedirs(varLibFolder)
            f = file('%s/README' % varLibFolder, 'w')
            f.write('This folder stores the %s database.\n' % self.appName)
            f.close()
            # /var/log/<app> (will store event.log and Z2.log)
            varLogFolder = j(debFolder, 'var', 'log', self.appNameLower)
            os.makedirs(varLogFolder)
            f = file('%s/README' % varLogFolder, 'w')
            f.write('This folder stores the log files for %s.\n' % self.appName)
            f.close()
            # /etc/<app>.conf (Zope configuration file)
            etcFolder = j(debFolder, 'etc')
            os.makedirs(etcFolder)
            name = '%s/%s.conf' % (etcFolder, self.appNameLower)
            n = self.appNameLower
            f = file(name, 'w')
            productsFolder = '/usr/lib/python%s/%s/zope' % \
                             (self.pythonVersions[0], self.appName)
            f.write(zopeConf % ('/var/lib/%s' % n, '/var/lib/%s' % n,
                                '/var/log/%s' % n, str(self.zopePort),
                                'products %s\n' % productsFolder))
            f.close()
            # /etc/init.d/<app> (start the app at boot time)
            initdFolder = j(etcFolder, 'init.d')
            os.makedirs(initdFolder)
            name = '%s/%s' % (initdFolder, self.appNameLower)
            f = file(name, 'w')
            n = self.appNameLower
            f.write(initScript % (n, n, 'Start Zope with the Appy-based %s ' \
                                  'application.' % n, '%sctl start' % n,
                                  '%sctl restart' % n, '%sctl stop' % n))
            f.close()
            os.chmod(name, 0744) # Make it executable by owner
            # /etc/init.d/lo (start LibreOffice at boot time)
            name = '%s/lo' % initdFolder
            f = file(name, 'w')
            f.write(initScript % ('lo','lo', 'Start LibreOffice in server mode',
                                  'startlo', 'startlo', "#Can't stop LO."))
            f.write('\n')
            f.close()
            os.chmod(name, 0744) # Make it executable by owner.
        # Get the size of the app, in Kb.
        os.chdir(tempFolder)
        out, err = executeCommand(['du', '-b', '-s', 'debian'])
        size = int(int(out.split()[0])/1024.0)
        os.chdir(debFolder)
        # Create data.tar.gz based on it
        executeCommand(['tar', 'czvf', 'data.tar.gz', '*'])
        # Create the control file
        f = file('control', 'w')
        nameSuffix = ''
        dependencies = []
        if self.appName != 'appy':
            nameSuffix = '-%s' % self.appNameLower
            dependencies.append('python-appy')
        if self.depends:
            for d in self.depends: dependencies.append(d)
        depends = ''
        if dependencies:
            depends = ', ' + ', '.join(dependencies)
        f.write(debianInfo % (nameSuffix, self.appVersion, size,
                              self.pythonVersions[0], depends))
        f.close()
        # Create md5sum file
        f = file('md5sums', 'w')
        toWalk = ['usr']
        if self.appName != 'appy':
            toWalk += ['etc', 'var']
        for folderToWalk in toWalk:
            for dir, dirnames, filenames in os.walk(folderToWalk):
                for name in filenames:
                    m = md5.new()
                    pathName = j(dir, name)
                    currentFile = file(pathName, 'rb')
                    while True:
                        data = currentFile.read(8096)
                        if not data:
                            break
                        m.update(data)
                    currentFile.close()
                    # Add the md5 sum to the file
                    f.write('%s  %s\n' % (m.hexdigest(), pathName))
        f.close()
        # Create postinst, a script that will:
        # - bytecompile Python files after the Debian install
        # - change ownership of some files if required
        # - [in the case of an app-package] call update-rc.d for starting it at
        #   boot time.
        f = file('postinst', 'w')
        content = '#!/bin/sh\nset -e\n'
        for version in self.pythonVersions:
            bin = '/usr/bin/python%s' % version
            lib = '/usr/lib/python%s' % version
            cmds = ' %s -m compileall -q %s/%s 2> /dev/null\n' % (bin, lib,
                                                                  self.appName)
            content += 'if [ -e %s ]\nthen\n%sfi\n' % (bin, cmds)
        if self.appName != 'appy':
            # Allow user "zope", that runs the Zope instance, to write the
            # database and log files.
            content += 'chown -R zope:root /var/lib/%s\n' % self.appNameLower
            content += 'chown -R zope:root /var/log/%s\n' % self.appNameLower
            # Call update-rc.d for starting the app at boot time
            content += 'update-rc.d %s defaults\n' % self.appNameLower
            content += 'update-rc.d lo defaults\n'
            # (re-)start the app
            content += '%sctl restart\n' % self.appNameLower
            # (re-)start lo
            content += 'startlo\n'
        f.write(content)
        f.close()
        # Create prerm, a script that will remove all pyc files before removing
        # the Debian package.
        f = file('prerm', 'w')
        content = '#!/bin/sh\nset -e\n'
        for version in self.pythonVersions:
            content += 'find /usr/lib/python%s/%s -name "*.pyc" -delete\n' % \
                       (version, self.appName)
        f.write(content)
        f.close()
        # Create control.tar.gz
        executeCommand(['tar', 'czvf', 'control.tar.gz', './control',
                        './md5sums', './postinst', './prerm'])
        # Create debian-binary
        f = file('debian-binary', 'w')
        f.write('2.0\n')
        f.close()
        # Create the signature if required
        if self.sign:
            # Create the concatenated version of all files within the deb
            out, err = executeCommand(['cat', 'debian-binary', 'control.tar.gz',
                                       'data.tar.gz'])
            f = file('/tmp/combined-contents', 'wb')
            f.write(out)
            f.close()
            executeCommand(['gpg', '-abs', '-o', '_gpgorigin',
                            '/tmp/combined-contents'])
            signFile = '_gpgorigin'
            os.remove('/tmp/combined-contents')
            # Export the public key and name it according to its ID as found by
            # analyzing the result of command "gpg --fingerprint".
            out, err = executeCommand(['gpg', '--fingerprint'])
            fingerprint = out.split('\n')
            id = 'pubkey'
            for line in fingerprint:
                if '=' not in line: continue
                id = line.split('=')[1].strip()
                id = ''.join(id.split()[-4:])
                break
            out, err = executeCommand(['gpg', '--export', '-a'])
            f = file('%s/%s.asc' % (self.out, id), 'w')
            f.write(out)
            f.close()
        else:
            signFile = None
        # Create the .deb package
        debName = 'python-appy%s-%s.deb' % (nameSuffix, self.appVersion)
        cmd = ['ar', '-r', debName]
        if signFile: cmd.append(signFile)
        cmd += ['debian-binary', 'control.tar.gz', 'data.tar.gz']
        out, err = executeCommand(cmd)
        # Move it to self.out
        os.rename(j(debFolder, debName), j(self.out, debName))
        # Clean temp files
        FolderDeleter.delete(debFolder)
        os.chdir(curdir)
# ------------------------------------------------------------------------------
