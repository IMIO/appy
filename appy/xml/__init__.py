# -*- coding: utf-8 -*-

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import xml.sax, io
from xml.sax.xmlreader import InputSource
from html.entities import entitydefs as htmlEntities
from xml.parsers.expat import XML_PARAM_ENTITY_PARSING_NEVER
from xml.sax.handler import ContentHandler, ErrorHandler, feature_external_ges

from appy.utils import asDict

# Constants  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
xmlPrologue = '<?xml version="1.0" encoding="utf-8" ?>\n'
xhtmlPrologue = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" '\
                '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n'

# Self-closing XHTML tags  - - - - - - - - - - - - - - - - - - - - - - - - - - -
XHTML_SC = asDict(('area', 'base', 'br', 'col', 'command', 'embed', 'hr',
                   'img', 'input', 'keygen', 'link', 'menuitem', 'meta',
                   'param', 'source', 'track', 'wbr'))

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Tag:
    '''Represents an XML tag'''

    def __init__(self, name, attrs=None, nsUri=None, parent=None):
        '''A Tag instance may represent:
           - an already parsed tag (in this case, p_name may be prefixed with a
             namespace);
           - the definition of an XML tag (in this case, no namespace can be
             found in p_name; but a namespace URI may be defined in p_nsUri).'''
        self.name = name
        self.attrs = attrs
        if name.find(':') != -1:
            self.nsName = name
            self.ns, self.name = name.split(':', 1)
        else:
            self.nsName = self.name = name
            self.ns = ''
            self.nsUri = nsUri
        self.parent = parent # The parent element

    def __repr__(self):
        r = '<tag %s' % self.name
        if self.attrs:
            attrs = ['%s="%s"' % (k, v) for k, v in self.attrs.items()]
            r += ' [%s]' % ', '.join(attrs)
        return '%s>' % r

    def getFullName(self, namespaces=None):
        '''Gets the name of the element including the namespace prefix'''
        if not namespaces:
            r = self.name
        else:
            r = '%s:%s' % (namespaces[self.nsUri], self.name)
        return r

#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Environment:
    '''An XML environment remembers a series of elements during a SAX parsing.
       This class is an abstract class that gathers basic things like
       namespaces.'''

    def __init__(self):
        '''Initialises an XML environment'''
        # Dict "namespaces" contains the XML namespace declarations encountered
        # so far.
        self.namespaces = {} # ~{s_namespaceUri: s_namespaceName}~
        self.currentTag = None # The currently parsed tag
        self.currentContent = '' # Currently collected tag content
        self.parser = None

    def manageNamespaces(self, attrs):
        '''Manages namespaces definitions encountered in p_attrs'''
        for name, value in attrs.items():
            if name.startswith('xmlns:'):
                self.namespaces[value] = name[6:]

    def ns(self, nsUri):
        '''Returns the namespace corresponding to o_nsUri'''
        return self.namespaces[nsUri]

#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Parser(ContentHandler, ErrorHandler):
    '''Basic expat-based XML parser'''

    # This parser manages:
    # - the stack of currently parsed tags;
    # - namespace declarations.
    # It knows about HTML entities.

    def __init__(self, env=None, caller=None, raiseOnError=True):
        '''p_env should be an instance of a class that inherits from
           appy.xml.Environment: it specifies the environment to use for this
           SAX parser.'''
        ContentHandler.__init__(self)
        self.env = env or Environment()
        self.env.parser = self
        # The class calling this parser
        self.caller = caller
        # Fast, standard expat parser
        self.parser = xml.sax.make_parser()
        # The result of parsing
        self.r = None
        # Raise or not an error when a parsing error is encountered
        self.raiseOnError = raiseOnError

    #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                         ContentHandler methods
    #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def startDocument(self):
        parser = self.parser._parser
        parser.UseForeignDTD(True)
        parser.SetParamEntityParsing(XML_PARAM_ENTITY_PARSING_NEVER)

    def setDocumentLocator(self, locator):
        self.locator = locator
        return self.env

    def endDocument(self): return self.env

    def startElement(self, name, attrs):
        env = self.env
        env.manageNamespaces(attrs)
        # Replace the current elem (or not if this is the root tag) by a fresh
        # Tag instance.
        env.currentTag = Tag(name, attrs=attrs, parent=env.currentTag)
        return env

    def endElement(self, name):
        '''Pops the currently walked elem'''
        env = self.env
        env.currentTag = env.currentTag.parent
        return env

    def characters(self, content): return self.env

    def skippedEntity(self, entity):
        '''Called every time expat does not recognize an entity. We provide here
           support for HTML entities.'''
        # When an unknown entity is encountered, put a question mark in the
        # result instead of raising an exception.
        char = htmlEntities.get(entity) or '?'
        self.characters(char)

    #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                         ErrorHandler methods
    #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def error(self, error):
        if self.raiseOnError: raise error
        else: print('SAX error %s' % str(error))

    def fatalError(self, error):
        if self.raiseOnError: raise error
        else:
            print('SAX fatal error %s on XML:' % str(error))

    def warning(self, error): pass

    def parse(self, xml, source='string', encoding='utf-8'):
        '''Parses a XML stream'''
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # If p_source | p_xml...
        # is...       |
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  "string"   | must be a string or bytes object containing valid XML
        #             | content;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  "file"     | can be:
        #             |  - a string containing the path to the XML file on disk;
        #             |  - a file handler opened for reading. Note that in this
        #             |    case, this method will close it.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self._xml = xml
        self.parser.setContentHandler(self)
        self.parser.setErrorHandler(self)
        self.parser.setFeature(feature_external_ges, False)
        inputSource = InputSource()
        if source == 'string':
            xml = xml.decode(encoding) if isinstance(xml, bytes) else xml
            xml = io.StringIO(xml)
        else:
            xml = xml if isinstance(xml, io.IOBase) \
                      else open(xml, encoding=encoding)
        inputSource.setByteStream(xml)
        self.parser.parse(inputSource)
        xml.close()
        return self.r
#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
