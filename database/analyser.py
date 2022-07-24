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
SANE_FILES = '  %d walked sane files (total size: %s).'
PH_FOUND   = '  %s phantom file(s) found (total size: %s), moved to %s.'
PH_NO      = '  No phantom file was found.'
MISS_TEXT  = '  Missing files on disk = %d.'
A_START    = 'Analysing database @%s...'
WALK       = '  Walking instances of class...'
WALK_C     = '   %s...'
WALKED     = '   > %d object(s) analysed.'
WALKED_TOT = '  %d objects in the datase.'
WALK_FS    = '  Walking filesystem @%s...'
DISK_KO    = '  Missing on disk for %s :: %s'
A_END      = 'Done.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Analyser:
    '''Detect (and possibly repair) incoherences between FileInfo instances as
       stored in the database and corresponding files stored on the
       DB-controlled filesystem.'''

    # One of the possible "repair actions" is to remove found phantom files and
    # folders. A phantom file is a file being present on the DB-controlled
    # filesystem but not mentioned in any FileInfo instance in the database.

    def __init__(self, handler, logger):
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
        # FileInfo instances, for which there is no corresponding file on the
        # filesystem.
        # ~
        # At present, for these missing files, no repair action is performed
        r = total = 0
        tool = self.tool
        pre = len(str(self.binariesFolder))
        self.log(WALK)
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
                        self.log(DISK_KO % (className, fpath), type='error')
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
                    fpath = str(filePath)[pre:]
                    # Ensure there is a corresponding object::FileInfo instance
                    # in the database.
                    if o is None:
                        # This object does not exist
                        self.log(PH_O_KO % fpath, type='error')
                        # Move the complete folder to the phantom folder
                        phantomFound = True
                        self.removePhantomFolder(filePath.parent)
                        continue
                    # Get the FileInfo
                    fname = filePath.stem
                    # Get the FileInfo system
                    text = None
                    try:
                        info = getattr(o, fname)
                    except AttributeError:
                        # vp_filePath does not correspond to any File field on
                        # p_o. Remove it.
                        info = None
                        text = PH_F_MM
                    if info is None:
                        # This file is not mentioned in the DB for this existing
                        # object.
                        self.log((text or PH_F_KO) % fpath, type='error')
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
        self.log(A_START % self.config.database.filePath)
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
