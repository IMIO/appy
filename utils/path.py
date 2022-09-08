'''Operations on files and folders (=paths)'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from pathlib import Path
import os, os.path, time, shutil, mimetypes, tempfile

from appy import utils

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
defaultMimeType = 'application/octet-stream'

def guessMimeType(fileName):
    '''Try to find the MIME type of file p_fileName'''
    fileName = str(fileName) if isinstance(fileName, Path) else fileName
    return mimetypes.guess_type(fileName)[0] or defaultMimeType

def getShownSize(size, unbreakable=False):
    '''Express p_size (a file size in bytes) in a human-readable way'''
    b = ' ' if unbreakable else ' '
    # Display the size in bytes if smaller than 1024 bytes
    if size < 1024: return '%d%sbyte(s)' % (size, b)
    size /= 1024 # This is the size, in Kb
    if size < 1024: return '%s%sKb' % (utils.formatNumber(size, precision=1), b)
    size /= 1024 # This is the size, in Mb
    if size < 1024: return '%s%sMb' % (utils.formatNumber(size, precision=1), b)
    size /= 1024 # This is the size, in Gb
    return '%s%sGb' % (utils.formatNumber(size, precision=1), b)

def getFolderSize(folder, nice=False, withCounts=False):
    '''Returns the size of this p_folder (all content, recursively)'''
    r = 0
    counts = 0 # Count the number of files
    for root, dirs, files in os.walk(folder):
        for name in files:
            r += os.stat(os.path.join(root, name)).st_size
            counts += 1
    # Nicely format the size if requested
    if nice:
        r = getShownSize(r)
    # Return the counts of files as well if requested
    if withCounts:
        r = r, counts
    return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def getOsTempFolder(sub=False):
    '''Gets the absolute path to the temp folder on this machine. If p_sub is
       True, it creates a sub-folder within this temp folder and returns its
       absolute path instead of the "root" temp folder path.'''
    return tempfile.mkdtemp(prefix='Appy') if sub else tempfile.gettempdir()

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def getTempFileName(prefix='', extension='', timestamp=True):
    '''Returns the absolute path to a unique file name in the OS temp folder.
       The caller will then be able to create a file with this name.

       A p_prefix to this file can be provided. If an p_extension is provided,
       it will be appended to the name. Both dotted and not dotted versions
       of p_extension are allowed (ie, ".pdf" or "pdf").'''
    # Suffix the file name with a timestamp when relevant
    suffix = timestamp and ('_%f' % time.time()) or ''
    res = os.path.join(getOsTempFolder(), '%s%s' % (prefix, suffix))
    if extension:
        if extension.startswith('.'): res += extension
        else: res += '.' + extension
    return res

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class FolderDeleter:
    '''Class allowing to delete folders and their content, recursively'''

    @classmethod
    def deleteEmpty(class_, dirName):
        '''Deletes p_dirName and its parent dirs if they are empty'''
        while True:
            try:
                if not os.listdir(dirName):
                    os.rmdir(dirName)
                    dirName = os.path.dirname(dirName)
                else:
                    break
            except OSError:
                break

    @classmethod
    def delete(class_, dirName, move=False):
        '''Recursively deletes p_dirName. If p_move is True, instead of
           effectively deleting p_dirName, it tries to move it to the OS temp
           folder.'''
        if move:
            # Instead of deleting it, try to move it to the OS temp folder
            name = os.path.basename(dirName)
            tempFolder = os.path.join(getOsTempFolder(), name)
            if os.path.exists(tempFolder):
                class_.delete(tempFolder, move=False)
            try:
                os.rename(dirName, tempFolder)
            except OSError:
                # Renaming the folder may crash if the source and target devices
                # are different.
                class_.delete(dirName, move=False)
            # Remove the parent folder if empty
            class_.deleteEmpty(os.path.dirname(dirName))
        else:
            # Delete p_dirName and its content
            dirName = os.path.abspath(dirName)
            for root, dirs, files in os.walk(dirName, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(dirName)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
extsToClean = ('.pyc', '.pyo', '.fsz', '.deltafsz', '.dat', '.log')
def cleanFolder(folder, exts=extsToClean, folders=(), verbose=False):
    '''This function allows to remove, in p_folder and subfolders, any file
       whose extension is in p_exts, and any folder whose name is in
       p_folders.'''
    if verbose: print('Cleaning folder %s...' % folder)
    # Remove files with an extension listed in p_exts
    if exts:
        for root, dirs, files in os.walk(folder):
            for fileName in files:
                ext = os.path.splitext(fileName)[1]
                if (ext in exts) or ext.endswith('~'):
                    fileToRemove = os.path.join(root, fileName)
                    if verbose: print('Removing file %s...' % fileToRemove)
                    os.remove(fileToRemove)
    # Remove folders whose names are in p_folders.
    if folders:
        for root, dirs, files in os.walk(folder):
            for folderName in dirs:
                if folderName in folders:
                    toDelete = os.path.join(root, folderName)
                    if verbose: print('Removing folder %s...' % toDelete)
                    FolderDeleter.delete(toDelete)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def resolvePath(path):
    '''p_path is a file path that can contain occurences of "." and "..". This
       function resolves them and procuces a minimal path.'''
    res = []
    for elem in path.split(os.sep):
        if elem == '.': pass
        elif elem == '..': res.pop()
        else: res.append(elem)
    return os.sep.join(res)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def copyFolder(source, dest, cleanDest=False):
    '''Copies the content of folder p_source to folder p_dest. p_dest is
       created, with intermediary subfolders if required. If p_cleanDest is
       True, it removes completely p_dest if it existed. Else, content of
       p_source will be added to possibly existing content in p_dest, excepted
       if file names corresponds. In this case, file in p_source will overwrite
       file in p_dest.'''
    dest = os.path.abspath(dest)
    # Delete the dest folder if required
    if os.path.exists(dest) and cleanDest:
        FolderDeleter.delete(dest)
    # Create the dest folder if it does not exist
    if not os.path.exists(dest):
        os.makedirs(dest)
    # Copy the content of p_source to p_dest.
    for name in os.listdir(source):
        sourceName = os.path.join(source, name)
        destName = os.path.join(dest, name)
        if os.path.isfile(sourceName):
            # Copy a single file
            shutil.copy(sourceName, destName)
        elif os.path.isdir(sourceName):
            # Copy a subfolder (recursively)
            copyFolder(sourceName, destName)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def chown(path, login, group=None, recursive=True):
    '''Grants, to p_login, p_path's ownership (and all its content, recursively,
       if p_recursive is True).'''
    # chown p_path
    shutil.chown(path, user=login, group=group)
    if not recursive: return
    # Manage the recursive case
    path = Path(path) if isinstance(path, str) else path
    for sub in path.glob('**/*'):
        shutil.chown(sub, user=login, group=group)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
