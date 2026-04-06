#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

'''Base evaluators to use for evaluating pod/px expressions and statement
   parts.'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import re

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# As explained in the pod Renderer's constructor, various evaluators can be
# used, depending on your attitude towards security and programming comfort.

# Class Evaluator below is the default appy.pod Evaluator, and also the base
# class to any other Appy built-in or to-build evaluator. When the pod renderer
# is called with evaluator=None (which is the default), an instance of this
# Evaluator class is created and used.

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

    def run(self, expression, context):
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

    def updateContext(self, context):
        '''This standard evaluator does not need to update the p_context'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Compromiser(Evaluator):
    '''Evaluator being less permissive than the standard Evaluator class, but
       not as strict as the RestrictedPython-based evaluator.'''

    # Instances of this class will be raised if the compromiser finds a
    # disallowed element in a pod expression or statement part.

    class Disallowed(Exception): pass

    # Texts explaining that a disallowed element was found
    DIS_MSG = 'Disallowed element found in: "%s".'
    DU_MSG  = 'Attributes, methods or variables having pattern __<name>__ ' \
              'are disallowed. One has been found in "%s".'

    # Names of standard functions and statements one may not use within pod
    # expressions or statement parts.

    banned = ['exec', 'eval', 'input', 'compile', 'getattr', 'setattr',
             'hasattr', 'open', 'print', 'import', 'del', 'global']

    # Regular expression representing a Python method name surrounded by double
    # underscores.
    underscored = re.compile(r'__\w+__')

    @classmethod
    def getBannedRex(class_, banned=None):
        '''Builds and return the regular expression allowing to detect the use
           of these p_banned terms, or p_class_.banned if p_banned is None.'''
        # Get the list of terms to ban
        names = '|'.join(banned or class_.banned)
        # The regex starts with a negative lookbehind assertion and ends with a
        # negative lookahead one: the objective is to avoid matching a banned
        # name if it is part of a larger name (ie, "mycompile" will be allowed,
        # while "compile" will not). Regarding the lookbehind assertion, a
        # second objective is to allow a method or package-prefixed call. For
        # example, "re.compile" is allowed, while "compile" is not.
        return re.compile(fr'(?<![a-zA-Z0-9_.])({names})(?!\w)')

    def __init__(self, banned=None, ban__=True):
        '''Compromiser's constructor'''
        # p_banned may contain names of functions or statements one may not use.
        # If None, defaults to Compromiser.banned.
        self.banned = self.getBannedRex(banned)
        # Must methods whose names are surrounded by double underscores be
        # banned ?
        self.ban__ = ban__

    def detect(self, expr, raiseError=True):
        '''Tries to detect banned terms in this p_expr'''
        # If a banned term is detected and...
        # - p_raiseError is True, an error is raised ;
        # - p_raiseError is False, an error message is returned.
        # If no banned term is detected, the method returns None.
        #
        # Check p_expr against p_self.banned
        if self.banned.search(expr):
            C = Compromiser
            text = C.DIS_MSG % expr
            if raiseError:
                raise C.Disallowed(text)
            else:
                return text
        # Check p_expr against p_self.underscored (if appropriate)
        if self.ban__ and self.underscored.search(expr):
            C = Compromiser
            text = C.DU_MSG % expr
            if raiseError:
                raise C.Disallowed(text)
            else:
                return text

    def run(self, expr, context):
        '''Evaluates this p_expr(ession) in this p_context'''
        # But first, detect the presence of any banned term
        self.detect(expr)
        # If we are here, p_expr can safely be evaluated
        return super().run(expr, context)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
