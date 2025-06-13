'''Analyses (and possibly repair) an appy database'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import os
from pathlib import Path

from DateTime import DateTime

from appy.utils import path as putils
from appy.model.fields.file import File

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
PH_EXISTS  = 'DB analysis aborted - Phantom folder "%s" exists.'
PH_KO      = '  DB-phantom file @%%s (%s).'
PH_O_KO    = PH_KO % 'inexistent object'
PH_F_KO    = PH_KO % 'unreferenced field'
PH_F_MM    = PH_KO % 'mismatched field'
PH_F_MP    = PH_KO % 'mismatched path · FileInfo path is %s'
SANE_FILES = '  %d walked sane files (total size: %s).'
PH_FOUND   = '  %s phantom file(s) found (total size: %s), moved to %s.'
PH_NO      = '  No phantom file was found.'
MISS_TEXT  = '  Missing files on disk = %d.'
A_START    = 'Analysing database @%s (%s)...'
WALK       = '  Walking instances of class...'
WALK_C     = '   %s...'
WALKED     = '   > %d object(s) analysed.'
WALKED_TOT = '  %d objects in the database.'
WALK_FS    = '  Walking filesystem @%s...'
DISK_KO    = '  Missing on disk for %s :: %s%s'
RISHES     = '  ✅ "Rise file from the ashes" method :: File %s is back.'
TMP_FOUND  = ' :: A copy exists in %s (%d bytes); the FileInfo-referred file ' \
             'is %d bytes).'
A_END      = 'Done.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Analyser:
    '''Detect (and possibly repair) incoherences between FileInfo objects as
       stored in the database and corresponding files stored on the
       DB-controlled filesystem.'''

    # One of the possible "repair actions" is to remove found phantom files and
    # folders. A phantom file is a file being present on the DB-controlled
    # filesystem but not mentioned in any FileInfo instance in the database.

    def __init__(self, handler, logger, method=None):
        self.handler = handler
        self.logger = logger
        self.tool = handler.dbConnection.root.objects.get('tool')
        self.config = handler.server.config
        # The folder containing the DB-controlled files
        cfg = self.config.database
        self.binariesFolder = cfg.binariesFolder
        # Define a folder where to move potentially found phantom files
        now = DateTime()
        self.phantomFolder = cfg.phantomFolder / now.strftime('%Y%m%d_%H%M%S')
        # p_method, if passed, is a "rise file from the ashes" method: it will
        # allow to find or rebuild a file being mentioned in a FileInfo object
        # but being missing on disk.
        self.method = method

    def log(self, text, type='info'):
        '''Logs this p_text'''
        getattr(self.logger, type)(text)

    def collectFields(self):
        '''Get a dict of all the app's File fields, keyed by class name'''
        r = {}
        for class_ in self.tool.model.classes.values():
            # Ignore not indexable classes, considered as transient
            if not class_.isIndexable(): continue
            className = class_.name
            for field in class_.fields.values():
                if isinstance(field, File):
                    # Add this field in v_r
                    if className in r:
                        r[className].append(field)
                    else:
                        r[className] = [field]
        return r

    def walkDatabase(self, fileFields):
        '''Walks all database objects, checking presence of disk files for every
           FileInfo object.'''
        # Logs a text message explaining the number of files, mentioned in
        # FileInfo objects, for which there is no corresponding file on the
        # filesystem.
        #
        # If a method is specified in p_self.method, it will be used to try to
        # find or rebuild the missing file.
        r = total = 0
        tool = self.tool
        pre = len(str(self.binariesFolder))
        self.log(WALK)
        method = getattr(tool, self.method) if self.method else None
        for className, fields in fileFields.items():
            self.log(WALK_C % className)
            count = 0 # Count the number of walked objects
            for o in tool.search(className):
                count += 1
                # Check all File fields on this object
                for field in fields:
                    info = getattr(o, field.name)
                    if info is None: continue
                    path = info.getFilePath(o, checkTemp=False)
                    if not path.is_file():
                        r += 1
                        fpath = str(path)[pre:]
                        # For this missing file, do we have a copy in the OS
                        # temp folder ?
                        tempPath = info.getTempFilePath(o)
                        if tempPath.is_file():
                            tempSize = os.stat(str(tempPath)).st_size
                            suffix = TMP_FOUND % (tempPath, tempSize, info.size)
                        else:
                            suffix = ''
                        self.log(DISK_KO % (className, fpath, suffix),
                                 type='error')
                        if method:
                            # Call this v_method on the tool to try to find or
                            # rebuild the file.
                            success = method(o, field, info)
                            # Uncount this file: it has been repaired
                            if success:
                                tool.log(RISHES % path)
                                r -= 1
            self.log(WALKED % count)
            total += count
        self.log(WALKED_TOT % total)
        self.log(MISS_TEXT % r)

    def getPhantomFolder(self):
        '''Returns p_self.phantomFolder. Create it if it does not exists on
           disk.'''
        r = self.phantomFolder
        if not os.path.isdir(r):
            os.makedirs(r)
        return r

    def removePhantomFolder(self, folder):
        '''Moves this phantom p_folder into the self.phantomFolder'''
        # Get the base phantom folder
        base = self.getPhantomFolder()
        # Move p_folder within v_base
        dest = os.path.join(base, os.path.basename(folder))
        os.rename(folder, dest)

    def removePhantomFile(self, path):
        '''Moves file @p_path into the self.phantomFolder'''
        # Get the base phantom folder
        base = self.getPhantomFolder()
        # p_path will be stored, in the phantom folder, in a sub-folder named
        # after its own parent folder.
        sub = os.path.basename(os.path.dirname(path))
        dest = os.path.join(base, sub)
        if not os.path.isdir(dest):
            os.makedirs(dest)
        os.rename(path, os.path.join(dest, os.path.basename(path)))

    def isPhantom(self, o, path, name):
        '''Is the file at this relative p_path, having this p_name, not referred
           in the database, via a FileInfo object ?'''
        # Get the name of the corresponding File field
        i = name.find('.')
        if i != -1:
            name = name[:i]
        # Try to get the corresponding FileInfo object
        r = False
        text = None
        try:
            info = getattr(o, name)
        except AttributeError:
            # v_name does not correspond to any File field on p_o
            info = None
            text = PH_F_MM
        if info is None:
            # This file is not mentioned in the DB for this existing object
            r = True
            self.log((text or PH_F_KO) % path, type='error')
        else:
            # There is a FileInfo object. But does it mention the file @p_path?
            infoPath = os.path.join(info.fsPath, info.fsName)
            if infoPath != path:
                # No
                self.log(PH_F_MP % (path, infoPath), type='error')
                r = True
        return r

    def walkFilesystem(self, fileFields):
        '''Walks all folders from the DB-controled filesystem, checking the
           presence of FileInfo objects for every file.'''
        tool = self.tool
        self.log(WALK_FS % self.binariesFolder)
        baseFolder = self.binariesFolder
        pre = len(str(baseFolder))
        phantomFound = False
        # The total size and number of sane files on disk
        totalNumber = totalSize = 0
        for path in baseFolder.iterdir():
            # Ignore non-folder files (like appy.fs) or
            if not path.is_dir() or not path.name.isdigit():
                continue
            # Walk every db-controlled folder
            for root, dirs, files in os.walk(path):
                # Ignore folders containing no file
                if not files: continue
                # Walk every file in this object folder
                folder = Path(root)
                id = folder.name
                o = tool.getObject(id)
                for name in files:
                    # Ignore frozen documents
                    if '_' in name: continue
                    # Ignore files that could have been deleted in the meanwhile
                    filePath = folder / name
                    if not filePath.is_file(): continue
                    # I have a File-field-related file
                    fpath = str(filePath)[pre+1:]
                    # Ensure there is a corresponding object in the database
                    if o is None:
                        # This object does not exist
                        self.log(PH_O_KO % fpath, type='error')
                        # Move the complete folder to the phantom folder
                        phantomFound = True
                        self.removePhantomFolder(filePath.parent)
                        continue
                    # Ensure a FileInfo object references this file
                    if self.isPhantom(o, fpath, name):
                        phantomFound = True
                        # Move this file to the phantom folder
                        self.removePhantomFile(filePath)
                        continue
                    # Update totals about sane walked files
                    totalNumber += 1
                    totalSize += filePath.stat().st_size
        # Return details about the operation, as a string
        if phantomFound:
            size, nb = putils.getFolderSize(self.phantomFolder, nice=True,
                                            withCounts=True)
            text = PH_FOUND % (nb, size, self.phantomFolder)
        else:
            text = PH_NO
        self.log(text)
        # End with info about the sane files found in the DB-controlled
        # filesystem.
        sane = SANE_FILES % (totalNumber, putils.getShownSize(totalSize))
        self.log(sane)

    def run(self):
        '''Run the analysis and repair process'''
        # Abort when relevant
        if self.phantomFolder.is_dir():
            self.log(PH_EXISTS % self.phantomFolder)
            return
        # Start the analysis
        tool = self.tool
        config = self.config.database
        self.log(A_START % (config.filePath, config.getDatabaseSize(True)))
        # Step #1 - Collect all File fields per Appy class
        fileFields = self.collectFields()
        # Step #2 - Walk all objects
        #         > Check FileInfo correctness w.r.t file system
        self.walkDatabase(fileFields)
        # Step #3 - Walk the file system
        #         > Check existing files not being mentioned in the DB
        self.walkFilesystem(fileFields)
        # Log and return final results
        self.log(A_END)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
