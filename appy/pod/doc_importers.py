# ~license~
# ------------------------------------------------------------------------------
import os, os.path, re, stat, shutil, struct, urlparse, base64, imghdr

import appy.pod
from appy import commercial
from appy import Object as O
from appy.shared.dav import Resource
from appy.shared import mimeTypesExts
from appy.pod import PodError, getUuid
from appy.shared import utils as sutils
from appy.pod.metadata import MetadataReader
from appy.shared.css import CssStyles, px2cm
from appy.shared.utils import getTempFileName
from appy.pod.odf_parser import OdfEnvironment
from appy.shared.errors import CommercialError

# ------------------------------------------------------------------------------
FILE_NOT_FOUND = "'%s' does not exist or is not a file."
PDF_TO_IMG_ERROR = 'A PDF file could not be converted into images. Please ' \
                   'ensure that Ghostscript (gs) is installed on your ' \
                   'system and the "gs" program is in the path.'
TO_PDF_ERROR = 'ConvertImporter error while converting a doc to PDF: %s.'

# ------------------------------------------------------------------------------
class ImageMagick:
    '''Allows to perform command-line calls to ImageMagick'''

    # The wrapper around any error message
    error = 'Error while executing ImageMagick command: %s. %s'

    @classmethod
    def run(class_, command):
        '''Executes this ImageMagick p_command, passed a list'''
        out, err = sutils.executeCommand(command)
        if err: raise Exception(class_.error % (' '.join(command), err))
        return out

# ------------------------------------------------------------------------------
class DocImporter:
    '''Base class used for importing external content into a pod template (an
       image, another pod template, another odt document...'''

    def __init__(self, content, at, format, renderer):
        self.content = content
        self.renderer = renderer
        # If content is None, p_at tells us where to find it (file path, url...)
        self.at = at
        # Check and standardize p_at
        self.format = format
        if at:
            self.at = self.checkAt(at)
        self.res = u''
        self.ns = renderer.currentParser.env.namespaces
        # Unpack some useful namespaces
        self.textNs = self.ns[OdfEnvironment.NS_TEXT]
        self.linkNs = self.ns[OdfEnvironment.NS_XLINK]
        self.drawNs = self.ns[OdfEnvironment.NS_DRAW]
        self.svgNs = self.ns[OdfEnvironment.NS_SVG]
        self.tempFolder = renderer.tempFolder
        self.importFolder = self.getImportFolder()
        # Create the import folder if it does not exist
        if not os.path.exists(self.importFolder): os.mkdir(self.importFolder)
        self.importPath = self.getImportPath()
        # A link to the global fileNames dict (explained in renderer.py)
        self.fileNames = renderer.fileNames
        if self.at:
            # Move the file within the ODT, if it is an image and if this image
            # has not already been imported.
            self.importPath = self.moveFile()
        else:
            # We need to dump the file content (in self.content) in a temp file
            # first. self.content may be binary, a file handler or a
            # FileWrapper.
            if isinstance(self.content, sutils.FileWrapper):
                self.content.dump(self.importPath)
            else:
                if isinstance(self.content, file):
                    fileContent = self.content.read()
                else:
                    fileContent = self.content
                f = file(self.importPath, 'wb')
                f.write(fileContent)
                f.close()
        # Some importers add specific attrs, through method init

    def checkAt(self, at, raiseOnError=True):
        '''Check and apply some transform to p_at'''
        # Resolve relative path
        if at.startswith('./'): at = os.path.join(os.getcwd(), at[2:])
        # Checks that p_at corresponds to an existing file if given
        if raiseOnError and not os.path.isfile(at):
            raise PodError(FILE_NOT_FOUND % at)
        return at

    def getImportFolder(self):
        '''This method gives the path where to dump the content of the document
           or image. In the case of a document it is a temp folder; in the case
           of an image it is a folder within the ODT result.'''
        return '%s/docImports' % self.tempFolder # For most importers

    def getImportPath(self):
        '''Gets the path name of the file to dump on disk (within the ODT for
           images, in a temp folder for docs).'''
        format = self.format
        if not format or format == 'image':
            at = self.at
            if not at or at.startswith('http') or not os.path.exists(at):
                # It is not possible yet to determine the format (will be done
                # later).
                self.format = ''
            else:
                self.format = os.path.splitext(at)[1][1:]
        fileName = '%s.%s' % (getUuid(), self.format)
        return os.path.abspath('%s/%s' % (self.importFolder, fileName))

    def moveFile(self):
        '''In the case "self.at" was used, we may want to move the file at
           self.at within the ODT result in self.importPath (for images) or do
           nothing (for docs). In the latter case, the file to import stays
           at self.at, and is not copied into self.importPath. So the previously
           computed self.importPath is not used at all.'''
        return self.at

