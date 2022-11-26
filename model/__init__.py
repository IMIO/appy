'''Management of the model behind a Appy application'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import pathlib

from appy.px import Px
from appy.model.workflow import Role

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Config:
    '''Model configuration'''

    def __init__(self):
        # The "root" classes are those that will get their menu in the user
        # interface. Put their names in the list below. If you leave the list
        # empty, all classes will be considered root classes (the default). If
        # rootClasses is None, no class will be considered as root.
        self.rootClasses = []
        # People having one of these roles will be able to create instances
        # of classes defined in your application.
        self.defaultCreators = ['Manager']
        # Roles in use in a Appy application are identified at make time from
        # workflows or class attributes like "creators": it is not needed to
        # declare them somewhere. If you want roles that Appy will be unable to
        # detect, add them in the following list. Every role can be a Role
        # instance or a string.
        self.additionalRoles = []
        # When marshalling File fields via the XML layout, binary content is, by
        # default, included as a series of fixed size Base64-encoded chunks
        # wrapped in "part" tags. If the target site has access to this site's
        # filesystem, an alternative is to marshall the disk location of the
        # binary file instead of its content. If you want to enable this latter
        # behaviour, set the following attribute to False.
        self.marshallBinaries = True

    def set(self, appFolder):
        '''Sets site-specific configuration elements'''
        # The absolute path to the app as a pathlib.Path instance
        self.appPath = pathlib.Path(appFolder)
        # The application name
        self.appName = self.appPath.name

    def get(self, config, logger=None, appOnly=False):
        '''Creates and returns a Model instance (see below)'''
        from appy.model.loader import Loader
        return Loader(self, config, logger, appOnly).run()

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Model:
    '''Represents an application's model = the base Appy model, completed and
       extended by the application model.'''

    class Error(Exception): pass

    # Names of base classes forming the base Appy model, in package appy.model,
    # and standard workflows defined in package appy.model.workflows.standard.
    # These classes and workflows are injected into any app's model.
    baseClasses = ('Page', 'User', 'Group', 'Tool', 'Translation', 'Carousel',
                   'Document', 'Query', 'Mover')
    baseWorkflows = ('Anonymous', 'Authenticated', 'Owner', 'TooPermissive')

    def __init__(self, config, classes, workflows):
        '''The unique Model instance is created by the
           appy.model.loader.Loader.'''
        # The app's global config
        self.config = config
        # All Appy classes, keyed by their name
        self.classes = classes # ~{s_className: appy.model.meta.Class}~
        # All Appy worfklows, keyed by their name
        self.workflows = workflows # ~{s_className: appy.model.meta.Workflow}~
        # The global, grantable roles (will be computed later, at run-time only)
        self.grantableRoles = None

    def getClasses(self, type=None):
        '''Returns a list of classes (sorted by alphabetical order of their
           name) from self.classes. If p_type is:
           - None:       all classes are returned;
           - "class":    only Appy classes are iterated;
           - "workflow": only Appy workflows are iterated.
        '''
        if type is None:
            attributes = ('classes', 'workflows')
        else:
            attributes = ('classes',) if (type == 'class') else ('workflows',)
        # Build the result list
        r = []
        for name in attributes:
            r += list(getattr(self, name).values())
        r.sort(key=lambda k: k.name.lower())
        return r

    def getRootClasses(self):
        '''Returns the list of root classes for this app'''
        r = self.config.model.rootClasses
        if r is None: return () # No root class at all
        if not r:
            # We consider every "app" class as being a root class
            r = [c for c in self.getClasses(type='class') if c.type == 'app']
        else:
            r = [self.classes[name] for name in r]
        return r

    def getRoles(self, base=None, local=None, grantable=None, sorted=False):
        '''Produces a list of all the roles used within all workflows and
           classes defined in this app.'''
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # If p_base is...
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # True  | it keeps only standard Appy roles;
        # False | it keeps only roles which are specific to this app;
        # None  | it has no effect (so it keeps both roles).
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # If p_local is...
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # True  | it keeps only local roles. A local role is granted to a user
        #       | or group, is stored and applies on a single object only;
        # False | it keeps only global roles. A global role is granted to a
        #       | group or user and applies everywhere throughout the app,
        #       | independently of any object;
        # None  | it has no effect (so it keeps both roles).
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # If p_grantable is...
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # True  | it keeps only roles that a Manager can grant;
        # False | if keeps only ungrantable roles (ie those that are implicitly
        #       | granted by the system like role "Authenticated";
        # None  | it has no effect (so it keeps both roles).
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        r = {} # ~{s_roleName: Role_role}~
        # Collect roles from workflow states and transitions
        for workflow in self.workflows.values():
            for name in workflow.attributes.keys():
                for elem in getattr(workflow, name).values():
                    for role in elem.getUsedRoles():
                        r[role.name] = role
        # Gather roles from "creators" attributes from every class
        for class_ in self.classes.values():
            creators = class_.getCreators()
            if not creators: continue
            for role in creators:
                r[role.name] = role
        # Get additional roles from the config
        for role in self.config.model.additionalRoles:
            if isinstance(role, str):
                role = Role(role)
            r[role.name] = role
        # Filter the result according to parameters and return a list
        r = [role for role in r.values() if role.match(base,local,grantable)]
        if sorted:
            r.sort(key= lambda r:r.name.lower())
        return r

    def getGrantableRoles(self, o):
        '''Returns the list of global roles that can be granted to a user'''
        return [(role.name, o.translate('role_%s' % role.name)) \
                for role in self.grantableRoles]

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                                  PX
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    view = Px('''
     <x var="className=req.className; model=o.model">
      <h2>Root classes (+tool) </h2>

      <!-- Class selector -->
      <select name="classes" var="murl='%s/view?page=model' % tool.url"
        onchange=":'goto(&quot;%s&amp;className=&quot; + this.value)' % murl">
       <option value="">-</option>
       <option for="class_ in model.getRootClasses()" var2="name=class_.name"
               value=":name" selected=":name == className">:name</option>
       <option value="Tool">Tool</option>
      </select>

      <!-- The current class -->
      <x if="className"
         var2="class_=model.classes[className]">:class_.pxBox</x>
     </x>''',

     css='''
      .mbox>tbody>tr>:nth-child(2) { border:none; background-color:transparent;
        padding-left:0 }
      .mbox>tbody>tr>th { text-transform:none; font-size:100%;
                          text-align:center }
      .mbox>tbody>tr>td { border-bottom:none; border-top:none }
      .mbox>tbody>tr:last-child>td:first-child { border-bottom:1px solid black }
      a.bref, a.bref:visited {
        padding:0 0.4em; border: 1px solid black; font-weight:bold;
        background-color:|darkColor|; color:|brightColor| }
      .boxIcon { width:1.4em; float:right; padding-top:2px }
     ''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
