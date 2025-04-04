# -*- coding: utf-8 -*-
# ~license~
# ------------------------------------------------------------------------------
import xml.sax, difflib, types, cgi, datetime, os.path, re
from xml.parsers.expat import XML_PARAM_ENTITY_PARSING_NEVER
from xml.sax.handler import ContentHandler, ErrorHandler, feature_external_ges
from xml.sax.xmlreader import InputSource
from xml.sax import SAXParseException

from appy.shared import UnicodeBuffer
from appy.shared.errors import AppyError
from appy.shared.utils import sequenceTypes

# Constants --------------------------------------------------------------------
xmlPrologue = '<?xml version="1.0" encoding="utf-8" ?>\n'
xhtmlPrologue = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" '\
                '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n'

CONVERSION_ERROR = '"%s" value "%s" could not be converted by the XML ' \
                   'unmarshaller.'
CUSTOM_CONVERSION_ERROR = 'Custom converter for "%s" values produced an ' \
                          'error while converting value "%s". %s'
XML_ENTITIES = {'lt': '<', 'gt': '>', 'amp': '&', 'quot': '"', 'apos': "'"}
HTML_ENTITIES = {
        'iexcl': '¡',  'cent': '¢', 'pound': '£', 'curren': '€', 'yen': '¥',
        'brvbar': 'Š', 'sect': '§', 'uml': '¨', 'copy':'©', 'ordf':'ª',
        'laquo':'«', 'not':'¬', 'shy':'­', 'reg':'®', 'macr':'¯', 'deg':'°',
        'plusmn':'±', 'sup2':'²', 'sup3':'³', 'acute':'Ž',
        'micro':'µ', 'para':'¶', 'middot':'·', 'cedil':'ž', 'sup1':'¹',
        'ordm':'º', 'raquo':'»', 'frac14':'Œ', 'frac12':'œ', 'frac34':'Ÿ',
        'iquest':'¿', 'Agrave':'À', 'Aacute':'Á', 'Acirc':'Â', 'Atilde':'Ã',
        'Auml':'Ä', 'Aring':'Å', 'AElig':'Æ', 'Ccedil':'Ç', 'Egrave':'È',
        'Eacute':'É', 'Ecirc':'Ê', 'Euml':'Ë', 'Igrave':'Ì', 'Iacute':'Í',
        'Icirc':'Î', 'Iuml':'Ï', 'ETH':'Ð', 'Ntilde':'Ñ', 'Ograve':'Ò',
        'Oacute':'Ó', 'Ocirc':'Ó', 'Otilde':'Õ', 'Ouml':'Ö', 'times':'×',
        'Oslash':'Ø', 'Ugrave':'Ù', 'Uacute':'Ú', 'Ucirc':'Û', 'Uuml':'Ü',
        'Yacute':'Ý', 'THORN':'Þ', 'szlig':'ß', 'agrave':'à', 'aacute':'á',
        'acirc':'â', 'atilde':'ã', 'auml':'ä', 'aring':'å', 'aelig':'æ',
        'ccedil':'ç', 'egrave':'è', 'eacute':'é', 'ecirc':'ê', 'euml':'ë',
        'igrave':'ì', 'iacute':'í', 'icirc':'î', 'iuml':'ï', 'eth':'ð',
        'ntilde':'ñ', 'ograve':'ò', 'oacute':'ó', 'ocirc':'ô', 'otilde':'õ',
        'ouml':'ö', 'divide':'÷', 'oslash':'ø', 'ugrave':'ù', 'uacute':'ú',
        'ucirc':'û', 'uuml':'ü', 'yacute':'ý', 'thorn':'þ', 'yuml':'ÿ',
        'euro':'€', 'nbsp':' ', "rsquo":"'", "lsquo":"'", "ldquo":"'",
        "rdquo":"'", 'ndash': '—', 'mdash': '—', 'oelig':'oe', 'quot': "'",
        'mu': 'µ'}
import htmlentitydefs
for k, v in htmlentitydefs.entitydefs.iteritems():
    if not HTML_ENTITIES.has_key(k) and not XML_ENTITIES.has_key(k):
        HTML_ENTITIES[k] = ''

class Escape:
    '''Escapes XML chars within strings'''
    # Escaping consists in replacing special chars used by the XML language by
    # replacement entities that can be used in the content of XML tags and
    # attributes. This class does it for various XML flavours:
    # --------------------------------------------------------------------------
    #   "odf"    | Open Document Format - The XML format for LibreOffice files
    #  "xhtml"   | The XML-compliant version of HTML
    #   "xml"    | Any other XML flavour
    # --------------------------------------------------------------------------
    # Base chars to escape
    chars = '<>&"'
    # For some XML flavours we escape "blanks" as well
    blanks = '\n\t\r'
    # Base regular expression matching these chars
    rex = re.compile('[%s]' % chars)
    # Regular expression also matching the single quote (less used)
    rexApos = re.compile("[%s']" % chars)
    # Regular expression also matching carriage returns and tabs (= "blanks")
    rexBlanks = re.compile('[%s%s]' % (chars, blanks))
    rexBlanksApos = re.compile("[%s'%s]" % (chars, blanks))
    # All regular expressions, grouped by flavour and 'apos' escaping or not
    nonXmlRex = { False: rexBlanks, True: rexBlanksApos }
    rexAll = {'xml'   : { False: rex, True: rexApos },
              'odf'   : nonXmlRex,
              'odf*'  : nonXmlRex,
              'xhtml' : nonXmlRex,
              'xhtml*': nonXmlRex}
    # Entities to use to escape base chars
    entities = {'<':'&lt;', '>':'&gt;', '&':'&amp;', '"':'&quot;', "'":'&apos;'}
    # For "odf" and "xhtml" flavours, we replace "blank" chars with their
    # counterparts in these flavours as well.
    values = {
     # While using an additional "text:tab" when replacing "\n" chars for
     # conversion to ODF solves problems with justified text, it causes problems
     # when converting the result to Microsoft Word. This is why there are 2
     # possibilities for ODF.
     'odf': {'\n':'<text:line-break/>', '\t':'<text:tab/>', '\r':''},
     'odf*':{'\n':'<text:tab/><text:line-break/>', '\t':'<text:tab/>', '\r':''},
     'xhtml': {'\n':'<br/>', '\t':'', '\r':''},
     'xhtml*': {'\n':'</p><p>', '\t':'', '\r':''},
     'xml': {} # We do not escape blanks by default
    }
    # Complete "values" with entities
    for value in values.itervalues(): value.update(entities)

    @staticmethod
    def xml(s, flavour='xml', escapeApos=False):
        '''Returns p_s, whose XML special chars have been replaced with XML
           entities. You can perform escaping for a specific XML flavour: "odf"
           or "xhtml" (see doc in class Escape) or use the default flavour
           "xml".

           Most of the time, we do not escape 'apos' (there is no particular
           need for that), excepted if p_escapeApos is True.'''
        # Choose the regular expression to use depending on parameters
        rex = Escape.rexAll[flavour][escapeApos]
        # Define the function to use to choose the replacement value depending
        # on the matched char.
        fun = lambda match: Escape.values[flavour][match.group(0)]
        # Apply it
        return rex.sub(fun, s)

    @staticmethod
    def xhtml(s, p=False):
        '''Shorthand for escaping XHTML content'''
        # If p_p is False, \n are replaced with <br/> tags. Else, every
        # encountered \n leads to the creation of a new paragraph, surrounded by
        # <p></p>.
        suffix = p and '*' or ''
        r = Escape.xml(s, flavour='xhtml%s' % suffix)
        return p and ('<p>%s</p>' % r) or r

