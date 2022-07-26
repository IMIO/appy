'''This script allows to perform a "grep" command that will be applied on files
   content.xml and styles.xml within all ODF files (odt and ods) found within a
   given folder.'''

# ------------------------------------------------------------------------------
from UserList import UserList
import re, sys, os.path, StringIO, difflib

from appy import Object as O
from appy.shared.zip import zip, unzip
from appy.shared import utils as sutils
from appy.shared.xml_parser import StringCleaner

# ------------------------------------------------------------------------------
OPT_C_V  = "Options -c and -v can't be use altogether."
FF_KO    = '%s does not exist.'
S_CLEAN  = '%d styled text part(s) %scleaned.'
F_CORR   = 'XML corruption in %s::%s - The file was left untouched.'

# ------------------------------------------------------------------------------
usage = '''Usage: python odfgrep.py [options] keyword file|folder [repl].

 *keyword* is the regular expression (or string if -s) to search within the
           file(s).

 If *file* is given, it is the path to an ODF file (odt or ods). grep will be
 run on this file only.

 If *folder* is given, the grep will be run on all ODF files found in this
 folder and sub-folders.

 If *repl* is given, within matched ODF files, *keyword* will be replaced with
 *repl*.

 OPTIONS

 -v : *v*erbose: dump more info about the find/replace zones (only available if
      option "-c" is not used, see below).

 -vv: similar to -v, must with even more *v*erbosity.

 -d : *d*ry-run: in the context of a replacement, if this option is set, no
      replacement will actually be performed, but output will give info
      (detailed if -v, minimal if not) about what replacements would have been
      performed without this option.

 -c : in *c*ontent. If unset, the find/replace process will only apply to the
      POD-controlled zones of POD template(s): notes and fields. If the option
      is set, it will occur in any part of the template(s).

 -s : by default, *keyword* is interpreted as a regular expression. If you want
      it to be a plain *s*tring instead, set this option.

 -n : *n*ice: if set in conjunction with -v or -vv, changes (being effective or
      potential, depending on -d) will be colorized. Else, changes will be
      rendered as standard diff output.

 IMPORTANT NOTES

 (1) The *repl*acement string may contain references to groups possibly defined
      within the *keyword* regular expression, but only via the "\<nb>"
      notation.

      For example, if *keyword* is cus(tom)_(agenda) and *repl* is \2_\1,
      every match will be replaced with tom_agenda.

 (2) From the command-line, *keyword* and *repl* special chars must be escaped.
     For example, cus(tom)_(agenda) must be written as  cus\(tom\)_\(agenda\)
                  \\2_\\1             must be written as  \\\\2_\\\\1
'''

