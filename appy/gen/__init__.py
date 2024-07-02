# ~license~
# ------------------------------------------------------------------------------
# Import stuff from appy.fields (and from a few other places too).
# This way, when an app gets "from appy.gen import *", everything is available.
import os.path
from appy.px import Px
from appy import Object
from appy.fields import Field
from appy.fields.pod import Pod

from appy.fields.text import Text
from appy.fields.info import Info
from appy.fields.date import Date
from appy.fields.file import File
from appy.fields.list import List
from appy.fields.dict import Dict
from appy.fields.rich import Rich
from appy.fields.page import Page
from appy.fields.hour import Hour
from appy.fields.workflow import *
from appy.fields.float import Float
from appy.fields.phase import Phase
from appy.fields.color import Color
from appy.fields.string import String
from appy.fields.action import Action
from appy.fields.custom import Custom
from appy.fields.switch import Switch
from appy.fields.boolean import Boolean
from appy.fields.integer import Integer
from appy.fields.ref import Ref, autoref
from appy.fields.computed import Computed
from appy.gen.layout import Table, Layouts
from appy.gen.monitoring import Monitoring
from appy.fields.group import Group, Column
from appy.fields.select import Select, Selection
from appy.fields.search import Search, UiSearch, Gridder
from appy.gen.utils import No, Tool, User, MessageException

# Make the following classes available here: people may need to override some
# of their PXs (defined as static attributes).
from appy.gen.wrappers import AbstractWrapper as BaseObject
from appy.gen.wrappers.ToolWrapper import ToolWrapper as BaseTool

# ------------------------------------------------------------------------------
class Ui:
    '''All configuration elements related to the user interface. Class Config
       below has a static attribute named "ui" holding this class.'''
    def __init__(self):
        # The top banner
        self.banner = 'banner.png'
        # If you place a function in the following attribute, it will be called
        # with, as args, the current PX and its context, and must return True
        # whenever the banner must be shown. If no function is set, the banner
        # will always be shown.
        self.bannerShow = None
        # Similar functions can be defined for determining visibility of other
        # UI elements.
        self.userStripShow = None
        self.footerShow = None
        # Fonts in use
        self.fonts = '"Lucida Grande","Lucida Sans Unicode",Arial,sans-serif'
        self.fontSize = '75%'
        # Among the fonts listed above, specify here, as a tuple, those being
        # Google fonts. That way, the corresponding "CSS include" will be
        # injected into all the pages from your app.
        self.googleFonts = ()
        # If you want to add specific CSS classes to some standard Appy parts,
        # specify a function in the following attribute. The function will
        # receive, as args, the name of the concerned part, the current PX and
        # its context; it must return the name of one or more CSS classes or
        # None when no class must be added. Currently defined parts are the
        # following.
        # ----------------------------------------------------------------------
        #   body      | The page "body" tag
        #   main      | The main zone of any page, behind the user strip
        # ----------------------------------------------------------------------
        self.css = None
        # Some input fields will get this background color once they will
        # contain erroneous content.
        self.wrongTextColor = '#f9edbe'
        # The tool may be configured in write-access only for a technical
        # reason, ie, for allowing user self-registration. Indeed, in that case,
        # anonymous users must be granted the ability to add a User instance in
        # Ref tool.users. In that case, we don't want to show the icon allowing
        # to access the tool to anyone having write-access to it. For these
        # cases, a specific function may be defined here for determining
        # showability of the tool's icon in the UI. This function will receive
        # the tool as unique arg.
        self.toolShow = None
        # Border style for tabs
        self.tabBorder = '1px solid #ff8040'

    def getBannerName(self, dir):
        '''If your site uses at least one RTL (right-to-left) language, you must
           propose a banner whose name is Ui.banner, suffixed with "rtl".'''
        res = self.banner
        if dir == 'rtl': res = '%srtl%s' % os.path.splitext(res)
        return res

    def _show(self, elem, px, context, inPopup):
        ''''As a general rule, always show UI p_elem, excepted in the popup or
            when a custom function prevents it.'''
        # Do not show it if we are in the popup
        if inPopup: return
        # A custom function may determine it. If no such function is defined,
        # show it.
        fun = getattr(self, '%sShow' % elem)
        return not fun and True or fun(px, context)

    def showBanner(self, px, context, inPopup):
        return self._show('banner', px, context, inPopup)

    def showUserStrip(self, px, context, inPopup):
        return self._show('userStrip', px, context, inPopup)

    def showFooter(self, px, context, inPopup):
        return self._show('footer', px, context, inPopup)

    def getClass(self, part, wide, px, context):
        '''Get the CSS classes that must be defined for some UI p_part, if
           any.'''
        # Start with the standard set of Appy classes that must set on p_part
        if part == 'main':
            r = wide and 'mainWide main rel' or 'main rel'
        else:
            r = ''
        # Add specific classes when relevant
        if self.css:
            add = self.css(part, px, context)
            if not add: return r
            if not r:
                r = add
            else:
                r = '%s %s' % (r, add)
        return r

    def getFontsInclude(self):
        '''If Google Fonts are in use, return the link to the CSS include
           allowing to use it.'''
        families = '|'.join(self.googleFonts)
        return 'https://fonts.googleapis.com/css?family=%s' % families

