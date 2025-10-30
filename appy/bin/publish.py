#!/usr/bin/env python3

'''Publishes the Appy framework on PyPI'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from pathlib import Path
import os, sys, shutil, time

import appy
from appy.bin import Program
from appy.utils.loc import Counter
from appy.utils import executeCommand
from appy.utils.path import cleanFolder, getOsTempFolder, FolderDeleter

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
bn = '\n'
HELP_COM = 'Use this if you want to build the commercial version of Appy.'
RUN_CMD  = 'Executing %s...'
PUB_APPY = 'Publishing Appy %s for Python 2 & 3...'
STATS_S  = '*** Stats for Appy (Python 3)...'
STATS_E  = '***'
UPLOAD_P = 'Upload %s on PyPI?'
PROCEED  = 'Proceed ?'
CLEAN_T  = 'Clean temp folder %s?'
NO_PY2   = '%s not found :: Publication process aborted.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#               Copyright information to inject in Python files
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

copyright = f"Copyright (C) 2007-{time.localtime()[0]} Gaetan Delannay"

licenses = {
  'commercial': f'# {copyright}',
  'libre': '''# %s

# This file is part of Appy.

# Appy is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.

# Appy is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with
# Appy. If not, see <http://www.gnu.org/licenses/>.''' % copyright
}

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Content of distutils files: setup.py, README and MANIFEST.in
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

setupPy = '''import os, sys
from setuptools import setup
def findPackages(base):
    r = []
    for dir, dns, fns in os.walk(base + os.sep + 'appy'):
        r.append(dir[4:].replace(os.sep, '.'))
    return r

# Python 2 or 3 ?
base = 'py%d' % sys.version_info[0]
if base == 'py3':
    dependencies = ['zodb', 'DateTime']
    scripts = ['py3/appy/bin/appy']
else:
    dependencies = []
    scripts = None

# The version specifier must be unique to both Python 2 and Python 3 (since
# setuptools has replaced distutils).
python = '>=2.4, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*'

setup(name = "appy", version = "{version}",
      description = "The Appy framework",
      long_description = "Appy is the simpliest way to build complex webapps.",
      author = "Gaetan Delannay",
      author_email = "gaetan.delannay@geezteem.com",
      license = "GPL", platforms="all",
      url = 'https://appyframe.work',
      packages = findPackages(base),
      package_dir = {'appy': base + os.sep + 'appy'},
      package_data = {'':["*.*"]},
      install_requires = dependencies, python_requires = python,
      scripts = scripts)
'''

readMe = '''
Appy is a web framework written in Python 3 to build webapps.

The part of the framework named "appy.pod" works with Python 2 as well.

Appy requires :
- Python 3.6 or higher;
- the Zope Object DataBase (ZODB)

To install pip (Debian/Ubuntu):
sudo apt install python3-pip

To install optional Python dependencies:
pip3 install python-ldap
'''

