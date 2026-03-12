#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

'''Base evaluators to use for evaluating pod/px expressions and statement
   parts.'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import re

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# As explained in the pod Renderer's constructor, various evaluators can be
# used, depending on your attitude towards security and programming comfort.

# Class Evaluator below is the default appy.pod Evaluator. Unlike other
# evaluators, no instance of it needs to be created: the class itself will be
# used as-is. But you don't even need to know that, because setting Renderer's
# "evaluator" attribute to None will automatically configure this one correctly.

# Class Compromiser tries to establish a well-balanced compromise between
# coders' power and security. Its objective is to let coders express themselves
# while preventing the use of most (in)famous risky Python functions and
# statements. The name of this evaluator has also been chosen for is polysemy:
# by using it, will your production servers be compromised ?

# Finally, for paranoia enthusiasts or large development teams, module
# appy/pod/restricted.py proposes an evaluator that integrates RestrictedPython
# into appy.pod (see details there).

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Evaluator:
    '''Wrapper around the built-in Python function "eval"'''

    @classmethod
    def run(class_, expression, context):
        '''Evaluates p_expression in this p_context'''
        # p_context can be a standard dict or an instance of class
        # appy.model.utils.Object. In this latter case, although it implements
        # dict-like methods, we prefer to unwrap its dict instead of using it
        # directly as context, because it does not raise a KeyError when a key
        # lookup produces no result, but returns None instead.
        context = context if isinstance(context, dict) else context.__dict__
        # Evaluate p_expression
        return eval(expression, None, context)
        # p_context is passed as locals, in order to avoid the "locals" dict to
        # be cloned by the eval function (see https://peps.python.org/pep-0667).
        # Before, v_context was passed as globals and, in that case, the "eval"
        # function added, within it, if not already present, Python built-ins
        # at key '__builtins__'. So, v_context['__builtins__'] was similar to
        # the homonym entry in dict globals().

    @classmethod
    def updateContext(class_, context):
        '''This standard evaluator does not need to update the p_context'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Compromiser:
    '''Evaluator being less permissive than the standard Evaluator class, but
       not as strict as the RestrictedPython-based evaluator.'''

    # Names of standard functions one may not use within pod expressions or
    # statement parts.

    banned = ['exec', 'eval', 'input', 'compile', 'getattr', 'setattr',
              'hasattr', 'open', 'print']

    def __init__(self, banned=None):
        '''Compromiser's constructor'''
        # p_banned may contain names of functions one may not use. If None,
        # defaults to Compromiser.banned.
        banned = banned or Compromiser.banned
        # Build a regular expression allowing to detect banned function names.
        names = '|'.join(banned)
        # The regex contains a negative lookbehind assertion, that will not
        # match the function name if it is part of a larger name (ie,
        # "mycompile" will be allowed, while "compile" will not) or if the
        # function is a method or package-prefixed call (ie, "re.compile" is
        # allowed, while "compile" is not).
        self.banned = re.compile(fr'(?<![a-zA-Z0-9_.]){names}\(')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