# ------------------------------------------------------------------------------
class XmlElement:
    '''Represents an XML tag.'''
    def __init__(self, elem, attrs=None, nsUri=None, parent=None):
        '''An XmlElement instance may represent:
           - an already parsed tag (in this case, p_elem may be prefixed with a
             namespace);
           - the definition of an XML element (in this case, no namespace can be
             found in p_elem; but a namespace URI may be defined in p_nsUri).'''
        self.elem = elem
        self.attrs = attrs
        if elem.find(':') != -1:
            self.ns, self.name = elem.split(':')
        else:
            self.ns = ''
            self.name = elem
            self.nsUri = nsUri
        self.parent = parent # The parent element

    def equalsTo(self, other, namespaces=None):
        '''Does p_elem == p_other? If a p_namespaces dict is given, p_other must
           define a nsUri.'''
        res = None
        if namespaces:
            res = self.elem == ('%s:%s' % (namespaces[other.nsUri], other.name))
        else:
            res = self.elem == other.elem
        return res

    def __repr__(self):
        res = self.elem
        if self.attrs:
            res += '[%s]' % ', '.join(['%s="%s"' % (k, v) \
                                      for k, v in self.attrs.items()])
        return res

    def getFullName(self, namespaces=None):
        '''Gets the name of the element including the namespace prefix.'''
        if not namespaces:
            res = self.elem
        else:
            res = '%s:%s' % (namespaces[self.nsUri], self.name)
        return res

class XmlEnvironment:
    '''An XML environment remembers a series of elements during a SAX parsing.
       This class is an abstract class that gathers basic things like
       namespaces.'''
    def __init__(self):
        # This dict contains the xml namespace declarations encountered so far
        self.namespaces = {} # ~{s_namespaceUri:s_namespaceName}~
        self.currentElem = None # The currently parsed element
        self.parser = None

    def manageNamespaces(self, attrs):
        '''Manages namespaces definitions encountered in p_attrs'''
        for attrName, attrValue in attrs.items():
            if attrName.startswith('xmlns:'):
                self.namespaces[attrValue] = attrName[6:]

    def ns(self, nsUri):
        '''Returns the namespace corresponding to o_nsUri'''
        return self.namespaces[nsUri]

class XmlParser(ContentHandler, ErrorHandler):
    '''Basic expat-based XML parser that does things like:
      - managing the stack of currently parsed elements;
      - managing namespace declarations.
      This parser also knows about HTML entities.'''

    def __init__(self, env=None, caller=None, raiseOnError=True):
        '''p_env should be an instance of a class that inherits from
           XmlEnvironment: it specifies the environment to use for this SAX
           parser.'''
        ContentHandler.__init__(self)
        env = env or XmlEnvironment()
        self.env = env
        self.env.parser = self
        # The class calling this parser
        self.caller = caller
        # Fast, standard expat parser
        self.parser = xml.sax.make_parser()
        # The result of parsing
        self.res = None
        # Raise or not an error when a parsing error is encountered
        self.raiseOnError = raiseOnError

    # ContentHandler methods ---------------------------------------------------
    def startDocument(self):
        parser = self.parser._parser
        parser.UseForeignDTD(True)
        parser.SetParamEntityParsing(XML_PARAM_ENTITY_PARSING_NEVER)

    def setDocumentLocator(self, locator):
        self.locator = locator
        return self.env

    def endDocument(self): return self.env

    def startElement(self, elem, attrs):
        env = self.env
        env.manageNamespaces(attrs)
        # Replace the current elem (or not if this is the root tag) by a
        # fresh XmlElement instance.
        env.currentElem = XmlElement(elem, attrs=attrs, parent=env.currentElem)
        return env

    def endElement(self, elem):
        '''Pops the currently walked elem'''
        env = self.env
        env.currentElem = env.currentElem.parent
        return env

    def characters(self, content): return self.env

    def skippedEntity(self, name):
        '''This method is called every time expat does not recognize an entity.
           We provide here support for HTML entities.'''
        if HTML_ENTITIES.has_key(name):
            self.characters(HTML_ENTITIES[name].decode('utf-8'))
        else:
            # Put a question mark instead of raising an exception.
            self.characters('?')

    # ErrorHandler methods ---------------------------------------------------
    def error(self, error):
        if self.raiseOnError: raise error
        else: print('SAX error %s' % str(error))

    def fatalError(self, error):
        if self.raiseOnError: raise error
        else:
            print('SAX fatal error %s on XML:' % str(error))
            #print(self._xml)

    def warning(self, error): pass

    def parse(self, xml, source='string'):
        '''Parses a XML stream.
           * If p_source is "string", p_xml must be a string containing
             valid XML content.
           * If p_source is "file": p_xml can be:
             - a string containing the path to the XML file on disk;
             - a file instance opened for reading. Note that in this case, this
               method will close it.
        '''
        try:
            from cStringIO import StringIO
        except ImportError:
            from StringIO import StringIO
        self._xml = xml
        self.parser.setContentHandler(self)
        self.parser.setErrorHandler(self)
        self.parser.setFeature(feature_external_ges, False)
        inputSource = InputSource()
        if source == 'string':
            inputSource.setByteStream(StringIO(xml))
        else:
            if not isinstance(xml, file):
                xml = file(xml)
            inputSource.setByteStream(xml)
        self.parser.parse(inputSource)
        if isinstance(xml, file): xml.close()
        return self.res

# ------------------------------------------------------------------------------
from appy.shared import UnmarshalledFile
from appy import Object
try:
    from DateTime import DateTime
except ImportError:
    DateTime = 'unicode'