manifestIn = '''
recursive-include py2 *
recursive-include py3 *
'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Cleaner:
    '''Removes any non-publishable file within Appy'''

    def __init__(self, path):
        # The Appy path
        self.path = path

    def run(self, verbose=True):
        path = self.path
        cleanFolder(path, verbose=verbose)
        # Remove all files in temp folders
        for folder in (path/'temp', path/'pod'/'test'/'temp'):
            if folder.exists():
                FolderDeleter.delete(str(folder))
        # Remove test reports if any
        report = path/'pod'/'test'/'Tester.report.txt'
        if report.exists():
            report.unink()
        # Remove all __pycache__ folders
        for folder in path.glob('**/__pycache__'):
            folder.rmdir()

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Publisher(Program):

    # Interpreter to use to retrieve Appy for Python 2
    python2 = 'python2.4.4'

    # Appy folders and files that must not be published, In python 2 or 3, open
    # source or commercial variants.
    pub = 'bin/publish.py'
    unpublished = {
      'py2': { 'commercial':  ('bin', 'doc', 'fields', 'gen', 'px', 'test'),
               'libre':       (pub, 'doc')
       },
      'py3': { 'commercial':  ('bin', 'data', 'database', 'deploy',
                               'model', 'px', 'server', 'tr', 'ui',
                               '__init__.py', 'all.py', 'INSTALL', 'VERSION'),
               'libre': (pub, 'VERSION',)
       }
    }

    def defineArguments(self):
        '''Define the allowed arguments for this program'''
        parser = self.parser
        # Optional arguments
        add = parser.add_argument
        add('-c', '--commercial', help=HELP_COM, action='store_true')

    def analyseArguments(self):
        '''Check and store arguments'''
        # Must the commercial version of Appy be built or the open source one ?
        self.type = 'commercial' if self.args.commercial else 'libre'

    def ask(self, question, default='yes'):
        '''Asks a p_question to the user and returns True if the user answered
           "yes".'''
        defaultIsYes = default.lower() in ('y', 'yes')
        yesNo = '[Y/n]' if defaultIsYes else '[y/N]'
        print(question + ' ' + yesNo, end=' ')
        sys.stdout.flush()
        response = sys.stdin.readline().strip().lower()
        r = False
        if response in ('y', 'yes'):
            r = True
        elif response in ('n', 'no'):
            r = False
        elif not response:
            # It depends on default value
            r = defaultIsYes
        return r

    def executeCommand(self, cmd):
        '''Executes the system command p_cmd'''
        print(RUN_CMD % cmd)
        out, err = executeCommand(cmd)
        if out: print(out)
        if err: print(err)

    def applyLicense(self, folder):
        '''Inject the appropriate license into any .py file found in p_folder
           at any depth.'''
        text = licenses[self.type]
        commercial = self.type == 'commercial'
        for pythonFile in folder.glob('**/*.py'):
            path = str(pythonFile)
            # Ignore POD contexts from the test system
            if '/test/contexts/' in path: continue
            # Must we patch the "commercial" variable ?
            patchCommercial = commercial and \
                              (path.endswith('py3/appy/utils/__init__.py') or \
                               path.endswith('py2/appy/__init__.py'))
            # Inject the license headers into it
            with open(pythonFile) as f: content = f.read()
            with open(pythonFile, 'w') as f:
                content = content.replace('# ~license~', text)
                if patchCommercial:
                    content = content.replace('commercial = False',
                                              'commercial = True')
                f.write(content)

    def copySources(self, py2path, py3path):
        '''Copy Python source files to a temp folder'''
        # Create the temp folder where the dist tree will be dumped
        self.tempFolder = Path(getOsTempFolder(sub=True))
        # Copy files in it
        for py in ('py2', 'py3'):
            folder = self.tempFolder / py
            folder.mkdir()
            folder = folder / 'appy'
            path = eval(f'{py}path')
            shutil.copytree(path, folder)
            # Clean unwanted files and folders
            for name in self.unpublished[py][self.type]:
                sub = folder / name
                if sub.is_file():
                    sub.unlink()
                    if sub.name == '__init__.py':
                        # Recreate an empty one
                        with sub.open('w') as f: f.write('# Appy')
                else:
                    FolderDeleter.delete(str(sub))
            # Delete .git folders and .gitignore files
            for git in folder.glob('**/.git'): FolderDeleter.delete(str(git))
            gignore = folder / '.gitignore'
            if gignore.is_file():
                gignore.unlink()
            # Inject the appropriate license in Python files
            self.applyLicense(folder)
            # Inject the Appy version in version.py
            with (folder / 'version.py').open('w') as f:
                f.write(f'short = "{self.version}"{bn}')
                f.write(f'verbose = "{self.versionLong}"')

    def createDistutils(self):
        '''Creates a distutils package from p_self.tempFolder content'''
        # Create the base files (setup.py, README...) required by distutils
        with (self.tempFolder / 'setup.py').open('w') as f:
            f.write(setupPy.replace('{version}', self.version))
        with (self.tempFolder / 'README').open('w') as f: f.write(readMe)
        with (self.tempFolder / 'MANIFEST.in').open('w') as f:
            f.write(manifestIn)
        # Create the source distribution
        os.chdir(self.tempFolder)
        self.executeCommand(['python3', 'setup.py', 'sdist'])
        # Distutils has created the .tar.gz file in p_self.tempFolder / dist
        distFolder = self.tempFolder / 'dist'
        name = os.listdir(distFolder)[0]
        # Upload it on PyPI ?
        if self.ask(UPLOAD_P % name, default='no'):
            self.executeCommand(['twine', 'upload', str(distFolder/name)])

    def run(self):
        '''Publishes Appy on PyPI'''
        # Get the Appy version, and paths to Appy for Python 2 & 3
        self.version = None
        path3 = Path(appy.__file__).parent
        with open(path3 / 'VERSION') as f:
            self.version = f.read().strip()
        # Long version includes release date and hour
        timestamp = time.strftime('%Y/%m/%d %H:%M')
        self.versionLong = f'{self.version} ({timestamp})'
        # As a preamble, count the number of lines of code within latest Appy
        print(STATS_S)
        Counter(path3, spaces=' '*3).run()
        print(STATS_E)
        # Retrieve the path to Appy for Python 2
        try:
            command = [self.python2,'-c','import appy; print(appy.__path__[0])']
            out, err = executeCommand(command)
            path2 = Path(out.strip())
        except FileNotFoundError:
            # Python 2 is not here
            print(NO_PY2 % self.python2)
            return
        # Start the publication process
        print(PUB_APPY % self.version)
        proceed = self.ask(PROCEED)
        if not proceed: sys.exit(1)
        # Clean Appy folders
        for path in (path2, path3): Cleaner(path).run(verbose=False)
        # Copy Appy sources to a temp folder
        self.copySources(path2, path3)
        # Create a distutils package in this temp folder
        self.createDistutils()
        # Clean the temp folder
        if self.ask(CLEAN_T % self.tempFolder, default='yes'):
            FolderDeleter.delete(str(self.tempFolder))

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
if __name__ == '__main__': Publisher().run()
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
