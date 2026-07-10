#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Response(Exception):
    '''An XML-marshalled instance of this class may be returned to peer sites'''

    # While class Response from appy/server/response.py represents an HTTP-level
    # response, the current Response class (from appy/peer/response.py)
    # represents a logical standardized response that can be marshalled as data
    # in the HTTP response as transmitted to peer sites, mainly in response to a
    # service that tries to create or update data.

    # Class Response inherits from class Exception, because an instance of it
    # can be raised when an error occurs.

    def __init__(self, tool, rootTag='Response'):
        '''Create a Response object and configures the low-level HTTP Appy
           Response object.'''
        #
        # 1. Configure the low-level Appy response
        #
        # Declare XML as return format
        resp = tool.resp
        resp.setContentType('xml')
        # The name of the root tag
        resp.rootTag = rootTag
        #
        # 2. Configure p_self
        #
        # An integer code. Possible values are the following. Any value >=1
        # represents an error. Not to be confused with the HTTP response code:
        # the code here represents a logical, app-related code.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  0  | The operation was successful.
        # -1  | The operation succeeded, but ended with some problem / warning.
        #  1  | Incoming data is incomplete, invalid and/or corrupted.
        #  2  | Object not found (but should exist).
        #  3  | Object in wrong state.
        #  4  | Object exists, but should not.
        #  5  | Unrecognized attribute value.
        #  6  | Fatal error.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.code = 0
        # Textual details about the code
        self.text = 'Success'
        # If structured data is to be returned by HubSessions, it will be stored
        # in attribute "data".
        self.data = None

    def get(self, tool, code=None, text=None, data=None, commit=False):
        '''Return the response. If not done before, sets, if passed, attributes
           p_code, p_text and/or p_data.'''
        # Set p_self's attributes if not done yet
        if code is not None:
            self.code = code
        if text:
            self.text = text
        if data:
            self.data = data
        # Commit the transaction if appropriate
        if commit:
            tool.H().commit = True
        return self
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