# ------------------------------------------------------------------------------
class Show:
    '''Provides some frequently used values for field's "show" attributes'''
    # As a convention, a trailing underscore indicates a negation

    # All layouts but edit. To use for users that can consult the field value
    # but cannot modify it. Also used for fields like some Ref fields that are
    # never manipulated via "edit" layouts.
    E_ = ('view', 'result', 'xml')
    # A variant, without "result"
    ER_ = ('view', 'xml')
    # A variant, with layout "buttons" instead of "result". "buttons"
    # corresponds, on lists, to the range of icons and/or buttons present in the
    # "title" column.
    E_B = ('view', 'buttons', 'xml')
    B = ('edit', 'view', 'buttons', 'xml')

    # All layouts but view. To use typically when, on view, the field value is
    # already shown as a part of some custom widget.
    V_ = ('edit', 'result', 'xml')
    # All layouts but view and edit. To use when you need both E_ and V_.
    VE_ = ('result', 'xml')
    # This set is used for showing workflow transitions in lists of objects
    TR = ('view', 'result')
    # This is, a.o., for custom widgets whose edit and view variants are not
    # that different, but that cannot be shown elsewhere (result, xml, etc).
    VE = ('view', 'edit')
    VX = ('view', 'xml')
    EX = ('edit', 'xml')

