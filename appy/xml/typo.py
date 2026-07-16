'''Transforms a portion of text, originating from XHTML code, into a target
   text, being conform to typographic rules of some natural language.'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import re
from html.entities import entitydefs as htmlEntities

from appy.xml.escape import Escape

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Transform:
    '''Abstract class being general to any natural language'''

    # Regex matching an HTML entity
    entity = re.compile(r'&(\w+);')

    # Regex matching chemical formulas
    formulas = re.compile('H2O(?:2)?|CO2|CH4|NO2|NH3')

    # Sub-regex matching a number within a chemical formula
    number = re.compile(r'\d+')

    @classmethod
    def resolveEntity(class_, match):
        '''Resolves this p_match(ed) entity'''
        return htmlEntities.get(match.group(1)) or '?'

    @classmethod
    def resolveEntities(class_, text):
        '''Convert explicit XML entities to their ASCII char'''
        return class_.entity.sub(class_.resolveEntity, text)

    @classmethod
    def subNumber(class_, match):
        '''Wraps the m_match(ed) number into a <sub> tag'''
        return f'<sub>{match.group()}</sub>'

    @classmethod
    def convertFormulas(class_, match):
        '''Wraps, in the p_match(ed) chemical formula, any number into a <sub>
           tag.'''
        return class_.number.sub(class_.subNumber, match.group())

    @classmethod
    def apply(class_, text):
        '''Applies the transforms, managing XML entities'''
        # DO NOT override this method: override m_run and/or m_runAfterEscape
        # instead.
        #
        # Resolve entities as a preamble
        text = class_.resolveEntities(text)
        # Apply a set of transforms
        text = class_.run(text)
        # Reify entities
        text = Escape.xml(text)
        # Then, potentially apply a second round of transforms that produce XML
        # chars that must not be escaped. These transforms must be able to
        # handle XHTML entities being potentially found within v_text.
        return class_.runAfterEscape(text)

    @classmethod
    def run(class_, text):
        '''Applies any transforms on this p_text, that does not produce any XML
           char that must not be escaped.'''
        return text

    @classmethod
    def runAfterEscape(class_, text):
        '''Applies any transform producing any not-to-be-escaped XML char(s)'''
        # Format chemical formulas
        text = class_.formulas.sub(class_.convertFormulas, text)
        return text

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class French(Transform):
    '''Text transformer applying typographic rules as applicable to french'''

    # Series of consecutive spaces that must be reduced to a single one
    spaces = re.compile('[  ]{2,5}')

    # Punctuation chars in front of which an unbreakable space must be inserted
    spaced = re.compile(r'([\w\d])[  ]*(!|\?|:|;|%)')

    # Management of *q*uotes, *d*ashes and the *e*uro symbol
    charsQDE = re.compile("(.)?(\"|'|«|»|“|”|‘|’|-|–|—| |€)(.)?")

    # Among chars being covered by regex v_charsQDE, the following dict contains
    # those that need to be replaced in any case, with their replacement char
    replacements = {
      "'": '’', # A straight apos must be come a curved one
      ' ':' ',  # A thin space must become an unbreakable one
      # English-tyle quotes must, in the end, be replaced with angle quotes.
      # Start by converting them to straight double quotes.
      '“': '"', '”': '"', '‘': '"'}

    # Persons' titles, and other words that must be followed by a non breakable
    # space.
    titles = re.compile(r'(M\.[  ]le|Mme[  ]la|M\.|MM\.|Mme|Mmes|Doc.) ')

    # Numbers, expressed as arab or roman numerals. For roman numbers, the
    # objective is restricted to matching centuries.
    figures = re.compile(r'(\d+|[IVX]{1,6})(er|re|e)(?!\w)(.)?')

    # Manage abbreviation "N°" or "n°"
    no = re.compile('(N|n)°(.)?')

    # In some cases, it may be appropriate to convert the "degree" char, "°", to
    # a lower "o" char, surrounded by "sup" tags. If you want this, set the
    # following static attribute to True.
    noToSup = False

    # Dashes
    dashes = '-', '–', '—'

    # Whitespace, being breakable or not
    whitespace = ' ', ' '

    # Angle quotes
    angle = '«', '»'

    # Chars OCR could wrongly identify as a lower "l"
    mimicsLowerL = '1', 'I'

    # Latin multiplicative adverbs
    latinAdverbs = 'bis', 'ter', 'quater', 'quinquies', 'sexies', 'septies', \
                   'octies', 'nonies', 'decies'

    # Law articles whose numbers make use of a latin multiplicative adverb
    subArticle = re.compile(fr'(\d+)({"|".join(latinAdverbs)})')

    # No unbreakable space must be left in "milliards|millions d'euros"
    mEuro = re.compile('(milliards|millions) d’euros')

    # "etc." must be replaced with "et cetera"
    etc = re.compile(r'etc\.(.)?')

    # If "etc." is followed by one of these chars, "et cetera" will not be
    # dumped with a trailing dot.
    etcNoDot = ',', ')', ';', ' '

    @classmethod
    def manageSpaces(class_, match):
        '''Reduce a series of consecutive spaces into a single space'''
        # Keep only the last space in the series, be it unbreakable or not.
        # While typing in a contenteditable field with (at least) Firefox, if 2
        # consecutive chars are typed, the first one will be converted to an
        # unbreakable space. Consequently, we guess that the more significative
        # space is not the first one, but the last one.
        return match.group()[-1]

    @classmethod
    def manageSpaced(class_, match):
        '''Standardize a punctuation char'''
        return f'{match.group(1)} {match.group(2)}'

    @classmethod
    def manageDash(class_, pre, char, post):
        '''Manage a p_char being a dash'''
        # As a preamble, convert any long dash with a shorter one
        if char == '—': char = '–'
        # Manage whitespace surrounding dashes
        white = class_.whitespace
        if char == '-':
            if pre in white and post in white:
                # This should be a longer dash, without any non breakable space
                pre = post = ' '
                char = '–'
            elif post == ',':
                # In that case, also replace it with a longer dash; ensure v_pre
                # is a space.
                char = '–'
                if pre and pre not in white:
                    pre = f'{pre} '
        elif char == '–':
            # Ensure it is surrrounded by spaces
            if pre and pre not in white:
                pre = f'{pre} '
            if post and post not in white and post != ',':
                post = f' {post}'
        return pre, char, post

    @classmethod
    def convertCurved(class_, pre, char, post):
        '''Currently disabled tentative to convert, when appropriate, a curved
           p_char into a double quote.'''
        # Is this a simple quote that must stay as is (like in: L’eau) or must
        # it be converted to an angle quote ? (like in: Il se dit ‘amusant’) ?
        if pre.isalnum() and (post.isalnum() or post == ')' or post == 'œ'):
            r = char
            # Examples of ending curved quotes that must not be converted
            # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
            # - "L'article (n’) est (pas) amendé": the "(n’)" part must stay as
            #   is (well managed).
            # - "La main d’œuvre" (well managed, but special char œ must be
            #   explicitly specified: method string.isalnum does not consider it
            #   as an alphanumeric char).
            # - "d’« anticiper" is wrongly converted to "d »« anticiper".
            # - There are probably more wrong cases.
            # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        else:
            r = '"'
            # This will be converted by the appropriate angle char by
            # m_manageAngleQuote.
        return r

    @classmethod
    def manageCurved(class_, pre, char, post):
        '''Manages the ending curved quote'''
        # Manage frequent OCR errors
        if pre in class_.mimicsLowerL and post not in class_.whitespace:
            # If p_post is whitespace, it could not be a confusion with a lower
            # "l", but a kind of numbering scheme: 1' ("un prime", in french).
            return 'l', char, post
        # [Currently disabled] Standardize curved quotes, like in this example:
        # ‘amusant’ must become "amusant". But too many conflicts occur with the
        # ending curved quote (’), also being the result of converting a single
        # quote ('). Consequently, currently, the ending curved quote stays
        # unchanged.
        # char = class_.convertCurved(pre, char, post)
        return pre, char, post

    @classmethod
    def manageAngleQuote(class_, pre, char, post):
        '''Ensure angle quote p_char has its companion non breakable space'''
        if char == '«':
            if post == ' ':
                post = ' ' # Convert a space into a non breakable
            elif post == ' ' or not post:
                pass # Everything is OK
            else:
                post = f' {post}' # Insert a non-breakable before v_post
        elif char == '»':
            if pre == ' ':
                pre = ' ' # Convert a space into a non breakable
            elif pre == ' ' or not pre:
                pass # Everything is OK
            else:
                pre = f'{pre} ' # Insert a non-breakable after v_pre
        return pre, char, post

    @classmethod
    def manageEuro(class_, pre, char, post):
        '''Converts the € symbol to pain text "euros"'''
        # ... but always to the plural
        #
        # Add a space if the symbol sticks a figure
        if pre and pre not in class_.whitespace:
            pre = f'{pre} '
        return pre, 'euros', post

    @classmethod
    def manageQDE(class_, match):
        '''Standardize a quote, dash or euro symbol, and its surroundings'''
        char = match.group(2)
        # Perform char replacements
        pre = match.group(1) or ''
        post = match.group(3) or ''
        char = class_.replacements.get(char) or char
        # Convert quote symbols into angle quotes
        if char == '’':
            pre, char, post = class_.manageCurved(pre, char, post)
        if char == '"':
            if pre.isalnum() or pre == ' ':
                char = '»'
            elif post.isalnum() or post == ' ':
                char = '«'
        # Manage angle quotes
        if char in class_.angle:
            pre, char, post = class_.manageAngleQuote(pre, char, post)
        # Manage dashes
        elif char in class_.dashes:
            pre, char, post = class_.manageDash(pre, char, post)
        elif char == '€':
            pre, char, post = class_.manageEuro(pre, char, post)
        return f'{pre}{char}{post}'

    @classmethod
    def unbreakableToNormal(class_, match):
        '''Replace any unbreakable space in the p_match by a standard space'''
        return match.group().replace(' ', ' ')

    @classmethod
    def manageEtc(class_, match):
        '''Replaces "etc." by "et cetera"'''
        # Get the char following "etc."
        post = match.group(1) or ''
        if not post or (post not in class_.etcNoDot):
            post = f'.{post}'
        return f'et cetera{post}'

    @classmethod
    def manageTitle(class_, match):
        '''Ensure non-breakable spaces are in use among people's titles'''
        title = match.group(1).replace(' ', ' ')
        return f'{title} '

    @classmethod
    def setUnbreakable(class_, char, insert=True):
        '''Returns a variant of p_char, starting with or being an unbreakable
           space.'''
        if not char: return char or ''
        if char == ' ':
            r = ' ' # A normal space is converted to an unbreakable one
        elif char == ' ':
            r = char # Already unbreakable, this is fine
        else:
            # Insert, when relevant, an unbreakable space before any other char
            r = f' {char}' if insert else char
        return r

    @classmethod
    def manageFigure(class_, match):
        '''Ensure letters after a figure are put in exponent'''
        post = class_.setUnbreakable(match.group(3), insert=False)
        return f'{match.group(1)}<sup>{match.group(2)}</sup>{post}'

    @classmethod
    def manageNo(class_, match):
        '''Ensure an unbreakable space follows chars "N°" or "n°"'''
        post = class_.setUnbreakable(match.group(2))
        # Convert char ° to letter "o" surrounded by tag "sup" if appropriate
        o = '<sup>o</sup>' if class_.noToSup else '°'
        return f'{match.group(1)}{o}{post}'

    @classmethod
    def formatSubArticle(class_, match):
        '''Italicise the latin part of the law article having been
           p_match(ed).'''
        return f'{match.group(1)}<i>{match.group(2)}</i>'

    @classmethod
    def run(class_, text):
        '''Applies the transforms'''
        # Reduce consecutive spaces into a single space
        text = class_.spaces.sub(class_.manageSpaces, text)
        # Manage punctuation chars
        text = class_.spaced.sub(class_.manageSpaced, text)
        # Manage quotes, dashes and euros
        text = class_.charsQDE.sub(class_.manageQDE, text)
        # Very specific rule, emanating from an error made by another software.
        # Quotes must have been converted first, before calling this (it is done
        # by the previous line).
        text = class_.mEuro.sub(class_.unbreakableToNormal, text)
        # Convert "etc." by "et cetera"
        text = class_.etc.sub(class_.manageEtc, text)
        # Manage persons' titles
        return class_.titles.sub(class_.manageTitle, text)

    @classmethod
    def runAfterEscape(class_, text):
        '''Manage transforms that produce not-to-be-escaped XML chars'''
        # Perform base treatments
        text = Transform.runAfterEscape(text)
        # Manage figures
        text = class_.figures.sub(class_.manageFigure, text)
        # Manage "N°/n°"
        text = class_.no.sub(class_.manageNo, text)
        # Format law articles suffixed by a latin multiplicative adverb
        text = class_.subArticle.sub(class_.formatSubArticle, text)
        return text
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