class XmlUnmarshaller(XmlParser):
    '''This class allows to parse a XML file and recreate the corresponding web
       of Python objects. This parser assumes that the XML file respects this
       convention: any tag may define in attribute "type" storing the type of
       its content, which may be:
       
       bool * int * float * long * datetime * DateTime * tuple * list * object

       If "object" is specified, it means that the tag contains sub-tags, each
       one corresponding to the value of an attribute for this object.
       if "tuple" is specified, it will be converted to a list.'''
    def __init__(self, classes={}, tagTypes={}, conversionFunctions={},
                 contentAttributes={}, utf8=True):
        XmlParser.__init__(self)
        # self.classes below is a dict whose keys are tag names and values are
        # Python classes. During the unmarshalling process, when an object is
        # encountered, instead of creating an instance of Object, we will create
        # an instance of the class specified in self.classes.
        # Root tag is named "xmlPythonData" by default by the XmlMarshaller.
        # This will not work if the object in the specified tag is not an
        # Object instance (ie it is a list or tuple or simple value). Note that
        # we will not call the constructor of the specified class. We will
        # simply create an instance of Objects and dynamically change the class
        # of the created instance to this class.
        if not isinstance(classes, dict) and classes:
            # The user may only need to define a class for the root tag
            self.classes = {'xmlPythonData': classes}
        else:
            self.classes = classes
        # We expect that the parsed XML file will follow some conventions
        # (ie, a tag that corresponds to a list has attribute type="list" or a
        # tag that corresponds to an object has attribute type="object".). If
        # it is not the case of p_xmlContent, you can provide the missing type
        # information in p_tagTypes. Here is an example of p_tagTypes:
        # {"information": "list", "days": "list", "person": "object"}.
        self.tagTypes = tagTypes
        # The parser assumes that data is represented in some standard way. If
        # it is not the case, you may provide, in this dict, custom functions
        # allowing to convert values of basic types (long, float, datetime...).
        # Every such function must take a single arg which is the value to
        # convert and return the converted value. Dict keys are strings
        # representing types ('bool', 'int', 'unicode', etc) and dict values are
        # conversion functions. Here is an example:
        # {'int': convertInteger, 'DateTime': convertDate}
        # NOTE: you can even invent a new basic type, put it in self.tagTypes,
        # and create a specific conversionFunction for it. This way, you can
        # for example convert strings that have specific values (in this case,
        # knowing that the value is a 'string' is not sufficient).        
        self.conversionFunctions = conversionFunctions
        # If you have the special case of a tag whose type is "object" and that
        # has direct text content, you can specify, in attribute
        # "contentAttributes", the name of the attribute onto which this content
        # will be stored. For example, suppose you have:
        #   <parent><child attr1="a1" attr2="a2">c1</child></parent>
        # If you specify:
        #   tagTypes={'child': 'object'}
        #   contentAttributes={'child': 'content'}
        # you will get, for "child", an object
        #   O(attr1='a1', attr2='a2', content='c1')
        self.contentAttributes = contentAttributes
        self.utf8 = utf8
        # Remember the name of the root tag
        self.rootTag = None

    def encode(self, value):
        '''Depending on self.utf8 we may need to encode p_value.'''
        if self.utf8: return value
        return value.encode('utf-8')

    def convertAttrs(self, attrs):
        '''Converts XML attrs to a dict.'''
        res = {}
        for k, v in attrs.items():
            if ':' in k: # An attr prefixed with a namespace. Remove this.
                k = k.split(':')[-1]
            res[str(k)] = self.encode(v)
        return res

    def getDatetime(self, value):
        '''From string vaue p_value representing a date, produce a
           datetime.datime instance.'''
        res = value.split()
        # First part should be the date part
        year, month, day = res[0].split('/')
        return datetime.datetime(int(year), int(month), int(day))

    def startDocument(self):
        XmlParser.startDocument(self)
        self.res = None # The resulting web of Python objects (Object instances)
        self.env.containerStack = [] # The stack of current "containers" where
        # to store the next parsed element. A container can be a list, a tuple,
        # an object (the root object of the whole web or a sub-object).
        self.env.currentBasicType = None # Will hold the name of the currently
        # parsed basic type (unicode, float...)
        self.env.currentContent = '' # We store here the content of tags

    containerTags = ('tuple', 'list', 'dict', 'object', 'file')
    numericTypes = ('bool', 'int', 'float', 'long')
    def startElement(self, elem, attrs):
        # Remember the name of the previous element
        previousElem = None
        if self.env.currentElem:
            previousElem = self.env.currentElem.name
        else:
            # We are walking the root tag
            self.rootTag = elem
        e = XmlParser.startElement(self, elem, attrs)
        # Determine the type of the element
        elemType = 'unicode' # Default value
        if attrs.has_key('type'):
            elemType = attrs['type']
        elif self.tagTypes.has_key(elem):
            elemType = self.tagTypes[elem]
        if elemType in self.containerTags:
            # I must create a new container object
            if elemType == 'object':
                newObject = Object(**self.convertAttrs(attrs))
            elif elemType == 'tuple': newObject = [] # Tuples become lists
            elif elemType == 'list': newObject = []
            elif elemType == 'dict': newObject = {}
            elif elemType == 'file':
                newObject = UnmarshalledFile()
                if attrs.has_key('name'):
                    newObject.name = self.encode(attrs['name'])
                if attrs.has_key('mimeType'):
                    newObject.mimeType = self.encode(attrs['mimeType'])
            else: newObject = Object(**self.convertAttrs(attrs))
            # Store the value on the last container, or on the root object.
            self.storeValue(elem, newObject)
            # Push the new object on the container stack
            e.containerStack.append(newObject)
        else:
            # If we are already parsing a basic type, it means that we were
            # wrong for our diagnotsic of the containing element: it was not
            # basic. We will make the assumption that the containing element is
            # then an object.
            if e.currentBasicType:
                # Previous elem was an object: create it on the stack.
                newObject = Object()
                self.storeValue(previousElem, newObject)
                e.containerStack.append(newObject)
            e.currentBasicType = elemType

    def storeValue(self, name, value):
        '''Stores the newly parsed p_value (contained in tag p_name) on the
           current container in environment self.env.'''
        e = self.env
        # Remove namespace prefix when relevant
        if ':' in name: name = name.split(':')[-1]
        # Change the class of the value if relevant
        if (name in self.classes) and isinstance(value, Object):
            value.__class__ = self.classes[name]
        # Where must I store this value?
        if not e.containerStack:
            # I store the object at the root of the web
            self.res = value
        else:
            currentContainer = e.containerStack[-1]
            if isinstance(currentContainer, list):
                currentContainer.append(value)
            elif isinstance(currentContainer, dict):
                # If the current container is a dict, it means that p_value is
                # a dict entry object named "entry" by convention and having
                # attributes "k" and "v" that store, respectively, the key and
                # the value of the entry. But this object is under construction:
                # at this time, attributes "k" and "v" are not created yet. We
                # will act in m_endElement, when the object will be finalized.
                pass
            elif isinstance(currentContainer, UnmarshalledFile):
                val = value or ''
                currentContainer.content += val
                currentContainer.size += len(val)
            else:
                # Current container is an object
                if hasattr(currentContainer, name) and \
                   getattr(currentContainer, name):
                    # We have already encountered a sub-object with this name.
                    # Having several sub-objects with the same name, we will
                    # create a list.
                    attrValue = getattr(currentContainer, name)
                    if not isinstance(attrValue, list):
                        attrValue = [attrValue, value]
                    else:
                        attrValue.append(value)
                else:
                    attrValue = value
                setattr(currentContainer, name, attrValue)

    def characters(self, content):
        content = self.encode(content)
        e = XmlParser.characters(self, content)
        if e.currentBasicType:
            e.currentContent += content
        elif e.currentElem.name in self.contentAttributes:
            # Store p_content in attribute named according to
            # p_self.contentAttributes on the current object.
            name = self.contentAttributes[e.currentElem.name]
            current = e.containerStack[-1]
            if hasattr(current, name):
                setattr(current, name, getattr(current, name) + content)
            else:
                setattr(current, name, content)

    def endElement(self, elem):
        e = XmlParser.endElement(self, elem)
        if e.currentBasicType:
            value = e.currentContent.strip()
            if not value: value = None
            else:
                # If we have a custom converter for values of this type, use it.
                if self.conversionFunctions.has_key(e.currentBasicType):
                    try:
                        value = self.conversionFunctions[e.currentBasicType](
                            value)
                    except Exception, err:
                        raise AppyError(CUSTOM_CONVERSION_ERROR % (
                            e.currentBasicType, value, str(err)))
                # If not, try a standard conversion
                elif e.currentBasicType in self.numericTypes:
                    try:
                        exec 'value = %s' % value
                    except SyntaxError:
                        raise AppyError(CONVERSION_ERROR % (
                            e.currentBasicType, value))
                    except NameError:
                        raise AppyError(CONVERSION_ERROR % (
                            e.currentBasicType, value))
                    # Convert ints to floats
                    if (e.currentBasicType == 'float') and \
                       isinstance(value, int):
                        value = float(value)
                    # Convert ints to longs
                    elif (e.currentBasicType == 'long') and \
                       isinstance(value, int):
                        value = long(value)
                    # Check that the value is of the correct type. For instance,
                    # a float value with a comma in it could have been converted
                    # to a tuple instead of a float.
                    if not isinstance(value, eval(e.currentBasicType)):
                        raise AppyError(CONVERSION_ERROR % (
                            e.currentBasicType, value))
                elif e.currentBasicType == 'DateTime':
                    value = DateTime(value)
                elif e.currentBasicType == 'datetime':
                    value = self.getDatetime(value)
                elif e.currentBasicType == 'base64':
                    value = e.currentContent.decode('base64')
            # Store the value on the last container
            self.storeValue(elem, value)
            # Clean the environment
            e.currentBasicType = None
            e.currentContent = ''
        else:
            elem = e.containerStack.pop()
            # This element can be a temporary "entry" object representing a dict
            # entry.
            if e.containerStack:
                lastContainer = e.containerStack[-1]
                if isinstance(lastContainer, dict):
                    lastContainer[elem.k] = elem.v

    # Alias: "unmarshall" -> "parse"
    unmarshall = XmlParser.parse

