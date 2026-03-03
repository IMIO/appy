# ~license~
# ------------------------------------------------------------------------------
import sys
from optparse import OptionParser

from appy.pod.converter import Converter, FILE_TYPES

# ------------------------------------------------------------------------------
P_ARGS_KO  = 'Wrong number of arguments.'
ERROR_CODE = 1
bn         = '\n'
DEF_SV     = 'localhost'
DEF_PORT   = 2002

# Default options when exporting to CSV
defaultCsvOptions = '59,34,76,1'

# Help messages
HELP_SERVER = 'The server IP or hostname that runs LibreOffice ' \
  '(defaults to "%s").' % DEF_SV
HELP_PORT = "The port on which LibreOffice runs (default is %d)." % DEF_PORT
HELP_TEMPLATE = 'The path to a LibreOffice template from which you may ' \
  'import styles.'
MANAGE_COLUMNS = 'Set this option to "True" if you want LibreOffice to %s ' \
  'for all tables included in the document. Alternately, specify a regular ' \
  'expression: only tables whose name match will be processed. And if the ' \
  'expression starts with char "~", only tables not matching it will be ' \
  'processed. WARNING - If, for some table, columns are both required to be ' \
  'optimized (parameter "optimalColumnWidths") and distributed (parameter ' \
  '"distributeColumns", only optimization will take place.'
HELP_OPTIMAL_COLUMN_WIDTHS = MANAGE_COLUMNS % 'optimize column widths'
HELP_DISTRIBUTE_COLUMNS = MANAGE_COLUMNS % 'distribute columns evenly'
HELP_SCRIPT = 'You can specify here (the absolute path to) a Python script ' \
  'containing functions that the converter will call in order to customize ' \
  'the process of manipulating the document via the LibreOffice UNO ' \
  'interface. The following functions can be defined in your script and must ' \
  'all accept a single parameter: the Converter instance. ' \
  '***updateTableOfContents***, if defined, will be called for producing a ' \
  'custom table of contents. At the time this function is called by the ' \
  'converter, converter.toc will contain the table of contents, already ' \
  'updated by LibreOffice. ***finalize*** will be called at the end of the '\
  'process, just before saving the result.'
HELP_VERBOSE = 'Writes more information on stdout.'
HELP_PPP = 'Enable the POD post-processor (PPP). The PPP is a series of UNO ' \
  'commands that react to PPP instructions encoded within object names and ' \
  'must be executed at the end of the process, when all other tasks have ' \
  'been performed on the document, just before converting it to another ' \
  'format or saving it to disk or as a stream.'
HELP_STREAM = 'By default (stream = "auto"), if you specify "localhost" as ' \
  'server running LibreOffice, the converter and LibreOffice will exchange ' \
  'the input and result files via the disk. If you specify anything else, ' \
  'the converter will consider that LibreOffice runs on a distant server: ' \
  'input and result files will be carried as streams via the network. If you ' \
  'want to bypass this logic and force exchange as streams or files on disk, ' \
  'set this option to "True" for stream or "False" for disk. You may also ' \
  'specify "in" (the input file is streamed and the result is written on ' \
  'disk) or "out" (the input file is read on disk and the result is streamed).'
HELP_PAGE_START = "Specify an integer number different from 1 and the " \
  "produced document's page numbering will start at this number."
HELP_RESOLVE_FIELDS = 'Set this option to "True" if you want LibreOffice to ' \
  'replace the content of fields by their values. It can be useful, for ' \
  'instance, if the POD result must be included in another document, but the ' \
  'total number of pages must be kept as is. Set this option to "PageCount" ' \
  'instead of "True" to update this field only. Note that field "PageNumber" ' \
  'is never resolved, whatever the value of the option, because its value is ' \
  'different from one page to another.'
HELP_PDF_URL = 'https://wiki.openoffice.org/wiki/API/Tutorials/PDF_export'
HELP_PDF = 'If the output format is PDF, you can define here conversion ' \
  'options, as a series of comma-separated key=value pairs, as in ' \
  '"ExportNotes=True,PageRange=1-20". Available options are documented in ' \
  '%s.' % HELP_PDF_URL
HELP_CSV_URL = 'https://wiki.openoffice.org/wiki/Documentation/DevGuide/' \
  'Spreadsheets/Filter_Options#Filter_Options_for_the_CSV_Filter'
HELP_CSV = 'If the ouput format is CSV, you can define here conversion ' \
  'options, as a comma-separated list of values. Default options are: %s.' \
  'Values correspond to ASCII codes. The first one represents the field ' \
  'separator. The most frequent values are: 59 (the semi-colon ;), 44 (the ' \
  'comma ,) and 9 (a tab). The second value represents the text delimiter. ' \
  'The most frequent values are: 34 (double quotes), 39 (single quotes) or ' \
  'no value at all (as in 59,,76,1). The third one is the file encoding. The ' \
  'most frequent values are 76 (UTF-8) and 12 (ISO-8859-1). Complete ' \
  'documentation about CSV options can be found at %s.' % \
  (defaultCsvOptions, HELP_CSV_URL)