# ------------------------------------------------------------------------------
class Note:
    '''Represents an ODF Note, be it included in an ODS or ODT template'''

    # Regex defining a paragraph within a note
    paraRex = re.compile('<text:p(.*?)>(.*?)</text:p>')

    # Regex for splitting metadata from real content within a note
    contentRex = re.compile('(.*?)(<text:(?:p|list).*)')

    # Regex used to remove formatting possibly found in notes
    spanRex = re.compile('<text:span[^>]*>(.*?)</text:span>')

    # On old templates, self-closing span tags may be found in notes
    spanSc = re.compile('<text:span[^>]*?/>')

    # Regex for parsing metadata present in a note
    metadataRex = re.compile('.*?(<dc:creator>.*?</dc:creator>)?' \
                             '<dc:date>(.*?)</dc:date>.*', re.S)

    # Regex representing an overstructured text-list note
    listRex = re.compile('<text:list.*?>(.*?)</text:list>')
    itemRex = re.compile('<text:list-item.*?>(.*?)</text:list-item>')

    @classmethod
    def extractMetadata(class_, content):
        '''Extract, from this note p_content, metadata from real payload'''
        match = class_.contentRex.match(content)
        return match.group(1), match.group(2)

    @classmethod
    def parseMetadata(class_, metadata):
        '''Extract p_metadata'''
        if not metadata: return None, None
        match = class_.metadataRex.match(metadata)
        creator, date = match.groups()
        if creator: creator = creator[12:-13]
        creator = (creator or 'unknown').strip()
        return creator, date

    @classmethod
    def extractListParas(class_, match):
        '''If this p_note has a text-list overstructure, extract and returns
           standard paragraphs from it.'''
        # Extract paragraphs from list-items found in this p_match
        return class_.itemRex.sub(lambda m:m.group(1), match.group(1))

    @classmethod
    def clean(class_, note, cleanMethod):
        '''Returns the content of this p_note, where any formatting and ODF tag
           has been removed (even text:p tags).'''
        # Preambles
        # (a) Remove self-closing span tags potentially found in old templates
        note = class_.spanSc.sub('', note)
        # (b) Remove text-list overstructure, illegal now but possibly found in
        #     old templates.
        note = class_.listRex.sub(class_.extractListParas, note)
        # Clean the note
        note = class_.spanRex.sub(cleanMethod, note)
        # Remove any paragraph
        r = []
        style = None # Remember the style of at least one paragraph
        for attrs, content in class_.paraRex.findall(note):
            style = attrs or style
            r.append(content)
        return '\n'.join(r), style

    @classmethod
    def reify(class_, note, paraStyle):
        '''Re-create a series of "text:p" tags from this naked p_note, made of
           carriage-return-separated lines of text.'''
        r = []
        style = paraStyle or ''
        for line in note.split('\n'):
            r.append('<text:p%s>%s</text:p>' % (style, line))
        return ''.join(r)

# ------------------------------------------------------------------------------
class Condition:
    '''Represents a conditional field storing a POD expression'''

    # Name of the attribute storing the expression
    trueAttr = 'text:string-value-if-true'

    # Regex representing the attribute storing the "true" condition
    trueRex = re.compile('%s="(.+?)"' % trueAttr)

    # The expression may be surrounded with double quotes
    quote = '&quot;'

    @classmethod
    def reifyAttribute(class_, match, expression):
        '''Recreates the attribute sotirng the true condition, containing the
           new p_expression.'''
        # Get the current expression
        current = match.group(1)
        # Surround the new expression with double quotes if the current one was
        if current.startswith(class_.quote):
            r = '%s%s%s' % (class_.quote, expression, class_.quote)
        else:
            r = expression
        return '%s="%s"' % (class_.trueAttr, r)

    @classmethod
    def replace(class_, attrs, expression):
        '''Replace, within this series of condition p_attributes, the "true"
           expression with this p_expression.'''
        fun = lambda match: class_.reifyAttribute(match, expression)
        return class_.trueRex.sub(fun, attrs, count=1)

# ------------------------------------------------------------------------------
class Cell:
    '''Represents a cell within an ODS sheet'''

    # Name of the attributes storing the POD expression
    formulaAttr = 'table:formula'
    valueAttr = 'office:string-value'

    # Regex representing the attributes storing the POD expression
    formulaRex = re.compile('%s="(.+?)"' % formulaAttr)
    valueRex = re.compile('%s="(.+?)"' % valueAttr)

    @classmethod
    def replace(class_, attrs, content, expr):
        '''Replace, within this series of cell p_attributes and this cell
           p_content, the POD expression with this new p_expr(ession).'''
        # Crazy: the POD expression is stored at 3 different places in the cell:
        # 2 within cell attributes and 1 more in the cell content.
        # ~
        c = class_
        # Perform replacements within p_attrs
        attrs = c.formulaRex.sub(
          lambda m: '%s="of:=&quot;%s&quot;"' % (c.formulaAttr, expr),
          attrs, count=1)
        attrs = c.valueRex.sub(lambda m: '%s="%s"' % (c.valueAttr, expr),
          attrs, count=1)
        # Perform the replacement within p_content
        return attrs, content