# ------------------------------------------------------------------------------
class XmlMarshaller:
    '''This class allows to produce a XML version of a Python object, which
       respects some conventions as described in the doc of the corresponding
       Unmarshaller (see above).'''
    xmlEntities = {'<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;',
                   "'": '&apos;'}
    trueFalse = {True: 'True', False: 'False'}
    fieldsToMarshall = 'all'
    fieldsToExclude = []
    atFiles = ('image', 'file') # Types of archetypes fields that contain files
    typesMap = {'list': 'list', 'PersistentList': 'list', 'LazyMap': 'list',
                'UserList': 'list', 'dict': 'dict', 'PersistentMapping': 'dict',
                'UserDict': 'dict', 'IOBTree': 'dict', 'OOBTree': 'dict',
                'FileInfo': 'file', 'bool': 'bool', 'int': 'int', 'float':
                'float', 'long': 'long', 'tuple': 'tuple',
                'DateTime': 'DateTime'}

    def __init__(self, cdata=False, dumpUnicode=False, conversionFunctions={},
                 dumpXmlPrologue=True, rootTag='xmlPythonData', namespaces={},
                 namespacedTags={}):
        # If p_cdata is True, all string values will be dumped as XML CDATA.
        self.cdata = cdata
        # If p_dumpUnicode is True, the result will be unicode.
        self.dumpUnicode = dumpUnicode
        # The following dict stores specific conversion (=Python to XML)
        # functions. A specific conversion function is useful when you are not
        # happy with the way built-in converters work, or if you want to
        # specify a specific way to represent, in XML, some particular Python
        # object or value. In this dict, every key represents a given type
        # (class names must be full-path class names); every value is a function
        # accepting 2 args: first one is the UnicodeBuffer where the result is
        # being dumped, while the second one is the Python object or value to
        # dump.
        self.conversionFunctions = conversionFunctions
        # If dumpXmlPrologue is True, the XML prologue will be dumped.
        self.dumpXmlPrologue = dumpXmlPrologue
        # The name of the root tag
        self.rootElementName = rootTag
        # The namespaces that will be defined at the root of the XML message.
        # It is a dict whose keys are namespace prefixes and whose values are
        # namespace URLs. If you want to specify a default namespace, specify an
        # entry with an empty string as a key.
        self.namespaces = namespaces
        # The following dict will tell which XML tags will get which namespace
        # prefix ({s_tagName: s_prefix}). Special optional dict entry
        # '*':s_prefix will indicate a default prefix that will be applied to
        # any tag that does not have it own key in this dict.
        self.namespacedTags = namespacedTags
        self.objectType = None # Will be given by method m_marshall
        # For binaries, content or disk path is marshalled
        self.marshallBinaries = True
        # If p_self.marshallBinaries is False, in order to compute absolute
        # paths to marshalled files, the base database folder, where those files
        # reside, will be set here.
        self.databaseFolder = None

    def getTagName(self, name):
        '''Returns the name of tag p_name as will be dumped. It can be p_name,
           or p_name prefixed with a namespace prefix (will depend on
           self.prefixedTags).'''
        # Determine the prefix
        prefix = ''
        if name in self.namespacedTags: prefix = self.namespacedTags[name]
        elif '*' in self.namespacedTags: prefix = self.namespacedTags['*']
        if prefix: return '%s:%s' % (prefix, name)
        return name

    def isAnObject(self, instance):
        '''Returns True if p_instance is a class instance, False if it is a
           basic type, or tuple, sequence, etc.'''
        if instance.__class__.__name__ == 'LazyMap': return
        iType = type(instance)
        if iType == types.InstanceType:
            return True
        elif iType.__name__ == 'Event' and \
             iType.__bases__[0].__name__ == 'Persistent':
            # An event from the calendar field
            return True
        elif iType.__name__ == 'ImplicitAcquirerWrapper':
            # This is the case with Archetype instances
            return True
        elif iType.__class__.__name__ == 'ExtensionClass':
            return True

    def dumpRootTag(self, res, instance):
        '''Dumps the root tag.'''
        # Dumps the name of the tag.
        tagName = self.getTagName(self.rootElementName)
        res.write('<'); res.write(tagName)
        # Dumps namespace definitions if any
        for prefix, url in self.namespaces.iteritems():
            if not prefix:
                pre = 'xmlns' # The default namespace
            else:
                pre = 'xmlns:%s' % prefix
            res.write(' %s="%s"' % (pre, url))
        # Dumps Appy- or Plone-specific attribute
        if self.objectType != 'popo':
            res.write(' type="object" id="%s" className="%s"' % \
                      (instance.id, instance.getClass().__name__))
        res.write('>')
        return tagName

    def dumpString(self, res, s):
        '''Dumps a string into the result.'''
        if self.cdata: res.write('<![CDATA[')
        if isinstance(s, str):
            try:
                s = s.decode('utf-8')
            except UnicodeDecodeError:
                # Wrongly-encoded user input ?
                s = s.decode('latin-1')
        # Replace special chars by XML entities
        for c in s:
            if self.xmlEntities.has_key(c):
                res.write(self.xmlEntities[c])
            else:
                res.write(c)
        if self.cdata: res.write(']]>')

    def dumpFile(self, res, v):
        '''Dumps a file into the result'''
        if not v or v.size == 0 or not self.marshallBinaries: return
        w = res.write
        # p_value contains the (possibly binary) content of a file. We will
        # encode it in Base64, in one or several parts.
        partTag = self.getTagName('part')
        res.write('<%s type="base64" number="1">' % partTag)
        if hasattr(v, 'data'):
            # The file is an Archetypes file
            if v.data.__class__.__name__ == 'Pdata':
                # There will be several parts.
                w(v.data.data.encode('base64'))
                # Write subsequent parts
                nextPart = v.data.next
                nextPartNb = 2
                while nextPart:
                    w('</%s>' % partTag) # Close the previous part
                    w('<%s type="base64" number="%d">' % (partTag, nextPartNb))
                    w(nextPart.data.encode('base64'))
                    nextPart = nextPart.next
                    nextPartNb += 1
            else:
                w(v.data.encode('base64'))
            w('</%s>' % partTag)
        elif hasattr(v, 'uploadName'):
            # The file is a Appy FileInfo instance. Read the file from disk.
            if v.fsPath.startswith('/') or not hasattr(self, 'instance'):
                filePath = v.fsPath
            else:
                filePath = v.getFilePath(self.instance)
            if not os.path.isfile(filePath):
                w('</%s>' % partTag) # Close the (empty) tag
                return
            f = file(filePath, 'rb')
            partNb = 1
            while True:
                chunk = f.read(v.BYTES)
                if not chunk: break
                # We have one more chunk. Dump the start tag (excepted if it is
                # the first chunk: the start tag has already been dumped, see
                # above).
                if partNb > 1:
                    w('<%s type="base64" number="%d">' % (partTag, partNb))
                w(chunk.encode('base64'))
                w('</%s>' % partTag) # Close the tag
                partNb += 1
            f.close()
        else:
            w(v.encode('base64'))
            w('</%s>' % partTag)

    def dumpDict(self, res, v):
        '''Dumps the XML version of dict p_v.'''
        for key, value in v.iteritems():
            res.write('<entry type="object">')
            self.dumpField(res, 'k', key)
            self.dumpField(res, 'v', value)
            res.write('</entry>')

    def dumpValue(self, res, value, fieldType, isRef=False):
        '''Dumps the XML version of p_value to p_res'''
        # Use a custom function if one is defined for this type of value.
        className = value.__class__.__name__
        if className in self.conversionFunctions:
            self.conversionFunctions[className](res, value)
            return
        # Use a standard conversion else.
        if fieldType == 'file':   self.dumpFile(res, value)
        elif fieldType == 'dict': self.dumpDict(res, value)
        elif isRef:
            if value:
                if type(value) in sequenceTypes:
                    for elem in value:
                        self.dumpField(res, 'url', elem.absolute_url())
                else:
                    self.dumpField(res, 'url', value.absolute_url())
        elif fieldType in ('list', 'tuple'):
            # The previous condition must be checked before this one because
            # referred objects may be stored in lists or tuples, too.
            for elem in value: self.dumpField(res, 'e', elem)
        elif isinstance(value, basestring): self.dumpString(res, value)
        elif isinstance(value, bool): res.write(self.trueFalse[value])
        elif fieldType == 'object':
            if hasattr(value, 'absolute_url'):
                # Dump the URL to the object only
                res.write(value.absolute_url())
            else:
                # Dump the entire object content
                for k, v in value.__dict__.iteritems():
                    if not k.startswith('__'):
                        self.dumpField(res, k, v)
                # Maybe we could add a parameter to the marshaller to know how
                # to marshall objects (produce an ID, an URL, include the entire
                # tag but we need to take care of circular references,...)
        else:
            res.write(value)

    def dumpField(self, res, fieldName, fieldValue, fieldType='basic'):
        '''Dumps in p_res, the value of the p_field for p_instance.'''
        # As a preamble, manage special case of p_fieldName == "_any". In that
        # case, p_fieldValue corresponds to a previously marshalled string that
        # must be included as is here, without dumping the tag name.
        if fieldName == '_any':
            res.write(value)
            return
        # Now, dump "normal" fields
        fieldTag = self.getTagName(fieldName)
        res.write('<'); res.write(fieldTag)
        # Dump the type of the field as an XML attribute
        fType = None # No type will mean "unicode"
        className = fieldValue.__class__.__name__
        if fieldType == 'file': fType = 'file'
        elif fieldType == 'ref': fType = 'list'
        elif className in self.typesMap: fType = self.typesMap[className]
        elif self.isAnObject(fieldValue): fType = 'object'
        if fType: res.write(' type="%s"' % fType)
        # Dump other attributes if needed
        if fType in ('list', 'tuple'):
            length = 0
            if fieldValue: length = len(fieldValue)
            res.write(' count="%d"' % length)
        if fType == 'file':
            # Get the MIME type
            mimeType = None
            if hasattr(fieldValue, 'content_type'):
                mimeType = fieldValue.content_type
            elif hasattr(fieldValue, 'mimeType'):
                mimeType = fieldValue.mimeType
            if mimeType: res.write(' mimeType="%s"' % mimeType)
            # Get the file name
            fileName = None
            if hasattr(fieldValue, 'filename'):
                fileName = fieldValue.filename
            elif hasattr(fieldValue, 'uploadName'):
                fileName = fieldValue.uploadName
            if fileName:
                res.write(' name="')
                self.dumpString(res, fileName)
                res.write('"')
            if not self.marshallBinaries:
                # Dump the file location
                if fieldValue.fsName:
                    # This is a DB-controlled file
                    location = '%s/%s/%s' % (self.databaseFolder,
                                             fieldValue.fsPath,
                                             Escape.xml(fieldValue.fsName))
                else:
                    # A not-in-db file
                    location = fieldValue.fsPath
                res.write(' location="%s"' % location)
        res.write('>')
        # Dump the field value
        self.dumpValue(res, fieldValue, fType, isRef=(fieldType=='ref'))
        res.write('</'); res.write(fieldTag); res.write('>')

    def mustDump(self, fieldName):
        '''Must field named p_fieldName be dumped ?'''
        if fieldName in self.fieldsToExclude:
            r = False
        elif self.fieldsToMarshall == 'all':
            r = True
        else:
            if (type(self.fieldsToMarshall) in sequenceTypes) \
               and (fieldName in self.fieldsToMarshall):
                r = True
            else:
                r = False
        return r

    def marshall(self, instance, objectType='popo', conversionFunctions={},
                 fieldNames=None):
        '''Returns in a UnicodeBuffer the XML version of p_instance. If
           p_instance corresponds to a Plain Old Python Object, specify 'popo'
           for p_objectType. If p_instance corresponds to an Archetypes object
           (Zope/Plone), specify 'archetype' for p_objectType. if p_instance is
           a Appy object, specify "appy" as p_objectType. If p_instance is not
           an instance at all, but another Python data structure or basic type,
           p_objectType is ignored.'''
        self.objectType = objectType
        # The Appy object is needed to marshall its File fields.
        if objectType == 'appy': self.instance = instance
        # Call the XmlMarshaller constructor if it hasn't been called yet.
        if not hasattr(self, 'cdata'):
            XmlMarshaller.__init__(self)
        if conversionFunctions:
            self.conversionFunctions.update(conversionFunctions)
        # Create the buffer where the XML result will be dumped.
        res = UnicodeBuffer()
        # Dump the XML prologue if required
        if self.dumpXmlPrologue:
            res.write(xmlPrologue)
        if self.isAnObject(instance):
            # Dump the root tag
            rootTagName = self.dumpRootTag(res, instance)
            # Dump the fields of this root object
            if objectType == 'popo':
                if fieldNames:
                    # The fields are specified in a list, in order to dump them
                    # in that specific order.
                    for fieldName in fieldNames:
                        if self.mustDump(fieldName):
                            fieldValue = getattr(instance, fieldName, None)
                            self.dumpField(res, fieldName, fieldValue)
                else:
                    # Get the field by browsing p_instance's dict
                    for fieldName, fieldValue in instance.__dict__.iteritems():
                        if self.mustDump(fieldName):
                            self.dumpField(res, fieldName, fieldValue)
            elif objectType == 'archetype':
                for field in instance.schema.fields():
                    # Dump only needed fields
                    mustDump = False
                    if field.getName() in self.fieldsToExclude:
                        mustDump = False
                    elif (self.fieldsToMarshall == 'all') and \
                       (field.schemata != 'metadata'):
                        mustDump = True
                    elif self.fieldsToMarshall == 'all_with_metadata':
                        mustDump = True
                    else:
                        if (type(self.fieldsToMarshall) in sequenceTypes) \
                           and (field.getName() in self.fieldsToMarshall):
                            mustDump = True
                    if mustDump:
                        fieldType = 'basic'
                        if field.type in self.atFiles:
                            fieldType = 'file'
                        elif field.type == 'reference':
                            fieldType = 'ref'
                        self.dumpField(res, field.getName(),field.get(instance),
                                       fieldType=fieldType)
            elif objectType == 'appy':
                # Dump base attributes
                for name in ('created', 'creator'):
                    self.dumpField(res, name, getattr(instance, name))
                # On very old objects, attribute "modified" may not exist
                modified = getattr(instance, 'modified', instance.created)
                self.dumpField(res, 'modified', modified)
                appyi = instance.appy()
                config = appyi.config
                self.marshallBinaries = config.marshallBinaries
                if not self.marshallBinaries:
                    self.databaseFolder = config.marshallFolder or \
                                          appyi.tool.getDbFolder()
                for field in instance.getAppyTypes('xml', None):
                    # Dump only needed fields
                    if field.name in self.fieldsToExclude: continue
                    if (type(self.fieldsToMarshall) in sequenceTypes) \
                        and (field.name not in self.fieldsToMarshall): continue
                    v = field.getXmlValue(appyi, field.getValue(instance))
                    self.dumpField(res, field.name, v)
                # Dump the object history
                if hasattr(instance.aq_base, 'workflow_history'):
                    histTag = self.getTagName('history')
                    eventTag = self.getTagName('event')
                    res.write('<%s type="list">' % histTag)
                    key = instance.workflow_history.keys()[0]
                    history = instance.workflow_history[key]
                    for event in history:
                        res.write('<%s type="object">' % eventTag)
                        for k, v in event.iteritems():
                            self.dumpField(res, k, v)
                        res.write('</%s>' % eventTag)
                    res.write('</%s>' % histTag)
                # Dump local roles
                self.dumpField(res, 'localRoles', instance.__ac_local_roles__)
            self.marshallSpecificElements(instance, res)
            res.write('</'); res.write(rootTagName); res.write('>')
        else:
            self.dumpField(res, self.rootElementName, instance)
        # Return the result
        res = res.getValue()
        if not self.dumpUnicode:
            res = res.encode('utf-8')
        return res

    def marshallSpecificElements(self, instance, res):
        '''You can use this marshaller as a base class for creating your own.
           In this case, this method will be called by the marshall method
           for allowing your concrete marshaller to insert more things in the
           result. p_res is the UnicodeBuffer buffer where the result of the
           marshalling process is currently dumped; p_instance is the instance
           currently marshalled.'''

