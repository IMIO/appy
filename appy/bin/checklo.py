'''Check the UNO interface to LibreOffice'''

# ------------------------------------------------------------------------------
import os.path, sys, time

import appy
from appy.shared.utils import executeCommand

# ------------------------------------------------------------------------------
usage = '''Usage: python checklo.py [port]

If port is not speficied, it defaults to 2002.'''

# ------------------------------------------------------------------------------
class LoChecker:
    def __init__(self, port):
        self.port = port
        # Get an ODT file from the pod test suite
        self.appyFolder = os.path.dirname(appy.__file__)
        # The path to converter.py
        j = os.path.join
        self.converter = j(self.appyFolder, 'pod', 'converter.py')
        # The path to ODT template in the test suite
        self.templatesFolder = j(self.appyFolder, 'pod', 'test', 'templates')

    def callLo(self, template, format, options=[]):
        '''Call LibreOffice by launching the script converter.py'''
        cmd = ['python3', self.converter, template, format, '-p',
               str(self.port)] + options
        print('Executing command:')
        print(' '.join(cmd))
        executeCommand(cmd)

    def checkRenderPdf(self):
        '''Ask LibreOffice to convert an ODT file to PDF'''
        # Get a simple ODT file from the test suite
        print('CHECK - generate PDF file...')
        odtFile = os.path.join(self.templatesFolder, 'NoPython.odt')
        # Call LibreOffice
        self.callLo(odtFile, 'pdf')
        # Check if the PDF was generated
        pdfFile = '%s.pdf' % os.path.splitext(odtFile)[0]
        if not os.path.exists(pdfFile):
            print('CHECK END - PDF was not generated.')
            return
        else:
            os.remove(pdfFile)
            print('CHECK END - Check successfull.')
            return True

    def checkOptimizeTables(self):
        '''Asks LibreOffice to use its algorithm to optimize table columns'
           widhts and measure time.'''
        start = time.time()
        print('CHECK - Optimize table columns width performance...')
        # Get a ODT file containing lots of tables whose column widths
        odtFile = os.path.join(self.templatesFolder, 'TablesToOptimize.odt')
        # Call LibreOffice
        self.callLo(odtFile, 'odt', ['-o', 'True'])
        res = '%s.res.odt' % os.path.splitext(odtFile)[0]
        print('POD result created@ %s' % res)
        print('CHECK - done in %.2f second(s).' % (time.time() - start))

    def run(self):
        # Check PDF generation (and connection to LO)
        success = self.checkRenderPdf()
        if not success:
            print('Error while contacting LibreOffice.')
            sys.exit(1)
        else:
            # Launch the remaining tests.
            # Check performance of the "optimize tables" functionality
            self.checkOptimizeTables()

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    nbOfArgs = len(sys.argv)
    if nbOfArgs not in (1, 2):
        print(usage)
        sys.exit()
    # Get the nb of args
    port = (nbOfArgs == 2) and int(sys.argv[1]) or 2002
    LoChecker(port).run()
# ------------------------------------------------------------------------------
