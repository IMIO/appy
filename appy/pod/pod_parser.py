# ~license~
# ------------------------------------------------------------------------------
import re

from appy.pod.elements import *
from appy.pod.graphic import Graphic
from appy.shared.xml_parser import XmlElement
from appy.pod.buffers import FileBuffer, MemoryBuffer
from appy.pod.odf_parser import OdfEnvironment, OdfParser

# ------------------------------------------------------------------------------
class OdTable:
    '''Informations about the currently parsed Open Document (Od)table'''

    def __init__(self, name=None):
        self.name = name
        self.nbOfColumns = 0
        self.nbOfRows = 0
        self.curColIndex = None
        self.curRowAttrs = None

    def isOneCell(self):
        return self.nbOfColumns == 1 and self.nbOfRows == 1

class OdInsert:
    '''While parsing an odt/pod file, we may need to insert a specific odt chunk
       at a given place in the odt file (ie: add the pod-specific fonts and
       styles). OdInsert instances define such 'inserts' (what to insert and
       when).'''
    def __init__(self, odtChunk, elem, nsUris={}):
        self.odtChunk = odtChunk.decode('utf-8') # The odt chunk to insert
        # The p_odtChunk will be inserted just after the p_elem starts, which
        # must be an XmlElement instance. If more than one p_elem is present in
        # the odt file, the p_odtChunk will be inserted only at the first
        # p_elem occurrence.
        self.elem = elem

