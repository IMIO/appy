#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import inspect
from persistent import Persistent

from appy.px import Px
from appy.ui.js import Quote
from appy.model.base import Base
from appy.model.fields import Field
from appy.server.request import Request
from appy.xml.marshaller import Marshaller
from appy.model.workflow.transition import Transition

# Errors - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
UN_TRAV   = 'Untraversable element "%s" while traversing %s.'
TRAV_KO   = 'Unknown traversal type "%s".'
TR_INF_NN = 'Traversal info is None.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class NotFound(Exception):
    '''Exception raised when an URL path does not correspond to an existing (or
       visible) object.'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Traversal:
    '''Traverses the path of an URL and executes the corresponding code'''
    Error = NotFound

    # Correspondence between some URL parts and their PXs
    layouts = {'default': 'view', 'view': 'view', 'edit': 'edit', 'xml' : 'xml',
               'pxTied': 'cell', 'pxResult': 'cell', 'save': 'edit'}

    # Let's define an URL as
    #               <protocol>://<domain name><path>
    # "Traversing" is the process of splitting <path> into parts and finding a
    # correpondance between these parts and database objects, their attributes
    # and methods. Here are some examples.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # <path> content | Description
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # /              | The root URL
    # /tool/view     | Attribute "view" on object having id "tool"
    # /a/b/c/d?var=1 | Evaluating attribute or method "b" on object "a" produces
    #                | a partial result "r". Then, evaluating "c" on "r"
    #                | produces "r2". Evaluating "d" or "r2" produces the final
    #                | result. While traversing all these parts, request
    #                | variable named "var" holding value "1", is available.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # "Traversing" thus finally produces a result as a page that is returned to
    # the browser.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # When the traversal is in the default, "standard" mode, fields are supposed
    # to be related to the currently walked object. If the traversal switches to
    # "static" mode, fields are supposed to run independently of any instance.
    # A switch from standard to static mode occurs as soon as a @-prefixed part
    # is encountered.
    STANDARD = 0
    STATIC   = 1

    def __init__(self, handler=None, other=None):
        # A traversal can be initialised from another one
        if other:
            self.init(other)
            self.parent = other
            other.child = self
            return
        # Perform standard initialisation
        self.handler = handler
        self.req = handler.req
        self.resp = handler.resp
        self.tool = handler.tool
        # The path that will be traversed, splitted into parts
        self.parts = handler.parts
        # The currently logged user
        self.user = handler.guard.user
        # Set additional attributes via m_reset
        self.reset(None)
        # The PX context
        self.context = None
        # The parent traversal, for a child traversal
        self.parent = None
        # The child traversal, for a parent traversal
        self.child = None

    def reset(self, o):
        '''This p_o(bject) has just been encountered: reset the traversal,
           starting with this new object as base.'''
        # If p_o is None, this method is used to initialise a base traversal
        # ~
        # The current result of traversing
        self.r = o
        # The current object being traversed
        self.o = o
        # The last encountered field. For inner fields, the field name is
        # explicitly mentioned in attribute p_self.fieldName.
        self.field = self.fieldName = None
        # The last encountered transition
        self.transition = None
        # The traversal mode
        self.mode = Traversal.STANDARD

    def init(self, other):
        for name, value in other.__dict__.items():
            setattr(self, name, value)

    def getPath(self):
        '''Returns the complete path, including, for a child traversal, the
           parent path.'''
        r = '/'.join(self.parts)
        if self.parent:
            r += ' (from %s)' % self.parent.getPath()
        return r

    def __repr__(self):
        '''p_self's short string representation'''
        return '<Traversal @%s>' % self.getPath()

    def createContext(self, layout='view'):
        '''Create and return a PX context for rendering p_o on p_layout'''
        return Px.createContext(self, layout, Quote)

    def getContext(self):
        '''Returns the existing context or create one if it does not exist'''
        r = self.context
        if r: return r
        # Determine the layout
        if self.parts:
            layout = Traversal.layouts.get(self.parts[-1], 'view')
        else:
            layout = 'view'
        self.context = r = self.createContext(layout)
        return r

    def asObjectId(self, part):
        '''Interpret p_part as an object ID and return this ID as
           * a positive integer (for a definitive object having a standard ID);
           * a negative integer (for a temporary object);
           * p_part itself if it does not represent a (positive or negative)
             integer: it is assumed to represent a custom string ID for a
             definitive object.
        '''
        if part.isdigit() or (part.startswith('-') and part[1:].isdigit()):
            return int(part)
        return part

    def getObject(self, part):
        '''Tries to get an object from "part" which is a part of the URL path'''
        if part:
            id = self.asObjectId(part)
            r = self.handler.server.database.getObject(self.handler, id)
            if not r: raise NotFound(self.getPath())
        else:
            # If "part" is empty, (path is "/"), use the tool as default object
            r = self.tool
        # Check if the user is allowed to consult this object
        self.handler.guard.allows(r, raiseError=True)
        return r

    def getSpecialObject(self, name):
        '''Gets the special object named p_name'''
        # A special object can be a class or an object
        if name[0] == ':':
            # It is an object
            r = self.tool.getObject(name[1:])
        else:
            # It is a class
            r = self.handler.server.model.classes.get(name).python
        return r

    def getLayout(self, pxName):
        '''Determine the layout type from the currently traversed PX'''
        return Traversal.layouts.get(pxName) or 'view'

    def getPermission(self, permission):
        '''If a field is currently traversed, a "read" or "write" permission
           must be converted to this field's potentially specific "read" or
           "write" permission.'''
        field = self.field
        if not field: return permission
        if permission == 'read':
            r = field.readPermission
        elif permission == 'write':
            r = field.writePermission
        else:
            r = permission
        return r

    def allowTraversal(self, info, o, name, raiseError=True):
        '''Raise an exception if the user is not allowed to traverse this
           p_o(bject). Traversal info is given in p_info.'''
        if isinstance(info, bool):
            r = info
        elif isinstance(info, str):
            if ':' not in info:
                # This is a role: the user must have it
                r = self.user.hasRole(info)
            else:
                type, info = info.split(':', maxsplit=1)
                if type == 'perm':
                    # The user must have this permission on p_o
                    permission = self.getPermission(info)
                    r = o.allows(permission=permission)
                elif type == 'user':
                    # The user must be the one whose login is in "info"
                    r = self.user.login == info
                else:
                    raise self.handler.guard.Error(TRAV_KO % type)
        elif info is None:
            # This should not happen
            r = False
            self.tool.log(TR_INF_NN, type='warning')
        else:
            # A tuple or list of logically OR'ed infos. Having at least one of
            # the listed prerogatives allows the user to traverse.
            r = False
            for inf in info:
                if self.allowTraversal(inf, o, name, raiseError=False):
                    r = True
                    break
        # Return the result or raise an Unauthorized exception if p_raiseError
        # is True and the object can't be traversed.
        if raiseError and not r:
            message = UN_TRAV % (name, self.getPath())
            raise self.handler.guard.Error(message)
        return r

    def getTraversalInfo(self, previous, name, current):
        '''Get traversal info about p_previous.<p_name> = p_current'''
        # Do we have traversal information ? p_previous can be an object, a
        # field, a module...
        traverse = getattr(previous, 'traverse', None)
        # Is p_name mentioned in the traversal info ?
        if traverse and name in traverse:
            # Yes: retrieve "traverse info" from it
            r = traverse[name]
        else:
            # No: determine default "traverse info" based on p_current's type
            if isinstance(current, Field):
                if self.mode == Traversal.STANDARD:
                    # One may traverse it if he has the read permission on the
                    # related object.
                    r = 'perm:%s' % current.readPermission
                else:
                    # The field is not related to any instance. At this
                    # traversal level, no more security check can be performed.
                    r = True
            elif isinstance(current, Transition):
                # The transition is traversable if triggerable
                r = current.isTriggerable(previous)
            elif isinstance(current, Px):
                # A PX is traversable by default
                r = True
            else:
                # Any other element (method, attribute, property...) is not
                # traversable by default.
                r = False
        # If we are walking an element of a Field in static mode, and this
        # element is protected by an instance-related info (=a permission),
        # convert this info to True: indeed, in that case, permission can't be
        # checked (we have no instance).
        if self.mode == Traversal.STATIC and isinstance(previous, Field) and \
           isinstance(r, str) and r.startswith('perm:'):
            r = True
        return r

    def executeMethod(self, method):
        '''Execute m_method and return the result. The args potentially given to
           the method may vary.'''
        if hasattr(method, '__self__'):
            # We have a bound method. If the last walked object is not the bound
            # object, give the last walked object as unique arg.
            o = self.o
            if o and method.__self__ != o:
                r = method(o)
            else:
                r = method()
        else:
            r = method(self.o or self.handler)
        return r

    def executePx(self, name, px):
        '''Renders this p_px, whose p_name is given'''
        # Firstly, execute the tied action if defined. Indeed, this action may
        # have an impact on the data possibly shown by the PX. For example, the
        # action may delete an object matching a search whose results are shown
        # in the PX.
        actionName = self.req.action
        if actionName:
            # Execute this action by performing a sub-traversal
            handler = self.handler
            sub = Traversal(other=self)
            sub.r = sub.field or sub.o
            sub.parts = actionName.split('*')
            # A database commit will probably be required
            handler.commit = True
            # Run the sub-traversal
            msg = sub.run()
            if msg:
                # Set a special cookie in the response containing the message
                self.resp.addMessage(msg)
        # Then, create or update the PX context
        layout = self.getLayout(name)
        if not self.context:
            self.context = self.createContext(layout)
        else:
            # Update the existing context
            self.context.o = self.o
            self.context.field = self.field
            self.context.layout = layout
        # For inner fields, ensure the full name is in the context
        if self.fieldName:
            self.context.fieldName = self.fieldName
        # Finally, call the PX
        return px(self.context)

    def managePart(self, previous, name, current):
        '''Manage the currently traversed element p_current, named p_name, after
           p_previous has already been traversed.

                       p_previous.<p_name> = p_current
        '''
        # Compute information allowing to determine if the user is allowed to
        # perform such traversal.
        info = self.getTraversalInfo(previous, name, current)
        # Raise an Unauthorized exception if the user is not allowed to do it
        self.allowTraversal(info, self.o, name)
        # "Execute" the p_current object
        if isinstance(current, Px):
            # p_current is a PX: render it in p_self.r
            self.r = self.executePx(name, current)
        elif callable(current) and not inspect.isclass(current):
            # Execute method "current"
            self.r = self.executeMethod(current)
        else:
            # Ensure p_current is already in p_self.r. This may not be the case
            # at the end of the traversal, if we add a default value.
            self.r = current

    def getPart(self, part):
        '''Get the attribute or method corresponding to p_part on the current
           result in p_self.r.'''
        # If p_self.r is an object and p_part corresponds to a specific
        # sub-element on this object (field or transition), return this
        # sub-element.
        r = self.r
        if isinstance(r, Base):
            # Is p_part a field defined on the current object ?
            field = r.getField(part)
            if field:
                self.field = field
                # For an inner field, store the full field name
                if '*' in part:
                    self.fieldName = part
                return field
            # Is p_part a transition defined on the current object's workflow ?
            transition = r.getWorkflow().transitions.get(part)
            if transition:
                self.transition = transition
                return transition
        # Try to get an attribute or method on p_self.r named p_part
        r = getattr(r, part, None)
        if r is None:
            # Raise a 404
            raise NotFound(self.getPath())
        if isinstance(r, Base):
            self.o = r
            self.field = self.fieldName = self.transition = None
        elif isinstance(r, Field):
            # A field may be directly specified from a class, not from an
            # instance.
            self.field = r
        return r

    def marshall(self, r, rootTag=None):
        '''Depending on the response type, the traversal p_r(esult) may need to
           be marshalled.'''
        if r is None: return r
        if self.resp.contentType == 'xml':
            # Currently, only XML marshalling is there
            tag = r.class_.name if isinstance(r, Base) else self.parts[-1]
            r = Marshaller(rootTag=rootTag or tag).marshall(r)
        return r

    def run(self):
        '''Traverses a given path whose parts are splitted into p_self.parts'''
        parts = self.parts
        if not parts:
            # There is nothing to traverse. Define the tool as the default
            # object to traverse.
            self.r = self.o = self.getObject(None)
        else:
            # Traverse URL parts
            length = len(parts)
            i = 0
            # Define the previously traversed part. It is None for a main
            # traversal, or an already filled self.r in the case of a
            # sub-traversal.
            previous = self.r
            while i < length:
                # Get and manage the next part
                part = parts[i]
                if part and part.startswith('@'):
                    # Manage direct navigation to a special object
                    self.r = self.getSpecialObject(part[1:])
                    # Switch to "static" mode
                    self.mode = Traversal.STATIC
                elif self.r is None:
                    # We are at the start of a traversal. p_self.r is still
                    # None: v_part must either be a traverser, or correspond to
                    # an object ID.
                    expr = self.handler.config.server.traversers.get(part)
                    if expr:
                        tool = self.tool
                        self.o = tool
                        self.r = eval(expr)
                    else:
                        # v_part must be an object ID
                        self.r = self.o = self.getObject(part)
                # Manage any not-empty part
                elif part:
                    if part.isdigit(): # An object (again): reset the traversal.
                        self.reset(self.tool.getObject(part))
                    else:
                        # Try to get attribute or method named "part" on self.r
                        self.r = self.getPart(part)
                        # Manage this part
                        self.managePart(previous, part, self.r)
                i += 1
                previous = self.r
        # If self.r is an object and the response must be HTML, call the default
        # PX on this object.
        if isinstance(self.r, Persistent) and self.resp.contentType == 'html':
            self.managePart(self.r, 'default', self.r.default)
        # Potentially marshall the result
        r = self.marshall(self.r)
        # If the result of the traversal is not a string nor bytes, it is
        # invalid. Produce a 404 error in that case.
        if r is not None and not isinstance(r, (str, bytes)):
            raise NotFound(self.getPath())
        return r
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