# ------------------------------------------------------------------------------
class XmlHandler(ContentHandler):
    '''This handler is used for producing, in self.res, a readable XML
       (with carriage returns) and for removing some tags that always change
       (like dates) from a file that need to be compared to another file.'''
    def __init__(self, xmlTagsToIgnore, xmlAttrsToIgnore):
        ContentHandler.__init__(self)
        self.res = unicode(xmlPrologue)
        self.namespaces = {} # ~{s_namespaceUri:s_namespaceName}~
        self.indentLevel = -1
        self.tabWidth = 3
        self.tagsToIgnore = xmlTagsToIgnore
        self.attrsToIgnore = xmlAttrsToIgnore
        self.ignoring = False # Some content must be ignored, and not dumped
        # into the result.
    def isIgnorable(self, elem):
        '''Is p_elem an ignorable element ?'''
        res = False
        for tagName in self.tagsToIgnore:
            if isinstance(tagName, list) or isinstance(tagName, tuple):
                # We have a namespace
                nsUri, elemName = tagName
                try:
                    nsName = self.ns(nsUri)
                    elemFullName = '%s:%s' % (nsName, elemName)
                except KeyError:
                    elemFullName = ''
            else:
                # No namespace
                elemFullName = tagName
            if elemFullName == elem:
                res = True
                break
        return res
    def setDocumentLocator(self, locator):
        self.locator = locator
    def endDocument(self):
        pass
    def dumpSpaces(self):
        self.res += '\n' + (' ' * self.indentLevel * self.tabWidth)
    def manageNamespaces(self, attrs):
        '''Manage namespaces definitions encountered in attrs'''
        for attrName, attrValue in attrs.items():
            if attrName.startswith('xmlns:'):
                self.namespaces[attrValue] = attrName[6:]
    def ns(self, nsUri):
        return self.namespaces[nsUri]
    def startElement(self, elem, attrs):
        self.manageNamespaces(attrs)
        # Do we enter into a ignorable element ?
        if self.isIgnorable(elem):
            self.ignoring = True
        else:
            if not self.ignoring:
                self.indentLevel += 1
                self.dumpSpaces()
                self.res += '<%s' % elem
                attrsNames = attrs.keys()
                attrsNames.sort()
                for attrToIgnore in self.attrsToIgnore:
                    if attrToIgnore in attrsNames:
                        attrsNames.remove(attrToIgnore)
                for attrName in attrsNames:
                    self.res += ' %s="%s"' % (attrName, attrs[attrName])
                self.res += '>'
    def endElement(self, elem):
        if self.isIgnorable(elem):
            self.ignoring = False
        else:
            if not self.ignoring:
                self.dumpSpaces()
                self.indentLevel -= 1
                self.res += '</%s>' % elem
    def characters(self, content):
        if not self.ignoring:
            self.res += content.replace('\n', '')

