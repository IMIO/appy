#!/usr/bin/env python3

'''Converts an ODF file into another format by calling LibreOffice in server
   mode.'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import sys
from pathlib import Path

from appy.utils import bn
from appy.bin import Program
from appy.pod.converter import Converter, FILE_TYPES

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
outFormats = ', '.join(FILE_TYPES)
DEF_SV     = 'localhost'
DEF_PORT   = 2002
DEF_CSV    = '59,34,76,1' # Default options when exporting to CSV

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Convert(Program):
    '''Wraps LibreOffice in server mode to perform file conversions'''

    # Help messages
    HELP_P   = 'is the absolute or relative path of the file you want to ' \
               'convert (or whose content like indexes need to be refreshed).' \
               ' Indeed, the input file can be "converted" to an output file ' \
               'having the same format, but whose internals have been ' \
               'modified in some way, like recomputing indexes.'
    HELP_O   = f'can be the output format, that must be one of: {outFormats}' \
               f'or the absolute path to the result file, whose extension ' \
               f'must correspond to a valid output format.'
    HELP_S   = f'The server IP or hostname that runs LibreOffice. Defaults to' \
               f' "{DEF_SV}".'
    HELP_PT  = f'The port on which LibreOffice runs. Defaults to {DEF_PORT}.'
    HELP_TPL = 'The absolute path to a LibreOffice template from which you ' \
               'may import styles.'
    MAN_COLS = 'Set this option to True if you want LibreOffice to %s for ' \
               'all tables included in the document. Alternately, specify a ' \
               'regular expression: only tables whose name match will be ' \
               'processed. And if the expression starts with char "~", only ' \
               'tables not matching it will be processed. WARNING - If, for ' \
               'some table, columns are both required to be optimized ' \
               '(parameter "optimalColumnWidths") and distributed (parameter ' \
               '"distributeColumns", only optimization will take place.'
    HELP_OCW = MAN_COLS % 'optimize column widths'
    HELP_DC  = MAN_COLS % 'distribute columns evenly'
    HELP_RF  = 'Set this option to True if you want LibreOffice to replace ' \
               'the content of fields by their values. It can be useful, for ' \
               'instance, if the POD result must be included in another ' \
               'document, but the total number of pages must be kept as is. ' \
               'Set this option to "PageCount" instead of True to update ' \
               'this field only. Note that field "PageNumber" is never ' \
               'resolved, whatever the value of the option, because its ' \
               'value is different from one page to another.'
    HELP_SCR = 'You can specify here the absolute path to a Python script ' \
               'containing functions that the converter will call in order ' \
               'to customize the process of manipulating the document via ' \
               'the LibreOffice UNO interface. The following functions can ' \
               'be defined in your script and must all accept a single ' \
               'parameter: the Converter instance. -=updateTableOfContents=-,' \
               ' if defined, will be called for producing a custom table of ' \
               'contents. At the time this function is called by the ' \
               'converter, converter.toc will contain the table of contents, ' \
               'already updated by LibreOffice. -=finalize=- will be called ' \
               'at the end of the process, just before saving the result.'
    HELP_V   = 'Writes more information on stdout.'
    PDF_DOC  = 'https://wiki.openoffice.org/wiki/API/Tutorials/PDF_export'
    HELP_PDF = f'If the output format is "pdf", you can define here ' \
               f'conversion options, as a series of comma-separated key=value '\
               f'pairs, as in "ExportNotes=True,PageRange=1-20". Available ' \
               f'options are documented in {PDF_DOC}.'
    CSV_DOC  = 'https://wiki.openoffice.org/wiki/Documentation/DevGuide/' \
               'Spreadsheets/Filter_Options#Filter_Options_for_the_CSV_Filter'
    HELP_CSV = f'If the ouput format is "csv", you can define here conversion '\
               f'options, as a comma-separated list of values. Default ' \
               f'options are: {DEF_CSV}. Values correspond to ASCII codes. ' \
               f'The first one represents the field separator. The most ' \
               f'frequent values are: 59 (the semi-colon ;), 44 (the comma ,) '\
               f'and 9 (a tab). The second value represents the text ' \
               f'delimiter. The most frequent values are: 34 (double quotes), '\
               f'39 (single quotes) or no value at all (as in 59,,76,1). The ' \
               f'third one is the file encoding. The most frequent values are '\
               f'76 (utf-8) and 12 (iso-8859-1). Complete documentation about '\
               f'CSV options can be found at {CSV_DOC}.'
    HELP_PPP = 'Enable the POD post-processor (PPP). The PPP is a series of ' \
               'UNO commands that react to PPP instructions encoded within ' \
               'object names and must be executed at the end of the process, ' \
               'when all other tasks have been performed on the document, ' \
               'just before converting it to another format or saving it to ' \
               'disk or as a stream.'
    HELP_STM = 'By default (stream = "auto"), if you specify "localhost" as ' \
               'server running LibreOffice, the converter and LibreOffice ' \
               'will exchange the input and result files via the disk. If ' \
               'you specify anything else, the converter will consider that ' \
               'LibreOffice runs on a distant server: input and result files ' \
               'will be carried as streams via the network. If you want to ' \
               'bypass this logic and force exchange as streams or files on ' \
               'disk, set this option to "True" for stream or "False" for ' \
               'disk. You may also specify "in" (the input file is streamed ' \
               'and the result is written on disk) or "out" (the input file ' \
               'is read on disk and the result is streamed).'
    HELP_PS =  "Specify an integer number different from 1 and the produced " \
               "document's page numbering will start at this number."

    # Help epilog
    epilog  = f'The Python interpreter running this command must be UNO-' \
              f'enabled (ie, the one being included in the LibreOffice ' \
              f'distribution).{bn}{bn}LibreOffice must be running in server ' \
              f'mode prior to running this command.'

    def defineArguments(self):
        '''Define the allowed arguments for this program'''
        add = self.parser.add_argument
        C = Convert
        # Positional args
        add('path', help=C.HELP_P)
        add('output', help=C.HELP_O)
        # Optional args
        b = {'action': 'store_true'} # For boolean options
        add('-e', '--server', dest='server', default=DEF_SV, help=C.HELP_S)
        add('-p', '--port', dest='port', default=DEF_PORT, type=int,
            help=C.HELP_PT)
        add('-t', '--template', dest='template', help=C.HELP_TPL)
        add('-o', '--optimalColumnWidths', dest='optimalColumnWidths',
            help=C.HELP_OCW)
        add('-d', '--distributeColumns', dest='distributeColumns',
            help=C.HELP_DC)
        add('-r', '--resolveFields', dest='resolveFields', help=C.HELP_RF)
        add('-s', '--script', dest='script', help=C.HELP_SCR)
        add('-v', '--verbose', help=C.HELP_V, **b)
        add('-f', '--pdf', dest='pdf', help=C.HELP_PDF)
        add('-i', '--csv', dest='csv', default=DEF_CSV, help=C.HELP_CSV)
        add('-c', '--ppp', help=C.HELP_PPP, **b)
        add('-a', '--stream', dest='stream', default='auto', help=C.HELP_STM)
        add('-g', '--pageStart', dest='pageStart', default=1, type=int,
            help=C.HELP_PS)

    def toBool(self, value, trueOnly=False):
        '''For some args, p_value may represent a boolean or a string value. If
           p_value represents a boolean value, this method converts it to a real
           bool object.'''
        if value == 'True':
            r = True
        elif not trueOnly and value == 'False':
            r = False
        else:
            r = value
        return r

    def analyseArguments(self):
        '''Checks and stores arguments'''
        # Some args may hold bool or string values. For these args, convert
        # boolean values to real bool objects.
        args = self.args
        toBool = self.toBool
        self.ocw = toBool(args.optimalColumnWidths)
        self.dc = toBool(args.distributeColumns)
        self.rf = toBool(args.resolveFields, trueOnly=True)
        self.stream = toBool(args.stream)

    def run(self):
        '''Create an instance of class Converter to do the job'''
        args = self.args
        converter = Converter(args.path, args.output, args.server, args.port,
          args.template, self.ocw, self.dc, args.script, self.rf, args.pdf,
          args.csv, args.ppp, self.stream, args.pageStart, args.verbose)
        try:
            converter.run()
        except Converter.Error as err:
            sys.stderr.write(str(err))
            sys.stderr.write(bn)
            sys.exit(1)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# The following intermediate method allows to define the script as a
# [console_scripts] entry in setuptools.
def main(): Convert().run()
if __name__ == '__main__': main()
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