class OdtImporter(DocImporter):
    '''This class allows to import the content of another ODT document into a
       pod template.'''

    # POD manages page breaks by inserting a paragraph whose style inserts a
    # page break before or after it.
    pageBreakTemplate = '<text:p text:style-name="podPageBreak%s"></text:p>'
    pageBreakCustom = '<text:p text:style-name="%s"></text:p>'
    pageBreaks = O(before=pageBreakTemplate % 'Before',
                   after=pageBreakTemplate % 'After',
                   beforeDuplex=pageBreakTemplate % 'BeforeDuplex')

    def init(self, pageBreakBefore, pageBreakAfter):
        '''OdtImporter-specific constructor'''
        self.pageBreakBefore = pageBreakBefore
        self.pageBreakAfter = pageBreakAfter

    def addPageBreakAfter(self):
        '''After sub-document insertion, must we insert a page break ?'''
        typE = None
        breaK = self.pageBreakAfter
        if breaK == 'duplex':
            # Read metadata about the sub-ODT, containing its number of pages
            metadata = MetadataReader(self.importPath).run()
            odd = (metadata.pagecount % 2) == 1
            # Inserting a page break of type "before" will force an additional
            # page break, while inserting a page break of type "after" will only
            # insert a page break if additional content is found after the
            # paragraph onto which the page break style is applied.
            typE = odd and 'beforeDuplex' or 'after'
        elif breaK is True:
            typE = 'after'
        elif breaK:
            # A specific style must be generated, that mentions a custom page
            # style that inherits from style "podPageBreakBefore".
            generator = self.renderer.stylesManager.stylesGenerator
            style = generator.addPageBreakStyle('podPageBreakBefore', breaK)
            styleDef = self.pageBreakCustom % style.name
            self.res = '%s%s' % (self.res, styleDef)
        if typE:
            # One of the standard page breaks as defined in OdtImport.pageBreaks
            # must be used.
            self.res = '%s%s' % (self.res, getattr(self.pageBreaks, typE))

    def run(self):
        '''Import the content of a sub-ODT document'''
        # Insert a page break before importing the doc if needed
        if self.pageBreakBefore:
            self.res += self.pageBreaks.before
        # Import the external odt document
        name = getUuid(removeDots=True, prefix='PodSect')
        self.res += '<%s:section %s:name="%s">' \
                    '<%s:section-source %s:href="file://%s" ' \
                    '%s:filter-name="writer8"/></%s:section>' % (
                        self.textNs, self.textNs, name, self.textNs,
                        self.linkNs, self.importPath, self.textNs, self.textNs)
        # Possibly insert (a) page break(s) after importing the doc if needed
        self.addPageBreakAfter()
        # Note that if there is no more document content after the last page
        # break, it will not be visible.
        return self.res