# ------------------------------------------------------------------------------
class Config:
    '''If you want to specify some configuration parameters for appy.gen and
       your application, please create a class named "Config" in the __init__.py
       file of your application and override some of the attributes defined
       here, ie:

       import appy.gen
       class Config(appy.gen.Config):
           langages = ('en', 'fr')
    '''
    # What skin to use for the web interface? Appy has 2 skins: the default
    # one (with a fixed width) and the "wide" skin (takes the whole page width).
    skin = None # None means: the default one. Could be "wide".
    # A reference to the Ui class (see above)
    ui = Ui()
    # For every language code that you specify in this list, appy.gen will
    # produce and maintain translation files.
    languages = ['en']
    # If languageSelector is True, on (almost) every page, a language selector
    # will allow to switch between languages defined in self.languages. Else,
    # the browser-defined language will be used for choosing the language
    # of returned pages.
    languageSelector = False
    # If "forceLanguage" is set, Appy will not take care of the browser
    # language, will always use the forced language and will hide the language
    # selector, even if "languageSelector" hereabove is True.
    forcedLanguage = None
    # When no translation is available in some language, Appy will fall back to
    # translations in this language.
    fallbackLanguage = 'en'
    # Show the link to the user profile in the user strip
    userLink = True
    # If you want to distinguish a test site from a production site, set the
    # "test" parameter to some text (lie "TEST SYSTEM" or
    # "VALIDATION ENVIRONMENT". This text will be shown on every page. This
    # parameter can also hold a function that will accept the tool as single
    # argument and returns the message.
    test = None

    @classmethod
    def getTestMessage(class_, tool):
        '''Returns the test message via attribute or method in "test"'''
        r = class_.test
        if callable(r): r = r(tool)
        return r

    # People having one of these roles will be able to create instances
    # of classes defined in your application.
    defaultCreators = ['Manager']
    # Roles in use in a Appy application are identified at generation time from
    # workflows or class attributes like "creators": it is not needed to declare
    # them somewhere. If you want roles that Appy will be unabled to detect, add
    # them in the following list. Every role can be a Role instance or a string.
    additionalRoles = []
    # What roles can unlock locked pages ? By default, only a Manager can do it.
    # You can place here roles expressed as strings or Role instances, global or
    # local.
    unlockers = ['Manager']
    # The "root" classes are those that will get their menu in the user
    # interface. Put their names in the list below. If you leave the list empty,
    # all gen-classes will be considered root classes (the default). If
    # rootClasses is None, no class will be considered as root.
    rootClasses = []
    # By default, instances of root classes will be stored in a database folder
    # named "data". You can specify an alternative base folder if the number of
    # created instances in this folder would become too high (maybe > 100 000).
    rootFolders = {}
    # Number of translations for every page on a Translation object
    translationsPerPage = 30
    # Language that will be used as a basis for translating to other
    # languages.
    sourceLanguage = 'en'
    # Activate or not the button on home page for asking a new password
    activateForgotPassword = True
    # Enable session timeout ?
    enableSessionTimeout = False
    # When a login is encoded by the user, a transform can be applied: upper,
    # lower or capitalize.
    loginTransform = None
    # If the following field is True, the login/password widget will be
    # discreet. This is for sites where authentication is not foreseen for
    # the majority of visitors (just for some administrators).
    discreetLogin = False
    # On user log on, you may want to ask them to choose their "authentication
    # context" in a list. Such a context may have any semantics, is coded as a
    # string and will be accessible on the Request object in attribute
    # "authContext". In order to activate authentication contexts, place here an
    # instance of a sub-class of appy.gen.authenticate::AuthenticationContext.
    # Please consult appy/gen/authenticate.py for more information.
    authContext = None
    # When using Ogone, place an instance of appy.gen.ogone.OgoneConfig in
    # the field below.
    ogone = None
    # When using Google analytics, specify here the Analytics ID
    googleAnalyticsId = None
    # Create a group for every global role ?
    groupsForGlobalRoles = False
    # When using a LDAP for authenticating users, place an instance of class
    # appy.shared.ldap.LdapConfig in the field below.
    ldap = None
    # When using, in front of an Appy server, a reverse proxy for authentication
    # for achieving single-sign-on (SSO), place an instance of
    # appy.shared.sso.SsoConfig in the field below.
    sso = None
    # When marshalling File fields via the XML layout, binary content is, by
    # default, included as a series of fixed size Base64-encoded chunks wrapped
    # in "part" tags. If the target site has access to this site's filesystem,
    # an alternative is to marshall the disk location of the binary file instead
    # of its content. If you want to enable this latter behaviour, set
    # the following attribute to False.
    marshallBinaries = True

    @classmethod
    def getLdap(class_):
        '''Returns the LDAP config if it exists'''
        # The LDAP config can be found either in global config attribute "ldap"
        # or in the context of a SSO system. This method returns a tuple
        #                     (ldapConfig, context)
        # "context" being None if the global LDAP config is returned, or being
        # the SSO config if the LDAP is the one embedded in this SSO config.
        if class_.ldap:
            r = class_.ldap, None
        else:
            sso = class_.sso
            if not sso or not sso.ldap:
                r = None, None
            else:
                r = sso.ldap, sso
        return r

    # When using a SMTP mail server for sending emails from your app, place an
    # instance of class appy.gen.mail.MailConfig in the field below.
    mail = None
    # For an app, the default folder where to look for static content for the
    # user interface (CSS, Javascript and image files) is folder "ui" within
    # this app.
    uiFolders = ['ui']
    # CK editor configuration. Appy integrates CK editor via CDN (see
    # http://cdn.ckeditor.com). Do not change "ckVersion" hereafter, excepted
    # if you are sure that the customized configuration files config.js,
    # contents.css and styles.js stored in appy/gen/ui/ckeditor will be
    # compatible with the version you want to use.
    ckVersion = '4.22.1'
    # ckDistribution can be "basic", "standard", "standard-all", "full" or
    # "full-all" (see doc in http://cdn.ckeditor.com).
    ckDistribution = 'standard'
    # CK toolbars are not configurable yet. So toolbar "Appy", defined in
    # appy/gen/ui/ckeditor/config.js, will always be used.

    # If the Python interpreter running this app is UNO-enabled, set None to
    # the following parameter. Else, specify the path to a UNO-enabled
    # interpreter. On Ubuntu, /usr/bin/python3 is UNO-enabled.
    unoEnabledPython = '/usr/bin/python3'
    # On what port does LibreOffice run ?
    libreOfficePort = 2002
    # Monitoring configuration. Update this instance (whose class is in
    # appy.gen.monitoring)) for changing the default configuration.
    monitoring = Monitoring()
# ------------------------------------------------------------------------------
