'''Base template for any UI page'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.px import Px
from appy.utils import asDict

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Template:
    '''The main UI template'''

    @classmethod
    def getPageTitle(class_, tool, o):
        '''Returns content for tag html > head > title'''
        # Return the error code as page title if an error occurred
        resp = tool.resp
        if resp.code != 200: return str(resp.code.value)
        # Return the app name in some cases
        if not o or o == tool:
            r = tool.translate('app_name_raw')
        else:
            # The page title is based on p_o's title
            r = o.getShownValue() or ''
        # Ensure this is a string
        r = r if isinstance(r, str) else str(r)
        # If a XHTML paragraph is found, keep the part before it
        if '</p>' in r: r = r[3:r.index('</p>')]
        # Add p_o's page title if found
        if o and 'page' in tool.req:
            label = '%s_page_%s' % (o.class_.name, tool.req.page)
            text = tool.translate(label, blankOnError=True)
            if text:
                if r: r += ' :: '
                r += text
        return Px.truncateValue(r, width=100)

    # PX for which compact CSS must be used
    compactPx = {'payload': ('homes',), 'content': ('public', 'homes')}

    # CSS classes to use, for every zone and compactness
    zoneCss = {'payload': {False: 'payload', True: 'payload payloadP'},
               'content': {False: 'content', True: 'contentP'}}

    # Values for "show header" that do not require a global top space
    showheaderNoTop = asDict((None, 'sub', 'portlet'))

    @classmethod
    def getCssFor(class_, zone, c):
        '''Return the CSS class(es) to apply to this p_zone'''
        # In some situations (ie, in the popup), a more compact design must be
        # applied.
        compact = c.popup or (not c.showPortlet and \
                              (c._px_.name in (class_.compactPx[zone])))
        return class_.zoneCss[zone][compact]

    @classmethod
    def includeLoginBox(class_, c):
        '''Must the login box be included in the current page ?'''
        # The login box has no sense if the user is already authenticated or in
        # the process of self-registering, or if browser incompatibility has be
        # detected.
        if not c.isAnon or c.o.isTemp() or c.bi: return
        # Moreover, if we are on the public page and the authentication will be
        # done by redirecting the user to tool/home, it is useless to include
        # the login box in this case, too.
        if c._px_.name == 'public' and c.cfg.discreetLogin == 'home':
            return
        # Include it in any other case
        return True

    @classmethod
    def getMainStyle(class_, c):
        '''Return the CSS properties for the main, global zone'''
        # Get the main background image
        r = c.cfg.getBackground(c._px_, c, type='home')
        # Get the global height. Substract the footer height if the footer is
        # shown, excepted if the portlet footer is there. In this latter case,
        # set the main height to 100%: the portlet itself will get a reduced
        # height taking into account its specific footer.
        if c.showFooter and not c.showFooterP:
            height = 'calc(100%% - %s)' % c.cfg.footerHeight
        else:
            height = '100%'
        height = 'height:%s' % height
        return '%s;%s' % (r, height) if r else height

    @classmethod
    def getPayloadStyle(class_, c):
        '''Gets the CSS styles to apply to the "payload" zone'''
        # The payload zone is the block portlet / content / sidebar
        # ~~~ Determine the background image
        r = c.cfg.getBackground(c._px_, c, type='popup' if c.popup else 'base')
        # ~~~ Determine the "top" property
        showHeader = c.showHeader
        if c.showHeader in class_.showheaderNoTop or c.payloadCss.endswith('P'):
            top = '0'
        else:
            top = c.headerHeight
        top = 'top:%s' % top
        r = '%s;%s' % (r, top) if r else top
        return r

    @classmethod
    def getIconsStyle(class_, c):
        '''Get CSS styles to apply to the block of icons in the page header'''
        margin = c.cfg.cget('headerMargin', c)
        return 'margin-%s:auto' % margin

    @classmethod
    def getContentStyle(class_, c):
        '''Get CSS dynamic CSS properties for the "content" zone'''
        # Fix vertical scroll when the portlet footer is shown together with
        # the global footer: in that case, the global height is 100% and does
        # not take footer height into account.
        if not c.popup and c.showFooter and c.showFooterP:
            r = ' style="overflow-y:auto"'
        else:
            r = ''
        return r

    @classmethod
    def getContent(class_, c):
        '''Returns the page content, with the sub-header when relevant'''
        r = '<div class="%s"%s>%s</div>' % (class_.getCssFor('content', c),
                                            class_.getContentStyle(c),
                                            c.content(c, applyTemplate=False))
        # Add the burger button to expand the portlet. Indeed, when the header
        # is inlaid into the portlet, the burger button being within ths header
        # is unavailable.
        if c.inlaidHeader:
            c.cookie = 'appyPortlet'
            c.bcss = 'eburger'
            r = '%s%s' % (class_.pxBurger(c), r)
        # Add the sub-header when appropriate
        if c.showHeader == 'sub':
            r = '<div class="subbed">%s%s</div>' % (class_.pxHeader(c), r)
        return r

    @classmethod
    def showConnect(class_, c):
        '''Show the "connect" link for anons only, if discreet login is enabled
           or if the login box is hidden, and if we are not already on a page
           allowing to log in.'''
        if not c.isAnon: return
        if c.cfg.discreetLogin:
            # Show it if we are not already on a page allowing to log in
            r = not c._px_.isHome(c, orPublic=False)
        else:
            # Show it if we are on the public site, where there is no login box
            r = c._px_.name == 'public'
        return r

    # Hooks for defining PXs proposing additional links or icons, before and
    # after the links / icons corresponding to top-level pages and icons.
    pxLinksBefore = pxLinks = pxLinksAfter = None

    @classmethod
    def getBurgerStyle(class_, c):
        '''Get dynamic CSS properties to apply to a burger button'''
        # A portlet-related "e-burger" (=*e*xternal burger, being outside the
        # main header), must only be shown if the portlet is collapsed.
        if c.bcss == 'eburger' and c.req.appyPortlet != 'collapsed':
            r = 'none'
        else:
            r = 'block'
        return 'display:%s' % r

    # PX for rendering a burger button
    pxBurger = Px('''
     <a class=":bcss|''" style=":Template.getBurgerStyle(_ctx_)"
        onclick=":'toggleCookie(%s,%s,%s,%s,%s)' %
                  (q(cookie), q('block'), q('expanded'), q('show'), q('hide'))">
      <img src=":svg('burger')" class="clickable icon"/>
     </a>''',

     css='''
      .burger { cursor:pointer; margin:|burgerMargin| }
      .eburger { position:absolute; top:2.7em; margin:0 7px }
      .eburger img { width:16px; transform:rotate(180deg) }''')

    # Link to go to the tool
    pxTool = Px('''
     <a href=":'%s/view' % tool.url" title=":_('Tool')">
      <img src=":svg('config')" class="icon"/></a>''')

    # The link to open the login box, if we are in "discreet login" mode
    pxLogin = Px('''
     <div class="textIcon" id="loginIcon" name="loginIcon"
          var2="loginUrl=guard.getLoginUrl(_ctx_)">
      <a href=":loginUrl">
       <img if="cfg.showLoginIcon" src=":svg('login')" class="icon textIcon"/>
      </a>
      <a href=":loginUrl"><span>:_('app_connect')</span></a>
     </div>''')

    # The link to log out
    pxLogout = Px('''
     <div if="not isAnon" class=":'textIcon' if cfg.logoutText else ''"
        var2="logoutText=_('app_logout');
              logoutUrl=guard.getLogoutUrl(tool, user)">
      <a href=":logoutUrl" title=":logoutText">
       <img src=":svg('logout')" class="icon"/></a>
      <a if="cfg.logoutText" href=":logoutUrl"><span>:logoutText</span></a>
     </div>''')

    # Global links, that can be shown within the template header but also from
    # other pages, like "home[s]", without the base header container.
    pxTemplateLinks = Px('''
     <!-- The burger button for collapsing the portlet -->
     <x if="showPortlet"
        var2="cookie='appyPortlet'; bcss='burger'">:Template.pxBurger</x>

     <!-- Custom links (I) -->
     <x>:Template.pxLinksBefore</x>

     <!-- Links and icons -->
     <div class="topIcons" style=":Template.getIconsStyle(_ctx_)">

      <!-- Custom links (II) -->
      <x>:Template.pxLinks</x>

      <!-- Header messages -->
      <span var="text=cfg.getHeaderText(tool)"
         if="not popup and text">::text</span>

      <!-- The home icon -->
      <a if="not isAnon and cfg.tget('showHomeIcon', tool)"
         href=":tool.computeHomePage()">
        <img src=":svg('home')" class="icon"/></a>

      <!-- Connect link if discreet login -->
      <x if="Template.showConnect(_ctx_)">:Template.pxLogin</x>

      <!-- Root pages -->
      <x if="cfg.tget('showRootPages', tool)"
         var2="pagesL, pagesO=tool.OPage.getRoot(tool)">
       <x if="pagesL or pagesO">:tool.OPage.pxSelector</x></x>

      <!-- Language selector -->
      <x if="ui.Language.showSelector(cfg,layout)">:ui.Language.pxSelector</x>

      <!-- User info and controls for authenticated users -->
      <x if="not isAnon">

       <!-- Config -->
       <x if="cfg.showTool(tool)">:Template.pxTool</x>

       <!-- User link -->
       <x if="cfg.tget('showUserLink', tool)">:user.pxLink</x>

       <!-- Authentication context selector -->
       <x var="ctx=config.security.authContext" if="ctx">:ctx.pxLogged</x>
      </x>

      <!-- Custom links (III) -->
      <x>:Template.pxLinksAfter</x>

      <!-- The burger button for collapsing the sidebar -->
      <x if="showSidebar" var2="cookie='appySidebar'">:Template.pxBurger</x>

      <!-- Logout -->
      <x if="not isAnon">:Template.pxLogout</x>
     </div>''',

     css='''
      .topIcons { display:flex; align-items:center; margin:|topIconsMargin|;
                  gap:|topIconsGap| }
      .topIcons > select { margin:0; color:|headerColor| }
      .topIcons > a { color:|headerColor|; font-weight:|topSpanWeight| }
      .topIcons span { text-transform:uppercase; font-weight:|topSpanWeight|;
                  letter-spacing:|topTextSpacing|; color:|headerSpanColor| }
      .textIcon { display:flex; align-items:center; gap:0.5em }''')

    # The global page header
    pxHeader = Px('''
     <div class="topBase"
          style=":cfg.getBackground(_px_, _ctx_, type='header')">
      <div class="top" style=":'height:%s' % headerHeight">
       <x>:Template.pxTemplateLinks</x>
      </div>
     </div>''',

     css='''
      .topBase { background-color:|headerBgColor|; width:100%; position:fixed;
                 color:|headerColor|; font-weight:lighter; z-index:1 }
      .top { display:flex; flex-wrap:nowrap; justify-content:space-between;
             align-items:center; margin:0 5px }
     ''')

    # The template of all base PXs
    px = Px('''
     <html var="x=handler.customInit(); cfg=config.ui; Template=ui.Template"
           dir=":dir">

      <head>
       <title>:Template.getPageTitle(tool, o or home)</title>
       <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1"/>
       <link rel="icon" type="image/x-icon" href=":url('favicon.ico')"/>
       <link rel="apple-touch-icon" href=":url('appleicon')"/>
       <x>::ui.Includer.getGlobal(handler, config, dir)</x>
      </head>

      <body class=":cfg.getClass('body', _px_, _ctx_)"
            var="showPortlet=ui.Portlet.show(tool, _px_, _ctx_);
                 showSidebar=ui.Sidebar.show(tool, o, layout, popup);
                 showHeader=cfg.showHeader(_px_, _ctx_, popup);
                 headerHeight=cfg.cget('headerHeight', _ctx_);
                 inlaidHeader=showHeader == 'portlet';
                 showFooter=cfg.showFooter(_px_, _ctx_, popup);
                 showFooterP=cfg.portletShowFooter;
                 bi=ui.Browser.getIncompatibilityMessage(tool, handler)">

       <!-- Browser incompatibility message -->
       <div if="bi" class="wrongBrowser">::bi</div>

       <!-- Google Analytics -->
       <x if="config.analytics">::config.analytics.get(tool)</x>

       <!-- Popups -->
       <x>::ui.Globals.getPopups(tool, svg, _, dleft, dright, popup)</x>

       <div class=":cfg.getClass('main', _px_, _ctx_)"
            style=":Template.getMainStyle(_ctx_)">

        <!-- Page header (top) -->
        <x if="showHeader == 'top'">:Template.pxHeader</x>

        <!-- Message zone -->
        <div height="0">:ui.Message.px</div>

        <!-- Login zone -->
        <x if="Template.includeLoginBox(_ctx_)">:guard.pxLogin</x>

        <!-- Payload: portlet / content / sidebar -->
        <div id="payload" var="payloadCss=Template.getCssFor('payload', _ctx_)"
             class=":payloadCss" style=":Template.getPayloadStyle(_ctx_)">

         <!-- Portlet -->
         <x if="showPortlet">:ui.Portlet.px</x>

         <!-- Page content -->
         <x>::Template.getContent(_ctx_)</x>

         <!-- Sidebar -->
         <x if="showSidebar">:ui.Sidebar.px</x>
        </div>

        <!-- Cookie warning -->
        <x if="not popup and not guard.cookiesAccepted">:guard.pxWarnCookies</x>

        <!-- Footer -->
        <x if="showFooter">:ui.Footer.px</x>

       </div>
      </body>
     </html>''', prologue=Px.xhtmlPrologue)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
