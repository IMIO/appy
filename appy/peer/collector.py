#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# A collector is a helper class allowing to collect data coming from the request
# in the context of a call to a web service that tries to create an object in
# this Appy site.

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from persistent.list import PersistentList

from .response import Response
from appy.model.fields import Field
from appy.utils import sequenceTypes
from appy.model.utils import Object as O

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
WS        = 'WS create/%s :: '
TITLE_MS  = '%s title is missing.'
TITLE_KO  = '%s title must be a string.'
REQ_NO    = 'Required attribute "%s" is missing or empty.'
REQ_TMM   = 'Attribute "%s" must be a %s but is a %s.'
REQ_DIG   = 'Attribute "%s" must hold a numeric value.'
REQ_DM    = 'Dict attribute %s should contain %d entry(ies); %d entry(ies) ' \
            'found.'
REQ_DWK   = 'Key "%s" not found among dict value for attributre "%s".'
REQ_TKO   = 'Attribute "%s" must contain a %s.'
SUB_KO    = 'Attribute "%s" :: Error :: %s'
REQ_RKO   = 'Ref "%s" :: Wrong value "%s" :: It must be an object iid.'
REQ_RLKO  = 'Ref "%s" :: Wrong value :: A list of object iids is expected.'
REQ_ROKO  = 'Ref "%s" :: IID "%s" does not correspond to an existing %s ' \
            'instance.'
