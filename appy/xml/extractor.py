#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.xml import Parser
from appy.utils.string import Normalize

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
PARAMS_KO = "You can't have both 'keepCRs' and 'normalize' being True. " \
            "Normalizing implies CRs to be removed."

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Extractor(Parser):
    '''Produces a text version of XML/XHTML content'''

    # There are 2 main usages to this parser. It can extract text:
    # - to produce a complete but textual version of some XHTML chunk, keeping
    #   accented chars and carriage returns;
    # - to extract text for search purposes, converting any accented char to its
    #   non-accented counterpart and removing any other element.

    paraTags = ('p', 'li', 'center', 'div', 'blockquote')

    def __init__(self, keepCRs=True, normalize=False, lower=True,
                       keepDashes=False, raiseOnError=False):
        Parser.__init__(self, raiseOnError=raiseOnError)
        # Must we keep carriage returns (and thus keep the global splitting of
        # the text into paragraphs) ?
        self.keepCRs = keepCRs
        # Must text be normalized ? When True, every accented char is converted
        # to its non-accented counterpart.
        self.normalize = normalize
        # Is is not possible to have both p_keepCRs and p_normalize being True
        if keepCRs and normalize: raise Exception(PARAMS_KO)
        # Must be lowerise text ? (only if p_normalize is True)
        self.lower = lower
        # Must we keep dashes ? (only if p_normalize is True)
        self.keepDashes = keepDashes

    def startDocument(self):
        Parser.startDocument(self)
        self.r = []

    def endDocument(self):
        sep = '' if self.keepCRs else ' '
        self.r = sep.join(self.r)
        return Parser.endDocument(self)

    def characters(self, content):
        if self.normalize:
            content = Normalize.text(content, lower=self.lower,
                                     keepDash=self.keepDashes)
            if len(content) <= 1: return
        else:
            # Even if we must keep CRs, those encountered here are not
            # significant.
            content = content.replace('\n', ' ')
        self.r.append(content)

    def startElement(self, name, attrs):
        '''In "non-normalizing" mode, dumps a carriage return every time a "br"
           tag is encountered'''
        if self.keepCRs and name == 'br': self.r.append('\n')

    def endElement(self, name):
        '''In "non-normalizing" mode, dumps a carriage return every time a
           paragraph is encountered.'''
        if self.keepCRs and name in Extractor.paraTags: self.r.append('\n')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
