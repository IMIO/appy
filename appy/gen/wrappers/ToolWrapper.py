# ------------------------------------------------------------------------------
import os.path, time
import appy
from appy import Object as O
from appy.px import Px
from appy.gen.mail import sendMail
from appy.gen.wrappers import AbstractWrapper
from appy.shared.utils import executeCommand
from appy.shared.ldap_connector import LdapConnector

# ------------------------------------------------------------------------------
class ToolWrapper(AbstractWrapper):
    # --------------------------------------------------------------------------
    # Navigation-related PXs
    # --------------------------------------------------------------------------
    # Icon for hiding/showing details below the title of an object shown in a
    # list of objects.
    pxShowDetails = Px('''
     <img if="(field.name == 'title') and ztool.subTitleIsUsed(className)"
          class="clickable" src=":url('toggleDetails')"
          onclick="toggleSubTitles()"/>''')

    # --------------------------------------------------------------------------
    # PXs for graphical elements shown on every page
    # --------------------------------------------------------------------------
    # Type-specific CSS and JS files to import in the current page
    pxCssJs = Px('''
     <link for="css in cssJs['css']"
           rel="stylesheet" type="text/css" href=":url(css)"/>
     <script for="js in cssJs['js']"
             src=":js.startswith('//') and js or url(js)"></script>''')

    # Global elements included in every page
    pxPagePrologue = Px('''
     <!-- Global form for deleting an object -->
     <form id="deleteForm" method="post" action=":'%s/onDelete' % tool.url">
      <input type="hidden" name="uid"/>
     </form>
     <!-- Global form for editing entries within an object's history -->
     <form id="eventForm" method="post" action="">
      <input type="hidden" name="objectId"/>
      <input type="hidden" name="eventTime"/>
      <input type="hidden" name="comment"/>
     </form>
     <!-- Global form for unlocking a page -->
     <form id="unlockForm" method="post" action="do">
      <input type="hidden" name="action" value="Unlock"/>
      <input type="hidden" name="objectUid"/>
      <input type="hidden" name="pageName"/>
     </form>
     <!-- Global form for generating/freezing a document from a pod template -->
     <form id="podForm" name="podForm" method="post"
           action=":'%s/doPod' % tool.url">
      <input type="hidden" name="objectUid"/>
      <input type="hidden" name="fieldName"/>
      <input type="hidden" name="template"/>
      <input type="hidden" name="podFormat"/>
      <input type="hidden" name="queryData"/>
      <input type="hidden" name="criteria"/>
      <input type="hidden" name="customParams"/>
      <input type="hidden" name="showSubTitles" value="true"/>
      <input type="hidden" name="checkedUids"/>
      <input type="hidden" name="checkedSem"/>
      <input type="hidden" name="mailing"/>
      <input type="hidden" name="mailText"/>
      <input type="hidden" name="action" value="generate"/>
     </form>''')

    pxPageSelector = Px('''
      <select var="pages=[p for p in tool.pages if p.o.mayView()]" if="pages"
              onchange="gotoURL(this)">
       <option value="">:_('goto_link')</option>
       <option for="page in pages" value=":page.url"
               selected=":page == obj">:page.title</option>
      </select>''',

     js='''
       function gotoURL(select) {
         var url = select.value;
         if (url) goto(url);
       }''')

    pxPageBottom = Px('''
     <script type="text/javascript">:'initSlaves(%s,%s)' % \
                    (q(zobj.absolute_url()), q(layoutType))</script>''')

    pxLiveSearchResults = Px('''
     <div var="className=req['className'];
               klass=ztool.getAppyClass(className);
               search=ztool.getLiveSearch(klass, req['w_SearchableText']);
               zobjects=ztool.executeQuery(className, search=search, \
                                           maxResults=10).objects"
          id=":'%s_LSResults' % className">
      <p if="not zobjects" class="lsNoResult">::_('query_no_result')</p>
      <div for="zobj in zobjects" style="padding: 3px 5px">
       <a href=":zobj.absolute_url()"
          var="content=ztool.truncateValue(zobj.Title(), width=80)"
          title=":zobj.Title()">:content</a>
      </div>
      <!-- Go to the page showing all results -->
      <div if="zobjects" align=":dright" style="padding: 3px">
       <a class="clickable" style="font-size: 95%; font-style: italic"
          onclick=":'document.forms[%s].submit()' % \
            q('%s_LSForm' % className)">:_('search_results_all') + '...'</a>
      </div>
     </div>''')

    pxLiveSearch = Px('''
     <form var="formId='%s_LSForm' % className"
           id=":formId" name=":formId" action=":'%s/do' % toolUrl">
      <input type="hidden" name="action" value="SearchObjects"/>
      <input type="hidden" name="className" value=":className"/>
      <table cellpadding="0" cellspacing="0"
             var="searchLabel=_('search_button')">
       <tr valign="bottom">
        <td style="position: relative">
         <input type="text" size="14" name="w_SearchableText" autocomplete="off"
                id=":'%s_LSinput' % className" class="inputSearch"
                title=":searchLabel"
                var="jsCall='onLiveSearchEvent(event, %s, %s, %s)' % \
                             (q(className), q('auto'), q(toolUrl))"
                onkeyup=":jsCall" onfocus=":jsCall"
                onblur=":'onLiveSearchEvent(event, %s, %s)' % \
                         (q(className), q('hide'))"/>
         <!-- Dropdown containing live search results -->
         <div id=":'%s_LSDropdown' % className" class="dropdown liveSearch">
          <div id=":'%s_LSResults' % className"></div>
         </div>
        </td>
        <td><input type="image" class="clickable" src=":url('search')"
                   title=":searchLabel"/></td>
       </tr>
      </table>
     </form>''')

    pxAddFrom = Px('''
     <a target="appyIFrame" id=":addFormName + '_from'"
        href=":ztool.getCreateLink(className,create,addFormName,sourceField)">
      <input var="css=fromRef and 'Small' or 'Icon';
                  label=_('object_add_from')"
         type="button" value=":fromRef and label or ''" 
         title=":label" class=":'button%s button' % css"
         onclick="openPopup('iframePopup')" style=":url('addFrom', bg=True)"/>
     </a>''')

    pxAdd = Px('''
     <!-- Create instances of this class -->
     <form var="create=ztool.getCreateFor(rootClass)"
           if="create" class="addForm" name=":'%s_add' % className"
           var2="target=ztool.getLinksTargetInfo(rootClass)"
           action=":'%s/do' % tool.url" target=":target.target">
      <input type="hidden" name="action" value="Create"/>
      <input type="hidden" name="className" value=":className"/>
      <input type="hidden" name="template" value=""/>
      <input type="hidden" name="insert" value=""/>
      <input type="hidden" name="nav" value=":nav"/>
      <input type="hidden" name="popup"
            value=":(inPopup or (target.target!='_self')) and '1' or '0'"/>
      <!-- Create from an empty form -->
      <input type="submit" value=":asButton and _('object_add') or ''"
             var="label=_('object_add');
                  css=asButton and 'buttonSmall' or 'buttonIcon'"
             title=":label" class=":'%s button' % css"
             onclick=":target.getOnClick('queryResult')"
             style=":url('add', bg=True)"/>
      <!-- Create from a pre-filled form when relevant -->
      <x if="create != 'form'"
         var2="fromRef=False; sourceField=None;
               addFormName='%s_add' % className">:tool.pxAddFrom</x>
     </form>''')

    pxPortlet = Px('''
     <x var="toolUrl=tool.url;
             queryUrl='%s/query' % toolUrl;
             currentSearch=req.get('search', None);
             currentClass=req.get('className', None);
             currentPage=req['AUTHENTICATION_PATH'].rsplit('/',1)[-1];
             rootClasses=ztool.getRootClasses()">

      <!-- One section for every searchable root class -->
      <x for="rootClass in rootClasses"
         if="ztool.userMaySearch(rootClass, layoutType)"
         var2="className=ztool.getPortalType(rootClass)">

       <!-- A separator if required -->
       <div class="portletSep" if="loop.rootClass.nb != 0"></div>

       <!-- Section title (link triggers the default search) -->
       <div class="portletContent"
            var="searchInfo=ztool.getGroupedSearches(rootClass)">
        <div class="portletTitle">
         <a var="queryParam=searchInfo.default and \
                            searchInfo.default.name or ''"
            href=":'%s?className=%s&amp;search=%s' % \
                   (queryUrl, className, queryParam)"
            onclick="clickOn(this)"
            class=":(not currentSearch and (currentClass==className) and \
                    (currentPage=='query')) and \
                    'current' or ''">::_(className + '_plural')</a>
         <!-- Create instances of this class -->
         <x if="ztool.userMayCreate(rootClass)"
            var2="asButton=False; nav='no'">:tool.pxAdd</x>
        </div>
        <!-- Searches -->
        <x if="ztool.advancedSearchEnabledFor(rootClass)">
         <!-- Live search -->
         <x>:tool.pxLiveSearch</x>

         <!-- Advanced search -->
         <div var="highlighted=(currentClass == className) and \
                               (currentPage == 'search')"
              class=":highlighted and 'portletSearch current' or \
                     'portletSearch'"
              align=":dright" style="margin-bottom: 4px">
          <a var="text=_('search_title')" style="font-size: 88%"
             href=":'%s/search?className=%s' % (toolUrl, className)"
             title=":text"><x>:text</x>...</a>
         </div>
        </x>

        <!-- Predefined searches -->
        <x for="search in searchInfo.searches" var2="field=search">
         <x if="search.type == 'group'">:search.px</x>
         <x if="search.type != 'group'">:search.pxView</x>
        </x>
        <!-- Portlet bottom, potentially customized by the app -->
        <x>::ztool.portletBottom(rootClass)</x>
       </div>
      </x>
     </x>''')

    # The message that is shown when a user triggers an action
    pxMessage = Px('''
     <div class=":inPopup and 'messagePopup message' or 'message'"
          style="display:none" id="appyMessage">
      <!-- The icon for closing the message -->
      <img src=":url('close')" align=":dright" class="clickable"
           onclick="this.parentNode.style.display='none'"/>
      <!-- The message content -->
      <div id="appyMessageContent"></div>
      <div if="validator and validator.errors">:validator.pxErrors</div>
     </div>
     <script var="messages=ztool.consumeMessages()"
             if="messages">::'showAppyMessage(%s)' % q(messages)</script>''')

    # The login form
    pxLogin = Px('''
     <form id="loginForm" name="loginForm" method="post" class="login"
           action=":tool.url + '/performLogin'">
      <input type="hidden" name="js_enabled" id="js_enabled" value="0"/>
      <input type="hidden" name="cookies_enabled" id="cookies_enabled"
             value=""/>
      <input type="hidden" name="login_name" id="login_name" value=""/>
      <input type="hidden" name="pwd_empty" id="pwd_empty" value="0"/>
      <input type="hidden" name="authInfo" id="authInfo"
             value=":req.get('authInfo') or ''"/>
      <!-- Login fields directly shown or not depending on discreetLogin -->
      <span id="loginFields" name="loginFields"
            style=":cfg.discreetLogin and 'display:none' or 'display:block'">
       <span class="userStripText">:_('app_login')</span>
       <input type="text" name="__ac_name" id="__ac_name" value=""
              style="width: 142px"/>&nbsp;
       <span class="userStripText">:_('app_password')</span>
       <input type="password" name="__ac_password" id="__ac_password"
              style="width: 142px"/>
       <!-- The authentication context -->
       <x var="ctx=cfg.authContext"
          if="ctx and ctx.chooseOnLogin">:ctx.pxOnLogin</x>
       <!-- The "submit" button -->
       <input type="submit" name="submit" onclick="setLoginVars()"
              var="label=_('app_connect')" value=":label" alt=":label"
              style="margin: 0 10px"/>
       <input type="hidden" name="goto" value=":req.get('goto', None)"/>
       <!-- Forgot password ? -->
       <a if="ztool.showForgotPassword()"
          href="javascript: openPopup('askPasswordReinitPopup')"
          class="lostPassword">:_('forgot_password')</a>
       <!-- Hide the strip -->
       <img if="cfg.discreetLogin" src=":url('close')"
            onclick="toggleLoginForm(false)" class="clickable"/>
      </span>
     </form>''')

    # The page footer
    pxFooter = Px('''<span class="footerContent">::_('footer_text')</span>''')

    # Hooks for defining a PX that proposes additional links, before and after
    # the links corresponding to top-level pages.
    pxLinks = Px('')
    pxLinksAfter = Px('')

    # Hook for defining a PX that proposes additional icons after standard
    # icons in the user strip.
    pxIcons = Px('')

    pxHome = Px('''
     <table>
      <tr valign="middle">
       <td align="center">::_('front_page_text')</td>
      </tr>
     </table>''', template=AbstractWrapper.pxTemplate,
                  hook='content', name='home')

    pxInfo = Px('''
     <table>
      <tr valign="middle">
       <td align="center">::tool.request.get('info')</td>
      </tr>
     </table>''', template=AbstractWrapper.pxTemplate,
                  hook='content', name='info')

    # Error 404: page not found
    px404 = Px('''<div>::msg</div>
     <div if="not isAnon and not inPopup">
      <a href=":ztool.getSiteUrl()">:_('app_home')</a>
     </div>''', template=AbstractWrapper.pxTemplate, hook='content')

    # Error 403: unauthorized
    px403 = Px('''<div>
     <img src=":url('fake')" style="margin-right: 5px"/><x>::msg</x>
      <x if="tool.user.has_role('Manager')">::error_traceback</x></div>''',
     template=AbstractWrapper.pxTemplate, hook='content')

    # Error 500: server error
    px500 = Px('''<div>
     <img src=":url('warning')" style="margin-right: 5px"/><x>::msg</x></div>
     <!-- Show the traceback for admins -->
     <x if="showTraceback">::error_traceback</x>''',
     template=AbstractWrapper.pxTemplate, hook='content')

    pxQuery = Px('''
     <div var="className=req['className'];
               uiSearch=ztool.getSearch(className, req['search'], ui=True);
               klass=ztool.getAppyClass(className);
               resultModes=uiSearch.getModes(klass, ztool);
               rootHookId=uiSearch.getRootHookId()"
          id=":rootHookId">
      <script>:uiSearch.getCbJsInit(rootHookId)</script>
      <x>:tool.pxPagePrologue</x>
      <div align=":dright" if="len(resultModes) &gt; 1">
       <select name="px"
               onchange=":'switchResultMode(this, %s)' % q('queryResult')">
        <option for="mode in resultModes"
                value=":mode">:uiSearch.Mode.getText(mode, _)</option>
       </select>
      </div>
      <x>:uiSearch.pxResult</x>
     </div>''', template=AbstractWrapper.pxTemplate, hook='content')

    pxSearch = Px('''
     <x var="className=req['className'];
             refInfo=req.get('ref', None);
             searchInfo=ztool.getSearchInfo(className, refInfo);
             cssJs={};
             layoutType='search';
             x=ztool.getCssJs(searchInfo.fields, 'edit', cssJs)">

      <!-- Include type-specific CSS and JS -->
      <x if="cssJs">:tool.pxCssJs</x>
      <script>var errors = null;</script>

      <!-- Search title -->
      <h1><x>:_('%s_plural'%className)</x> &ndash;
          <x>:_('search_title')</x></h1>
      <!-- Form for searching objects of request/className -->
      <form name="search" action=":ztool.absolute_url()+'/do'" method="post">
       <input type="hidden" name="action" value="SearchObjects"/>
       <input type="hidden" name="className" value=":className"/>
       <input if="refInfo" type="hidden" name="ref" value=":refInfo"/>

       <table class="searchFields">
        <tr for="searchRow in ztool.getGroupedSearchFields(searchInfo)"
            valign="top">
         <td for="field in searchRow" class="search"
             var2="scolspan=field and field.scolspan or 1"
             colspan=":scolspan"
             width=":'%d%%' % ((100/searchInfo.nbOfColumns)*scolspan)">
           <x if="field">:field.pxRender</x>
           <br class="discreet"/>
         </td>
        </tr>
       </table>

       <!-- Submit button -->
       <input var="label=_('search_button');
                   css=ztool.getButtonCss(label, small=False)" type="submit"
              class=":css" value=":label" style=":url('search', bg=True)"/>
      </form>
     </x>''', template=AbstractWrapper.pxTemplate, hook='content')

    def forToolWriters(self):
        '''Some elements are only accessible to tool writers (ie Managers)'''
        if self.allows('write'): return ('view', 'xml')

    def pageForToolWriters(self):
        '''Some tool pages are only accessible to tool writers (ie Managers)'''
        if self.allows('write'): return 'view'

    def computeConnectedUsers(self, expr=None, context=None):
        '''Computes a table showing users that are currently connected.

        If p_expr is given, it must be an expression that will be evaluated on
        every connected user. The user will be part ofthe result only if the
        expression evaluates to True. The user is given to the expression as
        variable "user".'''
        # Get and count connected users
        users = self.o.loggedUsers.items()
        users.sort(key=lambda u: u[1], reverse=True) # Sort by last access date
        count = len(users)
        # Prepare the expression's context when relevant
        if expr:
            if context == None: context = {}
        # Compute table rows
        rows = []
        for userId, access in users:
            user = self.search1('User', noSecurity=True, login=userId)
            if not user: continue # Could have been deleted in the meanwhile
            if expr:
                # Update the p_expr's context with the current user
                context['user'] = user
                # Evaluate it
                if not eval(expr, context): continue
            rows.append('<tr><td><a href="%s">%s</a></td><td>%s</td></tr>' % \
                        (user.url, user.title, self.formatDate(access)))
        # Create an empty row if no user has been found
        if not rows:
            rows.append('<tr><td colspan="2" align="center">%s</td></tr>' %
                        self.translate('no_value'))
            count = 0
        else:
            count = len(rows)
        # Build the entire table
        r = '<table cellpadding="0" cellspacing="0" class="list compact">' \
            '<tr><th>(%d)</th><th>%s</th></tr>' % \
            (count, self.translate('last_user_access'))
        return r + '\n'.join(rows) + '</table>'

    def getObject(self, id, temp=False):
        '''Allow to retrieve an object from its unique p_id'''
        return self.o.getObject(id, appy=True, temp=temp)

    def getDiskFolder(self):
        '''Returns the disk folder where the Appy application is stored'''
        return self.o.config.diskFolder

    def getDbFolder(self):
        '''Returns the folder where the database is stored'''
        return self.o.getDbFolder()

    def getClass(self, zopeName):
        '''Gets the Appy class corresponding to technical p_zopeName'''
        return self.o.getAppyClass(zopeName)

    def getAvailableLanguages(self):
        '''Returns the list of available languages for this application'''
        return [(t.id, t.title) for t in self.translations]

    def convert(self, fileName, format):
        '''Launches a UNO-enabled Python interpreter as defined in the tool for
           converting, using LibreOffice in server mode, a file named p_fileName
           into an output p_format.'''
        convScript = '%s/pod/converter.py' % os.path.dirname(appy.__file__)
        cfg = self.o.getProductConfig(True)
        cmd = [cfg.unoEnabledPython, convScript, fileName, format,
               '-p%d' % cfg.libreOfficePort]
        self.log('executing %s...' % str(cmd))
        return executeCommand(cmd) # The result is a tuple (s_out, s_err)

    def sendMail(self, to, subject, body, attachments=None, replyTo=None):
        '''Sends a mail. See doc for appy.gen.mail.sendMail'''
        mailConfig = self.o.getProductConfig(True).mail
        sendMail(mailConfig, to, subject, body, attachments=attachments,
                 log=self.log, replyTo=replyTo)

    def formatDate(self, date, format=None, withHour=True, language=None):
        '''Check doc @ToolMixin::formatDate'''
        if not date: return
        return self.o.formatDate(date, format, withHour, language)

    def now(self, format=None):
        '''Returns the current date/hour as a DateTime instance. If p_format is
           specified, it returns a formatted date instead.'''
        from DateTime import DateTime
        res = DateTime()
        if format: res = res.strftime(format)
        return res

    def getUserName(self, login=None, normalized=False):
        '''Gets the user name corresponding to p_login (or the currently logged
           user if None), or the p_login itself if the user does not exist
           anymore. If p_normalized is True, special chars in the first and last
           names are normalized.'''
        if not login:
            user = self.user
        else:
            user = self.search1('User', noSecurity=True, login=login)
            if not user: return login
        return user.getTitle(normalized=normalized)

    def refreshCatalog(self, startObject=None, onlyUID=False):
        '''Reindex all Appy objects, or only those starting at p_startObject.
           If p_onlyUID is True, a single index (UID) is recomputed. Else, all
           the other indexes are recomputed, this one excepted.'''
        indexes = ['UID']
        exclude = not onlyUID
        if not startObject:
            # All database objects must be reindexed
            app = self.o.getParentNode()
            if not onlyUID:
                # Starts by clearing the catalog
                self.log('recomputing the whole catalog ' \
                         '(starts by clearing it)...')
                app.catalog._catalog.clear()
                self.log('catalog cleared.')
                # Reindex special index UID for all objects. Indeed, other
                # indexes may depend on the links between objects, which are
                # implemented via this index.
                self.refreshCatalog(onlyUID=True)
                self.log('reindexing all indexes but "UID" for every object...')
            else:
                self.log('reindexing "UID" for every object...')
            # Reindex all Appy objects (in root folders)
            nb = 1
            failed = []
            for folder in self.o.getRootFolders():
                for obj in getattr(app, folder).objectValues():
                    subNb, subFailed = self.refreshCatalog(startObject=obj,
                                                           onlyUID=onlyUID)
                    nb += subNb
                    failed += subFailed
                if folder == 'config':
                    try: # Reindex the tool itself
                        app.config.reindex(indexes=indexes, exclude=exclude)
                    except Exception:
                        failed.append(app.config)
            # Try to re-index all objects for which reindexation has failed
            for obj in failed:
                try:
                    obj.reindex(indexes=indexes, exclude=exclude)
                except Exception:
                    self.log('%s coult not be reindexed' % str(obj),
                             type='error')
            failMsg = failed and ' (%d retried)' % len(failed) or ''
            self.log('%d object(s) reindexed%s.' % (nb, failMsg))
        else:
            nb = 1
            failed = []
            for obj in startObject.objectValues():
                subNb, subFailed = self.refreshCatalog(startObject=obj,
                                                       onlyUID=onlyUID)
                nb += subNb
                failed += subFailed
            try:
                startObject.reindex(indexes=indexes, exclude=exclude)
            except Exception, e:
                failed.append(startObject)
            return nb, failed

    def repairCatalog(self):
        '''Removes catalog's brains whose object does not exist anymore. This
           method returns the total number of Appy objects in the database.'''
        # We use here m_executeQuery's ability to auto-clean dead brains
        tool = self.o
        count = 0
        for className in tool.getAllClassNames():
            self.log('checking %s catalog entries...' % className)
            r = tool.executeQuery(className, maxResults='NO_LIMIT',
                                  noSecurity=True)
            classCount = len(r.objects)
            self.log('%d %s object(s) scanned.' % (classCount, className))
            count += classCount
        self.log('catalog cleaned.')
        return count

    def _login(self, login):
        '''Performs a login programmatically. Used by the test system.'''
        self.request.user = self.search1('User', noSecurity=True, login=login)

    def doSynchronizeExternalUsers(self):
        '''Synchronizes the local User copies with a distant LDAP user base'''
        cfg, context = self.o.getProductConfig(True).getLdap()
        if not cfg: raise Exception('LDAP config not found.')
        message = cfg.synchronizeUsers(self, sso=context)
        return True, message

    def showSynchronizeUsers(self):
        '''Show this button only if a LDAP connection exists and is enabled'''
        cfg, context = self.o.getProductConfig(True).getLdap()
        if cfg and cfg.enabled: return 'buttons'

    def mayDelete(self):
        '''No one can delete the tool'''
        return

    def inPopup(self):
        '''Are we in thre popup ?'''
        rq = self.request
        return rq and rq.get('popup') == '1'

    def calendarPreCompute(self, first, grid):
        '''Computes pre-computed information for the tool calendar'''
        # If this calendar is used as mode for a search, get this search
        req = self.request
        pxContext = req.pxContext
        mode = None
        if 'uiSearch' in pxContext:
            # The search and related mode are already in the PX context
            mode = pxContext['mode']
        elif req.has_key('search') and req.has_key('className'):
            # Get the search and its mode from request keys
            className = req['className']
            tool = self.o
            search = self.o.getSearch(className, req['search'], ui=True)
            mode = search.Calendar(tool.getAppyClass(className), className,
                                   search, pxContext['inPopup'], tool)
            mode.init(req, pxContext['dir'])
        # Trigger the search via the mode
        if mode: mode.search(first, grid)
        return O(mode=mode)

    def calendarAdditionalInfo(self, date, preComputed):
        '''Renders the content of a given cell in the calendar used for
           searches' calendar mode.'''
        info = preComputed.mode.dumpObjectsAt(date)
        if info: return info

    def initRequest(self, req):
        '''Every time a request is performed and the corresponding p_req(uest)
           object is created, if a method called "initialiseRequest" exists on
           the Appy app's tool, it will be called with the request object as
           unique arg. It is useful for caching info on it.'''
        if not hasattr(self, 'initialiseRequest'): return
        self.initialiseRequest(req)

    def setBaseVariables(self, context, obj):
        '''See doc for appy.px.Px::setBaseVariables'''
        return Px.setBaseVariables(self, context, obj)

    def showIcon(self, config):
        '''Wen must we show the tool icon in the UI ?'''
        if config.toolShow:
            # A specific condition has been defined
            r = config.toolShow(self)
        else:
            # No specific condition: show the icon to anyone having write access
            # to the tool.
            r = self.allows('write')
        return r

    def searchAll(self):
        '''Allows to retrieve search results from a peer site'''
        if not self.user.hasRole('Manager'): self.raiseUnauthorized()
        # Retrieve the name of the class for which instances must be searched
        className = self.request.get('className')
        if not className:
            raise Exception('Specify the name of the class in key "className".')
        sortBy = self.request.get('sortBy') or 'Created'
        return ['%s/xml' % o.url \
                for o in self.search(className, noSecurity=True, sortBy=sortBy)]
# ------------------------------------------------------------------------------
