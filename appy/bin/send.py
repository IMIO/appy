#!/usr/bin/env python3

'''Sends XML requests to an Appy site'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import os
from pathlib import Path

from appy.bin import Program
from appy.utils import bn
from appy.utils.client import Resource
from appy.utils.string import Variables
from appy.model.utils import Object as O

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
defaultPort = 8000 # Default port for the Appy site to attack

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
HELP_CMD  = 'The command to call on Appy site. It must correspond to the web ' \
            'service relative URL. Examples are: "create/item" or ' \
            '"ask/itemStatus".'

HELP_FILE = 'The complete path name of the xml file to use as data to send ' \
            'via the chosen command. 💡1 Note that the file mentioned in ' \
            'this "-f" option may hold the content of several xml files, in ' \
            'a sequence like this one: XML prologue Carriage return / XML ' \
            'content file 1 / Carriage return / XML prologue / and so on. In ' \
            'that case, a sequence of corresponding requests will be sent to ' \
            'the Appy site. If one of these requests generates an error, the ' \
            'script will stop and will not send any subsequent request. 💡2 ' \
            'If the name of the file contains an asterisc (*), it denotes ' \
            'several files that will be sequentially executed.'

HELP_PORT = f'The port, on localhost, where the Appy site runs. Defaults to ' \
            f'{defaultPort}.'

HELP_LGN  = 'The login to use for accessing the Appy site.'
HELP_PWD  = 'The password to use for accessing the Appy site.'
HELP_TIM  = 'The timeout, in seconds, used when contacting the Appy site.'

HELP_VARS = 'If the xml file passed via option "-f" contains variables (coded '\
            'as names surrounded by pipes), you may specify values for these ' \
            'variables via this "--vars" arg. For example, suppose your xml ' \
            'file contains: <proposingGroup>|proposerId|</proposingGroup>. ' \
            'If you specify "--vars=proposerId=group123", the xml file will ' \
            'be patched to contain <proposingGroup>group123</proposingGroup>.' \
            ' Several variables may be specified and must be separated by ' \
            'commas, like in this example: ' \
            '"--vars=proposerId=group123,categoryId=cat1".'

FILE_NO   = 'Specify a file via option "-f".'
DIR_KO    = 'Folder %s does not exist.'
FILE_KO   = 'File %s does not exist.'
FILES_KO  = 'Mask %s does not match any file.'


HS_CALL   = 'Calling %s...'
HTTP_RSP  = 'HTTP response :: %s %s'
HS_RSP    = 'HS response :: Code %s :: %s'
HS_DATA   = 'HS DATA :: %s'
SUB_MULT  = '%s :: %s requests sent.'
F_MULT    = f'{bn}%d requests were sent from %d input file(s).'
FILE_R    = '%s*** Reading XML request(s) to send from %s...'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Send(Program):
    '''Program allowing to simulate web service calls to Appy site'''

    # Default HTTP headers for a request
    defaultHeaders = {'Content-Type': 'text/xml'}

    # The number of characters read at once in the input file. Indeed, because
    # it may contain a large number of sub-xml files, the input file is not
    # globally loaded in RAM at once.
    CHARS = 10000

    # XML prologue start
    prologue = '<?xml '

    def defineArguments(self):
        '''Define the allowed arguments for this program'''
        parser = self.parser
        add = parser.add_argument
        # Positional arguments
        add('command', help=HELP_CMD)
        # Optional arguments
        add('-f', '--file'     , dest='file'     , help=HELP_FILE)
        add('-p', '--port'     , dest='port'     , help=HELP_PORT)
        add('-l', '--login'    , dest='login'    , help=HELP_LGN)
        add('-w', '--password' , dest='password' , help=HELP_PWD)
        add('-v', '--vars'     , dest='vars'     , help=HELP_VARS)
        add('-t', '--timeout'  , dest='timeout'  , help=HELP_TIM, default=10)

    def getVars(self, variables):
        '''Gets possibly passed variables in an Object instance'''
        if not variables: return
        r = O()
        for part in variables.split(','):
            name, value = part.split('=', 1)
            r[name] = value
        return r

    def analyseFile(self, args):
        '''Analyse the content of the -f arg file and return a tuple of the form
           (Path_folder, s_name).'''
        # Ensure a file has been specified
        spath = args.file
        if not spath:
            self.exit(FILE_NO)
        parts = spath.rsplit(os.sep, 1)
        if len(parts) == 1:
            # A simple file name, without path, has been specified
            folder = Path().resolve()
            name = parts[0]
        else:
            folder, name = parts
            folder = Path(folder)
            if not folder.is_dir():
                self.exit(DIR_KO % folder)
        return folder, name

    def analyseFiles(self, folder, name):
        '''Manages the file(s) behind this p_name'''
        if '*' in name:
            # Several files can be matched
            files = list(folder.glob(name))
            if not files:
                self.exit(FILES_KO % name)
            files.sort()
            self.paths = files
        else:
            # A single file: ensure it exists
            path = folder / name
            if not path.is_file():
                self.exit(FILE_KO % str(path))
            self.paths = [path]

    def analyseArguments(self):
        '''Check and store arguments'''
        args = self.args
        # Get the folder into which the input file(s) lie
        folder, name = self.analyseFile(args)
        # Manage the input file(s) from v_name and initialise p_self.paths, that
        # may contain a list of one or several Path objects, each one
        # representing an input file.
        self.analyseFiles(folder, name)
        # Get variables
        self.vars = self.getVars(args.vars)
        # Get the port
        self.port = int(args.port or defaultPort)
        self.command = args.command
        # Get credentials to connect to the Appy site
        self.login = args.login or 'admin'
        self.password = args.password or 'admin'
        self.timeout = int(args.timeout)
        # A string buffer to store a part of the input file
        self.buffer = ''

    def buildFileContent(self, j=None):
        '''Returns, as a string, the content of p_self.buffer, and empty this
           latter.'''
        # If p_j is specified, the returned string does not contain
        # p_self.buffer[j:], that will stay in p_self.buffer once the operation
        # has been completed.
        r = self.buffer
        if not r: return ''
        if j is None:
            end = '' # Return the whole buffer content
        else:
            end = r[j:]
            r = r[:j]
        # Empty p_self.buffer (or only keep v_end in it)
        self.buffer = end
        return r

    def hasCompleteFile(self):
        '''Do p_self.buffer contain a complete file ?'''
        # If yes, this method returns the index of the last char of the first
        # complete file found in p_self.buffer.
        buffer = self.buffer
        if buffer:
            prolog = self.prologue
            if buffer.startswith(prolog):
                j = buffer.find(prolog, len(prolog))
                if j != -1:
                    return j - 1

    def popFile(self, j):
        '''Pops the first (or unique) complete xml sub-file that currently
           resides in p_self.buffer[:p_j].'''
        # Invariant: p_self.buffer contains a complete xml sub-file, ending at
        # p_self.buffer[j-1].
        r = self.buffer[:j]
        self.buffer = self.buffer[j:]
        return r

    def getNextFileContent(self, f):
        '''Returns the content of the next xml sub-file within the currently
           opened input p_f(ile).'''
        # p_self.buffer may contain at least one complete file. If it is the
        # case, don't read more content from p_f: simply pop the next file from
        # p_self.buffer. It may happen when self.CHARS is big enough and xml
        # files are compact.
        j = self.hasCompleteFile()
        if j:
            return self.popFile(j+1)
        # Read a part of the file
        while True:
            part = f.read(self.CHARS)
            if not part:
                # All the file has been read: return the content of
                # p_self.buffer.
                return self.buildFileContent()
            # Add this p_part in p_self.buffer
            self.buffer = f'{self.buffer}{part}'
            # Is the start of a new file found within this new part ? Don't
            # search at the start of the buffer, in order to avoid finding the
            # first prologue.
            j = self.buffer.find(self.prologue, len(self.prologue))
            if j != -1:
                # Yes! Pop the complete sub-file from p_self.buffer
                return self.buildFileContent(j)

    def do(self):
        '''Calls p_self.command on the Appy site running on
           localhost:<p_self.port>.'''
        # Compute the URL to hit
        url = f'http://localhost:{self.port}/{self.command}'
        # Prepare counts
        counts = O(
          files = 0, # The number of input files
          sent  = 0  # The total number of requests sent to the Appy site, via
                     # all input files.
        )
        # Scan requests to send from potentially multiple input files
        for path in self.paths:
            counts.files += 1
            pre = bn if counts.files > 1 else ''
            print(FILE_R % (pre, path))
            # Read p_path. It may contain several sub-files; Each such sub-xml
            # file is called an "atomic" file.
            f = open(str(path))
            sent = 0 # The number of requests sent via request(s) as found in
                     # v_path.
            while True:
                # Read the content of the next atomic file
                body = self.getNextFileContent(f)
                if not body:
                    # The file@v_path has been entirely read
                    f.close()
                    break
                # Replace variables within v_body when relevant
                if self.vars:
                    # Apply replacements
                    body = Variables.replace(body, self.vars)
                # Call the URL
                print(HS_CALL % url)
                hs = Resource(url, username=self.login, password=self.password,
                              timeout=self.timeout)
                try:
                    r = hs.post(path=url, data=body, encode=None,
                                headers=Send.defaultHeaders)
                    sent += 1
                except Resource.Error as err:
                    return self.exit(str(err), printUsage=False)
                # Print response
                print(HTTP_RSP % (r.code, r.text))
                if r.code == 200:
                    data = r.data
                    print(HS_RSP % (data.code, data.text))
                    if data.data:
                        print(HS_DATA % str(data.data))
                elif r.code == 500:
                    print(HS_RSP % (r.code, r.data))
            # If several requests were sent via p_path, print it
            if sent > 1:
                print(SUB_MULT % (str(path), sent))
            # Update the global count
            counts.sent += sent
        # Print a global count if mor than one input file was read
        if counts.files > 1:
            print(F_MULT % (counts.sent, counts.files))

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
if __name__ == '__main__':
    Send().do()
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
