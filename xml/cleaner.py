# -*- coding: utf-8 -*-

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import re

from appy.xml import Parser
from appy.xml.escape import Escape

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Cleaner(Parser):
    '''Cleans XHTML content, so it becomes ready to be stored into a
       Appy-compliant format.'''

    # Tags that will never be in the result, content included
    tagsToIgnoreWithContent = ('style', 'head')

    # Tags that will be removed from the result, but whose content will be kept
    tagsToIgnoreKeepContent = ('x', 'html', 'body', 'font', 'center',
                               'blockquote')
    # Attributes to ignore
    attrsToIgnore = ('id', 'name', 'class', 'lang', 'rules')

    # Attrs to add, if not present, to ensure good formatting, be it at the web
    # or ODT levels.
    attrsToAdd = {'table': {'cellpadding':'6', 'cellspacing':'0', 'border':'1'},
                  'tr':    {'valign': 'top'}}

    # Tags that require a line break to be inserted after them
    lineBreakTags = ('p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'td', 'th')

    # No-end tags
    noEndTags = ('br', 'img')

    def __init__(self, env=None, caller=None, raiseOnError=True,
                 tagsToIgnoreWithContent=tagsToIgnoreWithContent,
                 tagsToIgnoreKeepContent=tagsToIgnoreKeepContent,
                 attrsToIgnore=attrsToIgnore, attrsToAdd=attrsToAdd):
        # Call the base constructor
        Parser.__init__(self, env, caller, raiseOnError)
        self.tagsToIgnoreWithContent = tagsToIgnoreWithContent
        if 'x' not in tagsToIgnoreKeepContent: tagsToIgnoreKeepContent += ('x',)
        self.tagsToIgnoreKeepContent = tagsToIgnoreKeepContent
        self.tagsToIgnore = tagsToIgnoreWithContent + tagsToIgnoreKeepContent
        self.attrsToIgnore = attrsToIgnore
        self.attrsToAdd = attrsToAdd

    def startDocument(self):
        # The result will be cleaned XHTML, joined from self.r
        Parser.startDocument(self)
        self.r = []

    def endDocument(self):
        self.r = ''.join(self.r)

    def startElement(self, tag, attrs):
        e = self.env
        # Dump any previously gathered content if any
        if e.currentContent:
            self.r.append(e.currentContent)
            e.currentContent = ''
        if e.ignoreTag and e.ignoreContent: return
        if tag in self.tagsToIgnore:
            e.ignoreTag = True
            if tag in self.tagsToIgnoreWithContent:
                e.ignoreContent = True
            else:
                e.ignoreContent = False
            e.currentTags.append( (tag, e.ignoreContent) )
            return
        # Add a line break before the start tag if required (ie: xhtml differ
        # needs to get paragraphs and other elements on separate lines).
        if (tag in self.lineBreakTags) and self.r and \
           (self.r[-1][-1] != '\n'):
            prefix = '\n'
        else:
            prefix = ''
        r = '%s<%s' % (prefix, tag)
        # Include the found attributes, excepted those that must be ignored
        for name, value in attrs.items():
            if name in self.attrsToIgnore: continue
            r += ' %s="%s"' % (name, Escape.xml(value))
        # Include additional attributes if required
        if tag in self.attrsToAdd:
            for name, value in self.attrsToAdd[tag].items():
                if name in attrs: continue
                r += ' %s="%s"' % (name, value)
        # Close the tag if it is a no-end tag
        suffix = '/>' if tag in self.noEndTags else '>'
        self.r.append('%s%s' % (r, suffix))

    def endElement(self, tag):
        e = self.env
        if e.ignoreTag and (tag in self.tagsToIgnore) and \
           (tag == e.currentTags[-1][0]):
            # Pop the currently ignored tag
            e.currentTags.pop()
            if e.currentTags:
                # Keep ignoring tags
                e.ignoreContent = e.currentTags[-1][1]
            else:
                # Stop ignoring elems
                e.ignoreTag = e.ignoreContent = False
        elif e.ignoreTag and e.ignoreContent:
            # This is the end of a sub-tag within a region that we must ignore
            pass
        else:
            if self.env.currentContent:
                self.r.append(self.env.currentContent)
            # Close the tag only if it is a no-end tag.
            if tag not in self.noEndTags:
                # Add a line break after the end tag if required (ie: xhtml
                # differ needs to get paragraphs and other elements on separate
                # lines).
                if (tag in self.lineBreakTags) and self.r and \
                   (self.r[-1][-1] != '\n'):
                    suffix = '\n'
                else:
                    suffix = ''
                self.r.append('</%s>%s' % (tag, suffix))
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
        self.env.currentContent += Escape.xml(toAdd)

    def clean(self, s):
        '''Cleaning XHTML code p_s allows to produce a Appy-compliant,
           ZODB-storable string.'''
        # a. Every <p> or <li> must be on a single line (ending with a carriage
        #    return); else, appy.utils.diff will not be able to compute XHTML
        #    diffs;
        # b. Optimize size: HTML comments are removed
        self.env.currentContent = ''
        # The stack of currently parsed elements (will contain only ignored
        # ones).
        self.env.currentTags = []
        # 'ignoreTag' is True if we must ignore the currently walked tag.
        self.env.ignoreTag = False
        # 'ignoreContent' is True if, within the currently ignored tag, we must
        # also ignore its content.
        self.env.ignoreContent = False
        return self.parse('<x>%s</x>' % s)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
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
            Parser().parse(s)
            return True
        except Exception:
            return False

    @classmethod
    def clean(class_, s):
        '''Return p_s whose illegal chars were removed'''
        if not s: return s
        return class_.illegal.sub('', s)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