class PodEnvironment(OdfEnvironment):
    '''Contains all elements representing the current parser state during
       parsing.'''
    # Possibles modes
    # ADD_IN_BUFFER: when encountering an impactable element, we must
    #                continue to dump it in the current buffer
    ADD_IN_BUFFER = 0
    # ADD_IN_SUBBUFFER: when encountering an impactable element, we must
    #                   create a new sub-buffer and dump it in it.
    ADD_IN_SUBBUFFER = 1
    # Possible states
    IGNORING = 0 # We are ignoring what we are currently reading
    READING_CONTENT = 1 # We are reading "normal" content
    READING_STATEMENT = 2 # We are reading a POD statement (for, if...)
    READING_EXPRESSION = 3 # We are reading a POD expression.
    # Tags that will be read within notes
    NOTE_TAGS = ('text:p', 'text:span')
    # Start and end tags for every expression holder
    exprStartTags = {
      'if': 'text:conditional-text', 'change': 'text:change-start',
      'input': 'text:text-input', 'db': 'text:database-display'}
    exprEndTags = {
      'if': 'text:conditional-text', 'change': 'text:change-end',
      'input': 'text:text-input', 'db': 'text:database-display'}

    def __init__(self, context, inserts, expressionsHolders):
        OdfEnvironment.__init__(self)
        # Buffer where we must dump the content we are currently reading
        self.currentBuffer = None
        # XML element content we are currently reading
        self.currentContent = ''
        # Current statement (a list of lines) that we are currently reading
        self.currentStatement = []
        # Current mode
        self.mode = self.ADD_IN_SUBBUFFER
        # Current state
        self.state = self.READING_CONTENT
        # Elements we must ignore (they will not be included in the result)
        self.ignorableElems = None # Will be set after namespace propagation
        # Elements that may be impacted by POD statements
        self.impactableElems = None # Idem
        # Elements representing start and end tags surrounding expressions
        self.exprStartElems = self.exprEndElems = None # Idem
        # Stack of currently visited tables
        self.tableStack = []
        self.tableIndex = -1
        # Evaluation context
        self.context = context
        # For the currently read expression, is there style-related information
        # associated with it?
        self.exprHasStyle = False
        # Namespace definitions are not already encountered.
        self.gotNamespaces = False
        # Store inserts
        self.inserts = inserts
        # Currently walked "if" actions
        self.ifActions = []
        # Currently walked named "if" actions
        self.namedIfActions = {} #~{s_statementName: appy.pod.actions.If}~
        # Currently parsed expression within an ODS template
        self.currentOdsExpression = None
        self.currentOdsHook = None
        # A Graphic object representing the currently parsed pod graphic
        self.currentOdsGraphic = None
        # A dict of Appy-controlled graphics ~{s_path: Graphic}~. s_path refers
        # to the folder, within the pod result, where LO stores the graphic.
        self.odsGraphics = None
        # Currently parsed expression from a database-display field
        self.currentDbExpression = None
        # Names of some tags, that we will compute after namespace propagation
        self.tags = None
        # When an error occurs, must we raise it or write it into he current
        # buffer?
        self.raiseOnError = None # Will be initialized by PodParser.__init__
        # The expressions holders in use
        self.expressionsHolders = expressionsHolders

    def getTable(self):
        '''Gets the currently parsed table'''
        res = None
        if self.tableIndex != -1:
            res = self.tableStack[self.tableIndex]
        return res

    def transformInserts(self):
        '''Now the namespaces were parsed; I can put p_inserts in the form of a
           dict for easier and more performant access while parsing.'''
        res = {}
        if not self.inserts: return res
        for insert in self.inserts:
            elemName = insert.elem.getFullName(self.namespaces)
            if not res.has_key(elemName):
                res[elemName] = insert
        return res

    def manageInserts(self, elem):
        '''We just dumped the start of an elem. Here we will insert any odt
           chunk if needed.'''
        if self.inserts.has_key(elem):
            insert = self.inserts[elem]
            self.currentBuffer.write(insert.odtChunk)
            # The insert is destroyed after single use
            del self.inserts[elem]

    def onStartElement(self, elem, attrs):
        ns = self.namespaces
        if not self.gotNamespaces:
            # We suppose that all the interesting (from the POD point of view)
            # XML namespace definitions are defined at the root XML element.
            # Here we propagate them in XML element definitions that we use
            # throughout POD.
            self.gotNamespaces = True
            self.propagateNamespaces()
        tableNs = self.ns(self.NS_TABLE)
        if elem == Table.OD.elem:
            name = attrs.get('table:name')
            self.tableStack.append(OdTable(name=name))
            self.tableIndex += 1
        elif elem == Row.OD.elem:
            table = self.getTable()
            table.nbOfRows += 1
            table.curColIndex = -1
            table.curRowAttrs = attrs
        elif elem == Cell.OD.elem:
            colspan = 1
            attrSpan = self.tags['number-columns-spanned']
            if attrs.has_key(attrSpan):
                colspan = int(attrs[attrSpan])
            self.getTable().curColIndex += colspan
        elif elem == self.tags['table-column']:
            table = self.getTable()
            cols = self.tags['number-columns-repeated']
            if attrs.has_key(cols):
                table.nbOfColumns += int(attrs[cols])
            else:
                table.nbOfColumns += 1
        elif elem == 'draw:object' and self.currentOdsGraphic:
            self.currentOdsGraphic.register(self, attrs)
        return ns

    def onEndElement(self):
        ns = self.namespaces
        if self.currentElem.elem == Table.OD.elem:
            self.tableStack.pop()
            self.tableIndex -= 1
        return ns

    def addSubBuffer(self):
        subBuffer = self.currentBuffer.addSubBuffer()
        self.currentBuffer = subBuffer
        self.mode = self.ADD_IN_BUFFER

    def propagateNamespaces(self):
        '''Propagates the namespaces in all XML element definitions that are
           used throughout POD.'''
        ns = self.namespaces
        for elemName in PodElement.POD_ELEMS:
            xmlElemDef = eval(elemName[0].upper() + elemName[1:]).OD
            elemFullName = xmlElemDef.getFullName(ns)
            xmlElemDef.__init__(elemFullName)
        # Create a table of names of used tags and attributes (precomputed,
        # including namespace, for performance).
        table = ns[self.NS_TABLE]
        text = ns[self.NS_TEXT]
        office = ns[self.NS_OFFICE]
        tags = {
          'tracked-changes': '%s:tracked-changes' % text,
          'change': '%s:change' % text,
          'annotation': '%s:annotation' % office,
          'table': '%s:table' % table,
          'table-name': '%s:name' % table,
          'table-cell': '%s:table-cell' % table,
          'table-column': '%s:table-column' % table,
          'formula': '%s:formula' % table,
          'value-type': '%s:value-type' % office,
          'value': '%s:value' % office,
          'string-value': '%s:string-value' % office,
          'span': '%s:span' % text,
          'number-columns-spanned': '%s:number-columns-spanned' % table,
          'number-columns-repeated': '%s:number-columns-repeated' % table,
        }
        self.tags = tags
        self.ignorableElems = (tags['tracked-changes'], tags['change'])
        self.exprStartElems = [self.exprStartTags[holder] \
                               for holder in self.expressionsHolders]
        self.exprEndElems = [self.exprEndTags[holder] \
                             for holder in self.expressionsHolders]
        self.impactableElems = (Text.OD.elem, Title.OD.elem, Item.OD.elem,
                                Table.OD.elem, Row.OD.elem, Cell.OD.elem,
                                Section.OD.elem, Frame.OD.elem, Doc.OD.elem)
        self.inserts = self.transformInserts()

    def getExpression(self, elem):
        '''We have found a pod expression within p_elem, get its value'''
        # Expression may have been found at various places
        if self.currentDbExpression:
            r = self.currentDbExpression
            self.currentDbExpression = None
        else:
            r = self.currentContent
        self.currentContent = ''
        return r.strip()

