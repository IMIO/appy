# ~license~
# ------------------------------------------------------------------------------

from appy.pod import PodError
from appy.pod.elements import *
from appy import Object, commercial
from appy.shared.utils import Traceback
from appy.shared.xml_parser import Escape
from appy.shared.errors import CommercialError

# ------------------------------------------------------------------------------
EVAL_ERROR = 'Error while evaluating expression "%s". %s'
FROM_EVAL_ERROR = 'Error while evaluating the expression "%s" defined in the ' \
                  '"from" part of a statement. %s'
WRONG_SEQ_TYPE = 'Expression "%s" is not iterable.'
WRONG_ITERATOR = 'Name "%s" cannot be used for an iterator variable.'
TABLE_NOT_ONE_CELL = "The table you wanted to populate with '%s' " \
                     "can\'t be dumped with the '-' option because it has " \
                     "more than one cell in it."
IF_UNEXEC   = 'The corresponding "if" action was not executed'
NAM_IF_NE   = '%s, there seems to be a structural problem in your if/else ' \
              'statements.' % IF_UNEXEC
UNN_IF_NE   = '%s. Try to name the correspondoing "if" and link this "else" ' \
              'to it.' % IF_UNEXEC

# ------------------------------------------------------------------------------
class EvaluationError(Exception):
    def __init__(self, originalError, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        self.originalError = originalError

# ------------------------------------------------------------------------------
class Action:
    '''Abstract class representing a action (=statement) that must be performed
       on the content of a buffer (if, for...).'''

    # If the action implies evaluating an expression (see attribute "expr"
    # defined in the Action constructor), must the expression result be stored
    # in the context ? By default, no.
    mustStoreExprResult = False

    # Within the context, expression results will be stored in a dict at this
    # key. This dict' keys will correspond to RAM IDs for Action objects.
    storeExprKey = '__e_r__'

    def __init__(self, name, buffer, expr, elem, minus):
        # Actions may be named. Currently, the name of an action is only used
        # for giving a name to "if" actions; thanks to this name, "else" actions
        # that are far away may reference their "if".
        self.name = name
        # The buffer hosting the action
        self.buffer = buffer
        # The Python expression to evaluate (may be None in the case of a
        # Null or Else action, for example).
        self.expr = expr
        # The element within the buffer that is the action's target
        self.elem = elem
        # If "minus" is True, the main elem(s) must not be dumped
        self.minus = minus
        # If "source" is "buffer", we must dump the (evaluated) buffer content.
        # If it is 'from', we must dump what comes from the "from" part of the
        # action (='fromExpr'). See m_setFrom below.
        self.source = 'buffer'
        self.fromExpr = self.fromPlus = None
        # Several actions may co-exist for the same buffer, as a chain of Action
        # instances, defined via the following attribute.
        self.subAction = None

    def setFrom(self, plus, expr):
        '''Associate to this action a "from" clause (pod only)'''
        self.source = 'from'
        self.fromPlus = plus
        self.fromExpr = expr

    def getExceptionLine(self, e):
        '''Gets the line describing exception p_e, containing the exception
           class, message and line number.'''
        return '%s: %s' % (e.__class__.__name__, str(e))

    def manageError(self, result, context, errorMessage, originalError=None):
        '''Manage the encountered error: dump it into the buffer or raise an
           exception.'''
        if self.buffer.env.raiseOnError:
            if not self.buffer.pod:
                # Add in the error message the line nb where the errors occurs
                # within the PX.
                locator = self.buffer.env.parser.locator
                # The column number may not be given
                col = locator.getColumnNumber()
                if col is None: col = ''
                else: col = ', column %d' % col
                errorMessage += ' (line %s%s)' % (locator.getLineNumber(), col)
                # Integrate the traceback (at least, its last lines)
                errorMessage += '\n' + Traceback.get(6).decode('utf-8')
            if originalError:
                raise EvaluationError(originalError, errorMessage)
            raise Exception(errorMessage)
        # Create a temporary buffer to dump the error. If I reuse this buffer to
        # dump the error (what I did before), and we are, at some depth, in a
        # for loop, this buffer will contain the error message and not the
        # content to repeat anymore. It means that this error will also show up
        # for every subsequent iteration.
        tempBuffer = self.buffer.clone()
        PodError.dump(tempBuffer, errorMessage, withinElement=self.elem)
        tempBuffer.evaluate(result, context)

    def _evalExpr(self, expr, context):
        '''Evaluates p_expr with p_context. p_expr can contain an error expr,
           in the form "someExpr|errorExpr". If it is the case, if the "normal"
           expr raises an error, the "error" expr is evaluated instead.'''
        eval = context['_eval_'].run
        if '|' not in expr:
            res = eval(expr, context)
        else:
            expr, errorExpr = expr.rsplit('|', 1)
            try:
                res = eval(expr, context)
            except Exception:
                res = eval(errorExpr, context)
        return res

    def storeExprResult(self, r, context):
        '''Store this expression evaluation p_r(esult) in the context'''
        key = self.storeExprKey
        if key in context:
            context[key][id(self)] = r
        else:
            context[key] = {id(self): r}

    def evaluateExpression(self, result, context, expr):
        '''Evaluates expression p_expr with the current p_context. Returns a
           tuple (result, errorOccurred).'''
        try:
            res = self._evalExpr(expr, context)
            error = False
        except Exception, e:
            # Hack for MessageException instances: always re-raise it as is
            if e.__class__.__name__ == 'MessageException': raise e
            res = None
            line = self.getExceptionLine(e)
            try:
                errorMessage = EVAL_ERROR % (expr, line)
            except UnicodeDecodeError:
                errorMessage = EVAL_ERROR % (expr, line.decode('utf-8'))
            self.manageError(result, context, errorMessage, e)
            error = True
        return res, error

    def execute(self, result, context):
        '''Executes this action given some p_context and add the result to
           p_result.'''
        # Check that if minus is set, we have an element which can accept it
        if self.minus and isinstance(self.elem, Table) and \
           (not self.elem.tableInfo.isOneCell()):
            self.manageError(result, context, TABLE_NOT_ONE_CELL % self.expr)
        else:
            error = False
            # Evaluate self.expr in eRes
            eRes = None
            expr = self.expr
            if expr:
                eRes, error = self.evaluateExpression(result, context, expr)
            if not error:
                # Store the expression result in the context if relevant
                if expr and self.mustStoreExprResult:
                    self.storeExprResult(eRes, context)
                # Trigger action-specific behaviour
                self.do(result, context, eRes)

    def getBufferSlice(self, context):
        '''If only a slice of the tied buffer must be evaluated, this method
           returns a tuple (startIndex, endIndex). In that case, only
           p_self.buffer.content[startIndex, endIndex] will be dumped in the POD
           result.'''
        return

    def evaluateBuffer(self, result, context,
                       forceSource=None, ignoreMinus=False):
        '''Evaluates the buffer tied to this action and add the result in
           p_result. The source for evaluation can be forced to p_forceSource
           but in most cases depends on self.source.'''
        # Determine the source
        source = forceSource or self.source
        # Determine "minus"
        if ignoreMinus:
            minus = False
        else:
            minus = self.minus
        if source == 'buffer':
            self.buffer.evaluate(result, context, removeMainElems=minus,
                                 slice=self.getBufferSlice(context))
            # m_getBufferSlice may determine if only a slice [start,end] of the
            # buffer content must be dumped in the POD result.
        else:
            # Evaluate self.fromExpr in fromRes
            fromRes = None
            error = False
            try:
                fromRes = context['_eval_'].run(self.fromExpr, context)
            except Exception, e:
                msg = FROM_EVAL_ERROR % (self.fromExpr,self.getExceptionLine(e))
                self.manageError(result, context, msg, e)
                error = True
            if not error:
                if not self.fromPlus:
                    # Write the result
                    result.write(fromRes)
                else:
                    # We must keep the root tag within self.buffer and dump the
                    # result into it.
                    content = self.buffer.content
                    result.write(content[:content.find('>') + 1])
                    result.write(fromRes)
                    result.write(content[content.rfind('<'):])

    def addSubAction(self, action):
        '''Adds p_action as a sub-action of this action'''
        if not self.subAction:
            self.subAction = action
            # Transmit "minus" to the sub-action. Indeed, the responsiblity to
            # dump content in the buffer is delegated to the sub-action,
            # "minus-ity" included.
            action.minus = self.minus
        else:
            self.subAction.addSubAction(action)

    def getAction(self, type):
        '''If p_self or one of its sub-actions (recursively) is of this p_type,
           returns it.'''
        # Return p_self itself, if it has this p_type
        if self.__class__.__name__ == type: return self
        # Check subAction
        sub = self.subAction
        if not sub: return
        return sub.getAction(type)

    def check(self):
        '''Returns a tuple (success, message) indicating if the action is well
           formed or not.'''
        return True, None

class If(Action):
    '''Action that determines if we must include the content of the buffer in
       the result or not.'''

    # The result of evaluating an "if" expression will be stored in the context.
    # That way, it can be reused by an "else" statement.
    mustStoreExprResult = True

    def do(self, result, context, exprRes):
        if exprRes:
            if self.subAction:
                self.subAction.execute(result, context)
            else:
                self.evaluateBuffer(result, context)
        else:
            if self.buffer.isMainElement(Cell.OD):
                # Don't leave the current row with a wrong number of cells
                result.dumpElement(Cell.OD.elem)

class Else(If):
    '''Action that is linked to a previous "if" action. In fact, an "else"
       action works exactly like an "if" action, excepted that instead of
       defining a conditional expression, it is based on the negation of the
       conditional expression of the last defined "if" action.'''

    def __init__(self, name, buff, expr, elem, minus, ifAction):
        If.__init__(self, name, buff, None, elem, minus)
        self.ifAction = ifAction

    def do(self, result, context, exprRes):
        '''Execute this "else" action: it occurs when the tied "if" action is
           not executed.'''
        # Retrieve the tied if's evaluation result
        evals = context[self.storeExprKey]
        actionId = id(self.ifAction)
        if actionId in evals:
            If.do(self, result, context, not evals[actionId])
        else:
            # The corresponding "if" action has not bee executed (was probably
            # included in a buffer whose main "if" action resolved to False).
            message = self.name and NAM_IF_NE or UNN_IF_NE
            self.manageError(result, context, message)

class For(Action):
    '''Actions that will include the content of the buffer as many times as
       specified by the action parameters.'''

    def __init__(self, name, buff, expr, elem, minus, iters):
        Action.__init__(self, name, buff, expr, elem, minus)
        # Name of the iterator variable(s) used in each loop
        self.iters = iters

    def initialiseLoop(self, context, elems):
        '''Initialises information about the loop, before entering into it. It
           is possible that this loop overrides an outer loop whose iterator
           has the same name. This method returns a tuple
           (loop, outerOverriddenLoop).'''
        # The "loop" object, made available in the POD context, contains info
        # about all currently walked loops. For every walked loop, a specific
        # object, accessible at getattr(loop, self.iters[0]), stores info about
        # its status:
        # ----------------------------------------------------------------------
        #  length   | the total number of walked elements within the loop
        # ----------------------------------------------------------------------
        #  nb       | the index (starting at 0) of the currently walked element
        # ----------------------------------------------------------------------
        #  first    | True if the currently walked element is the first one
        # ----------------------------------------------------------------------
        #  last     | True if the currently walked element is the last one
        # ----------------------------------------------------------------------
        #  odd      | True if the currently walked element is odd
        # ----------------------------------------------------------------------
        #  even     | True if the currently walked element is even
        # ----------------------------------------------------------------------
        #  previous | Points to the previous element, if any
        # ----------------------------------------------------------------------
        # For example, if you have a "for" statement like this:
        #                 for elem in myListOfElements
        # Within the part of the ODT document impacted by this statement, you
        # may access to loop.elem.length to know the total length of
        # myListOfElements, or loop.elem.nb to know the index of the current
        # elem within myListOfElements.
        if 'loop' not in context:
            # Attribute "_all_" stores the list of all currently running loops
            loops = context['loop'] = Object(_all_=[])
        else:
            loops = context['loop']
        try:
            total = len(elems)
        except Exception:
            total = 0
        curLoop = Object(length=total, previous=None, buffer=self.buffer)
        loops._all_.append(curLoop)
        # Does this loop override an outer loop with homonym iterator ?
        outerLoop = None
        iter = self.iters[0]
        if hasattr(loops, iter):
            outerLoop = getattr(loops, iter)
        # Put this loop in the global object "loop"
        setattr(loops, iter, curLoop)
        return curLoop, outerLoop

    def updateContext(self, context, item, forcedValue=None):
        '''We are in the loop, and p_item is the currently walked item. We must
           update the context by adding or updating values for iterator
           variable(s).'''
        # In most cases, there is a single iterator variable: for x in list
        names = self.iters
        if len(names) == 1:
            if forcedValue is None:
                value = item
            else:
                value = forcedValue
            context[names[0]] = value
        # This is the case: for a, b, c in list
        else:
            i = 0
            while i < len(names):
                if forcedValue is None:
                    value = item[i]
                else:
                    value = forcedValue
                context[names[i]] = value
                i += 1

    def do(self, result, context, elems):
        '''Performs the "for" action. p_elems is the list of elements to
           walk, evaluated from self.expr.'''
        # Check p_exprRes type
        try:
            # All "iterable" objects are OK
            iter(elems)
        except TypeError, te:
            self.manageError(result, context, WRONG_SEQ_TYPE % self.expr, te)
            return
        # Remember variables hidden by iterators if any
        hiddenVars = {}
        for name in self.iters:
            # Prevent reserved names to be used
            if name == '_all_':
                self.manageError(result, context, WRONG_ITERATOR % name)
                return
            if name in context:
                hiddenVars[name] = context[name]
        # In the case of cells, initialize some values
        isCell = False
        if isinstance(self.elem, Cell):
            isCell = True
            if 'columnsRepeated' in context:
                # This feature is only available in the open source version
                if commercial: raise CommercialError()
                nbOfColumns = sum(context['columnsRepeated'])
                customColumnsRepeated = True
            else:
                nbOfColumns = self.elem.tableInfo.nbOfColumns
                customColumnsRepeated = False
            initialColIndex = self.elem.colIndex
            currentColIndex = initialColIndex
            rowAttributes = self.elem.tableInfo.curRowAttrs
            # If p_elems is empty, dump an empty cell to avoid having the wrong
            # number of cells for the current row.
            if not elems:
                result.dumpElement(Cell.OD.elem)
        # Enter the "for" loop
        loop, outerLoop = self.initialiseLoop(context, elems)
        i = -1
        for item in elems:
            i += 1
            loop.nb = i
            loop.first = i == 0
            loop.last = i == (loop.length-1)
            loop.even = (i%2)==0
            loop.odd = not loop.even
            self.updateContext(context, item)
            # Cell: add a new row if we are at the end of a row
            if isCell and currentColIndex == nbOfColumns:
                result.dumpEndElement(Row.OD.elem)
                result.dumpStartElement(Row.OD.elem, rowAttributes)
                currentColIndex = 0
            # If a sub-action is defined, execute it
            if self.subAction:
                self.subAction.execute(result, context)
            else:
                # Evaluate the buffer directly
                self.evaluateBuffer(result, context)
            # Cell: increment the current column index
            if isCell:
                currentColIndex += 1
            loop.previous = item
        # Cell: leave the last row with the correct number of cells, excepted
        # if the user has specified himself "columnsRepeated": it is his
        # responsibility to produce the correct number of cells.
        if isCell and elems and not customColumnsRepeated:
            wrongNbOfCells = (currentColIndex-1) - initialColIndex
            if wrongNbOfCells < 0: # Too few cells for last row
                for i in range(abs(wrongNbOfCells)):
                    self.updateContext(context, None, forcedValue='')
                    self.buffer.evaluate(result, context, subElements=False)
                    # This way, the cell is dumped with the correct styles
            elif wrongNbOfCells > 0: # Too many cells for last row
                # Finish current row
                nbOfMissingCells = 0
                if currentColIndex < nbOfColumns:
                    nbOfMissingCells = nbOfColumns - currentColIndex
                    self.updateContext(context, None, forcedValue='')
                    for i in range(nbOfMissingCells):
                        self.buffer.evaluate(result, context, subElements=False)
                result.dumpEndElement(Row.OD.elem)
                # Create additional row with remaining cells
                result.dumpStartElement(Row.OD.elem, rowAttributes)
                nbOfRemainingCells = wrongNbOfCells + nbOfMissingCells
                nbOfMissingCellsLastLine = nbOfColumns - nbOfRemainingCells
                self.updateContext(context, None, forcedValue='')
                for i in range(nbOfMissingCellsLastLine):
                    self.buffer.evaluate(result, context, subElements=False)
        # Delete the current loop object and restore the overridden one if any
        loops = context['loop']
        name = self.iters[0]
        try:
            delattr(loops, name)
        except AttributeError:
            pass
        if outerLoop:
            setattr(loops, name, outerLoop)
        loops._all_.pop()
        # Restore hidden variables and remove iterator variables from the
        # context.
        context.update(hiddenVars)
        if elems:
            for name in self.iters:
                if (name not in hiddenVars) and (name in context):
                    # On error, name may not be in the context
                    del context[name]

    def getBufferSlice(self, context):
        '''When processing a "do doc" statement, depending on the current
           iteration, only a specific slice of the buffer must be dumped.'''
        if not isinstance(self.elem, Doc): return
        # Get the current loop object
        loop = getattr(context['loop'], self.iters[0])
        # If there is a single iteration, do no alter anything
        if loop.length == 1: return
        # Dump only a part of the complete buffer, depending on the current
        # iteration.
        end = self.buffer.content.rfind(self.elem.END_TAG)
        if loop.first:
            # Dump the start of the buffer, but not the very last end tag
            return 0, end
        else:
            # Remove the start of the doc: it must only be dumped once
            sd = self.elem.SD_END_TAG
            start = self.buffer.content.find(sd) + len(sd)
            if loop.last:
                # Dump the end tag
                return start, len(self.buffer.content)
            else:
                # Still do not dump the end tag
                return start, end

class Null(Action):
    '''Action that does nothing. Used in conjunction with a "from" clause, it
       allows to insert in a buffer arbitrary odt content.'''
    noFromError = 'There was a problem with this action. Possible causes: ' \
      '(1) you specified no action (ie "do text") while not specifying any ' \
      'from clause; (2) you specified the from clause on the same line as ' \
      'the action, which is not allowed (ie "do text from ...").'

    def __init__(self, buff, elem):
        Action.__init__(self, '', buff, None, elem, None)

    def do(self, result, context, exprRes):
        self.evaluateBuffer(result, context)

    def check(self):
        '''This action must have a tied from clause'''
        if self.source != 'from':
            return False, self.noFromError
        return True, None

class MetaIf(Action):
    '''Action allowing a note not to be evaluated and re-dumped as-is in the
       result, depending on some (meta-) condition.'''

    def __init__(self, buff, subExpr, elem, minus, statements):
        Action.__init__(self, '', buff, subExpr, elem, minus)
        # The list of statements containing in the original note
        self.statements = statements

    def reifyNote(self):
        '''Recreate the note as close to the original as possible'''
        # Use some fake buffer and dump the note in it. Reuse the code for
        # dumping an error, also dumped as a note.
        buf = self.buffer.clone()
        statements = [Escape.xml(st) for st in self.statements]
        PodError.dump(buf, u'</text:p>\n<text:p>'.join(statements),
                      dumpTb=False, escapeMessage=False)
        return buf

    def do(self, result, context, exprRes):
        if exprRes:
            # The "meta-if" condition is True. It means that content must really
            # be dumped.
            if self.subAction:
                self.subAction.execute(result, context)
            else:
                self.evaluateBuffer(result, context)
        else:
            # The note must be dumped unevaluated in the result; the potential
            # "from" expression must not be evaluated as well.
            note = self.reifyNote()
            # Inject the note in the buffer, after the first 'text:p' tag: else,
            # it might not be rendered. self.minus must not be interpreted. When
            # reifying several notes in the same paragraph, ensure they are
            # reified in order, by forcing to insert a note after another one.
            self.buffer.insertSubBuffer(note, after='text:p',
                                        afterClosing='office:annotation')
            self.evaluateBuffer(result, context,
                                forceSource='buffer', ignoreMinus=True)

class Variables(Action):
    '''Action that allows to define a set of variables somewhere in the
       template.'''

    def __init__(self, name, buff, elem, minus, variables, lasting=False):
        # The default Buffer.expr attribute is not used for storing the Python
        # expression, because several expressions can exist here, one for
        # every defined variable.
        Action.__init__(self, name, buff, None, elem, minus)
        # Definitions of variables: ~[(s_name|[s_name], s_expr)]~
        self.variables = variables
        # If p_lasting is:
        # ----------------------------------------------------------------------
        # False | (the default) every variable's scope will be the target
        #       | element (as determined by the corresponding buffer), not more.
        #       | Any homonym variable being defined in the outer scope will be
        #       | hidden in the context of the target element, and will be
        #       | visible again as soon as the walk leaves this sub-scope.
        # ----------------------------------------------------------------------
        # True  | From the moment such a "lasting" variable is defined, its
        #       | scope will be the remaining of the document. So, its scope
        #       | encompasses the target element + the remaining of the
        #       | document. Any homonym variable being previously defined will
        #       | be hidden forever, as soon as the lasting variable is defined.
        # ----------------------------------------------------------------------
        self.lasting = lasting

    def storeVariable(self, name, value, context, hidden):
        '''Adds a variable named p_name with this p_value in the p_context.
           Updates the dict of p_hidden variables and r_eturn it.'''
        if name.startswith('@'):
            # "name" represents a global variable. Update its value in the
            # context with p_value.
            context[name[1:]] = value
        else:
            # Store variable p_name with p_value in the p_context. If this
            # variable already exists in the context, remember its previous
            # value in p_hidden, excepted if the currently defined variables are
            # lasting.
            if not self.lasting and name in context:
                if not hidden:
                    hidden = {name: context[name]}
                else:
                    hidden[name] = context[name]
            # Store the result into the context
            context[name] = value
        return hidden

    def removeVariable(self, name, context, hidden):
        '''Remove, when relevant, variable p_name from the p_context'''
        # Do not remove it if it is a global variable
        if name.startswith('@'): return
        # Do not remove it if it is an overridden variable
        if hidden and name in hidden: return
        del context[name]

    def do(self, result, context, exprRes):
        '''Evaluate the variables' expressions'''

        # Because there are several expressions, the standard,
        # single-expression-minded Action code is not used for evaluating
        # expressions.

        # If the currently defined variables are not lasting, the names and
        # values of the variables that will be hidden in the context will be
        # stored: after execution of this buffer, their values will be restored.

        hidden = None
        for names, expr in self.variables:
            # Evaluate variable expression in v_value
            value, error = self.evaluateExpression(result, context, expr)
            if error: return
            if isinstance(names, basestring):
                # A single variable name
                hidden = self.storeVariable(names, value, context, hidden)
            else:
                # There are several variables whose values must be initialized
                # by unpacking v_values.
                i = -1
                for name in names:
                    i += 1
                    hidden = self.storeVariable(name, value[i], context, hidden)
        # If a sub-action is defined, execute it
        if self.subAction:
            self.subAction.execute(result, context)
        else:
            # Evaluate the buffer directly
            self.evaluateBuffer(result, context)
        # Restore hidden variables if any
        if hidden: context.update(hidden)
        # Delete not-hidden variables, if not lasting
        if not self.lasting:
            for names, expr in self.variables:
                if isinstance(names, basestring):
                    self.removeVariable(names, context, hidden)
                else:
                    for name in names:
                        self.removeVariable(name, context, hidden)
# ------------------------------------------------------------------------------