# ------------------------------------------------------------------------------
class XmlComparator:
    '''Compares 2 XML files and produces a diff'''
    def __init__(self, fileNameA, fileNameB, areXml=True, xmlTagsToIgnore=(),
        xmlAttrsToIgnore=()):
        self.fileNameA = fileNameA
        self.fileNameB = fileNameB
        self.areXml = areXml # Can also diff non-XML files
        self.xmlTagsToIgnore = xmlTagsToIgnore
        self.xmlAttrsToIgnore = xmlAttrsToIgnore

    def filesAreIdentical(self, report=None, encoding=None):
        '''Compares the 2 files and returns True if they are identical (if we
           ignore xmlTagsToIgnore and xmlAttrsToIgnore).
           If p_report is specified, it must be an instance of
           appy.shared.test.TestReport; the diffs will be dumped in it.'''
        # Perform the comparison
        differ = difflib.Differ()
        if self.areXml:
            f = file(self.fileNameA)
            contentA = f.read()
            f.close()
            f = file(self.fileNameB)
            contentB = f.read()
            f.close()
            xmlHandler = XmlHandler(self.xmlTagsToIgnore, self.xmlAttrsToIgnore)
            xml.sax.parseString(contentA, xmlHandler)
            contentA = xmlHandler.res.split('\n')
            xmlHandler = XmlHandler(self.xmlTagsToIgnore, self.xmlAttrsToIgnore)
            xml.sax.parseString(contentB, xmlHandler)
            contentB = xmlHandler.res.split('\n')
        else:
            f = file(self.fileNameA)
            contentA = f.readlines()
            f.close()
            f = file(self.fileNameB)
            contentB = f.readlines()
            f.close()
        diffResult = list(differ.compare(contentA, contentB))
        # Analyse, format and report the result.
        atLeastOneDiff = False
        lastLinePrinted = False
        i = -1
        for line in diffResult:
            i += 1
            if line and (line[0] != ' '):
                if not atLeastOneDiff:
                    msg = 'Difference(s) detected between files %s and %s:' % \
                          (self.fileNameA, self.fileNameB)
                    if report: report.say(msg)
                    else: print(msg)
                    atLeastOneDiff = True
                if not lastLinePrinted:
                    if report: report.say('...')
                    else: print('...')
                if self.areXml:
                    if report: report.say(line)
                    else: print(line)
                else:
                    if report: report.say(line[:-1])
                    else: print(line[:-1])
                lastLinePrinted = True
            else:
                lastLinePrinted = False
        return not atLeastOneDiff

