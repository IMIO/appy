#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# A collector is a helper class allowing to collect data coming from the request
# in the context of a call to a web service that tries to create an object in
# this Appy site.

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from .response import Response

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
WS        = 'WS create/%s :: '
TITLE_MS  = '%s title is missing.'
TITLE_KO  = '%s title must be a string.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Collector:
    '''Collects data coming from the request'''

    # "Collecting" refers to the process of retrieving, on the request, data
    # related to an object to create, and filling dict "params" from it (or
    # generating an error if data is missing or invalid).

    # This is an abstract collector. Every concrete collector must have the same
    # name as the Appy class for which it collects data.

    # Every sub-class must define logical parts of data to collect from the
    # request. Moreover, every part must correspond to a method named
    # "collect<part>" on the concrete collector. Here are the responsibilities
    # of every such method.

    # 1. If an error is detected, it must return a appy.peer.response.Response
    #    object initialised with the corresponding error, which can be easily
    #    done by calling method Collector.error.

    # 2. When collection produces no error, dict Collector.params must be
    #    updated with the collected field value(s), that will be used to create
    #    the corresponding Appy object.

    parts = ()

    def __init__(self, tool, req=None, resp=None, parent=None):
        self.tool = tool
        self.req = req or tool.req
        # Already prepare a Response object
        self.resp = resp or Response(tool)
        # This collector may be called by a p_parent collector
        self.parent = parent
        # The dict of parameters that will serve as basis for creating, within
        # HubSessions, the object described by request data.
        self.params = {}
        # The initiator object and field from which the object to create must be
        # created, when relevant. If None, the object will be created as a root
        # object.
        self.initiator = self.initiatorField = None
        # Language for i18n labels to translate
        self.language = tool.config.ui.fallbackLanguage

    def getName(self):
        '''The name of a collector is its class name, lowered'''
        return self.__class__.__name__.lower()

    def getRootName(self):
        '''Gets the name of the root collector'''
        parent = self.parent
        return parent.getRootName() if parent else self.getName()

    def error(self, code, text):
        '''Returns a Response object initialized with the error having this
           p_code and p_text.'''
        # Add a prefix to the p_text
        prefix = WS % self.getRootName()
        text = f'{prefix}{text}'
        tool = self.tool
        # Log the error and return it to the caller
        tool.log(text, type='warning')
        return self.resp.get(tool, code, text)

    def collectTitle(self):
        '''Collects an object title: most collectors will need it'''
        title = self.req.title
        if not title:
            return self.error(1, TITLE_MS % self.__class__.__name__)
        if not isinstance(title, str):
            return self.error(1, TITLE_KO % self.__class__.__name__)
        # We have a valid title
        self.params['title'] = title

    def collect(self):
        '''Collects, on p_self, data from the request'''
        # Collect every data part
        for part in self.parts:
            # Collect this p_part
            resp = getattr(self, f'collect{part}')()
            if resp: return resp

    def create(self):
        '''Creates, in HubSessions, an object corresponding to data as collected
           in p_self.params.'''
        tool = self.tool
        text = tool.translate('peer_created', language=self.language)
        # Must a root object be created, or an object tied to another one ?
        initiator = self.initiator
        if initiator:
            name = self.initiatorField.name
        else:
            initiator = tool
            name = self.__class__.__name__
        return initiator.create(name, initialComment=text, **self.params)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