# ------------------------------------------------------------------------------
class PodParser(OdfParser):
    def __init__(self, env, caller):
        OdfParser.__init__(self, env, caller)
        env.raiseOnError = caller.raiseOnError

    def endDocument(self):
        self.env.currentBuffer.content.close()

    def startElement(self, elem, attrs):
        e = OdfParser.startElement(self, elem, attrs)
        ns = e.onStartElement(elem, attrs)
        officeNs = ns[e.NS_OFFICE]
        textNs = ns[e.NS_TEXT]
        tableNs = ns[e.NS_TABLE]
        if elem in e.ignorableElems:
            e.state = e.IGNORING
        elif elem == e.tags['annotation']:
            # Be it in an ODT or ODS template, an annotation is considered to
            # contain a POD statement.
            e.state = e.READING_STATEMENT
        elif elem in e.exprStartElems:
            # Any track-changed text or being in a conditional or input field is
            # considered to be a POD expression.
            e.state = e.READING_EXPRESSION
            e.exprHasStyle = False
            if (elem == 'text:database-display') and \
               attrs.has_key('text:column-name'):
                e.currentDbExpression = attrs['text:column-name']
        elif (elem == e.tags['table-cell']) and \
             attrs.has_key(e.tags['formula']) and \
             attrs.has_key(e.tags['value-type']) and \
             (attrs[e.tags['value-type']] == 'string') and \
             attrs[e.tags['formula']].startswith('of:="'):
            # In an ODS template, any cell containing a formula of type "string"
            # and whose content is expressed as a string between double quotes
            # (="...") is considered to contain a POD expression. But here it
            # is a special case: we need to dump the cell; the expression is not
            # directly contained within this cell; the expression will be
            # contained in the next inner paragraph. So we must here dump the
            # cell, but without some attributes, because the "formula" will be
            # converted to the result of evaluating the POD expression.
            if e.mode == e.ADD_IN_SUBBUFFER:
                e.addSubBuffer()
            e.currentBuffer.addElement(e.currentElem.name)
            hook = e.currentBuffer.dumpStartElement(elem, attrs,
                     ignoreAttrs=(e.tags['formula'], e.tags['string-value'],
                                  e.tags['value-type']),
                     hook=True)
            # We already have the POD expression: remember it on the env
            e.currentOdsExpression = attrs[e.tags['string-value']]
            e.currentOdsHook = hook
        else:
            if e.state == e.IGNORING:
                pass
            elif e.state == e.READING_CONTENT:
                # Dump an Element object if the current tag is impactable
                if elem in e.impactableElems:
                    if e.mode == e.ADD_IN_SUBBUFFER:
                        e.addSubBuffer()
                    e.currentBuffer.addElement(e.currentElem.name)
                    graphic = Graphic.get(elem, attrs, e)
                else:
                    graphic = None
                # Dump the start tag in the current buffer
                e.currentBuffer.dumpStartElement(elem, attrs)
                # If a pod graphic is encountered, get info allowing to
                # complete it afterwards.
                if graphic:
                    e.currentOdsGraphic = graphic
            elif e.state == e.READING_STATEMENT:
                pass
            elif e.state == e.READING_EXPRESSION:
                if (elem == (e.tags['span'])) and not e.currentContent.strip():
                    e.currentBuffer.dumpStartElement(elem, attrs)
                    e.exprHasStyle = True
        e.manageInserts(elem)

    def endElement(self, elem):
        e = self.env
        ns = e.onEndElement()
        current = e.currentElem
        OdfParser.endElement(self, elem) # Pops the currently walked element
        officeNs = ns[e.NS_OFFICE]
        textNs = ns[e.NS_TEXT]
        if elem in e.ignorableElems:
            e.state = e.READING_CONTENT
        elif elem == e.tags['annotation']:
            # Manage statement
            oldCb = e.currentBuffer
            actionElemIndex = oldCb.createPodActions(e.currentStatement)
            e.currentStatement = []
            if actionElemIndex != -1:
                e.currentBuffer = oldCb.\
                    transferActionIndependentContent(actionElemIndex)
                if e.currentBuffer == oldCb:
                    e.mode = e.ADD_IN_SUBBUFFER
                else:
                    e.mode = e.ADD_IN_BUFFER
            e.state = e.READING_CONTENT
        else:
            if e.state == e.IGNORING:
                pass
            elif e.state == e.READING_CONTENT:
                # Dump the ODS POD expression if any
                if e.currentOdsExpression:
                    e.currentBuffer.addExpression(e.currentOdsExpression,
                                                  tiedHook=e.currentOdsHook)
                    e.currentOdsExpression = None
                    e.currentOdsHook = None
                # Dump the ending tag
                e.currentBuffer.dumpEndElement(elem)
                if elem in e.impactableElems:
                    if isinstance(e.currentBuffer, MemoryBuffer):
                        isMainElement = e.currentBuffer.isMainElement(elem)
                        # Unreference the element among buffer.elements
                        e.currentBuffer.unreferenceElement(elem)
                        if isMainElement:
                            parent = e.currentBuffer.parent
                            if not e.currentBuffer.action:
                                # Delete this buffer and transfer content to
                                # parent.
                                e.currentBuffer.transferAllContent()
                                parent.removeLastSubBuffer()
                                e.currentBuffer = parent
                            else:
                                if isinstance(parent, FileBuffer):
                                    # Execute buffer action and delete the
                                    # buffer.
                                    e.currentBuffer.action.execute(parent,
                                                                   e.context)
                                    parent.removeLastSubBuffer()
                                e.currentBuffer = parent
                            e.mode = e.ADD_IN_SUBBUFFER
            elif e.state == e.READING_STATEMENT:
                if elem == Text.OD.elem:
                    statementLine = e.currentContent.strip()
                    if statementLine:
                        e.currentStatement.append(statementLine)
                    e.currentContent = ''
            elif e.state == e.READING_EXPRESSION:
                if elem in e.exprEndElems:
                    expression = e.getExpression(elem)
                    # Manage expression
                    e.currentBuffer.addExpression(expression, current)
                    if e.exprHasStyle:
                        e.currentBuffer.dumpEndElement(e.tags['span'])
                    e.state = e.READING_CONTENT

    def characters(self, content):
        e = OdfParser.characters(self, content)
        if e.state == e.IGNORING:
            pass
        elif e.state == e.READING_CONTENT:
            if e.currentOdsExpression:
                # Do not write content if we have encountered an ODS expression:
                # we will replace this content with the expression's result.
                pass
            else:
                e.currentBuffer.dumpContent(content)
        elif e.state == e.READING_STATEMENT:
            # Ignore note meta-data: creator, date, sender-initials.
            if e.currentElem.elem in e.NOTE_TAGS:
                e.currentContent += content
        elif e.state == e.READING_EXPRESSION:
            e.currentContent += content
# ------------------------------------------------------------------------------