class PodImporter(DocImporter):
    '''This class allows to import the result of applying another POD template,
       into the current POD result.'''

    def mustStream(self):
        '''Returns True if communication with LibreOffice must be performed via
           streams.'''
        # The default value is the one from the main renderer
        default = self.renderer.stream
        # Must we communicate with LO via streams ?
        mustStream = (default in (True, 'in')) or \
                     ((default == 'auto') and \
                      (self.renderer.loPool.server != 'localhost'))
        # If the global result must be streamed, for this sub-pod, stream must
        # be "in": this way, the output is written on disk, on the distant LO
        # machine. Then, when we will, via the OdtImporter that will be called
        # just after this PodImporter, specify the sub-pod to include, the
        # distant LO will be able to read it from is own disk.
        return mustStream and 'in' or default

    def init(self, context, pageBreakBefore, pageBreakAfter,
             managePageStyles, resolveFields, forceOoCall):
        '''PodImporter-specific constructor'''
        self.context = context
        self.pageBreakBefore = pageBreakBefore
        self.pageBreakAfter = pageBreakAfter
        self.managePageStyles = managePageStyles
        self.resolveFields = resolveFields
        # Must we communicate with LO via streams ?
        self.stream = self.mustStream()
        # Force LO call if:
        # (a) fields must be resolved ;
        # (b) if we are inserting sub-documents in "duplex" mode (or, also, with
        #     a custom page style). Indeed, in duplex mode, we will need to know
        #     the exact number of pages for every sub-document. We will call LO
        #     for that purpose: it will produce correct document statistics
        #     within meta.xml, which is not the case for an ODT document
        #     produced by POD without forcing OO call (stats are those from the
        #     document template and not from the pod result) ;
        # (c) LO is on a distant machine. In that case, forcing OO call allows
        #     to transmit the sub-pod to the distant machine, ready to be
        #     incorporated by the distant LO in the main pod.
        if isinstance(pageBreakAfter, basestring) or resolveFields or \
            self.stream == 'in':
            force = True
        else:
            # Inherit from the parent renderer's value or get a specific value
            renderer = self.renderer
            if forceOoCall == renderer.INHERIT:
                force = renderer.forceOoCall
            else:
                # Else, keep the value as passed to p_self's constructor
                force = forceOoCall
        self.forceOoCall = force

    def run(self):
        # This feature is only available in the open source version
        if commercial: raise CommercialError()
        r = self.renderer
        stream = self.stream
        # Define where to store the pod result in the temp folder. If we must
        # stream the result, the temp folder will be on a distant machine, so it
        # must be at the root of the OS temp folder.
        base = (stream == 'in') and sutils.getOsTempFolder() or \
                                    self.getImportFolder()
        resOdt = os.path.join(base, '%s.odt' % getUuid())
        # The POD template is in self.importPath
        template = self.importPath
        # Re-use an existing renderer if we have one that has already generated
        # a result based on this template.
        renderer = r.children.get(template)
        if not renderer:
            renderer = r.clone(template, self.context, resOdt, stream=stream,
              forceOoCall=self.forceOoCall,
              managePageStyles=self.managePageStyles,
              resolveFields=self.resolveFields, metadata=False,
              deleteTempFolder=False, loPool=r.loPool)
            renderer.stylesManager.stylesMapping = r.stylesManager.stylesMapping
            # Add this renderer to the list of child renderers on the parent
            r.children[template] = renderer
        else:
            # Recycle this renderer and set him a new result
            renderer.reinit(resOdt, self.context)
        renderer.run()
        # The POD result is in "resOdt". Import it into the main POD result
        # using an OdtImporter.
        odtImporter = OdtImporter(None, resOdt, 'odt', self.renderer)
        odtImporter.init(self.pageBreakBefore, self.pageBreakAfter)
        return odtImporter.run()