# ------------------------------------------------------------------------------
class Match:
    '''When a Grep is ran with inContent=False (see class c_Grep), one of its
       outputs is the list of matches within every found ODF document. Every
       match is represented by an instance of class Match.'''

    # Start/end markers and colors to use for delimiting diff zones
    markers = O(
      xhtml = O(start='<span style="color:%s">', end='</span>'),
      term  = O(start='\x1b[3%sm', end='\x1b[0m')
    )
    colors = O(
      xhtml = O(insert='green', delete='red'),
      term  = O(insert='2', delete='1')
    )

    def __init__(self, keyword, tag, metadata, content, patched=None,
                 dryRun=False, kwString=False, isVerbose=False,
                 outputType='raw'):
        # The matched keyword (as a string)
        self.keyword = keyword
        # Is p_keyword built fom a plain string or from a regular expression ?
        self.kwString = kwString
        # The precise matched tag
        self.tag = tag
        # The type of tag (= "target") whose content has been (or could be)
        # patched.
        self.target = tag == 'office:annotation' and 'note' or 'field'
        # The tag metadata (creator, date, etc), for notes only
        self.metadata = metadata
        # Note-specific metadata, that will be extracted from p_metadata
        self.creator, self.date = Note.parseMetadata(metadata)
        # In the context of a replacement, the version of p_content after
        # replacements were done.
        if patched is not None:
            self.patched = self.parseContent(patched)
        else:
            self.patched = None
        # Are we in the context of a dry run ?
        self.dryRun = dryRun
        # Verbose __repr__ for a match ?
        self.isVerbose = isVerbose
        # Output type, defining the way to render the diff between the content
        # before and after the replacement.
        self.outputType = outputType
        # Extract payload from p_content
        self.content = self.parseContent(content)

    def unescape(self, content):
        '''Unescape special chars from p_content'''
        return content.replace('&apos;', "'")

    def parseNote(self, note):
        '''Within this p_note, unescape some entities'''
        return self.unescape(note)

    def parseField(self, field):
        '''Parses the content of this ODF p_field'''
        # Remove the end of the start tag
        i = field.find('>')
        return self.unescape(field[i+1:])

    def parseContent(self, content):
        '''Parses this p_content and returns its payload'''
        if self.target == 'note':
            r = self.parseNote(content)
        elif self.target == 'field':
            r = self.parseField(content)
        else:
            r = content
        return r

    def getDiff(self, type='raw'):
        '''Returns a diff between self.content and self.patched'''
        # ----------------------------------------------------------------------
        # If p_type | the output
        # is ...    | will be ...
        # ----------------------------------------------------------------------
        #   "raw"   | (default) raw text as outputed by standard module difflib
        # ----------------------------------------------------------------------
        #   "term"  | colorized output to be rendered in a Unix-like terminal
        # ----------------------------------------------------------------------
        #   "xhtml" | a colorized chunk of XHTML code, in a "div" tag
        # ----------------------------------------------------------------------
        #   "data"  | a list of data about insertions, deletions and
        #           | replacements, as returned by method
        #           |        difflib.SequenceMatcher::get_opcodes
        # ----------------------------------------------------------------------
        if type == 'raw':
            # Get the diff as raw text
            differ = difflib.Differ()
            r = list(differ.compare(self.content.split('\n'),
                                    self.patched.split('\n')))
            r = '\n'.join(r)
        else:
            # Get the diff as xhtml or colored text for a terminal
            r = []
            a = self.content
            b = self.patched
            matcher = difflib.SequenceMatcher(None, a, b)
            markers = self.markers[type]
            colors = self.colors[type]
            changes = matcher.get_opcodes()
            if type == 'data':
                # Return the data structures representing changes, as-is
                r = changes
            else:
                # Format data according to p_type
                for opcode, a0, a1, b0, b1 in changes:
                    if opcode == 'equal':
                        r.append(a[a0:a1])
                    elif opcode == 'insert':
                        start = markers.start % colors.insert
                        r.append('%s%s%s' % (start, b[b0:b1], markers.end))
                    elif opcode == 'delete':
                        start = markers.start % colors.delete
                        r.append('%s%s%s' % (start, a[a0:a1], markers.end))
                    elif opcode == 'replace':
                        dstart = markers.start % colors.delete
                        istart = markers.start % colors.insert
                        r.append('%s%s%s' % (dstart, a[a0:a1], markers.end))
                        r.append('%s%s%s' % (istart, b[b0:b1], markers.end))
                r = ''.join(r)
                if type == 'xhtml':
                    r = '<div>%s</div>' % r
        return r

    def __repr__(self, spaces=2, nb=None):
        '''p_self's string representation'''
        isVerbose = self.isVerbose
        sep = ' ' * spaces
        # Add, for a note, a line of text containing its creator and creation
        # date.
        if self.target == 'note' and isVerbose:
            part = '\n%sBy %s on %s\n' % (sep, self.creator, self.date)
        else:
            part = ''
        prefix = isVerbose and ('\n%s' % sep) or ''
        if self.patched is None:
            # No replacement
            info = '%sContent:\n\n%s' % (prefix, self.content)
        else:
            # A replacement: display a diff
            verb = self.dryRun and 'would have been' or 'were'
            diff = self.getDiff(type=self.outputType)
            info = '%sThese changes %s done:\n\n%s' % (prefix, verb, diff)
        # If v_isVerbose, add the target of the match (note or field) and repeat
        # the keyword(s) entered.
        if isVerbose:
            targetType = 'Match::on::%s (tag %s)\n' % (self.target, self.tag)
            kwType = self.kwString and 'string' or 'regex'
            keywords = '%sKeyword(s) (%s): %s' % (sep, kwType, self.keyword)
            vinfo = '%s%s%s' % (sep, targetType, keywords)
        else:
            vinfo = ''
        return '%s%s%s%s' % (vinfo, part, sep, info)

