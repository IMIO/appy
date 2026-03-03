'''This module contains command-line programs'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import sys, argparse

from appy.model.utils import Object as O

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Program:
    '''Abstract base class for all command-line programs'''

    # The docstring of a Program sub-class will be used as main description for
    # the program and will appear when launching the program with -h or --help
    # option.

    # Similarly, if a Program sub-class defines a string in this variable, it
    # will be shown at the end of the help message.
    epilog = None

    def __init__(self, **kwargs):
        # p_kwargs may be passed, if this program is not called via the
        # command-line, but programmatically.
        if kwargs:
            self.args = O(**kwargs)
        else:
            # Create the argument parser
            sub = self.__class__
            self.parser = argparse.ArgumentParser(description=sub.__doc__,
                                                  epilog=sub.epilog)
            # Define arguments
            self.defineArguments()
            # Parse arguments
            self.args = self.parser.parse_args()
        # Analyse parsed arguments
        self.analyseArguments()

    def defineArguments(self):
        '''Override this method to define arguments to self.parser (using
           method self.parser.add_argument): see documentation for the
           argparse module.'''

    def analyseArguments(self):
        '''Override this method to analyse arguments that were parsed an stored
           in self.args:
           * check their validity;
           * potentially apply some computation on it and store, on p_self, new
             attributes derived from self.args.
           If this method detects an error within self.args, abort program
           execution by calling m_exit (see below).
        '''

    def exit(self, msg, printUsage=True):
        '''Display this p_msg on stderr and exit the program afer an error has
           been encountered.'''
        print(msg, file=sys.stderr)
        if printUsage:
            self.parser.print_usage()
        return sys.exit(1)

    def run(self):
        '''Executes the program after arguments were successfully analysed'''
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
