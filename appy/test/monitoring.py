#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.server.status import Status

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Monitoring:
    '''Enables monitoring of a Appy site'''

    # - URL <yourSite>/1/check can be called to get monitoring info

    def __init__(self, ok='OK', ko='KO', forceComplete=False):
        # When returning a success status code, what code to return ?
        self.ok = ok
        # When returning a failure status code, what code to return ?
        self.ko = ko
        # Producing a complete or summarized status depends on request parameter
        # 'all'. That being said, p_forceComplete, if True, forces the
        # production of a complete status.
        self.forceComplete = forceComplete

    def get(self, tool):
        '''Returns status information about the current Appy site'''
        # Return ...
        if 'all' not in tool.req and not self.forceComplete:
            # ... only a status code. Currently, if the server is able to
            # respond, it responds: OK !
            success = True
            return self.ok if success else self.ko
        else:
            # ... complete status information, in XML
            tool.resp.setContentType('xml')
            status = Status(tool)
            # Don't expose the "previous" attribute, useless in this context
            del status.previous
            return status
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
