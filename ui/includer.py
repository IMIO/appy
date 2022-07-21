'''Includes external static files (CSS, JS) into HTML pages'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Includer:
    '''Produces chunks of XHTML for including external files like CSS and
       Javascript files.'''

    @classmethod
    def css(class_, url, version=None):
        '''Produces a chunk of XHTML for including CSS file with this p_url'''
        v = '?%d' % version if version else ''
        return '<link rel="stylesheet" type="text/css" href="%s%s"/>' % (url, v)

    @classmethod
    def js(class_, url, version=None):
        '''Produces a chunk of XHTML for including JS file with this p_url'''
        v = '?%d' % version if version else ''
        return '<script src="%s%s"></script>' % (url, v)

    @classmethod
    def vars(class_, tool):
        '''Defines the global Javascript variables being declared in every Appy
           page.'''
        return '<script>var siteUrl="%s", sameSite="%s"</script>' % \
               (tool.siteUrl, tool.config.server.sameSite)

    @classmethod
    def getGlobal(class_, handler, config, dir):
        '''Returns a chunk of XHTML code for including, within the main page
           template, CSS and Javascript files.'''
        r = []
        tool = handler.tool
        sconfig = config.server.static
        # Get CSS files
        ltr = dir == 'ltr'
        # Get global CSS files from dict Static.ram. Indeed, every CSS file is
        # patched from a template and stored in it.
        for name in handler.Static.ram.keys():
            if name.endswith('.css'):
                # Do not include appyrtl.css, the stylesheet specific to
                # right-to-left (rtl) languages, if the language is
                # left-to-right.
                if ltr and name == 'appyrtl.css':
                    continue
                r.append(class_.css(tool.buildUrl(name, ram=True),
                                    version=sconfig.versions.get(name)))
        # Get CSS include for Google Fonts, when some of them are in use
        if config.ui.googleFonts:
            r.append(class_.css(config.ui.getFontsInclude()))
        # Get Javascript files
        for base, path in sconfig.map.items():
            for jsFile in path.glob('*.js'):
                r.append(class_.js(tool.buildUrl(jsFile.name, base=base),
                                   version=sconfig.versions.get(jsFile.name)))
        # Initialise global JS variables
        r.append(class_.vars(tool))
        return '\n'.join(r)

    @classmethod
    def getUrl(class_, url, tool):
        '''Gets an absolute URL based on p_url, that can already be absolute or
           not.'''
        if url.startswith('http'): return url
        return tool.buildUrl(url)

    @classmethod
    def getSpecific(class_, tool, css, js):
        '''Returns a chunk of XHTML code for including p_css and p_js files
           specifically required by some fields.'''
        r = []
        if css:
            for url in css: r.append(class_.css(class_.getUrl(url, tool)))
        if js:
            for url in js:  r.append(class_.js(class_.getUrl(url, tool)))
        return '\n'.join(r)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
