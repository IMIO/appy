# -*- coding: utf-8 -*-

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.xml.escape import Escape
from appy.xml import Parser, XHTML_SC

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Modifier(Parser):
    '''Allows to perform modifications on XHTML content'''

    def __init__(self, env=None, caller=None, raiseOnError=False, p='p',
                 prefix='', replacements=None, replacementsFun=None,
                 preListClass=None, lastLiClass=None):
        # Call the base constructor
        Parser.__init__(self, env, caller, raiseOnError)
        # p_p indicates which tag is mainly used in p_s for paragraphs. It could
        # also be "div".
        self.p = p
        # p_prefix is some chunk of text that must be inserted at the start of
        # the first found paragraph (p_p) in p_s.
        self.prefix = prefix
        self.replacements = replacements
        self.replacementsFun = replacementsFun
        self.preListClass = preListClass
        self.lastLiClass = lastLiClass

    def startDocument(self):
        # The result will be updated XHTML, joined from self.r
        Parser.startDocument(self)
        self.r = []

    def endDocument(self):
        self.r = ''.join(self.r)

    def dumpCurrentContent(self):
        '''Dump currently collected content if any'''
        e = self.env
        if e.currentContent:
            self.r.append(e.currentContent)
            e.currentContent = ''

    def startElement(self, tag, attrs):
        e = self.env
        # Dump any previously gathered content if any
        self.dumpCurrentContent()
        # Dump the start tag. Close it if it is a no-end tag.
        sc = tag in XHTML_SC
        suffix = '/>' if sc else '>'
        r = '<%s%s' % (tag, suffix)
        # Include attributes
        if not sc:
            for name, value in attrs.items():
                r += ' %s="%s"' % (name, Escape.xml(value))
        self.r.append(r)

    def endElement(self, tag):
        e = self.env
        # Dump any previously gathered content if any
        self.dumpCurrentContent()
        # Close the tag only if it is a no-end tag.
        if tag not in XHTML_SC:
            self.r.append('</%s>' % tag)

    def characters(self, content):
        # Re-transform XML special chars to entities
        self.env.currentContent += Escape.xml(content)

    def modify(self, s):
        '''Returns p_s, modified'''
        r = self.parse('<x>%s</x>' % s)
        return r[3:-4]
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
