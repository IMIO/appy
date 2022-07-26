# ~license~
# ------------------------------------------------------------------------------
class AppyError(Exception):
    '''Root Appy exception class'''

class ValidationError(AppyError):
    '''Represents an error that occurs on data sent to the Appy server'''

class InternalError(AppyError):
    '''Represents a programming error: something that should never occur'''

class CommercialError(AppyError):
    '''Raised when some functionality is called from the commercial version but
       is available only in the free, open source version.'''
    MSG = 'This feature is not available in the commercial version. It is ' \
          'only available in the free, open source (GPL) version of Appy.'
    def __init__(self): AppyError.__init__(self, self.MSG)
# ------------------------------------------------------------------------------
