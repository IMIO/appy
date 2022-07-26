'''Functions for (un)zipping files'''

# ~license~
# ------------------------------------------------------------------------------
import os, os.path, zipfile, time
from appy.shared import mimeTypes

# ------------------------------------------------------------------------------
# Interesting sub-files within ODF files
odfInnerFiles = ('content.xml', 'styles.xml', 'meta.xml', 'mimetype')

def fixFileName(fileName):
    '''Fix potential encoding problems in p_fileName and return a fixed version
       of it.'''
    # Ensure the name can be converted to utf-8
    try:
        fileName.decode('utf-8')
    except UnicodeDecodeError:
        # CP 437 is the DOS encoding
        fileName = fileName.decode('cp437').encode('utf-8')
    return fileName

def subUnzip(folder, zipName, odf=False, fixNames=False):
    '''Unzip the zip file named p_zipName into this p_folder, by creating,
       within p_folder, a sub-folder with a unique name, into which p_zipName
       content will be unzippped. p_zipName is deleted at the end of the
       operation.'''
    # Create a folder whose name is derived from the zip
    subFolder = os.path.join(folder, zipName.replace('.', '_'))
    if os.path.exists(subFolder):
        # This name already exists, take another one
        i = 1
        exists = True
        candidate = subFolder
        while exists:
            candidate = '%s_%d' % (subFolder, i)
            if not os.path.exists(candidate):
                # This folder does not exist and can be used
                exists = False
            else:
                i += 1
        subFolder = candidate
    # Create the sub-folder in p_folder
    os.mkdir(subFolder)
    # Unzip p_zipName into it
    absZipName = os.path.join(folder, zipName)
    unzip(absZipName, subFolder, odf=odf, unzipSubZips=True, fixNames=fixNames)
    # Delete p_zipName
    os.remove(absZipName)

def unzip(f, folder, odf=False, unzipSubZips=False, fixNames=False):
    '''Unzips file p_f into p_folder. p_f can be any anything accepted by the
       zipfile.ZipFile constructor. p_folder must exist.
       
       If p_odf is True, p_f is considered to be an odt or ods file and this
       function will return a dict containing the content of content.xml,
       styles.xml, meta.xml and metadata from the zipped file.'''
    zipFile = zipfile.ZipFile(f)
    if odf: res = {}
    else: res = None
    for zippedFile in zipFile.namelist():
        # Before writing the zippedFile into p_folder, create the intermediary
        # subfolder(s) if needed.
        fileName = None
        if zippedFile.endswith('/') or zippedFile.endswith(os.sep):
            # This is an empty folder. Create it nevertheless. If zippedFile
            # starts with a '/', os.path.join will consider it an absolute
            # path and will throw away folder.
            os.makedirs(os.path.join(folder, zippedFile.lstrip('/')))
        else:
            fileName = os.path.basename(zippedFile)
            folderName = os.path.dirname(zippedFile)
            fullFolderName = folder
            if folderName:
                fullFolderName = os.path.join(fullFolderName, folderName)
                if not os.path.exists(fullFolderName):
                    os.makedirs(fullFolderName)
        # Unzip the file in folder
        if fileName:
            # Fix fileName when requested
            if fixNames: fileName = fixFileName(fileName)
            fullFileName = os.path.join(fullFolderName, fileName)
            f = open(fullFileName, 'wb')
            fileContent = zipFile.read(zippedFile)
            if odf and not folderName:
                # content.xml and others may reside in subfolders. Get only the
                # one in the root folder.
                if fileName in odfInnerFiles:
                    res[fileName] = fileContent
            f.write(fileContent)
            f.close()
            # If the unzipped file is itself a zip file, and p_unzipSubZips is
            # True, replace it with a folder containing its unzipped content.
            if unzipSubZips and fileName.endswith('.zip'):
                subUnzip(fullFolderName, fileName, odf=odf, fixNames=fixNames)
    zipFile.close()
    return res

# ------------------------------------------------------------------------------
def zip(f, folder, odf=False, encode=False):
    '''Zips the content of p_folder into the zip file whose (preferably)
       absolute filename is p_f. If p_odf is True, p_folder is considered to
       contain the standard content of an ODF file (content.xml,...). In this
       case, some rules must be respected while building the zip (see below).
       If p_encode is True, we ensure the name of every file in the zip is
       encoded with encoding CP437.'''
    # Remove p_f if it exists
    if os.path.exists(f): os.remove(f)
    try:
        zipFile = zipfile.ZipFile(f, 'w', zipfile.ZIP_DEFLATED)
    except RuntimeError:
        zipFile = zipfile.ZipFile(f, 'w')
    # If p_odf is True, insert first the file "mimetype" (uncompressed), in
    # order to be compliant with the OpenDocument Format specification,
    # section 17.4, that expresses this restriction. Else, libraries like
    # "magic", under Linux/Unix, are unable to detect the correct mimetype for
    # a pod result (it simply recognizes it as a "application/zip" and not a
    # "application/vnd.oasis.opendocument.text)".
    if odf:
        mimetypeFile = os.path.join(folder, 'mimetype')
        # This file may not exist (presumably, ods files from Google Drive)
        if not os.path.exists(mimetypeFile):
            f = file(mimetypeFile, 'w')
            f.write(mimeTypes[os.path.splitext(f)[-1][1:]])
            f.close()
        zipFile.write(mimetypeFile, 'mimetype', zipfile.ZIP_STORED)
    for dir, dirnames, filenames in os.walk(folder):
        for name in filenames:
            folderName = dir[len(folder)+1:]
            # For p_odf files, ignore file "mimetype" that was already inserted
            if odf and (folderName == '') and (name == 'mimetype'): continue
            targetName = os.path.join(folderName, name)
            if encode:
                targetName = targetName.decode('utf-8').encode('cp437')
            zipFile.write(os.path.join(dir, name), targetName)
        if not dirnames and not filenames:
            # This is an empty leaf folder. We must create an entry in the
            # zip for him.
            folderName = dir[len(folder):]
            zInfo = zipfile.ZipInfo("%s/" % folderName, time.localtime()[:6])
            zInfo.external_attr = 48
            zipFile.writestr(zInfo, '')
    zipFile.close()
# ------------------------------------------------------------------------------
