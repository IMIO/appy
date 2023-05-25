'''HTTP communication between peer Appy sites'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import time, random

from appy.peer import importer
from appy.utils.client import Resource
from appy.model.utils import Object as O
from appy.model.utils import notFromPortlet
from appy.peer.unresolved import Unresolved

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
IMPORT_START = 'Importing data from Appy 0 site %s...'
IMPORT_END   = "Done in %.2f''."
RESP_KO      = 'Distant site responded with an error. %s.'
IMPORT_KO    = 'Import aborted.'
IMPORT_404   = '404 on %s.'
ROOT_START   = 'Importing instance(s) of root class "%s"...'
ROOT_RUN     = ' > Reading %d distant "%s" instances...'
ROOT_END     = '%d instance(s) of root class "%s" imported.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Config:
    '''Configuration about peer Appy sites'''

    def __init__(self):
        # Place here an instance of appy.peer.Appy0 if you want to initialise
        # this site with data migrated from a Appy 0.x site.
        self.appy0 = None

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Peer:
    '''Represents a peer Appy site to/from which to communicate, generally via
       HTTP.'''

    # Exception classes
    class NotFound(Exception): pass # 404 error
    class Error(Exception): pass # Any other error code

    # Peer sub-classes may declare an alternate base object importer
    baseImporter = importer.Importer

    # The ID of the tool, in Appy 1, is 'tool'
    distantToolName = 'tool'

    # Symbols used for script output
    printSymbols = ('-', '-', '-', '°', '~', ':')

    # Separator for the object counter. Allows to easily view the counter
    counterSep = '-' * 5

    # Constructor  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def __init__(self, url, login=None, password=None, id=None, name=None,
                 myId=None, myName=None, folder=None, timeout=20):
        # The URL of the distant site
        self.url = url
        # An optional ID for this distant site
        self.id = id or url
        # An optional human-readable name for the distant site
        self.name = name or self.id
        # The ID of the site running this code, as known by peer sites
        self.myId = myId
        # A human-readable name for the site running this code
        self.myName = myName or myId
        # It may be important to know the absolute disk path to the distant site
        # (as a pathlib.Path instance).
        self.folder = folder
        # Attribute "importers" below allows to define specific importer classes
        # for specific Appy classes. When importing some instance, if its local
        # class is mentioned in "importers", it is used. Else, the base importer
        # is used, as set on the Peer's static attribute "baseImporter" (that,
        # itself, may be overridden by a Peer sub-class).
        self.importers = {'User': importer.UserImporter}
        # When importing objects from one site to another, attribute "add" on
        # Ref fields is used to determine if tied objects must be retrieved
        # distantly and localy created (add=True) or simply found and linked
        # (add=False). That being said, it may happen, in the code of an app,
        # that a Ref field is declared to be "add=False,link=False", because
        # every action on the Ref is done programmatically. In that case, if the
        # Ref is composite=True, it will nevertheless be considered as addable.
        # If not, it is not possible to automatically deduce its "addability".
        # If your app uses Refs being "add=False,link=False,composite=False" but
        # are "addable", you must declare them in the following attribute. If
        # you don't do it, those Refs will be considered as not addable. Another
        # tricky case: an autoref being add=False,link=False,composite=True
        # will be considered addable but this could be wrong.
        self.addable = {} # ~{s_className: {s_refFieldName: b_addable}}~
        # ~
        # The following attributes store run-time temporary data structures
        # ~
        # Create the proxy instance representing the distant server. The passed
        # p_timeout, expressed in seconds, will be used for every HTTP request
        # sent to the peer.
        self.server = Resource(url, login, password, timeout=timeout)
        # A temporary dict of local objects, keyed by their IDs on the distant
        # site. This is required to reify links between local objects via Refs.
        self.localObjects = {}
        # Unresolved links between objects (for now on)
        self.unresolved = Unresolved(self)
        # If you let the following attribute empty, instances of all classes
        # considered as root classes will be imported from the distant site. A
        # class is considered being "root" if its name appears in config
        # attribute "config.model.rootClasses" AND if class attribute's
        # "createVia" is not set to standard method
        #
        #                  appy.model.utils.notFromPortlet
        #
        # Indeed, root classes defined with createVia=notFromPortlet are not
        # real root classes: they have been added in config.model.rootClasses
        # to benefit from the portlet's search facilities. If your app does not
        # use method "notFromPortlet" or if you want to tailor the import
        # process, you can bypass this logic and explicitly specify, in the
        # following attribute, names of the root classes for which instances
        # must be imported. Beware: it can lead to problems if, due to this
        # customization, some instances are not imported at all but are
        # mentioned in Refs from other imported objects.
        self.root = None
        # If the names of the distant classes differ from the names of the
        # classes as defined on this site's app, you may specify a name mapping
        # in the following attribute. Any class not found in this dict will be
        # considered to have the same name on both sites.
        self.classNames = {}

    def getInfo(self, check=False):
        '''Info about a Peer instance is made from its self.url, self.id and
           self.name.'''
        r = [self.url]
        for name in ('id', 'name'):
            info = getattr(self, name)
            if info not in r: r.append(info)
        return r[0] if len(r) == 1 else ('%s (%s)' % (r[0], ', '.join(r[1:])))

    def get(self, url=None, params=None, post=False, raiseIfString=True,
            timeout=None):
        '''Sends a HTTP GET request (or POST if p_post is True) to p_url
           (or p_self.url if not given) with p_params.'''
        try:
            if post:
                r = self.server.post(path=url, data=params, timeout=timeout)
            else:
                r = self.server.get(path=url, params=params, timeout=timeout)
        except Resource.Error as re:
            raise self.Error('%s: %s' % (url or self.url, str(re)))
        if r.code == 404:
            raise self.NotFound(r)
        elif r.code != 200:
            raise self.Error(r)
        r = r.data
        if raiseIfString and isinstance(r, str):
            raise self.Error(RESP_KO % r)
        return r

    def getImporter(self, class_):
        '''Returns the importer class being suitable for importing instances of
           this p_class_.'''
        return self.importers.get(class_.name) or self.baseImporter

    def getRootClasses(self, tool):
        '''Returns the names of the root classes for which instances must be
           imported.'''
        # Root classes may be explicitly specified on this Peer instance
        if self.root: return self.root
        r = []
        for class_ in tool.model.getRootClasses():
            # Ignore classes with createVia=notFromPortlet
            if getattr(class_.python, 'createVia', None) == notFromPortlet:
                continue
            r.append(class_.name)
        return r

    def getIdFromUrl(self, url):
        '''Extract the ID of an object from its URL'''
        r = url.rsplit('/', 2)[-2]
        return int(r) if r.isdigit() else r

    def getSearchUrl(self, tool, className):
        '''Return the URL allowing to retrieve URLs of all instances from a
           given p_className on a distant site.'''
        # Get the name of the distant class corresponding to this local
        # p_className.
        distantName = self.classNames.get(className) or className
        return '%s/searchAll?className=%s' % (tool.url, distantName)

    def printSymbol(self, nb, total):
        '''Don't get bored while observing script execution'''
        if (nb % 100) == 0:
            # Every 100 elements, show the current element's p_nb
            r = '%s=%d/%d=%s' % (Peer.counterSep, nb, total, Peer.counterSep)
        else:
            # Print a random char
            r = random.choice(self.printSymbols)
        print(r, end='', flush=True)

    def printInfo(self, info):
        '''Print this p_info'''
        print(info, end='', flush=True)

    def pumpClass(self, tool, className):
        '''Imports all instances from p_className'''
        tool.log(ROOT_START % className)
        # Retrieve the base URL allowing to retrieve URLs of instances of
        # p_className on the distant site.
        searchUrl = self.getSearchUrl(tool, className)
        urls = self.get(searchUrl)
        class_ = tool.model.classes[className]
        importer = self.getImporter(class_)
        counts = O(current=0, created=0)
        total = len(urls)
        tool.log(ROOT_RUN % (total, className))
        for url in urls:
            counts.current += 1
            self.printSymbol(counts.current, total)
            # Get the distant object and its ID
            distant = self.get(url)
            distantId = self.getIdFromUrl(url)
            # Must we really import this object ?
            action, detail = importer.getAction(distant)
            if action != importer.CREATE: continue
            # Create a local object corresponding to the distant one
            id = distantId if importer.mustKeepDistantId(distantId) else None
            o = tool.create(className, id=id, executeMethods=False,
                            indexIt=False)
            # Fill local object's attributes from distant ones
            importer(tool, self, o, distant).run()
            # Add it to the dict of already imported objects
            self.localObjects[distantId] = o
            # Count it
            counts.created += 1
        tool.log(ROOT_END % (counts.created, className))

    def pump(self, tool):
        '''Imports data from a distant site'''
        start = time.time()
        url = self.url
        tool.log(IMPORT_START % url)
        # The starting point of the whole importing process is the tool
        try:
            url = '%s/%s/xml' % (url, self.distantToolName)
            dtool = self.get(url)
            importer = self.getImporter(tool.class_)
            importer(tool, self, tool, dtool,
                     importHistory=False, importLocalRoles=False).run()
            # After the tool and its dependent objects, import root classes and
            # their dependent objects.
            for className in self.getRootClasses(tool):
                self.pumpClass(tool, className)
        except Peer.Error as err:
            tool.log(str(err), type='error')
            tool.log(IMPORT_KO)
        except Peer.NotFound as err:
            tool.log(IMPORT_404 % err, type='error')
        else:
            # Resolve missing links
            self.unresolved.resolve(tool)
            # Perform misc final tasks, like reindexing fields requiring the
            # complete model will all Refs being completely reified.
            tool.log(IMPORT_END % (time.time() - start))
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
