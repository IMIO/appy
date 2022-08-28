#!/usr/bin/python3

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from pathlib import Path

from appy.bin import Program
from appy.deploy import Deployer

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Deploy(Program):
    '''This program allows to deploy apps in sites on distant servers'''

    # Available commands
    COMMANDS = {'list':    'Lists the available targets.',
                'info':    'Retrieve info about the target OS.',
                'install': 'Install required dependencies via the OS ' \
                           'package system (currently: "apt" only).',
                'site':    'Create an Appy site on the target.',
                'update':  'Updates a site and (re)start it.',
                'view':    "View app.log's tail on the target."
    }

    def helpCommands(COMMANDS):
        '''Builds the text describing available commands'''
        r = []
        # Get the longest command first
        longest = 0
        for command in COMMANDS:
            longest = max(longest, len(command))
        # Dump help about every command
        for command, text in COMMANDS.items():
            r.append('"%s" - %s' % (command.ljust(longest), text))
        return ' -=- '.join(r)

    # Help messages
    HELP_APP     = 'The path, on this machine, to the app to deploy ' \
                   '(automatically set if called from <site>/bin/deploy).'
    HELP_SITE    = 'The path, on this machine, to the reference site ' \
                   '(automatically set if called from <site>/bin/deploy).'
    HELP_COMMAND = 'The command to perform. Available commands are:\n%s' % \
                   helpCommands(COMMANDS)
    HELP_TARGET  = 'The target(s) to deploy to. If not specified, the ' \
                   'default will be chosen. [update command only] You can ' \
                   'specify several targets to deploy at once, using a ' \
                   'comma-separated list of targets containing no space, ie, ' \
                   '"dev,acc,prod". You can also specify term "ALL" to ' \
                   'deploy all available targets at once.'
    HELP_OPTIONS = 'Some commands acccept options. Options must be ' \
                   'specified as a comma-separated list of names. [Options ' \
                   'for command "install"] "lo" (Debian systems only) - ' \
                   'Creates an init script /etc/init.d/lo for running ' \
                   'LibreOffice (LO) in server mode.'
    HELP_BLIND   = '[update command only] If set, when updating several ' \
                   'targets, there is no stop between each one (such stops ' \
                   'allow to consult the target\'s app.log to ensure ' \
                   'everything went well).'

    # Error messages
    FOLDER_KO    = '%s does not exist or is not a folder.'
    COMMAND_KO   = 'Command "%s" does not exist.'

    def defineArguments(self):
        '''Define the allowed arguments for this program'''
        parser = self.parser
        # Positional arguments
        parser.add_argument('app', help=Deploy.HELP_APP)
        parser.add_argument('site', help=Deploy.HELP_SITE)
        parser.add_argument('command', help=Deploy.HELP_COMMAND)
        # Optional arguments
        parser.add_argument('-t', '--target', dest='target',
                            help=Deploy.HELP_TARGET)
        parser.add_argument('-o', '--options', dest='options',
                            help=Deploy.HELP_OPTIONS)
        parser.add_argument('-b', '--blind', dest='blind',
                            help=Deploy.HELP_BLIND, action='store_true')

    def analyseArguments(self):
        '''Check and store arguments'''
        args = self.args
        # Check and get the paths to the app and site
        for name in ('app', 'site'):
            path = Path(getattr(args, name))
            if not path.is_dir():
                self.exit(self.FOLDER_KO % path)
            setattr(self, name, path)
        self.command = args.command
        if self.command not in Deploy.COMMANDS:
            self.exit(self.COMMAND_KO % self.command)
        self.target = args.target
        if args.options:
            self.options = args.options.split(',')
        else:
            self.options = None
        self.blind = args.blind

    def run(self):
        return Deployer(self.app, self.site, self.command, self.target,
                        options=self.options, blind=self.blind).run()

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
if __name__ == '__main__': Deploy().run()
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
