'''Module implementing Javascript-related functionality'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import re

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Quote:
    '''This class escapes strings to be integrated as Javascript string literals
       in Javascript code, and, once escaped, quotes them.'''

    # The "escaping" part of this class is inspired by class appy/xml/Escape
    rex = re.compile("[\n\t\r']")
    blanks = {'\n':'', '\t':'', '\r':''}

    # There are 2 ways to escape a single quote
    values = {True: {"'": '&apos;'}, False: {"'": "\\'"}}
    for d in values.values(): d.update(blanks)

    # Match functions, used by m_js below. Dict keys represent values for
    # parameter "withEntity".
    matchFunctions = {
      True : lambda match: Quote.values[True][match.group(0)],
      False: lambda match: Quote.values[False][match.group(0)],
    }

    @classmethod
    def js(class_, s, withEntity=True):
        '''Escapes blanks and single quotes in string p_s. Single quotes are
           escaped with a HTML entity if p_withEntity is True or with a quote
           prefixed with a "backslash" char else. Returns p_s, escaped and
           quoted.'''
        s = s if isinstance(s, str) else str(s)
        fun = class_.matchFunctions[withEntity]
        return f"'{class_.rex.sub(fun, s)}'"
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
