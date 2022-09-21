# -*- coding: utf-8 -*-

'''Utility module related to string manipulation'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import re, string, random

from appy.utils import flipDict, asDict

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Normalize:
    '''Converts a string in some "purified" form, ie, without diacritics
       (accents) or freed from specific chars.'''

    # The process of normalizing strings is as follows.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # 1 | The set of chars that must be left untouched in the resulting string
    #   | must be defined. We do it by defining a regular expression that
    #   | matches any *other* char: that way, chars not matching it will be kept
    #   | in the result as-is. Such regular expressions generally take the form
    #   | of a set that has been complemented (see the doc about Python "re"
    #   | module).
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # 2 | For every char not being among this set of untouched chars, four
    #   | different actions may be performed:
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #   | "blankify" | the char will be converted to a blank char ;
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #   |  "ignore"  | the char will simply be ignored: it will not be part of
    #   |            | the result ;
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #   | "replace"  | the char will be replaced with an alternative char (or
    #   |            | string) ;
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #   |  "keep"    | the char will be left as-is in the result.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # Defining a concrete normalization thus consists in defining or choosing:
    # - a base regular expression defining chars to keep ;
    # - a list of chars to "blankify" ;
    # - a list of chars to ignore ;
    # - a dict of chars to replace, keys being chars to replace and values being
    #   chars or strings to use as replacements ;
    # - the fact of keeping or not, in the result, any char not being initially
    #   kept, not being blankified, ignored nor replaced.

    # Things will be processed in that order, ie, if a char is found in the list
    # of chars to blankify, it will be blankified, even if also found among
    # chars to ignore or replace.

    # On this class, you will find the generic classmethod named "string",
    # allowing to perform any kind of normalization. As method args, you must
    # specify a string to normalize and the 4 previously defined elements
    # (regular expression, chanrs to blankify, to ignore and to replace).

    # Then, concrete methods are proposed: they use predefined regular
    # expressions and lists/dicts of chars, defined as static attributes on this
    # class, in order to fulfill various purposes, like normalizing strings to
    # be ued as filenames or as texts to be stored in a database index.

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # A. The default replacement dictionary
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # The default replacement dict is the one allowing to convert latin accented
    # chars to their non-accented equivalent chars. More precisely, it concerns
    # chars from the table named "Latin-1 Supplement" on page
    #
    #        https://en.wikipedia.org/wiki/List_of_Unicode_characters
    #
    # completed with interlaced graphemes and UTF-8 space variants.
    replacements = flipDict(
      {'A':'ÀÁÂÃÄÅÆ', 'a':'àáâãäåæ', 'C':'Ç', 'c':'ç', 'D':'Ð', 'S':'ß',
       'E':'ÈÉÊË', 'e':'èéêë', 'I':'ÌÍÎÏ', 'i':'ìíîï', 'N':'Ñ', 'n':'ñ',
       'O':'ÒÓÔÕÖØ', 'o':'òóôõöðø', 'U':'ÙÚÛÜ', 'u':'ùúûü', 'Y':'Ý', 'y':'ýÿ'},
       byChar=True)
    replacements.update({'Æ':'AE', 'æ': 'ae', 'Œ':'OE', 'œ': 'oe',
                         ' ':' ', '‑':'-'})

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # B. The default regular expressions
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # The following default regular expressions define, depending on the needs,
    # various sets of chars that will not be among chars kept as-is in the
    # result.
    nonAlpha      = re.compile('[^a-zA-Z]')      # Matches any non-alpha char
    nonAlphanum   = re.compile('[^a-zA-Z0-9]')   # Matches any non-alphanum char
    nonAlphanumB  = re.compile('[^a-zA-Z0-9 ]')  # + blanks
    nonAlphanumD  = re.compile('[^a-zA-Z0-9-]')  # + dashes
    nonAlphanumBD = re.compile('[^a-zA-Z0-9 -]') # + blanks and dashes
    nonAlphanum_  = re.compile('[^a-zA-Z0-9_]')  # Alphanums + the underscore
    nonDigit      = re.compile('[^0-9]')

    # Access some of the previously defined regular expressions, depending on
    # the fact that blanks (1) and/or dashes (2) must be matched or not.
    textRex = { False: { False: nonAlphanum,  True: nonAlphanumD },
                True:  { False: nonAlphanumB, True: nonAlphanumBD }}

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # C. The default lists of chars to ignore or blankify
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # The following lists define, depending on the needs, various lists of chars
    # to ignore or blankify. These lists are the converted to dicts whose values
    # are None, because lookup in dicts are more efficient.

    # ~~~ A common set of chars, to ignore or blankify in most situations
    baseIgnorable = '.,:;*+=~?%^\'’"<>{}[]#|\t\\°-‑'

    # ~~~ The set of chars to ignore when producing a file name
    fileNameIgnorable = asDict(baseIgnorable + '  $£€/\r\n')

    # ~~~ The set of chars to blankify when extracting text for the purpose of
    #     database indexing, with 2 variants, keeping dashes (True) or not.
    moreIgnorable = '\n/()_'
    textIgnorable = {
      False: asDict(baseIgnorable + moreIgnorable),
      True:  asDict(baseIgnorable[:-2] + moreIgnorable)
    }

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # Base method normalizing chars by blankifying, ignoring, replacing or
    # keeping them untouched in the resulting string.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @classmethod
    def char(class_, c, blankify, ignore, replace, keep):
        '''Handles char p_c and returns the element corresponding to it that
           must be part of the result.'''
        if blankify and c in blankify:
            r = ' '
        elif ignore and c in ignore:
            r = ''
        elif replace and c in replace:
            r = replace[c]
        elif keep:
            r = c
        else:
            r = ''
        return r

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #       Generic method for performing any kind of string normalizing
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @classmethod
    def string(class_, s, rex, blankify=None, ignore=None, replace=None,
               keep=False):
        '''Normalizes string p_s'''
        # Any char matched by p_rex in p_s will be replaced with a blank,
        # ignored, replaced or kept as-is, depending on its presence as a key in
        # dicts p_blank, p_ignore or p_replace and of boolan arg p_keep.
        fun = lambda match: Normalize.char(match.group(0),
                                           blankify, ignore, replace, keep)
        return rex.sub(fun, s)

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                      Concrete normalizing methods
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @classmethod
    def text(class_, s, lower=True, keepDash=False, keepBlank=True):
        '''Normalizes string p_s, for producing a text being suitable for
           database keyword indexing or search terms cleaning.'''
        #
        # If p_keepDash is ...
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # True  | Dashes (-) are kept.
        #       |
        #       | Example:
        #       | Jean-François > jean-francois
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # False | Dashes are replaced with blanks.
        #       |
        #       | Example:
        #       | Jean-François > jean francois
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # Choose the appropriate regular expression and set of chars to ignore
        # or blankify, depending on the fact that dashes and/or blanks
        # must be kept or not (p_keepDash and p_keepBlank).
        r = Normalize.string(s, class_.textRex[keepBlank][keepDash],
                             blankify=class_.textIgnorable[keepDash],
                             replace=class_.replacements)
        # Lowerize the result if required (p_lower)
        return r.lower() if lower else r

    @classmethod
    def sortable(class_, s):
        '''Normalizes p_s such that it can be used as value for sorting'''
        r = Normalize.string(s, class_.nonAlphanum,
                             ignore=class_.textIgnorable[False],
                             replace=class_.replacements)
        return r.lower()

    @classmethod
    def fileName(class_, s):
        '''Normalizes p_s, for producing a string suitable for naming a file on
           disk.'''
        return Normalize.string(s, class_.nonAlphanum,
                                ignore=class_.fileNameIgnorable,
                                replace=class_.replacements)

    @classmethod
    def accents(class_, s):
        '''Returns a version of p_s whose accented chars have been "unaccented",
           ie, replaced with their non-accented versions.'''
        return Normalize.string(s, class_.nonAlphanum,
                                replace=class_.replacements, keep=True)

    @classmethod
    def alpha(class_, s):
        '''Returns a version of p_s, keeping only alpha chars, accented chars
           being "unaccented".'''
        return Normalize.string(s, class_.nonAlpha, replace=class_.replacements)

    @classmethod
    def alphanum(class_, s, keepUnderscore=False):
        '''Returns a version of p_s, keeping only alphanumeric chars (and
           possibly underscores if p_keepUnderscore is True), accented chars
           being "unaccented".'''
        rex = class_.nonAlphanum_ if keepUnderscore else class_.nonAlphanum
        return Normalize.string(s, rex, replace=class_.replacements)

    @classmethod
    def digit(class_, s):
        '''Returns a version of p_s whose non-digit chars have been removed'''
        return Normalize.string(s, class_.nonDigit)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Variables:
    '''Replaces, in some text, variables defined with syntax |name| with content
       as found on the homonym attribute of a passed object.'''

    # Regular expression defining a variable (with pipes as delimiters)
    withPipes = re.compile('\|(\w+?)\|', re.S)
    # A variant with asteriscs as delimiters
    withStars = re.compile('\*(\w+?)\*', re.S)

    @classmethod
    def replace(class_, s, o, stars=False):
        '''Replaces, in string p_s, any variable matching class_.definition with
           a value as found on the homonym attribute stored on this
           p_o(bject).'''
        fun = lambda match: getattr(o, match.group(1))
        rex = class_.withStars if stars else class_.withPipes
        return rex.sub(fun, s)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def getStringFrom(o, stringify=True, c="'"):
    '''Returns a string representation for p_o that can be transported over
       HTTP and manipulated in Javascript.

       If p_stringify is True, non-string literals (None, integers, floats...)
       are surrounded by this p_c(har). String literals are always surrounded by
       p_c(hars).
    '''
    if isinstance(o, dict):
        res = []
        for k, v in o.items():
            res.append("%s:%s" % (getStringFrom(k, stringify, c),
                                  getStringFrom(v, stringify, c)))
        return '{%s}' % ','.join(res)
    elif isinstance(o, list) or isinstance(o, tuple):
        return '[%s]' % ','.join([getStringFrom(v, stringify, c) for v in o])
    else:
        # Convert the value to a string
        isString = isinstance(o, str)
        isDate = not isString and (o.__class__.__name__ == 'DateTime')
        if not isString: o = str(o)
        # Manage the special case of dates
        if isDate and not stringify: o = "DateTime('%s')" % o
        # Surround the value by quotes when appropriate
        if isString or stringify:
            o = "%s%s%s" % (c, o.replace(c, "\\%s" % c), c)
        return o

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def getDictFrom(s):
    '''Returns a dict from string representation p_s of the form
       "key1:value1,key2:value2".'''
    r = {}
    if s:
        for part in s.split(','):
            key, value = part.split(':', 1)
            if value:
                r[key] = value
    return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def sadd(s, sub, sep=' ', append=True):
    '''Appends sub-string p_sub into p_s, which is a list of sub-strings
       separated by p_sep, and returns the updated string. If p_append is False,
       p_sub is inserted at the start of p_s instead.'''
    if not sub: return s
    if not s: return sub
    r = s.split(sep)
    for part in sub.split(sep):
        if part not in r:
            if append:
                r.append(part)
            else:
                r.insert(0, part)
    return sep.join(r)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def sremove(s, sub, sep=' '):
    '''Removes sub-string p_sub from p_s, which is a list of sub-strings
       separated by p_sep, and returns the updated string.'''    
    if not sub: return s
    if not s: return s
    r = s.split(sep)
    for part in sub.split(sep):
        if part in r:
            r.remove(part)
    return sep.join(r)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def stringIsAmong(s, l):
    '''Is p_s among list of strings p_l ? p_s can be a string or a
       list/tuple of strings. In this latter case, r_ is True if at least
       one string among p_s is among p_l.'''
    # The simple case: p_s is a string
    if isinstance(s, str): return s in l
    # The complex case: p_s is a list or tuple
    for elem in s:
        if elem in l:
            return True

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def stretchText(s, pattern, char=' '):
    '''Inserts occurrences of p_char within p_s according to p_pattern.
       Example: stretchText("475123456", (3,2,2,2)) returns "475 12 34 56".'''
    res = ''
    i = 0
    for nb in pattern:
        j = 0
        while j < nb:
            res += s[i+j]
            j += 1
        res += char
        i += nb
    return res

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def grammarJoin(l, sep=', ', lastSep=' and '):
    '''Joins list p_l with p_sep, excepted the last 2 elements that are joined
       with p_lastSep. grammarJoin(["a", "b", "c"]) produces "a, b and c".'''
    r = ''
    i = 0
    last = len(l) - 1
    for elem in l:
        # Determine the correct separator to use here
        if i == last:
            curSep = ''
        elif i == last-1:
            curSep = lastSep
        else:
            curSep = sep
        # Add the current element, suffixed with the separator, to the result
        r += elem + curSep
        i += 1
    return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
upperLetter = re.compile('[A-Z]')

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def produceNiceMessage(msg):
    '''Transforms p_msg into a nice msg'''
    r = ''
    if msg:
        r = msg[0].upper()
        for c in msg[1:]:
            if c == '_':
                r += ' '
            elif upperLetter.match(c):
                r += ' ' + c.lower()
            else:
                r += c
    return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def lower(s):
    '''French-accents-aware variant of string.lower'''
    isUnicode = isinstance(s, unicode)
    if not isUnicode: s = s.decode('utf-8')
    res = s.lower()
    if not isUnicode: res = res.encode('utf-8')
    return res

def upper(s):
    '''French-accents-aware variant of string.upper'''
    isUnicode = isinstance(s, unicode)
    if not isUnicode: s = s.decode('utf-8')
    res = s.upper()
    if not isUnicode: res = res.encode('utf-8')
    return res

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class WhitespaceCruncher:
    '''Takes care of removing unnecessary whitespace in several contexts'''

    # Base chars considered as whitespace
    baseChars = ' \r\t\n'

    # Whitechars, as a dict
    whiteChars = asDict(baseChars)

    # Whitechars, including the non-blocking space (nbsp)
    allChars = asDict(baseChars + ' ')

    @classmethod
    def crunch(class_, s, previous=None):
        '''Return a version of string p_s where "whitechars" are removed'''
        # More precisely, whitechars, as listed in p_class_.whiteChars, are:
        # * converted to real whitespace;
        # * reduced in such a way that there cannot be 2 consecutive
        #   whitespace chars.
        # ~~~
        # If p_previous is given, those rules must also apply globally to
        # previous+s.
        r = ''
        # Initialise the previous char
        previousChar = previous[-1] if previous else ''
        wchars = class_.whiteChars
        for char in s:
            if char in wchars:
                # Include the current whitechar in the result if the previous
                # char is not a whitespace or nbsp.
                if not previousChar or (previousChar not in class_.allChars):
                    r += ' '
            else: r += char
            previousChar = char
        # "r" can be a single whitespace. It is up to the caller method to
        # identify when this single whitespace must be kept or crunched.
        return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def randomName(length=3):
    '''Returns a randomly name made of p_length chars'''
    r = []
    for i in range(length):
        r.append(random.choice(string.ascii_letters))
    return ''.join(r)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
