'''Functions for evaluating Python expressions in a secure way'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

import urllib.parse
from DateTime import DateTime # Used as context for m_evalDict

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# The restricted evaluation context for evaluating expressions
context = {'DateTime': DateTime}
empty = {} # Will be used as local context

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def evalDict(s, urlDecode=False):
    '''Evaluates the dict as marshalled into p_s'''
    if not s: return
    if urlDecode:
        s = urllib.parse.unquote(s)
    if s[0] != '{' or s[-1] != '}': return
    return eval(s, context, empty)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
