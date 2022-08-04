'''Checks or updates a sub-pod template imported into a main one via a statement
   "do...from pod", using attribute "managePageStyles" being an integer value.
'''

# ------------------------------------------------------------------------------
import re, sys, os.path

from appy.shared.zip import zip, unzip
from appy.shared import utils as sutils
from appy.pod.styles_manager import StylesGenerator

# ------------------------------------------------------------------------------
usage = '''Usage: python2 odfsub.py [-c] path.

 *path* is the path to the odt file to update or check. When ' importing, via
   do...pod statement, a sub-pod template into a main one, using parameter
   "managePageStyles" being an integer value, page styles must explicitly be
   defined in the sub-pod template. If it is not the case on the passed file
   the default page style will explicitly be set (on the first document
   paragraph).

 OPTIONS

 -c : set this option if you want to *c*heck the explicit presence of page
      styles in the file, without performing any actual change on it.
'''

# ------------------------------------------------------------------------------
FILE_KO   = '%s does not exist or is not a file.'
FILE_WR   = '%s must be a .odt file.'
FILE_EM   = "No paragraph has been found in this file - It can't be analysed."
FILE_CP   = "File is corrupted: style %s, mentioned in the document's first " \
            "paragraph, does not exist."
NO_MASTER = "The main page style is not explicitly set in this file."
MASTER_OK = 'Page style "%s" is explicitly set, at least on the first page.'
MASTER_NM = 'Page style "%s" is already explicitly set on the first page: ' \
            'there is no need to modify the document.'
MASTER_ST = 'Master page style "%s" explicitly set on the document\'s first ' \
            'paragraph.'

# ------------------------------------------------------------------------------
class Sub:
    '''Checks or updates a sub-pod template'''

    # The regular expression for getting the first paragraph in content.xml,
    # with its style.
    anyG = '(.*?)'
    para = re.compile('<text:p%stext:style-name="%s"' % (anyG, anyG))

    # Template regex representing an ODF style
    style = '<style:style.*?style:name="%s"(.*?)</style:style>'

    # Regex for getting the master page name in a style definition
    master = re.compile('style:master-page-name="%s"' % anyG)

    # Regex for getting the master page definition
    masterDef = re.compile('<style:master-page.*?style:name="%s"' % anyG)

    # The style to generate
    genStyle = '<style:style style:name="%s" style:family="paragraph" ' \
               'style:parent-style-name="%s" style:master-page-name="%s">' \
               '</style:style>'

    # The hook used to inject the new styles in content.xml
    styleHook = '</office:automatic-styles>'

    def __init__(self, path=None, check=None):
        '''Retrieve command-line args. If p_path is passed, command-line args
           are ignored: p_path and p_check are used instead. This allows to use
           this class via another program.'''
        if path:
            self.path = path
            self.check = check
        else:
            # Get options from the command line
            options = {}
            args = sys.argv
            if '-c' in args:
                args.remove('-c')
                self.check = True
            else:
                self.check = False
            if len(args) != 2:
                print(usage)
                sys.exit(1)
            self.path = args[1]
            if not os.path.isfile(self.path):
                print FILE_KO % self.path
                sys.exit(1)
            if not self.path.endswith('.odt'):
                print FILE_WR % self.path
                sys.exit(1)

    def log(self, message):
        '''Logs this p_message'''
        print(message)

    def setNewStyle(self, newName, match):
        '''Return the first para, whose style has been replaced with the new
           one.'''
        anyG = Sub.anyG
        r = Sub.para.pattern.replace(anyG, match.group(1), 1)
        return r.replace(anyG, newName, 1)

    def setMasterStyleName(self, styleName, contentXml, stylesXml):
        '''Sets, to the first paragraph found in p_contentXml, a new style (to
           be created and added in contextXml) that inherits from p_styleName,
           being the style currently applied to this first paragraph. The new
           style must refer to the default page style.'''
        # Read the name of the default page style, as defined in styles.xml
        masterName = Sub.masterDef.search(stylesXml).group(1)
        # Assign the new style to the first para
        newName = '%spod%s' % (styleName, sutils.randomName())
        fun = lambda match: self.setNewStyle(newName, match)
        contentXml = Sub.para.sub(fun, contentXml, count=1)
        # Define the new style and add it to content.xml
        style = Sub.genStyle % (newName, styleName, masterName)
        hook = Sub.styleHook
        contentXml = contentXml.replace(hook, style+hook, 1)
        # Overwrite the file
        f = open(os.path.join(self.tempFolder, 'content.xml'), 'w')
        f.write(contentXml)
        f.close()
        self.log(MASTER_ST % masterName)

    def analyseContent(self, contents):
        '''Analyse the content of p_self.path, whose content of files
           content.xml and styles.xml are in dict p_content.'''
        r = False 
        # Get the first paragraph within content.xml
        contentXml = contents['content.xml']
        stylesXml = contents['styles.xml']
        match = Sub.para.search(contentXml)
        if not match:
            self.log(FILE_EM)
            return r
        # Get the paragraph style
        styleName = match.group(2)
        rexStyle = re.compile(Sub.style % styleName, re.M)
        match = rexStyle.search(contentXml) or rexStyle.search(stylesXml)
        if not match:
            self.log(FILE_CP % styleName)
            return r
        match = Sub.master.search(match.group(1))
        if not match or not match.group(1):
            # No master page is tied to this style
            if self.check:
                # Log a message
                self.log(NO_MASTER)
            else:
                # Create a new style
                self.setMasterStyleName(styleName, contentXml, stylesXml)
                r = True
        else:
            # A master page style is defined
            message = self.check and MASTER_OK or MASTER_NM
            self.log(message % match.group(1))
        return r

    def run(self):
        '''Analyse, and possibly update, the file @p_self.path'''
        # Unzip the file in the temp folder
        tempFolder = self.tempFolder = sutils.getOsTempFolder(sub=True)
        fileName = self.path
        self.tempFolder = tempFolder
        contents = unzip(fileName, tempFolder, odf=True)
        changed = self.analyseContent(contents)
        if changed:
            # Re-zip the result
            zip(fileName, tempFolder, odf=True)
        # Delete the temp folder
        sutils.FolderDeleter.delete(tempFolder)

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    Sub().run()
# ------------------------------------------------------------------------------