# ------------------------------------------------------------------------------
class XhtmlCleaner(XmlParser):
    '''This class cleans XHTML content, so it becomes ready to be stored into a
       Appy-compliant format.'''
    class Error(Exception): pass

    # Tags that will never be in the result, content included
    tagsToIgnoreWithContent = ('style', 'head')
    # Tags that will be removed from the result, but whose content will be kept
    tagsToIgnoreKeepContent = ('x', 'html', 'body', 'font', 'center',
                               'blockquote')
    # Attributes to ignore
    attrsToIgnore = ('id', 'name', 'class', 'lang', 'rules')
    # Attrs to add, if not present, to ensure good formatting, be it at the web
    # or ODT levels.
    attrsToAdd = {'table': {'cellspacing':'0', 'cellpadding':'6', 'border':'1'},
                  'tr':    {'valign': 'top'}}
    # Tags that require a line break to be inserted after them.
    lineBreakTags = ('p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'td', 'th')
    # No-end tags
    noEndTags = ('br', 'img')

    def __init__(self, env=None, caller=None, raiseOnError=True,
                 tagsToIgnoreWithContent=tagsToIgnoreWithContent,
                 tagsToIgnoreKeepContent=tagsToIgnoreKeepContent,
                 attrsToIgnore=attrsToIgnore, attrsToAdd=attrsToAdd):
        # Call the base constructor
        XmlParser.__init__(self, env, caller, raiseOnError)
        self.tagsToIgnoreWithContent = tagsToIgnoreWithContent
        if 'x' not in tagsToIgnoreKeepContent: tagsToIgnoreKeepContent += ('x',)
        self.tagsToIgnoreKeepContent = tagsToIgnoreKeepContent
        self.tagsToIgnore = tagsToIgnoreWithContent + tagsToIgnoreKeepContent
        self.attrsToIgnore = attrsToIgnore
        self.attrsToAdd = attrsToAdd

    def clean(self, s):
        '''Cleaning XHTML code p_s allows to produce a Appy-compliant,
           ZODB-storable string.
           a. Every <p> or <li> must be on a single line (ending with a
              carriage return); else, appy.shared.diff will not be able to
              compute XHTML diffs;
           b. Optimize size: HTML comments are removed.
        '''
        self.env.currentContent = ''
        # The stack of currently parsed elements (will contain only ignored
        # ones).
        self.env.currentElems = []
        # 'ignoreTag' is True if we must ignore the currently walked tag.
        self.env.ignoreTag = False
        # 'ignoreContent' is True if, within the currently ignored tag, we must
        # also ignore its content.
        self.env.ignoreContent = False
        try:
            res = self.parse('<x>%s</x>' % s).encode('utf-8')
        except SAXParseException, e:
            raise self.Error(str(e))
        return res

    def startDocument(self):
        # The result will be cleaned XHTML, joined from self.res.
        XmlParser.startDocument(self)
        self.res = []

    def endDocument(self):
        self.res = ''.join(self.res)

    def startElement(self, elem, attrs):
        e = self.env
        # Dump any previously gathered content if any
        if e.currentContent:
            self.res.append(e.currentContent)
            e.currentContent = ''
        if e.ignoreTag and e.ignoreContent: return
        if elem in self.tagsToIgnore:
            e.ignoreTag = True
            if elem in self.tagsToIgnoreWithContent:
                e.ignoreContent = True
            else:
                e.ignoreContent = False
            e.currentElems.append( (elem, e.ignoreContent) )
            return
        # Add a line break before the start tag if required (ie: xhtml differ
        # needs to get paragraphs and other elements on separate lines).
        if (elem in self.lineBreakTags) and self.res and \
           (self.res[-1][-1] != '\n'):
            prefix = '\n'
        else:
            prefix = ''
        res = '%s<%s' % (prefix, elem)
        # Include the found attributes, excepted those that must be ignored
        for name, value in attrs.items():
            if name in self.attrsToIgnore: continue
            res += ' %s="%s"' % (name, Escape.xml(value))
        # Include additional attributes if required
        if elem in self.attrsToAdd:
            for name, value in self.attrsToAdd[elem].iteritems():
                if attrs.has_key(name): continue
                res += ' %s="%s"' % (name, value)
        # Close the tag if it is a no-end tag
        if elem in self.noEndTags:
            suffix = '/>'
        else:
            suffix = '>'
        self.res.append('%s%s' % (res, suffix))

    def endElement(self, elem):
        e = self.env
        if e.ignoreTag and (elem in self.tagsToIgnore) and \
           (elem == e.currentElems[-1][0]):
            # Pop the currently ignored tag
            e.currentElems.pop()
            if e.currentElems:
                # Keep ignoring tags
                e.ignoreContent = e.currentElems[-1][1]
            else:
                # Stop ignoring elems
                e.ignoreTag = e.ignoreContent = False
        elif e.ignoreTag and e.ignoreContent:
            # This is the end of a sub-tag within a region that we must ignore
            pass
        else:
            if self.env.currentContent:
                self.res.append(self.env.currentContent)
            # Close the tag only if it is a no-end tag.
            if elem not in self.noEndTags:
                # Add a line break after the end tag if required (ie: xhtml
                # differ needs to get paragraphs and other elements on separate
                # lines).
                if (elem in self.lineBreakTags) and self.res and \
                   (self.res[-1][-1] != '\n'):
                    suffix = '\n'
                else:
                    suffix = ''
                self.res.append('</%s>%s' % (elem, suffix))
            self.env.currentContent = ''

    def characters(self, content):
        if self.env.ignoreContent: return
        # Remove whitespace
        current = self.env.currentContent
        if not current or (current[-1] == '\n'):
            toAdd = content.lstrip(u'\n\r\t')
        else:
            toAdd = content
        # Re-transform XML special chars to entities
        self.env.currentContent += cgi.escape(toAdd)

# ------------------------------------------------------------------------------
class XhtmlToText(XmlParser):
    '''Produces a text version of XHTML content'''
    paraTags = ('p', 'li', 'center', 'div')

    def startDocument(self):
        XmlParser.startDocument(self)
        self.res = []

    def endDocument(self):
        self.res = ''.join(self.res)
        return XmlParser.endDocument(self)

    def characters(self, content):
        self.res.append(content.replace('\n', ''))

    def startElement(self, elem, attrs):
        '''Dumps a carriage return every time a "br" tag is encountered'''
        if elem == 'br': self.res.append('\n')

    def endElement(self, elem):
        '''Dumps a carriage return every time a paragraph is encountered'''
        if elem in self.paraTags: self.res.append('\n')

# ------------------------------------------------------------------------------
class StringCleaner:
    '''Ensure a string does not contain any char that would provoke SAX parser
       errors. Also propose a method for producing clean strings, for which
       those chars were removed.'''

    # Chars (some of the ASCII control characters) provoking SAX parse errors in
    # strings, once being part of a XML data structure that must be parsed with
    # a SAX parser.
    numbers = tuple(range(1,20)) + ('0e',)
    chars = '|'.join(['\\x%s' % str(n).zfill(2) for n in numbers])
    illegal = re.compile(chars)

    @classmethod
    def isParsable(class_, s, wrap='x'):
        '''Returns True if p_s is SAX-parsable. If p_s represents a chunk of
           XHTML code not being wrapped in a single root XML tag, it can be
           wrapped into p_wrap. Specify p_wrap = None for disabling such
           wrapping.'''
        # Wrap p_s if required
        if wrap: s = '<%s>%s</%s>' % (wrap, s, wrap)
        try:
            XmlParser().parse(s)
            return True
        except Exception:
            return False

    @classmethod
    def clean(class_, s):
        '''Return p_s whose illegal chars were removed'''
        return class_.illegal.sub('', s)
# ------------------------------------------------------------------------------
