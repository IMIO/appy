#!/usr/bin/env python3

'''Splits an ODT document into a series of sub-documents. The split is based on
   page breaks.'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from pathlib import Path

from appy.bin import Program
from appy.utils.zip import zip, unzip
from appy.utils import path as putils
from appy.pod import odf_parser as op
from appy.pod import styles_manager as sm

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
FILE_KO   = '%s does not exist or is not a file.'
FILE_WR   = '%s must be a .odt file.'
SUB_EX    = 'Files generated from a previous script execution are in the way ' \
            '(ie, %s). Please remove it.'
NO_SPLIT  = 'No file was generated: no splitting page break was found.'
SPLITTED  = '%d files were generated.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class SplitParser(op.OdfParser):
    '''Parses content.xml and extracts, from it, the part of content.xml being
       common to all sub-parts, and the parts being specific to every splitted
       sub-document.'''

    # Possible parser states
    COMMON_START = 0 # Content must be dumped in the common part (start)
    COMMON_END   = 1 # Content must be dumped in the common part (end)
    CHUNK_LAST   = 2 # Content must be dumped in the last encountered chunk
    CHUNK_NEW    = 3 # Content must be dumped in a new chunk to add

    # In the following states, we are parsing the document payload
    IN_PAYLOAD   = CHUNK_LAST, CHUNK_NEW

    def startDocument(self):
        '''Initialises the parser's data structures'''
        # The parts of the document being common to any sub-document = its start
        # and its end.
        self.commonStart = []
        self.commonEnd = []
        # Parts being specific to every sub-document
        self.chunks = []
        # Styles being tied to page styles. Everytime a document part will be
        # encountered with one of these styles, a new chunk will be created in
        # p_self.chunks.
        self.splitStyles = {} # ~{s_styleName: s_pageStyleName}~
        # The parser state
        self.state = SplitParser.COMMON_START
        # Are we parsing styles ? This flag is a kind of sub-state within
        # COMMON_START.
        self.inStyles = False

    def getStore(self):
        '''Get the store into which to dump the currently parsed content'''
        SP = SplitParser
        state = self.state
        if state == SP.COMMON_START:
            r = self.commonStart
        elif state == SP.COMMON_END:
            r = self.commonEnd
        elif state == SP.CHUNK_LAST:
            r = self.chunks[-1]
        elif state == SP.CHUNK_NEW:
            # Create a new chunk and add it in p_self.chunks
            r = []
            self.chunks.append(r)
            self.state = SP.CHUNK_LAST
        return r

    def hasSplitStyle(self, elem, attrs):
        '''Is a split style defined on this p_elem ?'''
        name = attrs.get('text:style-name') if attrs else None
        return name and name in self.splitStyles

    def dumpStartTag(self, elem, attrs):
        '''Adds start tag p_elem and his p_attrs into the right store'''
        r = [f'<{elem}']
        for name, value in attrs.items():
            r.append(f' {name}="{value}"')
        r.append('>')
        self.getStore().append(''.join(r))

    def startElement(self, elem, attrs):
        '''Start tag p_elem is encountered'''
        # Potentially update p_self.inStyles
        SP = SplitParser
        state = self.state
        if state == SP.COMMON_START and not self.inStyles and \
           elem == 'office:automatic-styles':
            self.inStyles = True
        # Potentially detect a split style
        if self.inStyles and elem == 'style:style' and \
           'style:master-page-name' in attrs:
            # A split style has been found
            pageStyleName = attrs['style:master-page-name']
            self.splitStyles[attrs['style:name']] = pageStyleName
        # Potentially detect a new chunk
        if state == SP.CHUNK_LAST and self.hasSplitStyle(elem, attrs):
            self.state = SP.CHUNK_NEW
        # Dump this start tag at the right place
        self.dumpStartTag(elem, attrs)

    def dumpEndTag(self, elem):
        '''Adds end tag p_elem to the current store'''
        self.getStore().append(f'</{elem}>')

    def endElement(self, elem):
        '''End tag p_elem is encountered'''
        # Potentially update p_self.inStyles
        SP = SplitParser
        state = self.state
        if state == SP.COMMON_START and self.inStyles and \
           elem == 'office:automatic-styles':
            self.inStyles = False
        # Dump the end tag and possibly update the parser state
        if state in SP.IN_PAYLOAD and elem == 'office:text':
            # This is the end of the content payload and, consequently, the
            # start of the common part (end).
            self.state = SP.COMMON_END
            # Dump the end tag after the stage change
            self.dumpEndTag(elem)
        else:
            # Dump the end tag before any state change
            self.dumpEndTag(elem)
            if state == SP.COMMON_START and elem == 'text:sequence-decls':
                # This is the end of the common part (start)
                self.state = SP.CHUNK_NEW

    def characters(self, content):
        '''Tag p_content is read'''
        self.getStore().append(content)

    def endDocument(self):
        '''Injects, into every chunk from p_self.chunk, the common part from
           p_self.common.'''
        chunks = self.chunks
        if not chunks: return
        # Get the common parts as strings
        commonStart = ''.join(self.commonStart)
        commonEnd = ''.join(self.commonEnd)
        i = 0
        while i < len(chunks):
            payload = ''.join(chunks[i])
            chunks[i] = f'{commonStart}{payload}{commonEnd}'
            i += 1

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Split(Program):
    '''Splits an ODT document into sub-documents'''

    # Help messages
    HELP_P   = 'is the path to the odt file to split. Splitted sub-files ' \
               'will be created in the same folder as the file to split. A ' \
               'sequence number will be added to the name of each splitted ' \
               'file. For example, if the file named /a/b/file.odt is ' \
               'splitted into 2 files, these latters will be created as ' \
               '/a/b/file.1.odt and /a/b/file.2.odt.'

    def defineArguments(self):
        '''Define the allowed arguments for this program'''
        add = self.parser.add_argument
        # Positional arguments
        add('path', help=Split.HELP_P)

    def getResultPath(self, i):
        '''Returns a path representing the p_i(th) splitted document'''
        path = self.path
        return path.parent / f'{path.stem}.{i}{path.suffix}'

    def analyseArguments(self):
        '''Check and store arguments'''
        # Get args as p_self's attributes
        for name, value in self.args.__dict__.items():
            setattr(self, name, value)
        # Ensure the file exists and has a .odt extension
        path = Path(self.path).resolve()
        if not path.is_file():
            return self.exit(FILE_KO % self.path)
        if not path.name.endswith('.odt'):
            return self.exit(FILE_WR % self.path)
        self.path = path
        # Ensure there is no sub-document possibly generated by a previous
        # script execution.
        sub = self.getResultPath(1)
        if sub.is_file():
            return self.exit(SUB_EX % sub)

    def log(self, message):
        '''Logs this p_message'''
        print(message)

    def readPageStyles(self, stylesXml):
        '''Reads the page styles as defined in styles.xml, whose content is in
           p_stylesXml, as a string.'''
        parser = sm.StylesParser(sm.StylesEnvironment(), self)
        parser.parse(stylesXml)

    def run(self):
        '''Splits p_self.path into sub-files'''
        # Unzip the file in the temp folder
        tempFolder = self.tempFolder = putils.getOsTempFolder(sub=True)
        fileName = str(self.path)
        contents = unzip(fileName, tempFolder, odf=True, asBytes=False)
        # Read page styles and store them in p_self.pageStyles, as a dict
        #         ~{s_pageName: appy.pod.styles_manager.PageStyle}~
        self.readPageStyles(contents['styles.xml'])
        # Get chunks of content.xml, one per sub-document to create
        parser = SplitParser()
        parser.parse(contents['content.xml'])
        chunks = parser.chunks
        if len(chunks) < 2:
            # Nothing could be split
            self.log(NO_SPLIT)
        else:
            # Create one file per chunk
            contentFile = f'{tempFolder}/content.xml'
            i = 0
            for chunk in chunks:
                i += 1
                # Overwrite, in the temp folder, the unzipped content.xml with
                # the current chunk.
                with open(contentFile, 'w') as f:
                    f.write(chunk)
                # Get the path of the sub-file to generate
                path = self.getResultPath(i)
                # Delete the file if it exists
                if path.is_file(): path.unlink()
                # Create the file
                zip(str(path), tempFolder, odf=True)
            self.log(SPLITTED % len(chunks))
        # Delete the temp folder
        putils.FolderDeleter.delete(tempFolder)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
if __name__ == '__main__': Split().run()
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