# ------------------------------------------------------------------------------
usage = '''usage: python3 converter.py fileToConvert output [options]

   "fileToConvert" is the absolute or relative pathname of the file you
   want to convert (or whose content like indexes need to be refreshed)
   
   "output" can be the output format, that must be one of: %s
            or can be the absolute path to the result file, whose extension must
            correspond to a valid output format.

   "python" should be a UNO-enabled Python interpreter (ie the one which is
   included in the LibreOffice distribution).''' % str(FILE_TYPES.keys())

# ------------------------------------------------------------------------------
class ConverterScript:
    '''The command-line program'''

    # Some PDF options' values must be converted
    pdfOptionsValues = {'true': True, 'True': True,
                        'false': False, 'False': False}

    def getPdfOptions(self, options):
        '''Get and convert PDF options to a dict'''
        if not options: return
        r = {}
        for option in options.split(','):
            if not option: continue
            elems = option.split('=')
            if len(elems) != 2: continue
            key, value = elems
            if not key or not value: continue
            # Convert value when relevant
            if value in self.pdfOptionsValues:
                value = self.pdfOptionsValues[value]
            elif value.isdigit():
                value = int(value)
            # Add the final value to the result
            r[key] = value
        return r

    def run(self):
        optParser = OptionParser(usage=usage)
        add = optParser.add_option
        add('-e', '--server', dest='server', default=DEF_SV,
            metavar='SERVER', type='string', help=HELP_SERVER)
        add('-p', '--port', dest='port', default=DEF_PORT,
            metavar='PORT', type='int', help=HELP_PORT)
        add('-t', '--template', dest='template', default=None,
            metavar='TEMPLATE', type='string', help=HELP_TEMPLATE)
        add('-o', '--optimalColumnWidths', dest='optimalColumnWidths',
            default=None, metavar='OPTIMAL_COL_WIDTHS', type='string',
            help=HELP_OPTIMAL_COLUMN_WIDTHS)
        add('-d', '--distributeColumns', dest='distributeColumns',
            default=None, metavar='DISTRIBUTE_COLUMNS', type='string',
            help=HELP_DISTRIBUTE_COLUMNS)
        add('-r', '--resolveFields', dest='resolveFields', default=None,
            metavar='RESOLVE_FIELDS', type='string', help=HELP_RESOLVE_FIELDS)
        add('-s', '--script', dest='script', default=None, metavar='SCRIPT',
            type='string', help=HELP_SCRIPT)
        add('-v', '--verbose', action='store_true', help=HELP_VERBOSE)
        add('-f', '--pdf', dest='pdf', default=None, metavar='PDF_OPTIONS',
            type='string', help=HELP_PDF)
        add('-i', '--csv', dest='csv', default=defaultCsvOptions,
            metavar='CSV_OPTIONS', type='string', help=HELP_CSV)
        add('-c', '--ppp', action='store_true', help=HELP_PPP)
        add('-a', '--stream', dest='stream', default='auto',
            metavar='STREAM', type='string', help=HELP_STREAM)
        add('-g', '--pageStart', dest='pageStart', default=1,
            metavar='PAGESTART', type='int', help=HELP_PAGE_START)
        options, args = optParser.parse_args()
        if len(args) != 2:
            sys.stderr.write(P_ARGS_KO)
            sys.stderr.write(bn)
            optParser.print_help()
            sys.exit(ERROR_CODE)
        # Apply relevant type conversions to options
        optimize = options.optimalColumnWidths
        if optimize in ('True', 'False'): optimize = eval(optimize)
        distribute = options.distributeColumns
        if distribute in ('True', 'False'): distribute = eval(distribute)
        resolveFields = options.resolveFields
        if resolveFields == 'True': resolveFields = True
        pdfOptions = self.getPdfOptions(options.pdf)
        stream = options.stream
        if stream in ('True', 'False'): stream = eval(stream)
        converter = Converter(args[0], args[1], options.server, options.port,
          options.template, optimize, distribute, options.script, resolveFields,
          pdfOptions, options.csv, options.ppp, stream, options.pageStart,
          options.verbose)
        try:
            converter.run()
        except Converter.Error:
            e = sys.exc_info()[1]
            sys.stderr.write(str(e))
            sys.stderr.write(bn)
            optParser.print_help()
            sys.exit(ERROR_CODE)

# ------------------------------------------------------------------------------
# The following intermediate method allows to define the script as a
# [console_scripts] entry in setuptools.
def main(): ConverterScript().run()
if __name__ == '__main__': main()
# ------------------------------------------------------------------------------