REQ_LKO   = 'Field "%s" :: A list of objects is expected.'
LFE       = 'List field "%s" :: Entry %d '
REQ_LTKO  = f'{LFE}is not an object.'
REQ_LSKO  = f'{LFE}:: Unknown sub-field "%s".'
REQ_LSTKO = f'{LFE}:: Sub-field "%s" has type "%s" but type "%s" is expected.'
REQ_LSM   = f'{LFE}:: Missing value for mandatory sub-field "%s".'

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

    # 1. If an error is detected, it must raise a appy.peer.response.Response
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
        # The dict of parameters that will serve as basis for creating, on this
        # site, the object described by request data.
        self.params = {}
        # The initiator object and field from which the object to create must be
        # created, when relevant. If None, the object will be created as a root
        # object.
        self.initiator = self.initiatorField = None
        # Language for i18n labels to translate
        self.language = tool.config.ui.fallbackLanguage
        # The corresponding Appy class
        self.class_ = tool.model.classes[self.__class__.__name__]

    def getName(self):
        '''The name of a collector is its class name, lowered'''
        return self.__class__.__name__.lower()

    def getAttributeName(self, name, language=None):
        '''Returns this p_name, potentially suffixed with this p_language'''
        r = name
        if language:
            # Incorporate the p_language part into the name of the attribute
            r = f'{r} ({language})'
        return r

    def getRootName(self):
        '''Gets the name of the root collector'''
        parent = self.parent
        return parent.getRootName() if parent else self.getName()

    def error(self, code, text):
        '''Initialises the Response object being in p_self.resp with this error
           p_code and p_text, and raise it.'''
        # Add a prefix to the p_text
        prefix = WS % self.getRootName()
        text = f'{prefix}{text}'
        tool = self.tool
        # Log the error
        tool.log(text, type='warning')
        # Complete the Response object
        resp = self.resp
        resp.code = code
        resp.text = text
        # Raise it
        raise resp

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                             Value scanners
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # "Scanners" are methods that analyse incoming data and raise an error if it
    # detects an error in it. If no error is detected, it returns the valid
    # value.

    def scanRequired(self, name):
        '''Retrieve the value for the required incoming data attribute having
           this p_name.'''
        r = self.req[name]
        if r in Field.nullValues:
            self.error(1, REQ_NO % name)
        return r

    def scanDigit(self, name, value, language=None):
        '''Ensure this string p_value contains only numeric chars'''
        if value.isdigit(): return value
        # Possibly incrust the p_language in the attribute p_name
        name = self.getAttributeName(name, language)
        self.error(5, REQ_DIG % name)

    def scanRich(self, name, value, language=None):
        '''Ensure this string p_value is valid XHTML'''
        field = self.class_.fields[name]
        error = field.validateUniValue(self.tool, value)
        if error:
            name = self.getAttributeName(name, language)
            self.error(1, SUB_KO % (name, error))
        return value

    def scanString(self, name, required=False, subType=None, languages=None):
        '''Retrieve, from incoming data, the value for the attribute having this
           p_name. It must be a string, or, if p_languages is passed, a dict of
           strings keyed by every language from p_languages.'''
        # Manage value mandatoriness
        value = self.scanRequired(name) if required else self.req[name]
        if value is None: return
        # Ensure v_value has the right type
        typE = dict if (languages and len(languages) > 1) else str
        typeV = type(value)
        if typE != typeV:
            message = REQ_TMM % (name, typE.__name__, typeV.__name__)
            self.error(5, message)
        # Manage p_value differently, depending on it being a mono- or multi-
        # language value.
        if isinstance(value, str):
            # p_value is a string
            if subType:
                # Make one more check
                getattr(self, f'scan{subType}')(name, value)
        else:
            # Manage a multi-language, dict p_value. Ensure it contains one key
            # for every language as defined in p_languages.
            if len(languages) != len(value):
                message = REQ_DM % (name, len(languages), len(value))
                self.error(5, message)
            for key in languages:
                if key not in value:
                    # This language is not among p_value
                    self.error(5, REQ_DWK % (key, name))
                if subType:
                    # Make one more check
                    val = value[key]
                    getattr(self, f'scan{subType}')(name, val, language=key)
        return value

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                             Value setters
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # "Setters" are methods that make use of scanners for, finally, storing the
    # valid scanned incoming value in p_self.params, or raising an error.

    def setString(self, name, required=False, subType=None, languages=None):
        '''Stores the value for the incoming string attribute having this
           p_name.'''
        value = self.scanString(name, required, subType, languages)
        # Store it only if not empty
        if value:
            self.params[name] = value

    def setFloat(self, name, required=False):
        '''Stores the value for the incoming float attribute having this
           p_name.'''
        # Manage value mandatoriness
        value = self.scanRequired(name) if required else self.req[name]
        if value is None: return
        # Ensure it is a float
        if not isinstance(value, float):
            self.error(5, REQ_TKO % (name, 'float'))
        self.params[name] = value

    def setSelect(self, name, required=False, multiple=False):
        '''Stores the value for the incoming select attribute having this
           p_name.'''
        # Manage value mandatoriness
        value = self.scanRequired(name) if required else self.req[name]
        if value is None: return
        # Manage v_value validity
        field = self.class_.fields[name]
        error = field.validateValue(self.tool, value)
        if error:
            name = self.getAttributeName(name)
            self.error(1, SUB_KO % (name, error))
        self.params[name] = value

    def setBoolean(self, name):
        '''Stores the value for the incoming boolean attribute having this
           p_name.'''
        value = self.req[name]
        if value is None: return
        # Ensure it is a bool
        if not isinstance(value, bool):
            self.error(5, REQ_TKO % (name, 'bool'))
        self.params[name] = value

    def getTied(self, field, iid):
        '''Get the tied object behind this p_iid'''
        # Raise an error if p_iid does not correspond to a stringified object
        # iid.
        if not isinstance(iid, str) or not iid.isdigit():
            self.error(5, REQ_RKO % (field.name, str(iid)))
        # Try to get the object having this iid
        className = field.class_.meta.name
        r = self.tool.getObject(iid, className=className)
        if not r:
            self.error(5, REQ_ROKO % (field.name, str(iid), className))
        return r

    def setRef(self, name, required=False):
        '''Collect objects mentioned as tied objects via the Ref having this
           p_name, and set them as tied objects for that ref.'''
        # Manage value mandatoriness
        value = self.scanRequired(name) if required else self.req[name]
        if value is None: return
        # Manage mono- or multivalues
        field = self.class_.fields[name]
        if field.isMultiValued():
            # A list of values is expected
            if not isinstance(value, sequenceTypes):
                self.error(5, REQ_RLKO % name)
            value = [self.getTied(field, iid) for iid in value]
        else:
            # A single value is expected, that must be a stringified iid
            value = self.getTied(field, value)
        self.params[name] = value

    def setList(self, name, required=False):
        '''Collect a list of objects and store them as value for the List field
           having this p_name.'''
        # Manage value mandatoriness
        value = self.scanRequired(name) if required else self.req[name]
        if value is None: return
        # A list of values is expected
        if not isinstance(value, sequenceTypes):
            self.error(5, REQ_LKO % name)
        # Walk objects in the list
        field = self.class_.fields[name]
        # Get p_field's sub-fields, as a *d*ict
        fielDs = field.getSubFields(layout='xml', asDict=True)
        i = -1
        for info in value:
            i += 1
            # 1. Ensure p_info is an Object
            if not isinstance(info, O):
                self.error(5, REQ_LTKO % (name, i))
            # 2. Ensure every object attribute corresponds to a sub-field
            for subName, val in info.items():
                subField = fielDs.get(subName)
                if subField is None:
                    self.error(5, REQ_LSKO % (name, i, subName))
                # Finally, ensure each sub-value has the expected type
                subType = subField.pythonType
                if val is not None and type(val) != subType:
                    message = REQ_LSTKO % (name, i, subName,
                                           val.__class__.__name__,
                                           subType.__class__.__name__)
                    self.error(5, message)
            # 3. Ensure every mandatory sub-field has a value in v_info
            for subName, subField in fielDs.items():
                val = info.get(subName)
                if val is None and subField.required:
                    self.error(1, REQ_LSM % (name, i, subName))
        # Fine-tune the p_value to transform it into a perfectly appropriate
        # data structure.
        rowClass = field.rowClass
        if rowClass == O:
            # Simply convert p_value into a persistent list
            r = PersistentList(value)
        else:
            # Each list element must be converted to an instance of v_rowClass
            r = PersistentList()
            for val in value:
                val.__class__ = rowClass
                r.append(val)
        self.params[name] = r

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                        Default collect methods
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Some convenient collect methods are proposed here

    def collectTitle(self):
        '''Collects an object title: most collectors will need it'''
        title = self.req.title
        if not title:
            self.error(1, TITLE_MS % self.__class__.__name__)
        if not isinstance(title, str):
            self.error(1, TITLE_KO % self.__class__.__name__)
        # We have a valid title
        self.params['title'] = title

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                     Trigger collection of values
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def collect(self):
        '''Collects, on p_self, data from the request'''
        # Collect every data part
        for part in self.parts:
            # Collect this p_part
            getattr(self, f'collect{part}')()

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #              Create the object, with all collected values
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def create(self):
        '''Creates, in this Appy site, an object corresponding to data as
           collected in p_self.params.'''
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