class PdfImporter(DocImporter):
    '''This class allows to import the content of a PDF file into a pod
       template. It calls gs to split the PDF into images and calls the
       ImageImporter for importing it into the result.'''
    # Ghostscript devices that can be used for converting PDFs into images
    gsDevices = {'jpeg': 'jpg', 'jpeggray': 'jpg',
                 'png16m': 'png', 'pnggray': 'png'}

    def run(self):
        # This feature is only available in the open source version
        if commercial: raise CommercialError()
        imagePrefix = os.path.splitext(os.path.basename(self.importPath))[0]
        # Split the PDF into images with Ghostscript. Create a sub-folder in the
        # OS temp folder to store those images.
        imagesFolder = sutils.getOsTempFolder(sub=True)
        device = 'png16m'
        ext = PdfImporter.gsDevices[device]
        dpi = '125'
        cmd = ['gs', '-dSAFER', '-dNOPAUSE', '-dBATCH', '-sDEVICE=%s' % device,
               '-r%s' % dpi, '-dTextAlphaBits=4', '-dGraphicsAlphaBits=4',
               '-sOutputFile=%s/%s%%d.%s' % (imagesFolder, imagePrefix, ext),
               self.importPath]
        sutils.executeCommand(cmd)
        # Check that at least one image was generated
        succeeded = False
        firstImage = '%s1.%s' % (imagePrefix, ext)
        for fileName in os.listdir(imagesFolder):
            if fileName == firstImage:
                succeeded = True
                break
        if not succeeded: raise PodError(PDF_TO_IMG_ERROR)
        # Insert images into the result
        noMoreImages = False
        i = 0
        while not noMoreImages:
            i += 1
            nextImage = '%s/%s%d.%s' % (imagesFolder, imagePrefix, i, ext)
            if os.path.exists(nextImage):
                # Use internally an Image importer for doing this job
                imgImporter = ImageImporter(None, nextImage, ext, self.renderer)
                imgImporter.init('as-char', True, None, None, 'page', 'page',
                                 None, True, None)
                self.res += imgImporter.run()
                os.remove(nextImage)
            else:
                noMoreImages = True
        os.rmdir(imagesFolder)
        return self.res

    # Other useful gs commands -------------------------------------------------
    # Convert a PDF from colored to grayscale
    #gs -sOutputFile=grayscale.pdf -sDEVICE=pdfwrite
    #   -sColorConversionStrategy=Gray -dProcessColorModel=/DeviceGray
    #   -dCompatibilityLevel=1.4 -dNOPAUSE -dBATCH colored.pdf
    # Downsample inner images to produce a smaller PDF
    #gs -sOutputFile=smaller.pdf -sDEVICE=pdfwrite
    #   -dCompatibilityLevel=1.4 -dPDFSETTINGS=/screen
    #   -dNOPAUSE -dBATCH some.pdf
    # The "-dPDFSETTINGS=/screen is a shorthand for:
    #-dDownsampleColorImages=true \
    #-dDownsampleGrayImages=true \
    #-dDownsampleMonoImages=true \
    #-dColorImageResolution=72 \
    #-dGrayImageResolution=72 \
    #-dMonoImageResolution=72

class ConvertImporter(DocImporter):
    '''This class allows to import the content of any file that LibreOffice (LO)
       can convert into PDF: doc(x), rtf, xls(x)... It first calls LO to convert
       the document into PDF, then calls a PdfImporter.'''
    def run(self):
        # This feature is only available in the open source version
        if commercial: raise CommercialError()
        # Convert the document into PDF with LibreOffice
        pdfFile = getTempFileName(extension='pdf')
        output = self.renderer.callLibreOffice(self.importPath,
                                               outputName=pdfFile)
        if output: raise PodError(TO_PDF_ERROR % output)
        # Launch a PdfImporter to import this PDF into the POD result
        pdfImporter = PdfImporter(None, pdfFile, 'pdf', self.renderer)
        return pdfImporter.run()

# ------------------------------------------------------------------------------
class Image:
    '''Represents an image on disk. This class is used to detect the image type
       and size.'''
    jpgTypes = ('jpg', 'jpeg')

    def __init__(self, path, format, unit='cm'):
        self.path = path # The image absolute path on disk
        self.format = format or imghdr.what(path)
        # Determine image size in pixels (again, by reading its first bytes)
        self.width, self.height = self.getSizeIn(unit)

    def getSizeIn(self, unit='cm'):
        '''Reads the first bytes from the image on disk to get its size'''
        x = y = None
        # Get the file format from the file name of absent
        format = self.format or os.path.splitext(self.path)[1][1:]
        # Read the file on disk
        f = file(self.path, 'rb')
        if format in Image.jpgTypes:
            # Dummy read to skip header ID
            f.read(2)
            while True:
                # Extract the segment header
                marker, code, length = struct.unpack("!BBH", f.read(4))
                # Verify that it's a valid segment
                if marker != 0xFF:
                    # No JPEG marker
                    break
                elif code >= 0xC0 and code <= 0xC3:
                    # Segments that contain size info
                    y, x = struct.unpack("!xHH", f.read(5))
                    break
                else:
                    # Dummy read to skip over data
                    f.read(length-2)
        elif format == 'png':
            # Dummy read to skip header data
            f.read(12)
            if f.read(4) == "IHDR":
                x, y = struct.unpack("!LL", f.read(8))
        elif format == 'gif':
            imgType = f.read(6)
            buf = f.read(5)
            if len(buf) == 5:
                # else: invalid/corrupted GIF (bad header)
                x, y, u = struct.unpack("<HHB", buf)
        f.close()
        if (x and y) and (unit == 'cm'):
            return float(x)/px2cm, float(y)/px2cm
        else:
            # Return the size, in pixels, or as a tuple (None, None) if
            # uncomputable.
            return x, y

