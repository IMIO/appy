#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from pathlib import Path
import re, urllib.parse, subprocess

import appy.ui
from appy.tr import po
from appy.px import Px
from appy import Config
from appy.server import Server
from appy.utils import Function
from appy.model.base import Base
from appy.model.user import User
from appy.model.root import Model
from appy.data import nativeNames
from appy.model.group import Group
from appy.model.fields import Show
from appy.model.query import Query
from appy.model.mover import Mover
from appy.database import Database
from appy.ui.layout import Layouts
from appy.xml.escape import Escape
from appy.database.log import Viewer
from appy.ui.template import Template
from appy.model.fields.ref import Ref
from appy.server.backup import Backup
from appy.model.searches import Search
from appy.utils import dates as dutils
from appy.model.fields.rich import Rich
from appy.model.fields import Initiator
from appy.model.carousel import Carousel
from appy.model.fields.phase import Page
from appy.model.utils import Object as O
from appy.model.page import Page as OPage
from appy.database.catalog import Catalog
from appy.model.fields.string import String
from appy.model.fields.action import Action
from appy.test.monitoring import Monitoring
from appy.model.translation import Translation
from appy.model.fields.calendar import Calendar
from appy.model.fields.computed import Computed
from appy.utils.mail import sendMail, sendMailIf
from appy.server.context import AuthenticationContext

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
RS_FG_KO   = 'Server cannot be restarted if running in the foreground.'
RESTART_S  = "Restarting server (wait %d'')..."
SRV_CONF   = 'Server(s) %s configured.'
USR_CREA   = 'User "%s" created.'
GRP_CREA   = 'Group "admins" created.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Tool(Base):
    '''Base class for the Appy tool, a persistent instance storing configuration
       elements and more, like users, group and translations.'''

    # Make some modules and classes available and/or traversable via the tool
    ui = appy.ui
    OPage = OPage
    Date = dutils.Date
    Database = Database
    AuthContext = AuthenticationContext

    # While most users have generally the read permission on the tool and
    # translations, they must not be allowed to consult tool/view and sub-pages.
    # Traversing tool/view is thus by default restricted to those having the
    # write permission on the tool.
    traverse = Base.traverse.copy()
    traverse.update({'ui':True, 'guard':True, 'AuthContext': 'Authenticated',
                     'Database':True, 'Server':True, 'view': 'perm:write'})

    Initiator = Initiator

    # The tool is not indexed by default
    indexable = False

    @staticmethod
    def update(class_):
        '''Hide pages being not necessary'''
        fields = class_.fields
        for name in ('title', 'record'):
            fields[name].page.show = False

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    #  Tool initialisation
    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    def checkServers(self, config):
        '''Log the names of servers (LDAP, mail...) this app wants to connect
           to. Servers declared as "testable" are contacted to check the app's
           connection to it.'''
        servers = []
        # Browse connected servers
        for cfg in (config.security.ldap, config.mail, config.security.sso):
            if not cfg: continue
            # Initialise and check this server config
            cfg.init(self)
            enabled = 'enabled' if cfg.enabled else 'disabled'
            # Test the connection to the server
            status = ''
            if cfg.enabled and cfg.testable:
                status = cfg.test(self)
                if status: status = ', ' + status
            servers.append('%s (%s%s)' % (cfg, enabled, status))
        if servers:
            self.log(SRV_CONF % ', '.join(servers))

    def init(self, handler, poFiles, method=None):
        '''Ensure all required tool sub-objects are present and coherent'''
        # Get the root database object from the current request p_handler
        root = handler.dbConnection.root
        # Create the default users if they do not exist
        for login, roles in User.defaultUsers.items():
            # Does this user exist in the database ?
            if login in root.objects:
                # Yes. Do not create it. But ensure, for "anon" and "system",
                # that they have no email.
                user = root.objects.get(login)
                if login != 'admin': user.email = None
            else:
                # No. Create it.
                user = self.create('users', secure=False, id=login, login=login,
                            password=login, roles=roles)
                self.log(USR_CREA % login)

        # Ensure group "admins" exists. This group is granted role "Manager",
        # the role with the highest level of prerogatives in Appy.
        if 'admins' not in root.objects:
            self.create('groups', secure=False, id='admins', login='admins',
                        title='Administrators', roles=['Manager'])
            self.log(GRP_CREA)

        # Load Appy "po" files if we need to inject their values into
        # Translation objects. app's "po" files are already in p_poFiles.
        # Also load ext's "po" files if an ext is defined.
        config = handler.server.config
        ui = config.ui
        load = ui.loadTranslationsAtStartup
        extFiles = None
        if load:
            appyFiles = po.load(pot=False, languages=ui.languages)
            if config.ext:
                extPath = '%s/tr' % __import__(config.ext).__path__[0]
                extFiles = po.load(path=Path(extPath), pot=False,
                                   languages=ui.languages)

        # Ensure a Translation object exists for every supported language
        for language in ui.languages:
            if language not in root.objects:
                # Create a Translation file
                tr = self.create('translations', secure=False, id=language,
                            title='%s (%s)' % (language, nativeNames[language]),
                            sourceLanguage=ui.sourceLanguage)
                tr.updateFromFiles(appyFiles, poFiles, extFiles or {})
            else:
                tr = root.objects[language]
                if load: tr.updateFromFiles(appyFiles, poFiles, extFiles or {})

        # Check connected servers
        self.checkServers(config)

        # Define the home page
        Tool.default = getattr(Tool, config.ui.home)

        # Call method "onInstall" on the tool when available. This hook allows
        # an app to execute code on server initialisation.
        if hasattr(self, 'onInstall'): self.onInstall()

        # Call this custom p_method on the tool
        if method: Function.scall(self, method)

        # Import an Appy 0 site when relevant
        peers = config.peers
        if peers and peers.appy0:
            peers.appy0.pump(self)

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    #  Page "main"
    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    # Methods protecting visibility of tool pages and fields
    def forToolWriters(self):
        '''Some elements are only accessible to tool writers (ie Managers)'''
        if self.allows('write'): return Show.ER_

    def pageForToolWriters(self):
        '''Some tool pages are only accessible to tool writers (ie Managers)'''
        if self.allows('write'): return 'view'

    ta = {'label': 'Tool'}

    # Storing the Appy version on the tool (in the form of a string "x.y.z")
    # allows to trigger automatic migrations at server startup.
    appyVersion = String(show='view', **ta)

    # This hidden calendar is used for searches in "calendar" mode
    def calendarPreCompute(self, first, grid):
        '''Computes pre-computed information for the tool calendar'''
        # If this calendar is used as mode for a search, get this search
        ctx = self.traversal.context
        mode = ctx.mode
        if not mode:
            Px.injectRequest(ctx, self.req, self)
        # Trigger the search via the mode
        if mode: mode.search(first, grid)
        return O(mode=mode)

    def calendarAdditionalInfo(self, date, preComputed):
        '''Renders the content of a given cell in the calendar used for
           searches' calendar mode.'''
        info = preComputed.mode.dumpObjectsAt(date)
        if info: return info

    calendar = Calendar(preCompute=calendarPreCompute, show=False,
                        additionalInfo=calendarAdditionalInfo, **ta)

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    #  Page "users"
    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    userPage = Page('users', show=pageForToolWriters, label='Tool_page_users',
                    icon='pageUsers.svg')

    # The "main" page, reserved to technical elements, may be hidden by apps
    def getDefaultViewPage(self): return 'users'

    # Ref(User) will maybe be transformed into Ref(AppUser)
    users = Ref(User, multiplicity=(0,None), add=True, link=False,
      composite=True, back=Ref(attribute='toTool', show=False, layouts='f'),
      page=userPage, queryable=True, queryFields=('searchable','login','roles'),
      show=forToolWriters, showHeaders=True, actionsDisplay='right',
      shownInfo=User.listColumns, **ta)

    def doSynchronizeExternalUsers(self):
        '''Synchronizes the local User copies with a distant LDAP user base'''
        cfg, context = self.config.security.getLdap()
        if not cfg: raise Exception('LDAP config not found.')
        message = cfg.synchronizeUsers(self, sso=context)
        return True, message

    def showSynchronizeUsers(self):
        '''Show this button only if a LDAP connection exists and is enabled'''
        cfg, context = self.config.security.getLdap()
        if cfg and cfg.enabled: return 'buttons'

    synchronizeExternalUsers = Action(action=doSynchronizeExternalUsers,
      show=showSynchronizeUsers, confirm=True, page=userPage, **ta)

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    #  Page "groups"
    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    # Ref(Group) will maybe be transformed into Ref(AppGroup)
    groups = Ref(Group, multiplicity=(0,None), add=True, link=False,
      composite=True, back=Ref(attribute='toTool', show=False,layouts='f'),
      page=Page('groups', show=pageForToolWriters, label='Tool_page_groups',
                icon='groups.svg'),
      show=forToolWriters, queryable=True, queryFields=('title', 'login'),
      showHeaders=True, actionsDisplay='inline',
      shownInfo=('title', 'login*20%|', 'roles*20%|'), **ta)

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    #  Page "translations"
    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    pt = Page('translations', show=pageForToolWriters,
              label='Tool_page_translations', icon='pageTranslations.svg')

    # Ref(Translation) will maybe be transformed into Ref(AppTranslation)
    translations = Ref(Translation, multiplicity=(0,None), add=False,
      link=False, composite=True, show='view', page=pt, actionsDisplay='inline',
      back=Ref(attribute='toTool', show=False, layouts='f'), **ta)

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    #  Page "pages"
    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    def showPagePages(self):
        '''Show page "pages" if the logged user is allowed to write the tool'''
        # The page may be edited only if there is at least one page defined (in
        # order to select it as default page).
        if not self.allows('write'): return
        return 'view' if self.isEmpty('pages') else True

    pp = Page('pages', show=showPagePages, label='Tool_page_pages',
              icon='pagePages.svg')

    pages = Ref(OPage, multiplicity=(0,None), add=True, link=False,
                composite=True, show=Show.VX, actionsDisplay='inline', page=pp,
                back=Ref(attribute='toTool', show=False, layouts='f'),
                numbered=True, showHeaders=True, shownInfo=OPage.listColumns,
                **ta)

    # The page, among "pages", being defined as the default one
    defaultPage = Ref(OPage, add=False, link=True, render='links', page=pp,
                      back=Ref(attribute='toTool2', show=False, layouts='f'),
                      show=lambda o: not o.isEmpty('pages'),
                      select=lambda o: o.pages, **ta)

    # Update the base URL of all internal links within pages's rich fields
    updateBaseUrl = Action(action=lambda o, options: options.run(),
                           show='buttons', options=Mover, page=pp, **ta)

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    #  Page "carousels"
    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    pc = Page('carousels', show=lambda o: 'view' if o.allows('write') else None,
              label='Tool_page_carousels')

    carousels = Ref(Carousel, multiplicity=(0,None), add=True, link=False,
                    composite=True, show=Show.VX, actionsDisplay='inline',
                    back=Ref(attribute='toTool', show=False, layouts=Layouts.f),
                    layouts=Layouts.dv, page=pc, showHeaders=True, **ta)

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    #  Page "queries"
    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    pq = Page('queries', show=lambda o: 'view' if o.allows('write') else None,
              label='Tool_page_queries')

    queries = Ref(Query, multiplicity=(0,None), add=True, link=False,
                  composite=True, show=Show.VX, actionsDisplay='inline',
                  back=Ref(attribute='toTool', show=False, layouts=Layouts.f),
                  layouts=Layouts.dv, page=pq, showHeaders=True,
                  shownInfo=Query.listColumns, **ta)

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    #  "admin" zone
    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    def forAdmin(self):
        '''Returns page visibility for pages from the admin zone'''
        return 'view' if self.user.hasRole('Manager') else None

    onlineUsers = Computed(method=lambda o: User.getOnline(o), layouts='f',
      show='view', page=Page('online', phase='admin', show=forAdmin,
                             label='Tool_page_online'), **ta)

    serverInfo = Computed(method=Server.view, layouts='f',
      page=Page('server', phase='admin', show=forAdmin,
                label='Tool_page_server'), **ta)

    databaseInfo = Computed(method=Database.view, layouts='f',
      page=Page('database', phase='admin', show=forAdmin,
                label='Tool_page_database'), **ta)

    modelInfo = Computed(method=Model.view, layouts='f',
      page=Page('model', phase='admin', show=forAdmin,
                label='Tool_page_model'), **ta)

    # View site's config.py from the UI
    def getConfigPy(self):
        '''Display the content of this Appy site's config.py file'''
        with open('%s/config.py' % self.config.server.sitePath, 'r') as f:
            return '<pre>%s</pre>' % Escape.xhtml(f.read())

    configPy = Computed(method=getConfigPy,
      page=Page('configPy', phase='admin', show=forAdmin,
                label='Tool_page_configPy'), **ta)

    logsViewer = Computed(method=Viewer.run,
      page=Page('logsViewer', phase='admin', show=forAdmin,
                label='Tool_page_logsViewer'), **ta)

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    #  Monitoring
    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    traverse['check'] = True
    def check(self):
        '''Returns monitoring-related info about this instance'''
        return Monitoring().get(self)

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    #  Main methods
    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    def sendMail(self, to, subject, body, attachments=None, replyTo=None,
                 split=False):
        '''Sends a mail. See doc for appy.utils.mail.sendMail.'''
        return sendMail(self.config.mail, to, subject, body,
          attachments=attachments, log=self.log, replyTo=replyTo, split=split)

    def sendMailIf(self, o, privilege, subject, body, attachments=None,
                   privilegeType='permission', excludeExpression='False',
                   userMethod=None, replyTo=None, split=False):
        '''Sends a mail concerning this p_o(bject), to people having this
           p_privilege.'''
        return sendMailIf(o.config.mail, o, privilege, subject, body,
          attachments=attachments, privilegeType=privilegeType,
          excludeExpression=excludeExpression, userMethod=userMethod, log=o.log,
          replyTo=replyTo, split=split)

    def computeHomePage(self):
        '''Compute the page that is shown to the user when he hits the app'''
        # Does the app's tool define a custom method for getting the home page ?
        # If yes, call it.
        r = None
        if hasattr(self, 'getHomePage'):
            r = self.getHomePage()
        if not r:
            # Get the currently logged user
            user = self.user
            # Bring anonymous users to tool/home, Managers to tool/view and
            # others to user/view.
            if user.isAnon():
                suffix = 'public' if self.config.ui.discreetLogin else 'home'
                r = '%s/%s' % (self.url, suffix)
            elif user.hasRole('Manager'):
                r = '%s/view' % self.url
            else:
                r = '%s/view' % user.url
        return r

    def computeHomeObject(self, user, popup=False):
        '''The concept of "home object" is the object where the user must "be",
           even if he is "nowhere". For example, if the user is on a search
           screen, there is no contextual object (the tool excepted). In this
           case, if we have a home object for him, we will use it as contextual
           object, and its portlet menu will nevertheless appear: the user will
           not have the feeling of being lost.'''
        # If we are in the popup, we do not want any home object in the way
        if popup: return
        if hasattr(self, 'getHomeObject'):
            # If the app defines a method "getHomeObject", call it
            r = self.getHomeObject()
        else:
            # For managers, the home object is the tool. For others, there is
            # no default home object.
            if user.hasRole('Manager'): return self

    def formatDate(self, date, format=None, withHour=True, language=None,
                   hourSep=' (', hourEnd=')'):
        '''Check doc in called method'''
        if not date: return
        return dutils.Date.format(self, date, format, withHour, language,
                                  hourSep=hourSep, hourEnd=hourEnd)

    def restart(self, wait=5):
        '''Restarts the currently running Appy server (S), by forking another
           process that will wait p_wait seconds before restarting S.'''
        # This cannot be done for servers running in the foreground
        if self.H().server.mode == 'fg':
            self.log(RS_FG_KO, type='warning')
            return
        # Fork a process that will launch a "./site restart" command. Waiting
        # p_wait seconds may give enough time to the Appy server for committing
        # ongoing transactions.
        sitePath = self.config.server.sitePath
        args = [str(sitePath / 'bin' / 'site'), 'restart']
        if wait:
            args.append('-w')
            args.append(str(wait))
        self.log(RESTART_S % wait)
        subprocess.Popen(args, stdin=None, stdout=None, stderr=None)

    def backup(self):
        '''Method allowing to trigger the backup of a Appy site'''
        return Backup(self).run()

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    #  PXs
    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    # PX "home" is the default page shown for a standard Appy site, excepted
    # when discreet logins are enabled. In this latter case, PX "public",
    # hereafter, is more appropriate.
    home = Px('''
     <!-- Redirect the user when appropriate -->
     <x if="(not isAnon or cfg.discreetLogin) and not req.stay"
        var2="x=tool.goto(tool.computeHomePage())"></x>

     <!-- Links -->
     <div class=":f'{_px_.name}Top'">:Template.pxTemplateLinks</div>

     <!-- The home logo and text -->
     <div if="isAnon and _px_.name == 'home'" class="homeText">
       <img if="cfg.homeShowLogo" src=":url('homeLogo')"/>
       <!-- The home text must not be shown here, if shown on a public page -->
       <x if="not tool.isEmpty('defaultPage') and 
         not cfg.discreetLogin">::tool.defaultPage.getShownValue('content')</x>
     </div>

     <!-- The backgrounds for px "homes" -->
     <div if="_px_.name == 'homes'" class="homes">
      <div for="fileName, width in cfg.homesBackgrounds.items()"
           var2="bg=tool.buildUrl(fileName, bg=True)"
           style=":f'{bg};width:{width}'"></div>
     </div>''',

     css='''
      .homeText { position:fixed; left:|homeTextLeft|; top:|homeTextTop|;
                  color:|homeTextColor| }
      .homeText h1 { font-size:|homeH1FSize|; margin-left:-5px; padding:0 }
      .homeText h2 { font-size:|homeH2FSize| }
      .homeText p { font-size:|homeTextFSize|; margin:0 }
      .homeText a, .homeText a:visited { color:|homeLinkColor| }
      .homeTop { position:fixed; top:20px; right:20px; color:|headerColor|;
                 z-index:1 }
     ''',

     template=Template.px, hook='content', name='home')

    # A variant of page "home", allowing to define several backgrounds, rendered
    # one besides each other.
    homes = Px(home.content, template=Template.px, hook='content', name='homes',
     css='''.homes { display:flex; width:100%; height:100% }
            .homes div { background-size: cover }
            .homesTop { position:absolute; text-align:center; left:0; right:0;
               top:15px; z-index:10 }
            .homesTop .topIcons { background-color:|topIconsHomesBg|;
              display:inline-flex; flex-direction:|topIconsHomesDir| }''')

    # PX "public" shows one of the root pages (rp), or the default one if none
    # of them is specified. When discreet logins are enabled, the public page
    # is shown, loaded with the default page.
    public = Px('''
     <!-- The home text -->
     <div class="public"
          var="layout='view';
               root=tool.getObject(req.rp) if req.rp else tool.defaultPage">
      <x if="root">
       <!-- Display links on top of the 1st page, if the header is not shown -->
       <div if="not showHeader"
            class="publicTop">:Template.pxTemplateLinks</div>

       <!-- Display the root page and all pages chained to it -->
       <x for="o in root.getChain()"
          var2="x=o.initialiseLocalPage(req)">:o.view</x>
      </x>
      <x if="not root">::_('no_default_page')</x>
     </div>''',

     css='''
      .publicTop { position:fixed; top:20px; right:20px; color:|headerColor| }
      .publicTop .img { width:27px }
      .publicTop .topIcons { display:inline-flex }
     ''',

     template=Template.px, hook='content', name='public')

    # Disable tool removal
    def mayDelete(self): return
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
