#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from pathlib import Path
from DateTime import DateTime
import io, os, os.path, time, shutil, base64

from appy.px import Px
from appy import utils, n
from appy.xml.escape import Escape
from appy.model.fields import Field
from appy.model.utils import Object
from appy.server.static import Static
from appy.utils import path as putils
from appy.utils import string as sutils
from appy.pod.converter import Converter
from appy.ui.layout import Layouts, LayoutF
from appy.xml.unmarshaller import UnmarshalledFile

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
BAD_FTUPLE = 'This is not the way to set a file. You can specify a 2-tuple ' \
             '(fileName, fileContent) or a 3-tuple (fileName, fileContent, ' \
             'mimeType).'
CONV_ERR   = 'Pod::Converter error. %s'
CONV_PDF_E = 'Pod::Converter error while converting the file to PDF.'
CONV_PDF_T = 'converted as PDF'
PATH_KO    = 'Missing absolute disk path for %s.'
RESIZED    = '%s resized to %spx.'
DOWNLOADED = "%s • %s :: Downloaded in %s''."

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class FileInfo:
    '''A FileInfo instance holds metadata about a file on the filesystem'''

    # For every File field, we will store a FileInfo instance in the dabatase;
    # the real file will be stored in the Appy/ZODB database-managed filesystem.

    # This is the primary usage of FileInfo instances. FileInfo instances can
    # also be used every time we need to manipulate a file. For example, when
    # getting the content of a Pod field, a temporary file may be generated and
    # you will get a FileInfo that represents it.

    BYTES = 50000
    NOT_FOUND = 'File "%s" was not found.'

    # Max number of chars shown for a file's upload name
    uploadNameMax = 30

    # Fields to copy when cloning a FileInfo object
    clonable = 'uploadName', 'size', 'mimeType', 'modified'

    def __init__(self, fsPath, inDb=True, uploadName=n):
        '''FileInfo constructor. p_fsPath is the path of the file on disk.'''
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # If p_inDb | This FileInfo
        # is ...    | instance ...
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   True    | ... will be stored in the database and will hold metadata
        #           | about a File field whose content will lie in the database-
        #           | controlled filesystem. In this case, p_fsPath is the path
        #           | of the file *relative* to the root DB folder. We avoid
        #           | storing absolute paths in order to ease the transfer of
        #           | databases from one place to the other. Moreover, p_fsPath
        #           | does not include the filename, that will be computed
        #           | later, from the field name and, when needed, a hash of the
        #           | file content ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  False    |  ... is a simple temporary object representing any file on
        #           | the filesystem (not necessarily in the db-controlled
        #           | filesystem). For instance, it could represent a temp file
        #           | generated from a Pod field in the OS temp folder. In this
        #           | case, p_fsPath is the absolute path to the file, including
        #           | the filename. If you manipulate such a FileInfo instance,
        #           | please avoid using methods that are used by Appy to
        #           | manipulate db-controlled files (like methods removeFile,
        #           | writeFile or copyFile).
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.fsPath = fsPath
        # The name of the file in fsPath. For an in-DB file, it may have 2
        # formats: <fieldName>.<ext> (ie, 'file.pdf') or, if a file hash
        # has been computed, <fieldName>.<hexdigest>.<ext>.
        self.fsName = None
        # The name of the uploaded file
        self.uploadName = uploadName
        # Its size, in bytes
        self.size = 0
        # Its MIME type
        self.mimeType = None
        # The last modification date for this file, as a DateTime object
        self.modified = None
        # Complete metadata if p_inDb is False. p_inDb is not stored as is:
        # checking if self.fsName is the empty string is equivalent.
        if not inDb:
            self.fsName = '' # is already included in self.fsPath
            self.setAttributes(self.fsPath)
        # If p_self.fsName contains the hex digest of a hash computed from the
        # binary file content, the algo used to produce this digest is defined
        # here, as a string (ie: 'md5', 'sha1', 'sha256'...).
        self.algo = None

    def setAttributes(self, path):
        '''Compute file attributes (size, MIME type and last modification date)
           for a file whose absolute p_path is passed and store these attributes
           on p_self.'''
        try:
            info = os.stat(path)
            self.size = info.st_size
            self.mimeType = putils.guessMimeType(path)
            self.modified = DateTime(info.st_mtime)
        except FileNotFoundError as err:
            # The file on disk does not exist
            pass

    def inDb(self):
        '''Does this FileInfo represent a file from the DB-controlled
           filesystem ?'''
        return bool(self.fsName)

    def getTempFilePath(self, o, folder=n):
        '''Return the path to the copy, made in the OS temp folder, of the file
           corresponding to p_self (see m_getFilePath).'''
        # Return None if p_self is a not-in-db file
        name = self.fsName
        if not name: return
        folder = folder or o.getFolder()
        return Path(putils.getOsTempFolder()) / folder.name / name

    def getFilePath(self, o, checkTemp=True):
        '''Returns the Path object corresponding to the file on disk that
           corresponds to this FileInfo object.'''
        # For a not-in-db file, its full path is already in p_self.fsPath
        name = self.fsName
        if not name: return self.fsPath
        # Build the full path to this db-controlled file
        folder = o.getFolder()
        r = folder / name
        if checkTemp and not r.is_file():
            # It may already have been deleted by a failed transaction. Try to
            # get a copy we may have made in the OS temp folder.
            r = self.getTempFilePath(o, folder)
        return r

    def getUploadName(self, shorten=True):
        '''Returns the upload name, nicely formatted'''
        # The upload name may be missing
        r = self.uploadName
        if not r: return '?'
        # Simply return the upload name if not too long
        keep = FileInfo.uploadNameMax
        if not shorten or len(r) <= keep: return r
        # Return an "acronym" tag with the first chars of the name
        return f'<abbr title="{r}" style="cursor:pointer">{r[:keep]}...</abbr>'

    def exists(self, o):
        '''Does the file really exist on the filesystem ?'''
        # If the file exists but has no content, we consider it does not exist
        if self.size == 0: return
        path = self.getFilePath(o)
        return path.is_file() and path.stat().st_size > 0

    def removeFile(self, folder, removeEmptyFolders=False):
        '''Removes the file from the filesystem'''
        path = folder / self.fsName
        if path.is_file():
            # If the current ZODB transaction is re-triggered, the file may
            # already have been deleted.
            path.unlink()
        # Don't leave empty folders on disk. So delete folder and parent folders
        # if this removal leaves them empty (unless p_removeEmptyFolders is
        # False).
        if removeEmptyFolders:
            putils.FolderDeleter.deleteEmpty(str(folder))

    def normalizeFileName(self, name):
        '''Normalizes file p_name.'''
        return name[max(name.rfind('/'), name.rfind('\\'), name.rfind(':'))+1:]

    def getShownSize(self):
        '''Gets p_self's nicely formatted size'''
        return putils.getShownSize(self.size, unbreakable=True)

    def getNameAndSize(self, shorten=True):
        '''Gets the file name and size, nicely formatted'''
        name = self.getUploadName(shorten=shorten)
        return f'{name} - {self.getShownSize()}'

    def replicateFile(self, src, dest):
        '''p_src and p_dest are open file handlers. This method copies content
           of p_src to p_dest and returns the file size. Note that p_src can
           also be binary data as bytes.'''
        size = 0
        src = io.BytesIO(src) if isinstance(src, bytes) else src
        while True:
            chunk = src.read(self.BYTES)
            if not chunk: break
            size += len(chunk)
            dest.write(chunk)
        return size

    def getBase64(self, o=n, asString=False):
        '''Returns the file content, as base64-encoded bytes, or string if
           p_asString is True.'''
        path = self.getFilePath(o) if o else self.fsPath
        f = open(path, 'rb')
        r = base64.b64encode(f.read())
        f.close()
        return r.decode() if asString else r

    def getExtension(self):
        '''Get the file extension from the MIME type or from the upload name'''
        if self.mimeType in utils.mimeTypesExts:
            return utils.mimeTypesExts[self.mimeType]
        elif self.uploadName:
            parts = os.path.splitext(self.uploadName)
            if len(parts) > 1:
                return parts[-1][1:]

    def writeResponse(self, handler, path=n, disposition='attachment',
                      cache=False):
        '''Returns the content the file in the HTTP response'''
        if not self.fsName:
            # Not in-database file: we have its full path
            path = self.fsPath
        elif not path:
            # An in-database file for which we do not have the full path
            raise Exception(PATH_KO % self.fsName)
        # Prepare some log about the file download, when appropriate
        size = self.size
        log = size and size > handler.config.server.static.logDownloadAbove
        # Count the time spent for serving the file and log it
        if log: start = time.time()
        # Serve the file via the Static class
        Static.write(handler, path, None, fileInfo=self,
                     disposition=disposition, enableCache=cache)
        if log:
            # How long did it take to serve the file (in seconds) ?
            duration = utils.formatNumber(time.time() - start)
            text = DOWNLOADED % (path, self.getNameAndSize(False), duration)
            handler.log('app', 'info', text)

    def writeFileTo(self, path, value, isO, config):
        '''Called by p_writeFile, this method writes file content as passed in
           p_value, to the file having this p_path on disk.'''
        # Write the file on disk (and compute/get its size in bytes)
        f = open(path, 'wb')
        if isO:
            content = value.value
            self.size = len(content)
            f.write(content)
        elif isinstance(value, FileInfo):
            fsPath = value.fsPath
            if not fsPath.startswith('/'):
                # The p_value is a "in-db" FileInfo instance. If p_config is
                # there, we can reconstitute its absolute path.
                fsPath = config.database.binariesFolder / fsPath / value.fsName
                fsPath = str(fsPath)
            try:
                src = open(fsPath, 'rb')
                self.size = self.replicateFile(src, f)
                src.close()
            except FileNotFoundError:
                pass # The file does not exist
        else:
            # Write value[1] on disk
            content = value[1]
            if isinstance(content, str):
                content = content.encode('utf-8')
            if isinstance(content, bytes):
                self.size = len(content)
                f.write(content)
            else:
                # An open file handler
                self.size = self.replicateFile(content, f)
        f.close()

    def writeFile(self, name, value, folder, config=n, hash=n):
        '''Writes a file to the filesystem, from p_value that can be:
           - an Object instance (coming from a HTTP post);
           - another ("not-in-DB") FileInfo instance;
           - a tuple (fileName, content, mimeType): see method File.store.'''
        # Determine the file's MIME type
        isO = isinstance(value, Object) or isinstance(value, UnmarshalledFile)
        if isO:
            mimeType = value.type
            niceName = value.name
        elif isinstance(value, FileInfo):
            mimeType = value.mimeType
            niceName = value.uploadName
        else:
            mimeType = value[2]
            niceName = value[0]
        self.mimeType = mimeType or putils.defaultMimeType
        # The name of the file to be written on disk is based on the field name,
        # serving as an identifier within the database p_folder.
        ext = utils.mimeTypesExts.get(self.mimeType) or 'bin'
        if hash:
            # The name of the final file is not known yet: create a temp file
            # first.
            path = putils.getTempFileName(extension=ext)
        else:
            self.fsName = f'{name}.{ext}'
            path = str(folder / self.fsName)
        self.uploadName = self.normalizeFileName(niceName or 'file')
        # Write the file on disk (and compute/get its size in bytes)
        self.writeFileTo(path, value, isO, config)
        # If the file was a temp file, compute now its final name (that must
        # include a digest) and move it to its final place.
        if hash:
            digest = putils.getHash(path, algo=hash)
            self.algo = hash
            self.fsName = f'{name}.{digest}.{ext}'
            final = folder / self.fsName
            if final.is_file():
                final.unlink()
            shutil.move(path, str(final))
        self.modified = DateTime()

    def copyFile(self, fieldName, filePath, dbFolder, hash=None):
        '''Copies the "external" file stored at p_filePath in the db-controlled
           file system, for storing a value for p_fieldName.'''
        # Set names for the file
        if isinstance(filePath, UnmarshalledFile):
            name = self.normalizeFileName(filePath.name)
            location = filePath.location
            self.mimeType = filePath.type or putils.guessMimeType(location)
            filePath = location
        else:
            filePath = str(filePath) if isinstance(filePath, Path) else filePath
            name = self.normalizeFileName(filePath)
            self.mimeType = putils.guessMimeType(filePath)
        self.uploadName = name
        if hash:
            # Incorporate a file hash into the destination file name
            self.algo = hash
            digest = f'.{putils.getHash(filePath, algo=hash)}'
        else:
            digest = ''
        self.fsName = f'{fieldName}{digest}{os.path.splitext(name)[1]}'
        # Copy the file
        fsName = dbFolder / self.fsName
        shutil.copyfile(filePath, fsName)
        self.modified = DateTime()
        self.size = os.stat(fsName).st_size

    def dump(self, o, filePath=n, format=n):
        '''Exports this file to disk (outside the db-controlled filesystem)'''
        # The tied p_o(bject) is required. If p_filePath is specified, it is the
        # path name where the file will be dumped; folders mentioned in it must
        # exist. If not, the file will be dumped in the OS temp folder. The
        # method returns the absolute path name of the dumped file. If an error
        # occurs, the method returns None. If p_format is specified, LibreOffice
        # will be called for converting the dumped file to the desired format.
        if not filePath:
            tempFolder = putils.getOsTempFolder()
            filePath = f'{tempFolder}/file{time.time():.6f}.{self.fsName}'
        # Copies the file to disk
        shutil.copyfile(self.getFilePath(o), filePath)
        if format:
            # Convert the dumped file using LibreOffice
            try:
                Converter(filePath, format).run()
            except Converter.Error as err:
                o.log(CONV_ERR % str(err), type='error')
                return
            # Even if we have an "error" message, it could be a simple warning.
            # So we will continue here and, as a subsequent check for knowing if
            # an error occurred or not, we will test the existence of the
            # converted file (see below).
            os.remove(filePath)
            # Get the name of the converted file
            baseName, ext = os.path.splitext(filePath)
            if ext == f'.{format}':
                filePath = f'{baseName}.res.{format}'
            else:
                filePath = f'{baseName}.{format}'
            if not os.path.exists(filePath):
                o.log(CONV_ERR % err, type='error')
                return
        return filePath

    def resize(self, folder, width, o):
        '''Resize this image if it is a resizable image'''
        if self.mimeType not in File.resizableImages: return
        # Get the absolute path to the file on disk
        path = folder / self.fsName
        spath = str(path)
        # Get the width, in pixels, that will be used to resize it
        width = sutils.Normalize.digit(str(width))
        try:
            utils.ImageMagick.convert(spath, f'-resize {width}x{width}>')
            o.log(RESIZED % (spath, width))
        except Exception as err:
            o.log(err, type='warning')
        # (re)compute p_self's attributes, after resizing
        self.setAttributes(spath)

    def cloneOut(self, o):
        '''Clones p_self, being inDb, to a standalone, outside-DB File info
           object. This method does not perform any file copy.'''
        filePath = self.getFilePath(o)
        r = FileInfo(filePath, inDb=False)
        for name in self.clonable:
            setattr(r, name, getattr(self, name))
        return r

    def move(self, src, dest):
        '''Moves p_self, being in-db and tied to this p_src object, to the disk
           folder of this p_dest object.'''
        currentPath = self.getFilePath(src, checkTemp=False)
        # Update the path to the new file on p_self
        destFolder, relPart = dest.getFolder(create=True, withRelative=True)
        self.fsPath = relPart
        newPath = self.getFilePath(dest, checkTemp=False)
        # Move the file on disk
        return currentPath.rename(newPath)

    def __repr__(self):
        '''p_self's short string representation'''
        return f'‹File @{self.fsPath}/{self.fsName} {self.getShownSize()}›'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class File(Field):
    '''Field allowing to upload a binary file'''

    # Some elements will be traversable
    traverse = Field.traverse.copy()

    # MIME types for images
    imageMimeTypes = 'image/png', 'image/jpeg', 'image/gif'

    # MIME types for resizable images
    resizableImages = imageMimeTypes

    # Classes that may contain information about a binary file
    objectTypes = Object, FileInfo, UnmarshalledFile

    # Types that may represent paths to a binary file
    pathTypes = str, Path

    # A file field may store a binary file in the object folder, within the
    # database-controlled filesystem.
    disk = True

    # Make class FileInfo available here
    Info = FileInfo

    # Extensions for files LibreOffice may convert to PDF in the objective of
    # showing a file preview in the browser.
    previewExts = 'odt', 'ods', 'doc', 'docx', 'xls', 'xlsx'

    class Layouts(Layouts):
        '''File-specific layouts'''
        b = Layouts(edit='lrv-f', view='l-f')
        bg = Layouts(edit='frvl', view='fl')

        @classmethod
        def getDefault(class_, field):
            '''Default layouts for this File p_field'''
            return class_.bg if field.inGrid() else class_.b

    view = cell = buttons = Px('''
      <div class="flexc">::field.getLinkOrPreview(o, layout, name)</div>''')

    edit = Px('''
     <x var="fname=f'{name}_file'; rname=f'{name}_action'">
      <x if="value">
       <x>:field.view</x><br/>
       <!-- Keep the file unchanged -->
       <input type="radio" value="keep" checked=":bool(value)" name=":rname"
              id=":f'{name}_keep'"
              onclick=":f'document.getElementById({q(fname)}).disabled=true'"/>
       <label lfor=":f'{name}_keep'">:_('keep_file')</label><br/>
       <!-- Delete the file -->
       <x if="not field.required">
        <input type="radio" value="delete" name=":rname" id=":f'{name}_delete'"
               onclick=":f'document.getElementById({q(fname)}).disabled=true'"/>
        <label lfor=":f'{name}_delete'">:_('delete_file')</label><br/>
       </x>
       <!-- Replace with a new file -->
       <input type="radio" value="replace" id=":f'{name}_upload'"
              checked=":None if value else 'checked'" name=":rname"
              onclick=":f'document.getElementById({q(fname)}).disabled=false'"/>
       <label lfor=":f'{name}_upload'">:_('replace_file')</label><br/>
      </x>
      <!-- The upload field -->
      <input type="file" name=":fname" id=":fname" style=":field.getStyle()"
             onChange=":field.getJsOnChange()"/>
      <script var="isDisabled=not value \
             and 'false' or 'true'">:'document.getElementById(%s).disabled=%s'%\
                                     (q(fname), isDisabled)</script></x>''')

    search = ''

    @classmethod
    def validExt(class_, o, exts, value):
        '''Has the file uploaded in p_value one of the correct extensions as
           defined in p_exts ?'''
        if not value: return True
        ext = value.name.rsplit('.', 1)[-1]
        if not ext or ext not in exts:
            r = o.translate('ext_ko', mapping={'exts': ', '.join(exts)})
        else:
            r = True
        return r

    def __init__(self, validator=n, multiplicity=(0,1), default=n,
      defaultOnEdit=n, show=True, renderable=n, page='main', group=n,
      layouts=n, move=0, readPermission='read', writePermission='write',
      width=n, height=n, inputWidth=n, maxChars=n, colspan=1, master=n,
      masterValue=n, masterSnub=n, focus=False, historized=False, mapping=n,
      generateLabel=n, label=n, isImage=False, downloadAction=n, sdefault='',
      scolspan=1, swidth=n, sheight=n, view=n, cell=n, buttons=n, edit=n,
      custom=n, xml=n, xmlLocation=n, translations=n, render=n,
      icon='paperclip', disposition='attachment', nameStorer=n, cache=False,
      resize=False, thumbnail=n, preview=n, previewMaxSize=1048576*10, # 10Mb
      previewConvertMaxSize=1048576, previewFormats=previewExts, viewWidth=n,
      viewHeight=n, hash='md5', noValueLabel='no_value'):
        # This boolean is True if the file is an image
        self.isImage = isImage
        # "downloadAction" can be a method called every time the file is
        # downloaded. The method gets, as single arg, the FileInfo instance
        # representing the downloaded file.
        self.downloadAction = downloadAction
        # If "render" is "icon", the file will be rendered as an icon
        # (self.icon) on "buttons" and "result" layouts.
        self.render = render
        # Icon to use when this file is rendered as an icon
        self.icon, self.iconBase, self.iconRam = utils.iconParts(icon)
        # In "nameStorer", you can specify the name of another field that will
        # store the file name. This field must be a String belonging to the same
        # class as p_self. As soon as, in the UI, a file is selected in p_self's
        # widget, its name will be copied into the nameStorer field, without the
        # extension, only if this latter is not empty.
        self.nameStorer = nameStorer
        # When downloading the file, the browser may try to open it within the
        # browser ("inline" disposition) or save it to the disk ("attachment"
        # disposition). This latter is the default. You may also specify a
        # method returning one of these 2 valid values.
        self.disposition = disposition
        # By default, caching is disabled for this field: the browser will not
        # be able to cache the file stored in it. This is the default, for
        # security reasons. If you decide the browser can cache the file stored
        # here, set the following attribute to True. Attribute p_cache can also
        # store a method that must return a boolean value.
        self.cache = cache
        # Attribute "width" is used to specify the width of the image or
        # document. The width of the input field allowing to upload the file can
        # be defined in attribute "inputWidth".
        self.inputWidth = inputWidth
        # If attribute "resize" is False (the default), the image will be
        # previewed in the UI with dimensions as defined in attributes "width"
        # and "height", but without being effectively resized. If "resize" is
        # True, when uploading the file, it will be resized to self.width,
        # keeping the width / height ratio.
        self.resize = resize
        # If you place here the name of another File field, it will be used to
        # store a thumbnail of the image stored in the current field. The
        # thumbnail's dimension is defined, as usual, via attribute "width" of
        # the File field storing it. Everytime a document is uploaded in p_self,
        # if a thumbnail is defined in its "thumbnail" attribute, the thumbnail
        # field will be updated and will store the same image as the one stored
        # in p_self, resized accordingly (provided you have defined it as
        # "resizable").
        self.thumbnail = thumbnail
        # The following attribute allows to define a width for the file or image
        # preview. For an image, it will be used on /view and /cell. For a non-
        # image file, it will be used on /view. For an image, it can represent a
        # width being smaller than the actual image width. For a non-image file,
        # this width is the PDF viewer's width. p_viewWidth must store a string
        # (ie, '700px', '100%', '100vw') or a method that returns such a string.
        self.viewWidth = viewWidth
        # Similarly, the following attribute allows to define a height for a
        # file preview. It is ignored for an image, for which the aspect ratio
        # is respected: its height is automatically computed based on its width.
        # For a non-file image, it must be a string or a method returning it.
        # Using the viewport height unit (vh) is in general the best solution,
        # ie, "80vh".
        self.viewHeight = viewHeight
        # The name of the file, in the object folder, will contain a digest
        # produced with the algo as defined in p_hash. This allows to avoid name
        # clashes when several transactions using, temporarily, the same object
        # IID, are executed at the same time, potentially leading to writing a
        # file at the same place, with the same name, on disk. Moreover, it
        # allows to check if the file on disk corresponds to the file as
        # uploaded via the app, because the file name (that contains the digest)
        # is stored in the database, within the FileInfo object.
        self.hash = hash
        # p_preview determines if the document, when possible, is visible on
        # /view. This is achieved via the html "object" tag. This is possible
        # for:
        # - images that can be rendered within a browser ;
        # - PDF files ;
        # - any file format LibreOffice may convert to PDF, if LibreOffice runs
        #   in server mode.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # If p_preview is ...
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  None  | (the default) a preview will be rendered only for images
        #        | whose size does not exceed p_previewMaxSize (see below) ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  False | there will be no preview at all, whatever file/image type ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  True  | a preview will be rendered, provided (a) it is possible to
        #        | render a preview for this type of file and (b) the file does
        #        | not exceed the max size for which a preview may be rendered
        #        | (see below).
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # p_preview may also hold a method that returns one of the hereabove
        # values.
        self.preview = preview
        # For performance reasons, no preview is generated for files whose size
        # exceeds this limit, expressed in bytes.
        self.previewMaxSize = previewMaxSize
        # While the previous size limit holds for files that do not need any
        # conversion, the next one holds for those for which LibreOffice must be
        # called to convert the file to PDF.
        self.previewConvertMaxSize = previewConvertMaxSize
        # Specify, in the following attribute, a list or tuple of file
        # extensions for which a preview will be generated (provided the file
        # size allows it) by converting the file to PDF. The default list is
        # already built in File.previewExts. Use an alternate list if you want
        # to disable some formats, or None to disable all formats, leaving PDF
        # as the sole previewable file type.
        self.previewFormats = previewFormats
        # On /view, if there is no file in the field, a dash is rendered, being
        # the translation, in all languages, of the default label that exists
        # for that purpose ("no_value"). If you prefer a customized message, set
        # an alternate i18n label here.
        self.noValueLabel = noValueLabel
        # Call the base constructor
        super().__init__(validator, multiplicity, default, defaultOnEdit, show,
          renderable, page, group, layouts, move, False, True, n, n, False, n,
          n, readPermission, writePermission, width, height, n, colspan, master,
          masterValue, masterSnub, focus, historized, mapping, generateLabel,
          label, sdefault, scolspan, swidth, sheight, True, False, view, cell,
          buttons, edit, custom, xml, translations)
        # On the XML layout, when binary content is not dumped into the XML
        # content, but a location to the file on disk is dumped instead (see
        # config.model.marshallBinaries), this location defaults to the absolute
        # path to the file on the site's DB-controlled disk. If you want to
        # specify an alternate location, specify, in p_xmlLocation, a method.
        # This method will accept no arg and return the alternate location, as
        # a string.
        self.xmlLocation = xmlLocation

    def getRequestValue(self, o, requestName=n):
        name = requestName or self.name
        return o.req[f'{name}_file']

    def getRequestSuffix(self, o): return '_file'

    def getCopyValue(self, o):
        '''Create a copy of the FileInfo instance stored for p_o for this field.
           This copy will contain the absolute path to the file on the
           filesystem. This way, the file may be read independently from p_o
           (and copied somewhere else).'''
        info = self.getValue(o)
        if not info: return
        # Create a "not-in-DB", temporary FileInfo
        return FileInfo(str(info.getFilePath(o)), inDb=False,
                        uploadName=info.uploadName)

    def isEmptyValue(self, o, value):
        '''Must p_value be considered as empty ?'''
        if value: return
        # If "keep", the value must not be considered as empty
        return o.req[f'{self.name}_action'] != 'keep'

    def getJsOnChange(self):
        '''Gets the JS code for updating the name storer when defined'''
        storer = self.nameStorer
        if not storer: return ''
        name = storer.name if isinstance(storer, Field) else storer
        return f'updateFileNameStorer(this,"{name}")'

    def getStyle(self):
        '''Get the content of the "style" attribute of the "input" tag on the
           "edit" layout for this field.'''
        return 'width: %s' % self.inputWidth if self.inputWidth else ''

    def isRenderableOn(self, layout):
        '''A file with 'icon' rendering is potentially renderable everywhere'''
        if self.render == 'icon':
            return layout not in Layouts.topLayouts
        return super().isRenderableOn(layout)

    def notPreviewOversized(self, o, value, maxSize):
        '''Is file @ p_value not oversized (=equal or below p_maxSize) for a
           preview ?'''
        if value.size > maxSize:
            r = False
            maP = {'size': value.getShownSize()}
            text = o.translate('file_unpreviewable_size', mapping=maP)
        else:
            r = True
            text = None
        return r, text

    def isPreviewable(self, o, value):
        '''Is the file at p_value previewable ?'''
        # If yes, it returns a tuple (True, None). Else, it returns a tuple
        # (False, s_reason), s_reason being a translated text explaining why no
        # preview could be rendered.
        #
        # 1. Is file @ p_value previewble according to its file format ?
        r = False
        text = None
        mimeType = value.mimeType
        isPdf = mimeType == utils.mimeTypes['pdf']
        if isPdf:
            r = True
        else:
            # Is this file format among self.previewFormats ?
            formats = self.previewFormats
            if formats:
                # Get the file extension corresponding to v_mimeType
                ext = utils.mimeTypesExts.get(mimeType)
                r = ext and ext in formats
            else:
                r = False
        if not r:
            return r, o.translate('file_unpreviewable_format')
        # 2. Is the file not oversized ?
        maxSize = self.previewMaxSize if isPdf else self.previewConvertMaxSize
        return self.notPreviewOversized(o, value, maxSize)

    def mustPreview(self, o, value, layout):
        '''Must the document at p_value be previewed ?'''
        # If yes, it returns a tuple (True, None). Else, it returns a tuple
        # (False, s_reason), s_reason being a translated text explaining why no
        # preview could be rendered.
        #
        # Previewing docs is only possible on /view
        if layout != 'view': return n, n
        r = False
        text = None
        preview = self.getAttribute(o, 'preview')
        if preview is None:
            # By default, preview (not-oversized) images only
            if self.isImage:
                r, text = self.notPreviewOversized(o, value,self.previewMaxSize)
        elif preview:
            # Previewing could be enabled: is the file previewable ?
            r, text = self.isPreviewable(o, value)
        return r, text

    def getPreview(self, o, value, url, layout):
        '''Return a preview for p_value, as an "object" tag'''
        # Determine tag dimensions
        dimensions = []
        width = self.getAttribute(o, 'viewWidth')
        if width: dimensions.append(f'width:{width}')
        height = self.getAttribute(o, 'viewHeight')
        if height: dimensions.append(f'height:{height}')
        if dimensions:
            dimensions = ';'.join(dimensions)
            style = f' style="{dimensions}"'
        else:
            style = ''
        mimePdf = utils.mimeTypes['pdf']
        if value.mimeType != mimePdf:
            # The preview is a PDF file converted from an original file. Add a
            # link to download the original file.
            pre = self.getDownloadLink(o, value, url, layout, None,
                                       forceIcon=True)
        else:
            pre = ''
        # The link for downloading the file, if the preview can't be downloaded
        text = o.translate('file_preview_ko')
        link = self.getDownloadLink(o, value, url, layout, text, forceIcon=True)
        # Build and return the complete object tag
        return f'{pre}<object type="{mimePdf}"{style} ' \
               f'data="{url}?disposition=inline&pdf=1">{link}</object>'

    def getDownloadLink(self, o, value, url, layout, text, forceIcon=False):
        '''Return a link for downloading p_self, as an icon when relevant'''
        # Render the link as an icon or as text
        if forceIcon or self.render == 'icon':
            title = value.getNameAndSize(shorten=False)
            content = f'<span class="iconU8" title="{title}">↧</span>'
            # On /view, we have place, so display a v_title besides the icon
            suffix = Px.truncateText(title, 80) if layout == 'view' else ''
        else:
            # Display textual information only. If p_text is passed, it is a
            # translated text explaining why no file preview could be produced.
            content = value.getNameAndSize()
            suffix = ''
        # Style the suffix
        if suffix: suffix = f'<span class="refLink">{suffix}</span>'
        # Render the link
        r = f'<a href="{url}">{content}{suffix}</a>'
        # In front of the link, render this p_text if passed
        if text:
            r = f'<div class="noPreview"><div>{text}</div>{r}</div>'
        return r

    def getLinkOrPreview(self, o, layout='view', name=n):
        '''Gets the HTML code for downloading the file as stored in field
           named p_name on p_o, or for previewing it in the browser (depending
           on p_self.preview).'''
        name = name or self.name
        value = self.getValueIf(o, name, layout)
        # Display an empty value
        if not value:
            return '' if layout == 'cell' else o.translate(self.noValueLabel)
        # On /edit, simply repeat the file title
        if layout == 'edit': return value.getUploadName()
        # Build the URL for downloading or displaying the file
        url = f'{o.url}/{name}/download'
        preview, text = self.mustPreview(o, value, layout)
        # For previewable images, display them directly, in an "img" tag
        if preview and self.isImage:
            # Define a max width when relevant
            viewWidth = self.getAttribute(o, 'viewWidth')
            css = f' style="max-width:{viewWidth}"' if viewWidth else ''
            titleI = value.getNameAndSize(shorten=False)
            r = f'<img src="{url}" title="{titleI}"{css}/>'
        elif preview:
            # Return an object tag for previewing the file
            r = self.getPreview(o, value, url, layout)
        else:
            r = self.getDownloadLink(o, value, url, layout, text)
        return r

    def isCompleteValue(self, o, value):
        '''Always consider the value being complete, even if empty, in order to
           be able to check if, when the user has checked the box indicating
           that he will replace the file with another one, he has uploaded
           another file.'''
        return True

    def validateValue(self, o, value):
        '''Ensure p_value is valid'''
        # Multiplicity must be enforced because of our little cheat in
        # m_isCompleteValue.
        action = o.req[f'{self.name}_action']
        if self.required and not value and action != 'keep':
            return o.translate('field_required')
        if not value and action == 'replace':
            # The user has selected "replace the file with a new one" but has
            # not uploaded a new file.
            return o.translate('file_required')
        # Check that, if self.isImage, the uploaded file is really an image
        elif value and self.isImage:
            if value.type not in File.imageMimeTypes:
                return o.translate('image_required')

    def deleteFile(self, o, deleteFileInfo=True, removeEmptyFolders=True):
        '''Delete the file stored on this p_o(bject) corresponding to p_self'''
        info = o.values.get(self.name)
        if info:
            folder = o.getFolder()
            info.removeFile(folder, removeEmptyFolders=removeEmptyFolders)
            # Delete the FileInfo in the DB
            if deleteFileInfo:
                del o.values[self.name]

    def deleteFiles(self, o):
        '''Deletes the file possibly stored for this field on this p_o(bject)'''
        # In this context, we are only interested by removing the file on the
        # filesystem.
        self.deleteFile(o, deleteFileInfo=False, removeEmptyFolders=False)

    def store(self, o, value):
        '''Stores the p_value that represents some file'''
        # p_value can be:
        #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  a | an instance of class appy.model.utils.Object, built from data
        #    | originating from a HTTP POST request, having attributes:
        #    |  - "name",    containing the name of an uploaded file;
        #    |  - "type",    containing the MIME type of this file;
        #    |  - "value",   containing its binary content;
        #    | or an instance of appy.xml.unmarshalled.UnmarshalledFile, having
        #    | the same attributes, representing a file unmarshalled from XML
        #    | content.
        #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  b | a string, a pathlib.Path instance or an instance of
        #    | appy.xml.unmarshalled.UnmarshalledFile having attribute
        #    | "location". In theses cases, p_value represents the path of a
        #    | file on disk;
        #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  c | a 2-tuple (name, content) where:
        #    | - "name"     is the name of the file (ie "myFile.odt")
        #    | - "content"  is the binary or textual content of the file or an
        #    |              open file handler.
        #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  d | a 3-tuple (name, content, mimeType) where
        #    | - "name" and "content" have the same meaning than above;
        #    | - "mimeType" is the MIME type of the file.
        #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  e | a FileInfo instance, be it "in-DB" or not.
        #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        if value:
            # There is a new value to store. Get the folder on disk where to
            # store the new file.
            folder, relative = o.getFolder(create=True, withRelative=True)
            # Remove the previous file if it existed
            info = o.values.get(self.name)
            if info: info.removeFile(folder)
            # Store the new file. As a preamble, create a FileInfo object.
            info = FileInfo(relative)
            if isinstance(value, File.pathTypes) or \
               (isinstance(value, UnmarshalledFile) and value.location):
                # Case (b)
                info.copyFile(self.name, value, folder, self.hash)
            elif isinstance(value, File.objectTypes):
                # Cases (a) and (e)
                info.writeFile(self.name, value, folder, config=o.config,
                               hash=self.hash)
            else:
                # Cases (c) and (d): extract file name, content and MIME type
                name = type = None
                if len(value) == 2:
                    name, content = value
                elif len(value) == 3:
                    name, content, type = value
                if not name:
                    raise Exception(BAD_FTUPLE)
                type = type or putils.guessMimeType(name)
                info.writeFile(self.name, (name, content, type), folder,
                               hash=self.hash)
            # Store the FileInfo instance in the database
            o.values[self.name] = info
            # Resize the image when relevant
            if self.resize and self.width:
                width = self.getAttribute(o, 'width')
                info.resize(folder, width, o)
            # Update the thumbnail if defined
            fileName = str(folder / info.fsName)
            if self.thumbnail:
                o.getField(self.thumbnail).store(o, fileName)
        else:
            # Delete the file, excepted if we find, in the request, the desire
            # to keep it unchanged.
            if o.req[f'{self.name}_action'] == 'keep': return
            # Delete the file on disk if it existed
            self.deleteFile(o)

    def getDownloadInfo(self, o, info):
        '''Returns the FileInfo object that represents the file to download via
           m_download.'''
        # In most cases, the resulting FileInfo object is p_info, being the one
        # stored on this p_o(bject) for p_self. The result is not p_info when a
        # PDF file is requested and p_info doesn't represent a PDF file but a
        # file whose format can be converted to it. In that case, a temp PDF
        # file is generated and wrapped as an outside-db-controlled-file-system
        # FileInfo object, that is returned.
        #
        # The return value is a 2-tuple (FileInfo, error). If the file
        # conversion generated an error, the first tuple element is None and the
        # second one is an error message, as a string.
        #
        # Must p_info be converted to PDF ?
        asPdf = o.req.pdf == '1' and info.mimeType != utils.mimeTypes['pdf'] \
                and utils.mimeTypesExts.get(info.mimeType) in self.previewExts
        if asPdf:
            # A conversion to PDF is required: do it in the OS temp folder
            path = info.dump(o, format='pdf')
            if path is None:
                r = None, CONV_PDF_E
            else:
                uploadName = info.uploadName or ''
                uploadBase = uploadName.rsplit('.', 1)[0]
                infoR = FileInfo(path, inDb=False,
                                 uploadName=f'{uploadBase}.pdf')
                r = infoR, None
        else:
            r = info, None
        return r

    traverse['download'] = 'perm:read'
    def download(self, o):
        '''Triggered when a file download is requested from the ui'''
        # Security check: ensure v_o is viewable. Indeed, the traversal only
        # checks standard security, like permissions or roles, but not security
        # complements like the custom "mayView" method.
        o.guard.mayView(o, permission=None, raiseError=True)
        # Write the file in the HTTP response
        info = o.values.get(self.name)
        config = o.config.server.static
        handler = o.H()
        if info:
            # Return a 404 if the file does not exist
            path = info.getFilePath(o)
            if not path.is_file():
                Static.notFound(handler, config)
                return
            # Call the "download action" if specified
            if self.downloadAction:
                self.downloadAction(o, info)
                # In that case, a commit is required
                o.H().commit = True
            # Get the FileInfo object corresponding to the file to download
            infoD, error = self.getDownloadInfo(o, info)
            if error:
                # Return a 404
                Static.notFound(handler, config, detail=CONV_PDF_T)
            else:
                # Send the file to the client. The file disposition may be
                # forced by a request parameter.
                disposition = o.req.disposition or \
                              self.getAttribute(o, 'disposition')
                # Recompute the path to the file, if it has been converted
                if infoD != info: path = info.getFilePath(o)
                # Write the file content via the response object
                infoD.writeResponse(handler, str(path), disposition=disposition,
                                    cache=self.getAttribute(o, 'cache'))
        else:
            # Return a 404
            Static.notFound(handler, config)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
