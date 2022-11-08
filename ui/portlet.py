'''Portlet management'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.px import Px

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Portlet:
    '''The portlet, in the standard layout, is a zone from the UI shown as a
       column situated at the left of the screen for left-to-right languages,
       and at the right for right-to-left languages.'''

    @classmethod
    def show(class_, tool, px, c):
        '''When must the portlet be shown ?'''
        # Do not show the portlet on 'edit' pages, if we are in the popup or if
        # there is no root class.
        if c.popup or c.layout == 'edit' or px.name == 'home' or \
           c.config.model.rootClasses is None:
            return
        # If we are here, portlet visibility depends on the app, via method
        # "tool::showPortletAt", when defined.
        return tool.showPortletAt(c.handler.path) \
               if hasattr(tool, 'showPortletAt') else True

    @classmethod
    def getZoneCss(class_, c, userZone=False):
        '''Get the CSS class(es) to define for the current portlet zone'''
        # Add one more class if the zone must be considered as currently
        # "selected".
        if userZone:
            # The user zone (in the inlaid portlet) is considered being selected
            # if the current object corresponds to the current user's profile.
            r = ' psel' if c.o == c.user else ''
        else:
            # A class-related zone is considered as selected if the current
            # object is an instance of this class or if the current search
            # related to it.
            if c.currentClass == c.className or \
               c.o.class_.name == c.className:
                r = ' psel'
            else:
                r = ''
        return 'pzone%s' % r

    @classmethod
    def getStyle(class_, c):
        '''Get the CSS properties to apply to the main portlet zone'''
        if c.showFooterP:
            # If the portlet-specific footer must be shown, it must appear on
            # top of the global footer: its z-index must then be higher.
            z = 12
            # Moreover, the portlet height must be computed to substract the
            # footer, being rendered in fixed position.
            sub = ' - %s' % c.cfg.portletFHeight
            if c.showFooter:
                sub += ' - %s' % c.cfg.footerHeight
            height = ';height:calc(100%%%s)' % sub
        else:
            z = 4
            height = ''
        return 'z-index:%d;%s%s' % (z, c.collapse.style, height)

    # A zone displaying user-related infos and controls
    pxUser = Px('''
     <div class=":ui.Portlet.getZoneCss(_ctx_, userZone=True)">
      <!-- The colored zone -->
      <div class="colorZ" style=":'background-color:%s' % cfg.svg.flashyColor">
      </div>
      <!-- Zone payload -->
      <div>
       <x if="not isAnon">

        <!-- Link to the user profile -->
        <x if="cfg.tget('showUserLink', tool)"
           var2="showUserIcon=False">:user.pxLink</x>

        <!-- User full title -->
        <div if="cfg.userTitle" class="utitle">
         <img src=":svg('user')" class="icon"/><x>:user.getTitle()</x></div>
       </x>

       <!-- Language selector -->
       <x if="ui.Language.showSelector(cfg,layout)">:ui.Language.pxSelector</x>

       <!-- Connect link if discreet login -->
       <x if="Template.showConnect(_ctx_)">:Template.pxLogin</x>

       <!-- Authentication context selector -->
       <x var="ctx=config.security.authContext" if="ctx">:ctx.pxLogged</x>

      </div>
     </div>''')

    # An alternate PX for the header, when inlaid in the portlet
    pxHeader = Px('''
     <!-- First line: the portlet logo, app name an a minimal set of icons -->
     <div class="htp">
       <a href=":tool.computeHomePage()">
        <img if="cfg.portletShowLogo" src=":url('portletLogo')"/>
       </a>
       <div>::_('app_name')</div>
       <!-- Icons -->
       <div>
        <!-- The burger button for collapsing the portlet -->
        <x var="cookie='appyPortlet'">:Template.pxBurger</x>
        <!-- Link to the config -->
        <x if="not isAnon and cfg.showTool(tool)">:Template.pxTool</x>
        <!-- Logout -->
        <x if="not isAnon">:Template.pxLogout</x>
       </div> 
     </div>

     <!-- The user zone -->
     <x>:ui.Portlet.pxUser</x>

     <!-- Pages and custom zone -->
     <div class="pzone">
      <div class="colorZ" style=":'background-color:%s' % cfg.svg.lightColor">
      </div>
      <div class="vflex">
       <!-- Custom links (I & II) -->
       <x>:Template.pxLinksBefore</x>
       <x>:Template.pxLinks</x>

       <!-- Header messages -->
       <div var="text=cfg.getHeaderText(tool)" class="test"
            if="not popup and text">::text</div>

       <!-- Root pages -->
       <x if="cfg.tget('showRootPages', tool)"
          var2="pagesL, pagesO=tool.OPage.getRoot(tool)">
        <x if="pagesL or pagesO">:tool.OPage.pxSelector</x></x>

       <!-- Custom links (III) -->
       <x>:Template.pxLinksAfter</x>
      </div>
     </div>''',

     # "htp" stands for *h*eader *t*op in *p*ortlet
     css='''
      .htp { display:flex; align-items:flex-start; padding:0 0 1.5em 1.5em;
             gap:0.7em; border-bottom: 1px solid lightgrey }
      .htp > :nth-child(2) { text-transform:uppercase; font-weight:bold }
      .htp > :nth-child(3) { display:flex; gap:0.4em; align-items:flex-end;
                             padding-right:1em; margin-left:auto }
      .htp .icon { width:16px }
      .vflex { display:flex; flex-direction:column }
      .portlet .textIcon { display:flex; flex-wrap:nowrap; gap:0.4em;
                           align-items:flex-end; text-transform:uppercase;
                           font-weight:bold; font-size:140% }
      .portlet .textIcon .icon { width:25px }
      .portlet #loginIcon { font-size:95% }
      .portlet #loginIcon img { width:20px }
      .utitle { font-size:110%; margin:0.2em 0 }
      .utitle img { width:18px; padding-right:0.3em }''')

    px = Px('''
     <div var="collapse=ui.Collapsible.get('portlet', dleft, req);
           toolUrl=tool.url;
           queryUrl='%s/Search/results' % toolUrl;
           cfg=config.ui;
           currentSearch=req.search;
           currentClass=req.className;
           currentPage=handler.parts[-1] if handler.parts else None;
           rootClasses=handler.server.model.getRootClasses()"
      id="appyPortlet" class="portlet" style=":ui.Portlet.getStyle(_ctx_)">

      <!-- The possibly inlaid header -->
      <x if="inlaidHeader">::ui.Portlet.pxHeader</x>

      <!-- The portlet logo -->
      <div if="cfg.portletShowLogo and not inlaidHeader" class="pzone">
       <img src=":url('portletLogo')" class="portletLogo"/>
      </div>

      <!-- One section for every searchable root class -->
      <x for="class_ in rootClasses" if="class_.maySearch(tool, layout)"
         var2="className=class_.name;
               pside=class_.getCssFor(tool, 'pside')">

       <!-- The section content -->
       <div class=":ui.Portlet.getZoneCss(_ctx_)">

        <!-- The colored portlet side -->
        <div if="pside" class=":'colorR %s' % pside"></div>

        <!-- Section title (link triggers the default search) -->
        <div class="portletContent"
             var="searches=class_.getGroupedSearches(tool, _ctx_);
                  labelPlural=_(className + '_plural');
                  indexable=class_.isIndexable();
                  viaPopup=None">
         <div class="portletTitle">
          <a if="indexable"
             var="queryParam=searches.default.name if searches.default else ''"
             href=":'%s?className=%s&amp;search=%s' % \
                    (queryUrl, className, queryParam)"
             onclick="clickOn(this)"
             class=":'current' if not currentSearch and
                     (currentClass == className) and
                     currentPage == 'pxResults' else ''">::labelPlural</a>
          <x if="not indexable">::labelPlural</x>
         </div>

         <!-- Create instances of this class -->
         <div if="guard.mayInstantiate(class_)"
              var2="buttonType='portlet'; nav='no';
                    label=None">:class_.pxAdd</div>

         <!-- Searches -->
         <x if="indexable and class_.maySearchAdvanced(tool)">

          <!-- Live search -->
          <x var="pre=className; liveCss='lsSearch'">:tool.Search.live</x>

          <!-- Advanced search -->
          <div var="highlighted=currentClass == className and
                                (req.search == 'customSearch')"
               class=":'portletAdv current' if highlighted else 'portletAdv'">
           <a var="text=_('search_title')"
              href=":'%s/Search/advanced?className=%s' % (toolUrl, className)"
              title=":text"><x>:text</x>...</a>
          </div>
         </x>

         <!-- Predefined searches -->
         <x for="search in searches.all" var2="field=search">
          <x>:search.px if search.type == 'group' else search.view</x>
         </x>

         <!-- Portlet bottom, potentially customized by the app -->
         <x var="bt=class_.getPortletBottom(tool)" if="bt">::bt</x>
        </div>
       </div>
      </x>
      <!-- The portlet footer -->
      <div if="showFooterP" class="portletFooter">
       <img src=":url('portletLogoF')" class="portletLogoF"/>
      </div>
     </div>''',

     css='''
       .portlet { padding:|portletPadding|; box-shadow:|portletShadow|;
                  position:sticky; top:0; overflow-y:auto; overflow-x:clip;
                  width:|portletWidth|; min-width:|portletMinWidth|;
                  font-size:98%; background-color:|portletBgColor| }
       .portlet a, .portlet a:visited { color: |portletTextColor| }
       .portletSearch a:hover { background-color:|brightColor|;
                                color:|linkColor| }
       .portletContent { padding-left: 18px; width: 100% }
       .portletTitle { padding:|portletTPadding|; text-transform:uppercase;
                       font-weight:|portletTWeight|; font-size:|portletTSize| }
       .portletLogo { margin:auto; left:0; right:0; padding:0 0 1em 1.5em }
       .portletLogoF { margin:auto }
       .portletGroup { display:flex; flex-wrap:nowrap; gap:|pgGap|;
                       align-items:center; text-transform:|pgTransform|;
                       padding:|pgPadding|; margin:|pgMargin|;
                       color:|portletTextColor|; line-height:|pgLineHeight| }
       .portletGC { padding:|gcPadding|; font-size:|gcFSize|;
                    font-style:|gcFStyle| }
       .portletAdv { margin:|asMargin|; font-size:|asFSize| }
       .portletSearch { text-align:left }
       .portletCurrent { font-weight:bold }
       .portletFooter { position:fixed; display:flex; bottom:0;
                        width:|portletFWidth|; height:|portletFHeight|;
                        background-color:|portletFBgColor| }
       .portlet form { margin:|pgMargin| }
       input.buttonPortlet { border:0; background-position:|portletBgPos|;
          background-color:transparent; background-size:|portletISize|;
          width:100%; height:|portletAHeight|; color:|portletTextColor|;
          border-radius:unset; text-align:left; font-size:100% }
       .pzone { display:flex; flex-wrap:nowrap; align-items:stretch;
                border-bottom:|portletSep|; margin-bottom:|portletSepGap|;
                padding-bottom:|portletSepGap| }
       .pzone > :nth-child(2) { padding-bottom:1.3em; margin-top:1em }
       .pzone:last-child { border:0; margin-bottom:0 }
       .psel { background-color:|portletBgColorS| }
       .colorZ { width:12px; margin-right:0.8em }
       .colorR { width:13px }''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