# ------------------------------------------------------------------------------
class Matches(UserList):
    '''List of Match instances found in a given file'''

    def __init__(self, fileName, *args, **kwargs):
        UserList.__init__(self, *args, **kwargs)
        self.fileName = fileName

    def __repr__(self):
        '''p_self's string representation'''
        if len(self) == 1:
            prefix = '1 match'
        else:
            prefix = '%d matches' % len(self)
        r = [':: %s for %s ::' % (prefix, self.fileName)]
        i = 0
        for match in self:
            i += 1
            r.append(match.__repr__(nb=i))
        return '%s\n' % '\n\n'.join(r)

# ------------------------------------------------------------------------------
class Grep:
    '''Perform UNIX grep-like searches within ODF files'''

    toGrep = ('content.xml', 'styles.xml')
    toUnzip = ('.ods', '.odt')

    # Messages ~{ b_replace: { b_match: s_message }}~
    messageTexts = { True:  { True:  '%s: %d replacement(s) done.',
                              False: 'No replacement was made.'},
                     False: { True:  '%s matches %d time(s).',
                              False: 'No match found.'}}

    # ODF tags used by POD statements or expressions
    podTags = {
      'odt': ('office:annotation', 'text:conditional-text', 'text:text-input'),
      # In ODS templates, office:annotation tags are contained within table
      # cells. Consequently, they do not appear at the first level.
      'ods': ('table:table-cell',),
      'inner': ('office:annotation',)
    }

    # Regex allowing to detect mentions, in the replacement string, to groups
    # defined in the keywords regex.
    groupsRex = re.compile('\\\(\d)+')


    # Regex for parsing a POD expression within an ODS formula
    formulaRex = re.compile('table:formula="of:=&quot;(.*?)&quot;"')

    def __init__(self, keyword, fileOrFolder, repl=None, inContent=False,
                 silent=None, verbose=1, dryRun=False, asString=False,
                 outputType='raw'):
        # Create a regex from the passed p_keyword
        skeyword = self.getPureString(keyword)
        self.skeyword = skeyword
        # If p_asString is True, p_keyword is interpreted as a plain string.
        # Else, it is interpreted as a regular expression.
        self.asString = asString
        if asString:
            skeyword = re.escape(skeyword)
        self.keyword = re.compile(skeyword, re.S)
        # The file or folder where to find POD templates
        self.fileOrFolder = fileOrFolder
        # A temp folder where to unzip the POD templates
        self.tempFolder = sutils.getOsTempFolder()
        # (optional) The replacement text
        if repl is not None:
            repl = self.getPureString(repl)
        self.repl = repl
        # (optional) Find/replace p_keyword in raw ODF content, or in POD-
        #            controlled zones (fields, statements) ?
        self.inContent = inContent
        # If find/replace must occur in POD-controlled zones, define these zones
        # via regular expressions: one for ODT templates, one for ODS templates.
        self.zoneRex = {
          'odt': self.getZoneRex(inContent, 'odt'),
          'ods': self.getZoneRex(inContent, 'ods'),
          # Sub-rex for ODS notes within cells
          'inner': self.getZoneRex(inContent, 'inner'),
        }
        # Must lists of matches be built for every found ODF document ?
        if not inContent:
            # Yes
            self.matches = {} # ~{s_filePath:[Match]}~
        # If called programmatically, we don't want any output on stdout
        self.silent = silent
        if silent:
            self.messages = []
        # When replacing, count the number of styled text parts whose style was
        # removed (see Note::clean).
        self.cleaned = 0
        # Verbosity: 0 (less) to 3 (more). 0 means: no output at all, fatal
        # errors excepted. 1 is the default. 2 and 3 produce more detailed
        # output.
        self.verbose = verbose
        # In dry-run mode (see below), force verbosity to be at least 2
        if dryRun and verbose < 2:
            self.verbose = 2
        # In dry-run mode, a replacement is not truly done: output indicates
        # what replacement(s) would have been performed.
        self.dryRun = dryRun
        # When a p_repl(acement) is specified and outputed (depending on
        # p_verbose), how must be rendered the diff representing the
        # replacement ? More info in method Match::getDiff.
        self.outputType = outputType

    def getPureString(self, s):
        '''Converts p_value to a string, if unicode'''
        if isinstance(s, unicode):
            r = s.encode('utf-8')
        else:
            r = s
        return r

    def getZoneRex(self, inContent, fileType):
        '''Return, if p_inContent is False, the regex representing pod zones
           within content|styles.xml.'''
        if inContent: return
        # Build the regex
        tags = '|'.join(self.podTags[fileType])
        # Negative lookahead assertion (?!-) is used to prevent matching tag
        # "office:annotation-end".
        rex = '<(?P<tag>%s)(?!-)(.*?)>(.*?)</(?P=tag)>' % tags
        return re.compile(rex, re.S)

    def dump(self, message, raiseError=False):
        '''Dumps a p_message, either on stdout or in self.messages if we run in
           silent mode.'''
        # Raise an exception if requested
        if raiseError: raise Exception(message)
        # Log or store the p_message, depending on p_silent
        if self.silent:
            self.messages.append(message)
        else:
            print message

    def getMessage(self):
        '''Returns self.messages, concatenated in a single string'''
        messages = getattr(self, 'messages', None)
        if not messages: return ''
        return '\n'.join(messages)

    def getReplacement(self, match, counts=None):
        '''In the context of a replacement, this method returns p_self.repl,
           that will replace the matched p_self.keyword. In the context of a
           simple grep, the method returns the matched content, left untouched.
           In both contexts, p_counts about matches are updated.'''
        if counts is not None:
            counts.inXml += 1
        if self.repl:
            fun = lambda m: match.group(int(m.group(1)))
            r = self.groupsRex.sub(fun, self.repl)
        else:
            # The replacement has just been triggered to build self.matches.
            # Return the matched zone unchanged.
            r = match.group(0)
        return r

    def addMatch(self, fileName, imatch):
        '''Adds this p_imatch concerning this p_fileName among p_self.matches'''
        matches = self.matches
        if fileName in matches:
            matches[fileName].append(imatch)
        else:
            matches[fileName] = Matches(fileName, [imatch])

    def cleanStyle(self, match):
        '''A styled text part has been found in p_match. Clean it and update the
           count in p_self.cleaned.'''
        if self.repl:
            self.cleaned += 1
        return match.group(1)

    def findIn(self, fileName, match, counts):
        '''A POD zone has been found, in m_match, in a file whose name is
           p_fileName. Perform replacements within this zone.'''
        # Remember the current count of matches
        initialCount = counts.inXml
        initialCleaned = self.cleaned
        originalContent = match.group(0)
        tag = match.group(1)
        attrs = match.group(2)
        content = code = match.group(3)
        search = True
        metadata = ''
        subCount = 0
        isFormula = isNote = isCond = False
        if tag == 'office:annotation':
            # Further split v_content into *pure* content (=Python code) and
            # meta-data, like note creator and creation date.
            metadata, code = Note.extractMetadata(content)
            # Ensure there is no formatting in the note before applying the
            # replacement.
            code, paraStyle = Note.clean(code, self.cleanStyle)
            isNote = True
        elif tag == 'table:table-cell':
            # In an ODS template, a table cell may contain an expression (as a
            # formula) and also an annotation.
            # (a) Manage a potential inner annotation
            fun = lambda subMatch: self.findIn(fileName, subMatch, counts)
            content = self.zoneRex['inner'].sub(fun, content)
            subCount = counts.inXml - initialCount
            # (b) Manage a potential POD expression
            fmatch = Grep.formulaRex.search(attrs)
            if not fmatch:
                search = False # No POD expression here
            else:
                code = fmatch.group(1)
                isFormula = True
        elif tag == 'text:conditional-text':
            isCond = True
        # When a table cell only contains a note, the job is already done
        if search:
            r = self.keyword.sub(lambda m: self.getReplacement(m, counts), code)
            matched = counts.inXml > (initialCount + subCount)
            if matched:
                # p_self.keyword has matched. Create a Match instance.
                if self.repl:
                    patched = r # A true replacement was done
                else:
                    patched = None # There was a match, but v_r repeats
                                   # v_content, because we are not in the
                                   # context of a replacement.
                m = Match(self.skeyword, tag, metadata, code, patched,
                          self.dryRun, self.asString, self.verbose > 2,
                          self.outputType)
                self.addMatch(fileName, m)
                # Count the number of matches instead of the number of
                # individual replacements.
                counts.inXml = initialCount + 1
            else:
                # Cleaning for this file will finally not be applied, so set the
                # count to the one that existed before managing this file.
                self.cleaned = initialCleaned
            # Reinsert v_r at the right place when reifying the whole tag
            if matched and self.repl:
                if isFormula:
                    attrs, content = Cell.replace(attrs, content, r)
                elif isNote:
                    content = Note.reify(r, paraStyle)
                elif isCond:
                    content = r
                    attrs = Condition.replace(attrs, r)
                else:
                    content = r
            elif isNote and self.repl:
                # Even if there was no match in some note, every note is cleaned
                # in any case, so, must be reified.
                content = Note.reify(r, paraStyle)
        return '<%s%s>%s%s</%s>' % (tag, attrs, metadata, content, tag)

    def grepFileContent(self, fileName, tempFolder, contents):
        '''Finds self.keyword among p_tempFolder/content.xml and
           p_tempFolder/styles.xml, whose content is in p_contents and was
           extracted from p_fileName, and return the number of matches. If
           Match objects must be built, p_self.matches are updated accordingly.

           If self.repl is there, and if there is at least one match, the method
           replaces self.keyword by self.repl for all matches, re-zips the ODF
           file whose parts are in p_tempFolder and overwrites the original file
           in p_fileName.'''
        # Initialise counts
        counts = O(
          inXml = 0,    # The number of matches within the currently analysed
                        # XML file (content.xml or styles.xml) within p_fileName
          inFile = 0,   # The number of matches within p_fileName (sums all
                        # inner counts from content.xml and styles.xml)
          corrupted = 0 # The number of XML files whose content is not
                        # SAX-parsable anymore after replacements have been
                        # performed
        )
        fileType = os.path.splitext(fileName)[-1][1:].lower()
        zoneRex = self.zoneRex[fileType]
        for name in self.toGrep:
            # Get the file content
            content = contents[name]
            # Step #1: find (and potentially replace) matches in the content of
            #          the file as loaded in a string, in v_content...
            if not zoneRex:
                # ... either in the full document ...
                found = self.keyword.findall(content)
                if not found: continue
                counts.inXml = len(found)
                if self.repl:
                    # Make the replacement
                    fun = lambda match: self.getReplacement()
                    content = self.keyword.sub(fun, content)
            else:
                # ... or within every POD expression or statement
                counts.inXml = 0 # Reinitialise the XML count
                fun = lambda match: self.findIn(fileName, match, counts)
                content = zoneRex.sub(fun, content)
                if not counts.inXml: continue
            counts.inFile += counts.inXml
            # Step #2: actually perform replacements on the file on disk, if a
            #          p_self.repl(acement) is required, if at least one
            #          replacement can be performed and if p_content has not
            #          been corrupted.
            if counts.inXml and self.repl and not self.dryRun:
                # Output a warning if p_content has been corrupted
                if not StringCleaner.isParsable(content, wrap=None):
                    self.dump(F_CORR % (fileName, name))
                    counts.corrupted += 1
                    # Remove the matches
                    if fileName in self.matches: del self.matches[fileName]
                    # Nothing will be cleaned
                    self.cleaned = 0
                else:
                    # Overwrite the file on disk
                    tempFileName = os.path.join(tempFolder, name)
                    f = open(tempFileName, 'w')
                    f.write(content)
                    f.close()
        # Re-zip the result when relevant
        if counts.inFile and self.repl and not self.dryRun and \
           counts.corrupted == 0:
            zip(fileName, tempFolder, odf=True)
        return counts.inFile

    def grepFile(self, fileName):
        '''Unzip the .xml files from file named p_fileName and perform a grep on
           it.'''
        # Unzip the file in the temp folder
        tempFolder = sutils.getOsTempFolder(sub=True)
        # Unzip the file in its entirety
        contents = unzip(fileName, tempFolder, odf=True)
        nb = self.grepFileContent(fileName, tempFolder, contents)
        if nb and self.verbose == 1:
            # If verbose is 2 or more, Match instances will all be dumped at the
            # end.
            msg = self.messageTexts[bool(self.repl)][bool(nb)] % (fileName, nb)
            self.dump(msg)
        # Delete the temp folder
        sutils.FolderDeleter.delete(tempFolder)
        return nb

    def run(self):
        '''Performs the "grep" on self.fileOrFolder'''
        nb = 0
        if os.path.isfile(self.fileOrFolder):
            nb += self.grepFile(self.fileOrFolder)
        elif os.path.isdir(self.fileOrFolder):
            # Grep on all files found in this folder
            for dir, dirnames, filenames in os.walk(self.fileOrFolder):
                for name in filenames:
                    if os.path.splitext(name)[1] in self.toUnzip:
                        nb += self.grepFile(os.path.join(dir, name))
        else:
            # Dump this error message, whatever verbose is
            self.dump(FF_KO % self.fileOrFolder)
        verbose = self.verbose
        if not nb and verbose > 0:
            self.dump(self.messageTexts[bool(self.repl)][False])
        elif verbose > 1:
            # Dump the match instances
            for match in self.matches.itervalues():
                self.dump(repr(match))
        if self.cleaned and verbose > 0:
            verb = self.dryRun and 'would have been ' or ''
            self.dump(S_CLEAN % (self.cleaned, verb))
        return nb

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    # Get options
    args = sys.argv
    options = {}
    if '-c' in args: # Find/replace in content or in POD zones ?
        args.remove('-c')
        options['inContent'] = True
    if '-v' in args: # verbose
        args.remove('-v')
        options['verbose'] = 2
    if '-vv' in args: # verbose+
        args.remove('-vv')
        options['verbose'] = 3
    if '-d' in args: # Dry-run (replace)
        args.remove('-d')
        options['dryRun'] = True
    if '-s' in args: # Keyword is interpreted as a string and not a regex
        args.remove('-s')
        options['asString'] = True
    if '-n' in args:
        args.remove('-n')
        options['outputType'] = 'term'
    # Check args validity
    if len(sys.argv) not in (3, 4, 5):
        print usage
        sys.exit()
    if 'verbose' in options and 'inContent' in options:
        print OPT_C_V
        sys.exit()
    Grep(*sys.argv[1:], **options).run()
# ------------------------------------------------------------------------------