# Compute size of images -------------------------------------------------------
class ImageImporter(DocImporter):
    '''This class allows to import into the ODT result an image stored
       externally.'''
    anchorTypes = ('page', 'paragraph', 'char', 'as-char')
    WRONG_ANCHOR = 'Wrong anchor. Valid values for anchors are: %s.'
    pictFolder = '%sPictures%s' % (os.sep, os.sep)
    # Path of a replacement image, to use when the image to import is not found
    imageNotFound = os.path.join(os.path.dirname(appy.pod.__file__),
                                 'imageNotFound.jpg')

    # Regular expression for finding orientation within EXIF meta-data
    orientationRex = re.compile('exif:Orientation\s*=\s*(\d+)')

    def getZopeImage(self, at):
        '''Gets the Zope Image via an image resolver'''
        resolver = self.renderer.imageResolver
        if not resolver or not at.startswith(resolver.absolute_url()): return
        # The resolver is a Zope application or a sub-object within it. From it,
        # we will retrieve the object on which the image is stored and get the
        # file to download.
        urlParts = urlparse.urlsplit(at)
        path = urlParts[2][1:].split('/')
        image = None
        try:
            image = resolver.unrestrictedTraverse(path)
        except Exception:
            # Maybe a rewrite rule as added some prefix to all URLs ?
            try:
                path = path[1:]
                # Make sure we still have a path, or it gets the resolver
                if path:
                    image = resolver.unrestrictedTraverse(path)
            except Exception:
                pass # The image was not found
        # Return it only if it is an image
        if image and not hasattr(image, 'getBlobWrapper'): image = None
        return image

    def isImage(self, response):
        '''Cheks that the p_response received after a HTTP GET supposed to
           retrieve an image actually contains an image.'''
        if not response or (response.code != 200): return
        # Check p_response's content type
        type = response.headers.get('content-type')
        # The most frequent case: the HTTP GET returns an error page, ie, if the
        # image URL requires authentication.
        if type and not type.startswith('image/'): return
        return True

    def checkAt(self, at):
        '''Do not raise an exception when p_at does not correspond to an
           existing file. We will dump a replacement image instead.'''
        at = DocImporter.checkAt(self, at, raiseOnError=False)
        if at.startswith('http'):
            # Try to get the image
            try:
                response = Resource(at).get(followRedirect=False)
            except (Resource.Error, AttributeError):
                response = None # Can't get the distant image
            if self.isImage(response):
                # Remember the response
                self.httpResponse = response
                return at
            # The HTTP GET did not work, maybe for security reasons (we probably
            # have no permission to get the file). But maybe the URL was a local
            # one, from an application server running this POD code. In this
            # case, if an image resolver has been given to POD, use it to
            # retrieve the image.
            self.zopeImage = self.getZopeImage(at)
            if self.zopeImage:
                return at
            # We could not find the image
            self.format = 'jpg'
            return self.imageNotFound
        elif at.startswith('data:'):
            # The image content and type are embedded in p_at, which comes from
            # the "src" attribute of a HTML "img" tag of the form:
            #              "data:<mimeType>;base64,<base64 content>"
            mimeType = at[5:at.index(';')]
            # The MIME type may be "image/*". In that case, set "img" as virtual
            # format; the real format will be detected once the file will be
            # dumped to disk.
            self.format = mimeTypesExts.get(mimeType) or 'img'
            content = at[at.index(',')+1:]
            # Decode the base64 content and store it in a temp file on disk
            content = base64.b64decode(content)
            fileName = sutils.getTempFileName(extension=self.format)
            f = open(fileName, 'wb')
            f.write(content)
            f.close()
            if self.format == 'img':
                self.format = imghdr.what(fileName)
            return fileName
        else:
            if at.startswith('file://'): at = at[7:]
            if not os.path.isfile(at):
                self.format = 'jpg'
                at = self.imageNotFound
            elif self.format == 'image':
                # Read its format by reading its first bytes
                self.format = imghdr.what(str(at))
            return at

    def getImportFolder(self):
        return os.path.join(self.tempFolder, 'unzip', 'Pictures')

    def moveFile(self):
        '''Copies file at self.at into the ODT file at self.importPath'''
        at = self.at
        importPath = self.importPath
        # Has this image already been imported ?
        for imagePath, imageAt in self.fileNames.iteritems():
            if imageAt == at: # Yes
                i = importPath.rfind(self.pictFolder) + 1
                return importPath[:i] + imagePath
        # The image has not already been imported: copy it
        r = None
        if not at.startswith('http'):
            # A file on disk
            shutil.copy(at, importPath)
            r = importPath
        else:
            # The image has (maybe) been retrieved from a HTTP GET
            response = getattr(self, 'httpResponse', None)
            if response:
                # Retrieve the image format
                format = response.headers['Content-Type']
                if format in mimeTypesExts:
                    # At last, I can get the file format
                    self.format = mimeTypesExts[format]
                    importPath += self.format
                    f = file(importPath, 'wb')
                    f.write(response.body)
                    f.close()
                    r = importPath
            if not r:
                # The image has (maybe) been retrieved from Zope
                zopeImage = getattr(self, 'zopeImage', None)
                if zopeImage:
                    blobWrapper = zopeImage.getBlobWrapper()
                    self.format = mimeTypesExts[blobWrapper.content_type]
                    importPath += self.format
                    blob = blobWrapper.getBlob()
                    # If we do not check 'readers', the blob._p_blob_committed is
                    # sometimes None.
                    blob.readers
                    blobPath = blob._p_blob_committed
                    shutil.copy(blobPath, importPath)
                    r = importPath
        if r:
            # Ensure we can modify the image (with ImageMagick)
            os.chmod(r, stat.S_IREAD | stat.S_IWRITE)
            return r

    def manageExif(self):
        '''Read, with ImageMagick, EXIF metadata in the image, and apply a
           rotation (still with ImageMagick) if required.'''
        # Indeed, LO will not interpret EXIF metadata when reading the image
        path = self.importPath
        cmd = ['identify', '-format', '%[EXIF:*]', path]
        out = ImageMagick.run(cmd)
        if out:
            match = self.orientationRex.search(out)
            if match:
                code = int(match.group(1))
                cmd = ['convert', path, '-auto-orient', path]
                ImageMagick.run(cmd)

    def init(self, anchor, wrapInPara, size, sizeUnit, maxWidth, maxHeight,
             cssAttrs, keepRatio, convertOptions):
        '''ImageImporter-specific constructor'''
        # Initialise anchor
        if anchor not in self.anchorTypes:
            raise PodError(self.WRONG_ANCHOR % str(self.anchorTypes))
        self.anchor = anchor
        self.wrapInPara = wrapInPara
        self.size = size
        self.sizeUnit = sizeUnit
        pageLayout = self.renderer.stylesManager.pageLayout
        if maxWidth == 'page':
            maxWidth = pageLayout.getWidth()
        self.maxWidth = maxWidth
        if maxHeight == 'page':
            maxHeight = pageLayout.getHeight()
        self.maxHeight = maxHeight
        self.keepRatio = keepRatio
        self.convertOptions = convertOptions
        # CSS attributes
        self.cssAttrs = cssAttrs
        if cssAttrs:
            w = getattr(self.cssAttrs, 'width', None)
            h = getattr(self.cssAttrs, 'height', None)
            if w and h:
                self.sizeUnit = w.unit
                self.size = (w.value, h.value)
        # Manage EXIF tags when relevant
        if self.renderer.rotateImages: self.manageExif()
        # Call ImageMagick to perform a custom conversion if required
        options = self.convertOptions
        image = None
        transformed = False
        if options:
            # This feature is only available in the open source version
            if commercial: raise CommercialError()
            if callable(options): # It is a function
                image = Image(self.importPath, self.format)
                options = self.convertOptions(image)
            if options:
                cmd = ['convert', self.importPath] + options.split() + \
                      [self.importPath]
                ImageMagick.run(cmd)
                transformed = True
        # Avoid creating an Image instance twice if no transformation occurred
        if image and not transformed:
            self.image = image
        else:
            self.image = Image(self.importPath, self.format)

    def applyMax(self, width, height):
        '''Return a tuple (width, height), potentially modified w.r.t. p_width
           and p_height, to take care of p_self.maxWidth & p_self.maxHeight.'''
        # Apply max width
        maxW = self.maxWidth
        if maxW and width > maxW:
            ratio = maxW / width
            width = maxW
            # Even if the width/height ratio must not be kept, in this case,
            # nevertheless apply it.
            height *= ratio
        # Apply max height
        maxH = self.maxHeight
        if maxH and height > maxH:
            ratio = maxH / height
            height = maxH
            # Even if keepRatio is False, in that case, nevertheless apply the
            # ratio on height, too.
            width *= ratio
        return width, height

    def getImageSize(self):
        '''Get or compute the image size and returns the corresponding ODF
           attributes specifying image width and height expressed in cm.'''
        # Compute image size, in cm
        width, height = self.image.width, self.image.height
        keepRatio = self.keepRatio
        if self.size:
            # Apply a percentage when p_self.sizeUnit is 'pc'
            if self.sizeUnit == 'pc':
                # If width or height could not be computed, it is impossible
                if not width or not height: return ''
                if keepRatio:
                    ratioW = ratioH = float(self.size[0]) / 100
                else:
                    ratioW = float(self.size[0]) / 100
                    ratioH = float(self.size[1]) / 100
                width = width * ratioW
                height = height * ratioH
            else:
                # Get, from p_self.size, required width and height, and convert
                # it to cm when relevant.
                w, h = self.size
                if self.sizeUnit == 'px':
                    try:
                        w = float(w) / px2cm
                        h = float(h) / px2cm
                    except ValueError:
                        # Wrong values: use v_width and v_height
                        w = width
                        h = height
                # Use (w, h) as is if we don't care about keeping image ratio or
                # if we couldn't determine image's width or height.
                if (not width or not height) or not keepRatio:
                    width, height = w, h
                else:
                    # Compute height and width ratios and apply the minimum
                    # ratio to both width and height.
                    ratio = min(w/width, h/height)
                    width = width * ratio
                    height = height * ratio
        if not width or not height: return ''
        # Take care of max width & height if specified
        width, height = self.applyMax(width, height)
        # Return the ODF attributes
        s = self.svgNs
        return ' %s:width="%fcm" %s:height="%fcm"' % (s, width, s, height)

    def run(self):
        # Some shorcuts for the used xml namespaces
        d = self.drawNs
        t = self.textNs
        x = self.linkNs
        # Compute path to image
        i = self.importPath.rfind(self.pictFolder)
        imagePath = self.importPath[i+1:].replace('\\', '/')
        self.fileNames[imagePath] = self.at
        # In the case of SVG files, perform an image conversion to PNG
        if imagePath.endswith('.svg'):
            newImportPath = os.path.splitext(self.importPath)[0] + '.png'
            ImageMagick.run(['convert', self.importPath, newImportPath])
            os.remove(self.importPath)
            self.importPath = newImportPath
            imagePath = os.path.splitext(imagePath)[0] + '.png'
            self.format = 'png'
        # Compute image alignment if CSS attr "float" is specified
        floatValue = getattr(self.cssAttrs, 'float', None)
        if floatValue:
            floatValue = floatValue.value.capitalize()
            styleInfo = '%s:style-name="podImage%s" ' % (d, floatValue)
            self.anchor = 'char'
        else:
            styleInfo = ''
        name = getUuid(prefix='I', removeDots=True)
        image = '<%s:frame %s%s:name="%s" %s:z-index="0" ' \
                '%s:anchor-type="%s"%s><%s:image %s:type="simple" ' \
                '%s:show="embed" %s:href="%s" %s:actuate="onLoad"/>' \
                '</%s:frame>' % (d, styleInfo, d, name, d, t, self.anchor,
                self.getImageSize(), d, x, x, x, imagePath, x, d)
        if hasattr(self, 'wrapInPara') and self.wrapInPara:
            style = isinstance(self.wrapInPara, str) and \
                    (' text:style-name="%s"' % self.wrapInPara) or ''
            image = '<%s:p%s>%s</%s:p>' % (t, style, image, t)
        self.res += image
        return self.res
# ------------------------------------------------------------------------------
