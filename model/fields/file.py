# -*- coding: utf-8 -*-

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from pathlib import Path
from DateTime import DateTime
import io, os, os.path, time, shutil, base64

from appy.px import Px
from appy import utils
from appy.ui.layout import Layouts
from appy.model.fields import Field
from appy.model.utils import Object
from appy.server.static import Static
from appy.utils import path as putils
from appy.utils import string as sutils
from appy.pod.converter import Converter
from appy.xml.unmarshaller import UnmarshalledFile

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
BAD_FTUPLE = 'This is not the way to set a file. You can specify a 2-tuple ' \
             '(fileName, fileContent) or a 3-tuple (fileName, fileContent, ' \
             'mimeType).'
CONV_ERR   = 'Pod::Converter error. %s'
PATH_KO    = 'Missing absolute disk path for %s.'
RESIZED    = '%s resized to %spx.'

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

    def __init__(self, fsPath, inDb=True, uploadName=None):
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
        #           | later, from the field name.
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
        self.fsName = None # The name of the file in fsPath
        self.uploadName = uploadName # The name of the uploaded file
        self.size = 0 # Its size, in bytes
        self.mimeType = None # Its MIME type
        # The last modification date for this file, as a DateTime instance
        self.modified = None
        # Complete metadata if p_inDb is False. p_inDb is not stored as is:
        # checking if self.fsName is the empty string is equivalent.
        if not inDb:
            self.fsName = '' # Already included in self.fsPath
            self.setAttributes(self.fsPath)

    def setAttributes(self, path):
        '''Compute file attributes (size, MIME type and last modification date)
           for a file whose absolute p_path is passed and store these attributes
           on p_self.'''
        info = os.stat(path)
        self.size = info.st_size
        self.mimeType = putils.guessMimeType(path)
        self.modified = DateTime(info.st_mtime)

    def inDb(self):
        '''Does this FileInfo represent a file from the DB-controlled
           filesystem ?'''
        return bool(self.fsName)

    def getFilePath(self, o, checkTemp=True):
        '''Returns the Path instance corresponding to the file on disk that
           corresponds to this FileInfo instance.'''
        # For a not-in-db file, its full path is already in p_self.fsPath
        if not self.fsName: return self.fsPath
        # Build the full path to this db-controlled file
        folder = o.getFolder()
        path = folder / self.fsName
        if not path.is_file() and checkTemp:
            # It may already have been deleted by a failed transaction. Try to
            # get a copy we may have made in the OS temp folder.
            path = Path(putils.getOsTempFolder()) / folder.name / self.fsName
        return path

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

    def getShownSize(self): return putils.getShownSize(self.size)

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

    def getBase64(self, o=None):
        '''Returns the file content, as a base64-encoded string'''
        path = self.getFilePath(o) if o else self.fsPath
        f = open(path, 'rb')
        r = base64.b64encode(f.read())
        f.close()
        return r

    def getExtension(self):
        '''Get the file extension from the MIME type or from the upload name'''
        if self.mimeType in utils.mimeTypesExts:
            return utils.mimeTypesExts[self.mimeType]
        elif self.uploadName:
            parts = os.path.splitext(self.uploadName)
            if len(parts) > 1:
                return parts[-1][1:]

    def writeResponse(self, handler, path=None, disposition='attachment',
                      cache=False):
        '''Returns the content the file in the HTTP response'''
        if not self.fsName:
            # Not in-database file: we have its full path
            path = self.fsPath
        elif not path:
            # An in-database file for which we do not have the full path
            raise Exception(PATH_KO % self.fsName)
        # Produce the file via the Static class
        Static.write(handler, path, None, fileInfo=self,
                     disposition=disposition, enableCache=cache)

    def writeFile(self, name, value, folder, config=None):
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
        # Force the file to be written on disk with the field name, serving as
        # an identifier within the database p_folder.
        ext = utils.mimeTypesExts.get(self.mimeType) or 'bin'
        self.fsName = '%s.%s' % (name, ext)
        self.uploadName = self.normalizeFileName(niceName or 'file')
        # Write the file on disk (and compute/get its size in bytes)
        path = str(folder / self.fsName)
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
            src = open(fsPath, 'rb')
            self.size = self.replicateFile(src, f)
            src.close()
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
        self.modified = DateTime()

    def copyFile(self, fieldName, filePath, dbFolder):
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
        self.fsName = '%s%s' % (fieldName, os.path.splitext(name)[1])
        # Copy the file
        fsName = dbFolder / self.fsName
        shutil.copyfile(filePath, fsName)
        self.modified = DateTime()
        self.size = os.stat(fsName).st_size

    def dump(self, o, filePath=None, format=None):
        '''Exports this file to disk (outside the db-controlled filesystem).
           The tied p_o(bject) is required. If p_filePath is specified, it
           is the path name where the file will be dumped; folders mentioned in
           it must exist. If not, the file will be dumped in the OS temp folder.
           The absolute path name of the dumped file is returned. If an error
           occurs, the method returns None. If p_format is specified,
           LibreOffice will be called for converting the dumped file to the
           desired format.'''
        if not filePath:
            filePath = '%s/file%f.%s' % (putils.getOsTempFolder(), time.time(),
                                         self.fsName)
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
            if ext == ('.%s' % format):
                filePath = '%s.res.%s' % (baseName, format)
            else:
                filePath = '%s.%s' % (baseName, format)
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
            utils.ImageMagick.convert(spath, '-resize %sx%s>' % (width, width))
            o.log(RESIZED % (spath, width))
        except Exception as err:
            o.log(err, type='warning')
        # (re)compute p_self's attributes, after resizing
        self.setAttributes(spath)

    def __repr__(self):
        '''p_self's short string representation'''
        return '<File @%s/%s %s>' % \
               (self.fsPath, self.fsName, self.getShownSize())

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class File(Field):
    '''Field allowing to upload a binary file'''

    # Some elements will be traversable
    traverse = Field.traverse.copy()

    # MIME types for images
    imageMimeTypes = ('image/png', 'image/jpeg', 'image/gif')

    # MIME types for resizable images
    resizableImages = imageMimeTypes

    # Classes that may contain information about a binary file
    objectTypes = (Object, FileInfo, UnmarshalledFile)

    # Types that may represent paths to a binary file
    pathTypes = (str, Path)

    class Layouts(Layouts):
        '''File-specific layouts'''
        b = Layouts(edit='lrv-f', view='l-f')
        bg = Layouts(edit='frvl', view='fl')

        @classmethod
        def getDefault(class_, field):
            '''Default layouts for this File p_field'''
            return class_.bg if field.inGrid() else class_.b

    view = cell = buttons = Px('''
      <x>::field.getDownloadLink(name, o, layout)</x>''')

    edit = Px('''
     <x var="fName='%s_file' % name">
      <x if="value">
       <x>:field.view</x><br/>
       <!-- Keep the file unchanged -->
       <input type="radio" value="keep" checked=":bool(value)"
              name=":'%s_action' % name" id=":'%s_keep' % name"
              onclick=":'document.getElementById(%s).disabled=true'% q(fName)"/>
       <label lfor=":'%s_keep' % name">:_('keep_file')</label><br/>
       <!-- Delete the file -->
       <x if="not field.required">
        <input type="radio" value="delete"
               name=":'%s_action' % name" id=":'%s_delete' % name"
               onclick=":'document.getElementById(%s).disabled=true'%q(fName)"/>
        <label lfor=":'%s_delete' % name">:_('delete_file')</label><br/>
       </x>
       <!-- Replace with a new file -->
       <input type="radio" value="replace"
              checked=":not value and 'checked' or None"
              name=":'%s_action' % name" id=":'%s_upload' % name"
              onclick=":'document.getElementById(%s).disabled=false'%q(fName)"/>
       <label lfor=":'%s_upload' % name">:_('replace_file')</label><br/>
      </x>
      <!-- The upload field -->
      <input type="file" name=":fName" id=":fName" style=":field.getStyle()"
             onChange=":field.getJsOnChange()"/>
      <script var="isDisabled=not value \
             and 'false' or 'true'">:'document.getElementById(%s).disabled=%s'%\
                                     (q(fName), isDisabled)</script></x>''')

    search = ''

    def __init__(self, validator=None, multiplicity=(0,1), default=None,
      defaultOnEdit=None, show=True, renderable=None, page='main', group=None,
      layouts=None, move=0, readPermission='read', writePermission='write',
      width=None, height=None, inputWidth=None, maxChars=None, colspan=1,
      master=None, masterValue=None, focus=False, historized=False,
      mapping=None, generateLabel=None, label=None, isImage=False,
      downloadAction=None, sdefault='', scolspan=1, swidth=None, sheight=None,
      view=None, cell=None, buttons=None, edit=None, xml=None,
      translations=None, render=None, icon='paperclip',
      disposition='attachment', nameStorer=None, cache=False, resize=False,
      thumbnail=None, viewWidth=None):
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
        # When the uploaded file is an image, on "view" and "cell" layouts, you
        # may want to display it smaller than its actual size. In order to do
        # that, specify a width (as a string, ie '700px') in the following
        # attribute. The attribute may also hold a method returning the value.
        self.viewWidth = viewWidth
        # Call the base constructor
        Field.__init__(self, validator, multiplicity, default, defaultOnEdit,
          show, renderable, page, group, layouts, move, False, True, None, None,
          False, None, readPermission, writePermission, width, height, None,
          colspan, master, masterValue, focus, historized, mapping,
          generateLabel, label, sdefault, scolspan, swidth, sheight, True,
          False, view, cell, buttons, edit, xml, translations)

    def getRequestValue(self, o, requestName=None):
        name = requestName or self.name
        return o.req['%s_file' % name]

    def getRequestSuffix(self): return '_file'

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
        return o.req['%s_action' % self.name] != 'keep'

    def getJsOnChange(self):
        '''Gets the JS code for updating the name storer when defined'''
        storer = self.nameStorer
        if not storer: return ''
        name = storer.name if isinstance(storer, Field) else storer
        return 'updateFileNameStorer(this,"%s")' % name

    def getStyle(self):
        '''Get the content of the "style" attribute of the "input" tag on the
           "edit" layout for this field.'''
        return 'width: %s' % self.inputWidth if self.inputWidth else ''

    def isRenderableOn(self, layout):
        '''A file with 'icon' rendering is potentially renderable everywhere'''
        if self.render == 'icon':
            return layout not in Layouts.topLayouts
        return super().isRenderableOn(layout)

    def getDownloadLink(self, name, o, layout):
        '''Gets the HTML code for downloading the file as stored in field
           named p_name on p_o.'''
        value = self.getValueIf(o, name, layout)
        # Display an empty value
        if not value: return '' if layout == 'cell' else '-'
        # On "edit", simply repeat the file title
        if layout == 'edit': return value.uploadName
        # Get the "file title", derived from the upload name and size
        size = value.getShownSize()
        title = "%s - %s" % (value.uploadName, size)
        # Build the URL for downloading or displaying the file
        url = '%s/%s/download' % (o.url, name)
        # For images, display them directly
        if self.isImage:
            # Define a max width when relevant
            viewWidth = self.getAttribute(o, 'viewWidth')
            css = ' style="max-width: %s"' % viewWidth if viewWidth else ''
            return '<img src="%s" title="%s"%s/>' % (url, title, css)
        # For non-images, display a link for downloading it, as an icon when
        # relevant.
        if self.render == 'icon':
            iurl = o.buildUrl(self.icon, base=self.iconBase, ram=self.iconRam)
            content = '<img src="%s" title="%s"/>' % (iurl, title)
            # On "view", we have place, so display "title" besides the icon
            suffix = title if layout == 'view' else ''
        else:
            # Display textual information only
            content = title
            suffix = ''
        # Style the suffix
        if suffix: suffix = '<span class="refLink">%s</span>' % suffix
        return '<a href="%s">%s%s</a>' % (url, content, suffix)

    def isCompleteValue(self, o, value):
        '''Always consider the value being complete, even if empty, in order to
           be able to check if, when the user has checked the box indicating
           that he will replace the file with another one, he has uploaded
           another file.'''
        return True

    def validateValue(self, o, value):
        '''Ensure p_value is valid'''
        if not value and (o.req['%s_action' % self.name] == 'replace'):
            # The user has selected "replace the file with a new one" but has
            # not uploaded a new file.
            return o.translate('file_required')
        # Check that, if self.isImage, the uploaded file is really an image
        elif value and self.isImage:
            if value.type not in File.imageMimeTypes:
                return o.translate('image_required')

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
            # Store the new file. As a preamble, create a FileInfo instance.
            info = FileInfo(relative)
            if isinstance(value, File.pathTypes) or \
               (isinstance(value, UnmarshalledFile) and value.location):
                # Case (b)
                info.copyFile(self.name, value, folder)
            elif isinstance(value, File.objectTypes):
                # Cases (a) and (e)
                info.writeFile(self.name, value, folder, config=o.config)
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
                info.writeFile(self.name, (name, content, type), folder)
            # Store the FileInfo instance in the database
            o.values[self.name] = info
            # Resize the image when relevant
            if self.resize and self.width:
                width = self.getAttribute(o, 'width')
                info.resize(folder, width, o)
            # Update the thumbnail if defined
            fileName = str(folder / info.fsName)
            if self.thumbnail: o.getField(self.thumbnail).store(o, fileName)
        else:
            # Store value "None", excepted if we find, in the request, the
            # desire to keep the file unchanged.
            if o.req['%s_action' % self.name] != 'keep':
                # Delete the file on disk if it existed
                info = o.values.get(self.name)
                if info:
                    info.removeFile(o.getFolder(), removeEmptyFolders=True)
                    # Delete the FileInfo in the DB
                    del(o.values[self.name])

    traverse['download'] = 'perm:read'
    def download(self, o):
        '''Triggered when a file download is requested from the ui'''
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
            # Send the file to the browser
            info.writeResponse(handler, str(path),
                               disposition=self.getAttribute(o, 'disposition'),
                               cache=self.getAttribute(o, 'cache'))
        else:
            # Return a 404
            Static.notFound(handler, config)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
