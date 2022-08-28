'''User-interface module'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import os.path, re

from appy.px import Px
from appy.utils import asDict
from appy.utils.string import Variables
from appy.model.utils import Object as O

# Make classes from sub-packages available here  - - - - - - - - - - - - - - - -
from appy.ui.js import Quote
from appy.ui.title import Title
from appy.ui.iframe import Iframe
from appy.ui.message import Message
from appy.ui.portlet import Portlet
from appy.ui.globals import Globals
from appy.ui.columns import Columns
from appy.ui.template import Template
from appy.ui.navigate import Siblings
from appy.ui.includer import Includer
from appy.ui.language import Language
from appy.ui.validate import Validator
from appy.ui.svg import Config as SvgConfig

# Some elements in this module will be traversable - - - - - - - - - - - - - - -
traverse = {'Language': True}

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Config:
    '''Represents user-interface configuration for your app'''

    # Defaults fonts used in the web user interface
    defaultFonts = "Rajdhani, sans-serif"

    def __init__(self):
        '''Constructor for the UI configuration'''

        # For any standard image provided by Appy (background images, icons...),
        # if you want to use an alternate image provided by your app or ext:
        # - create, in your app's or ext's "static" folder, an image having the
        #   same name and extension as the Appy file you want to override,
        #   located in appy/ui/static ;
        # - if the file is a SVG file, you're already done! Indeed, SVG files
        #   are managed in a special way, loaded in RAM ;
        # - else, add, in dict "images" hereafter, an entry whose key is the
        #   name of the image and whose value is the name of the app or ext
        #   whose "static" folder stores your variant.
        
        # For example, suppose your app is named "MyApp" and you want to provide
        # your own home background picture. In folder MyApp/static, create your
        # own picture and store it under the name homeBG.jpg. Then, add the
        # following entry into dict "images":
        
        #                      "homeBG.jpg" : "MyApp"

        # The following table lists the names of the most frequent images you
        # could override.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # Name            | Description
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # homeBG.jpg      | The home page's background image
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # baseBG.jpg      | The background image for any other non-popup page
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # popupBG.jpg     | The background image for any page in the popup
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # homeLogo.png    | The logo shown on the home page for anonymous users,
        #                 | in the top left corner, on top of the home
        #                 | background.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # headerBG.png    | The background image for the header
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # portletLogo.png | The logo at the top of the portlet
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # loginLogo.png   | The logo at the top of the login box
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # ...             | Consult folder appy/ui/static for a complete list of
        #                 | images to override. Do not try to override CSS or JS
        #                 | files.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

        # This system implies that:
        # - you are "forced" to use images having the same type and extension as
        #   Appy standard ones. For example, because Appy uses SVG icons, your
        #   replacement icons must be SVG, too ;
        # - the names of the replacement images must be exactly the same as the
        #   names of the files from appy/ui/static.
        self.images = {}

        # Appy comes with a set of standard SVG icons, stored in appy/ui/static.
        # If you develop an app with an elaborate graphic design, you may end up
        # with proposing an alternative for every SVG icon. That's fine, but for
        # some projects, you may find it interesting to have a cheaper yet
        # satisfying approach, consisting in using the base set of SVG icons,
        # whose colors have been changed according to your needs. Appy allows to
        # do that, via the SvgConfig instance as defined hereafter. Basically,
        # within most Appy SVG icons, 3 different colors may be used; they are
        # defined in a unique place, in this SvgConfig instance (see details in
        # appy/ui/svg.py). At server startup, all SVG files will be pre-loaded
        # in RAM and will be updated with these colors.
        self.svg = SvgConfig()

        # Name of the home page. Here are the possibilites.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "home"  | (the default one) The default home page displays the login
        #         | box on top of a window-wide, single background image.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "homes" | This page displays the login box on top of a space divided
        #         | in as much sections as there are defined background images
        #         | in attribute "homesBackgrounds", each one rendered besides
        #         | each other.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.home = 'home'

        # The background images to use when the home page is "homes". Every
        # entry looks like:
        #
        #                "<file_name>": "<image_width>"
        #
        # Here is an example, for a triptych:
        #
        #                     {"bg1.jpg": "30%",
        #                      "bg2.jpg": "40%",
        #                      "bg3.jpg": "30%"}
        #
        # As usual, if the background files originate from an alternate place
        # (ie, an ext), also add them in dict images as defined hereabove.
        self.homesBackgrounds = {}

        # Attribute "headerBackground" determines properties for the header's
        # background image, as a tuple or list
        # 
        #                      (name, repetition, position)
        #
        # The default value as defined hereafter is appropriate for placing a
        # logo at the center of the header. Because there may be several
        # different headers (ie, a specific header may be defined on public
        # pages), it is possible to define another name for the background
        # image, rather than the default "headerBG.png". Attribute
        # "headerBackground" may hold a function, accepting the current root PX
        # and its context as args, and must return a tuple or list as described
        # hereabove. If name of the background image is None or the empty
        # string, no background will be rendered. Specifying None as global
        # value for attribute "headerBackground" is invalid.
        self.headerBackground = ['headerBG.png', 'no-repeat', 'center']

        # Attributes "[home|base|popup]background determine properties for the
        # corresponding backgrounds whose standard files are described
        # hereabove, as tuples (or lists) of the form
        # 
        #                      (name, repetition, size)
        #
        # Each such attribute may also hold a function, accepting the current
        # root PX and its context as args, and returning a tuple or list as
        # described hereabove. If name of the background image is None or the
        # empty string, no background will be rendered. Specifying None as
        # global value for any attribute is invalid.
        self.homeBackground  = ['homeBG.jpg' , 'no-repeat', 'cover']
        self.baseBackground  = ['baseBG.jpg' , 'no-repeat', 'cover']
        self.popupBackground = ['popupBG.jpg', 'no-repeat', 'cover']

        # The following attribute determines how the block of controls is
        # aligned within the header. If the margin is defined to be "left", the
        # block will be aligned to the right, and vice versa. The attribute may
        # hold a function, accepting the current root PX and its context as
        # args, and must return one of the above-mentioned values.
        self.headerMargin = 'left'

        # Attribute "headerShow" determines when and where the page header must
        # be shown. Possible values are the following.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   "top"   | The header will be placed on top of the page, in order to
        #           | produce this global page schema:
        #           |
        #           |   H         e         a         d         e          r
        #           |
        #           |   Portlet   P  a  g  e   c  o  n  t  e  n  t   Sidebar
        #           |
        #           |   F         o         o         t         e          r
        #           |
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   "sub"   | The header will be placed on top of the page content, in
        #           | between the portlet and sidebar, to produce this global
        #           | page schema:
        #           |
        #           |   Portlet   H     e     a     d     e       r  Sidebar
        #           |
        #           |             P  a  g  e    c  o  n  t  e  n  t
        #           |
        #           |   F         o         o         t         e          r
        #           |
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "portlet" | The header will be placed on top and within the portlet:
        #           |
        #           |   Header    P  a  g  e    c  o  n  t  e  n  t  Sidebar
        #           |   Portlet
        #           |
        #           |   F         o         o         t         e          r
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   None    | The header will be invisible
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # If you place a function in this attribute, it will be called with, as
        # args, the current root PX and its context, and must return one of the
        # above-mentioned values.
        self.headerShow = lambda px, ctx: 'top' if not px.isHome(ctx) else None

        # Attribute "footerShow" determines when the page footer must be shown.
        # It can be a boolean value or a function. If a function is placed, it
        # will be called with, as args, the current root PX and its context, and
        # must return a boolean value.
        self.footerShow = False

        # Fonts in use
        self.fonts = Config.defaultFonts
        self.fontSize = '100%'

        # Among the fonts listed above, specify here, as a tuple, those being
        # Google fonts. That way, the corresponding "CSS include" will be
        # injected into all the pages from your app.
        self.googleFonts = ('Rajdhani',)

        # If you want to add specific CSS classes to some standard Appy parts,
        # specify a function in the following attribute. The function will
        # receive, as args, the name of the concerned part, the current root PX
        # and its context; it must return the name of one or more CSS classes,
        # or None when no class must be added. Currently defined parts are the
        # following.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   body      | The page "body" tag
        #   main      | The main zone of any page
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.css = None

        # Color used when a bright color is required
        self.brightColor = 'white'
        # Color used when a dark background is required
        self.darkColor = '#002039'
        # Alternate, lighter color
        self.lightColor = '#f0f0f0'
        # Alternate text color, also used for button borders and other discreet
        # places.
        self.altColor = '#009aa4'
        # Variant being lighter
        self.altColorLight = '#e9f2f3'
        # Color for some selected text
        self.selectColor = self.brightColor
        # Row background colors for most list-based data
        self.evenColor = 'rgba(243,243,247,0.7)'
        self.oddColor = 'rgba(255,255,255,0.5)'
        # Background, border and font colors for some dark table headers
        self.thColor = self.brightColor
        self.thBdColor = self.darkColor
        self.thBgColor = self.darkColor
        # Styling groups with style "grid". It corresponds to CSS class "ggrid",
        # not to be confused with CSS class "grid".
        self.gridGPadding = '8px' # Padding, on all layouts
        self.gridVLFSize = '100%' # Font size, on *v*iew (*l*abels)
        self.gridVFFSize = '100%' # Font size, on *v*iew (*f*ield values)
        self.gridELFSize = '100%' # Font size, on *e*dit (*l*abels)
        self.gridEFFSize = '100%' # Font size, on *e*dit (*f*ield values)
        # In the popup, everything is smaller. If you want to achieve the same
        # result in the main window, set "compact" to True.
        self.compact = False
        # Some input fields will get this background color once they will
        # contain erroneous content.
        self.wrongTextColor = '#009ba4'
        # Text color representing a problem or warning (some flavour of red)
        self.warnColor = '#e15151'
        # Text color in the header
        self.headerColor = self.brightColor
        # Background color for the header
        self.headerBgColor = self.darkColor
        self.headerSpanColor = self.brightColor # Color for standard text
                                                # rendered within in the header.

        # Text color for links
        self.linkColor = self.darkColor
        self.visitedColor = self.linkColor
        self.messageLinkColor = self.linkColor
        # Border bottom for input fields
        self.itextBottom = '1px solid'
        self.itextBottomColor = '#afb8d4'
        # Color used as "fill" color, ie, for the message box
        self.fillColor = '#dab823'
        # Background color for the inline Python interpreter
        self.pythonBgColor = self.darkColor

        # Styling the home page
        self.homeShowLogo = True # Logo on the top-left corner on the home page
        self.homeTextColor = self.brightColor # Text color
        self.homeTextLeft = '45px' # Distance from the left of the screen
        self.homeTextTop = '25px'  # Distance from the top of the screen

        # Styling the login box
        self.loginTitleWeight = 'normal'
        self.loginTitleSize = '160%'
        self.loginTitleTransform = 'none'
        self.loginTitleMargin = '0.7em 0 3px 0'
        self.boxBgColor = self.brightColor
        self.loginBgColor = '#f5f3f2'
        self.loginBoxPadding = '35px'
        self.loginColor = self.darkColor
        self.loginColorPh = '#a9b1b7' # Color for the input *p*lace*h*older
        self.loginWeightPh = 'bold' # Font-weight for the placeholder
        self.loginTransformPh = 'uppercase' # Text transform for the
                                            # placeholder. Other possible values
                                            # include "none" or "capitalize".
        self.loginWidth = '240px'
        self.loginInputSize = '100%' # Font size within input fields
        self.loginPadding = '12px'
        self.loginRadius = '0'
        self.loginMargin = '8px 0'
        self.loginBorder = '0px solid' # Background excepted
        self.loginBorderD = self.loginBorder # For the *d*iscreet variant of
                                             # the login box
        self.loginShadow = '0 4px 8px 0 rgba(160, 104, 132, 0.2), ' \
                           '0 6px 20px 0 rgba(0, 0, 0, 0.19)'
        self.loginShadowD = self.loginShadow
        self.loginBorderRadius = '0'
        self.loginAlign = 'center'
        self.loginTop = '50%' # Position of the login box on the y axis
        self.loginTopD = self.loginTop

        # Styling the "connect" button
        self.submitTop = '30px' # Vertical space between login/password inputs
                                # and the "connect" button
        self.submitColor = self.brightColor
        self.submitAlign = 'center'
        self.submitBgColor = self.darkColor
        self.submitBgUrl = 'none'
        self.submitBgRadius = '0'
        self.submitWidth = '260px' # If you want it to have the same width as
                                   # the login and connect fields, set a width
                                   # being 20px more than these fields' widths.
        self.submitHeight = 'inherit'
        self.submitWeight = 'normal'
        self.submitPadding = '12px'

        # Popups
        self.popupColor = self.brightColor

        # Portlet
        self.portletShowLogo = True # Logo on top of the portlet
        self.portletShowFooter = False # Portlet-specific footer
        self.portletWidth = '250px'
        self.portletMinWidth = '140px'
        self.portletBgColor = 'transparent'
        # The following attribute allows to colorize the background of the
        # portlet zone corresponding to the currently shown page.
        self.portletBgColorS = 'transparent'
        self.portletTextColor = self.darkColor
        self.portletShadow = '2px 2px 5px #002039' # Set "unset" to remove  it
        self.portletSep = '1px solid #002039' # Set "none" to remove it
        self.portletSepGap = '1.5em' # Vertical gap between portlet zones
        self.portletPadding = '30px 50px 0 0'
        self.portletTPadding = '5px 0' # Portlet title: padding
        self.portletTWeight = 'normal' # Portlet title boldness: could be "bold"
        self.portletTSize = '100%' # Portlet title font-size
        self.portletISize = '24px' # Size of most *i*cons in the portlet
        self.portletAHeight = '24px' # Height for *A*dd buttons. If the imahe
                                     # image height is < text height, space can
                                     # be reduced using value 'min-content'.
        self.portletBgPos = '0' # Background position for portlet buttons
        self.portletFBgColor = self.darkColor # *F*ooter background color
        self.portletFWidth = self.portletWidth # *F*ooter width
        self.portletFHeight = '100px' # *F*ooter height
        self.pgMargin = '0.5em 0 0.3em' # *p*ortlet *group margins
        self.pgPadding = '5px 0 0 0' # *p*ortlet *group padding
        self.pgTransform = 'uppercase' # Set "none" to disable it
        self.pgLineHeight = 'normal'
        self.pgGap = '0.4em'
        self.gcPadding  = '0 0 0 10px' # *G*roup *c*ontent paddings
        self.gcFSize = '100%' # *F*ont size
        self.gcFStyle = 'normal' # *F*ont style, can be "italic"

        # The sidebar (sb)
        self.sbPadding = '28px 8px 30px 0px'

        # Advanced search link
        self.asMargin = '3px 0 10px 30px' # For link "*a*dvanced *s*earch"
        self.asFSize = '90%'

        # Live search (ls)
        self.lsBgColor = 'transparent' # Bg color for zone "search field + icon"
        self.lsInputBgColor = 'transparent' # Bg color for the search field only
        self.lsInputWidth = '7.5em'
        self.lsInputHeight = '22px'
        self.lsInputPadding = '0'
        self.lsrBgColor = self.brightColor # Bg color for search *r*esults
        self.lsPadding = '0'
        self.lsMargin = '0' # Needs !important suffix
        self.lsFSize ='100%' # *F*ont size
        self.lsBottom = '1px solid' # Border bottom
        self.lsBottomColor = '#afb8d4'
        self.sdropWidth = '11em' # *s*earch results dropdown width
        self.sdropMargin = '0.6em 0 0 0'

        # The search "top" zone (above search results)
        self.sTopFSize = '100%'
        self.sTopPadding = '0 0 1em 0'
        self.sTopMargin = 'initial'
        self.sTopBorderB = 'none' # Border bottom

        # Other elements
        self.gridFiltersMargin = '20px 0 0 0' # Filter in grid search results
        self.weekEndBg = '#797979' # Background for calendar week-end cells
        self.ecWidth = '12px' # Width for *e*xpand / *c*ollapse icons
        self.podIWidth = '18px' # Width for the POD icons
        self.podPWidth = '50px' # Width for the POD icons in phases
        self.podITopC = '21px' # *I*con's text top position on *c*ell layouts
        self.podIRightC = '3px' # *I*con's text right position on *c*ell layouts
        self.sfDirection = 'row' # *s*earch *f*ilter direction: set
                                 # "row-reverse" to position the search/funnel
                                 # icon before the search field.
        self.gridPadding = '10px' # Padding for tables having CSS class "grid"
        self.histMargin = 'margin:0 0 5px 0' # Margins for zone "history"
        self.lgMargin = '0' # Margin for a multi*l*in*g*ual block

        # Header
        self.headerHeight = '60px'
        self.burgerMargin = '0 5px'
        self.topIconsMargin = '0 0.5em 0 0'
        self.topIconsGap = '0.5em 1em'
        self.topIconsHomesDir = 'row' # On "homes", if the number of icons/links
                                      # is too high, it may be convenient to
                                      # display them in flex-direction "column"
                                      # instead of "row".
        self.topIconsHomesBg = 'transparent'
        self.topTextPadding = '0 0.5em' # Padding for links or chunks of text
                                        # shown in the header.
        self.topTextSpacing = '1px' # Letter sppacing
        self.topSpanWeight = 'bold'

        # Footer
        self.footerHeight = '20px'
        self.footerBgColor = '#ececec'
        self.footerBgTop = '1px solid #c4c4c4'
        self.footerAlign = 'right'
        self.footerFontSz = '65%'

        # Tabs
        self.tabMargin = '0 0 1px 0' # Space between tabs and content
        self.tabMarginP = '0' # Same space, for tabs within *p*hases
        self.tabColor = self.linkColor # Color for clickable labels
        self.tabFSize = '95%' # *F*ont size
        self.tabBg = '#f1eeee' # background color for an unselected tab
        self.tabBgS = '#fbfbfb' # BG for the selected tab
        self.tabBorder = '1px solid %s' % self.linkColor # Top, l, r borders
        self.tabTransform = 'none' # Could be "uppercase"
        self.tabBorderBottom = self.tabBorder # Bottom border
        self.tabBorderBottomP = 'unset' # Bottom border for tabs within *p*hases
        self.tabBorderRadius = '5px 5px 0 0'

        # Styling phases (containing a picto per page)
        self.phaseBgColor = self.brightColor # When unselected
        self.phaseBgcColor = self.darkColor # When selected (*c*urrent)
        self.phaseFilter = 'invert(66%)' # The CSS filter to apply when selected
        self.phaseBorderColor = self.linkColor # Set "transparent" to hide it
        self.phaseColor = self.linkColor # Font color unselected
        self.phaseCcolor = self.brightColor # Font color, selected (*c*urrent)
        self.phaseMargin = '0 0 30px -30px' # Margins for phases
        self.phaseCMargin = '0 0 20px 0' # Margins for phases, *c*ompact variant
        self.pageGap = '0 0' # Gap between pages (vertical & horizontal).
                             # Example: "0.6em ​1em"

        # Pages' attributes, with alternate values when the UI is compact (see
        # attribute "compact "hereabove).
        self.pageHeight = '115px'
        self.pageCHeight = '80px'
        self.pageWidth = '125px'
        self.pageCWidth = '110px'
        self.pagePadding = '0'
        self.pageCPadding = '0'
        self.pageRadius = 'unset' # Border radius
        self.pageCRadius = 'unset' # Example: "0 0 5px 5px"
        self.pageTextTransform = 'uppercase'  # "none", "lowercase",
        self.pageCTextTransform = 'uppercase' # "capitalize" ...
        self.pageTextWeight = 'bold'
        self.pageFontSize = '90%'
        self.pageCFontSize = '9pt'
        self.pageChars = 27  # Max # of shown chars for a page title
        self.pageCharsS = 31 # Max # of shown chars for a page title, when shown
                             # in a *s*elect widget.

        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # If attribute          | The name of the page 
        # "pageDisplay" is ...  | will be rendered ...
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "block"               | under the picto ;
        # "inline"              | besides the picto.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.pageDisplay = 'block'
        # Styling block "Navigation to siblings", that appears in the phases
        self.navsPadding = '10px 0 0 0'
        # Size of pictos (width and height)
        self.pictoSize = '55px'
        self.pictoCWidth = '35px'
        self.pictoCHeight = '35px'
        self.pictoMargin = '0 0 6px 0'
        self.pictoCMargin = '0 0 4px 0'

        # Standard buttons, generally appearing on top of dark backgrounds.
        # Buttons appearing in standard bright backgrounds use p_self.darkColor
        # and not this p_self.buttonColor.
        self.buttonColor = self.brightColor
        self.buttonCase = 'uppercase'

        # *A*ction buttons (fields being actions and workflow transitions)
        self.abuttonBgColor = 'transparent' # Standard buttons outside phases
        self.abuttonBgColorS = 'transparent' # *S*mall buttons

        # Bottom space for every field
        self.fieldBottom = '0.7em'

        # Within a page, by default, the "edit" icon has an "absolute" position.
        # If you want to use standard positioning, set value "inherit".
        self.epictoPosition = 'absolute'
        self.epictoPadding = '0'
        self.epictoWidth = '22px'

        # Application-wide default formats for hours and dates
        self.dateFormat = '%d/%m/%Y'
        self.hourFormat = '%H:%M'

        # Fadeout duration for the message
        self.messageFadeout = '6s'
        # Application-wide maximum results on a single page of query results
        self.maxPerPage = 30
        # Number of translations for every page on a Translation object
        self.translationsPerPage = 30
        # If users modify translations via the ui, we must now overwrite their
        # work with the current content of po files at every server restart. In
        # any other case, it is preferable to do it.
        self.loadTranslationsAtStartup = True
        # Language that will be used as a basis for translating to other
        # languages.
        self.sourceLanguage = 'en'
        # For every language code that you specify in this list, Appy will
        # produce and maintain translation files.
        self.languages = ['en']
        # If languageSelector is True, on (almost) every page, a language
        # selector will allow to switch between languages defined in
        # self.languages. Else, the browser-defined language will be used for
        # choosing the language of returned pages.
        self.languageSelector = False
        # If the language selector is shown, the default selectable languages
        # will be those from p_self.languages hereabove, excepted if you specify
        # a sub-set of it in the following attribute.
        self.selectableLanguages = None
        # If "forceLanguage" is set, Appy will not take care of the browser
        # language, will always use the forced language and will hide the
        # language selector, even if "languageSelector" hereabove is True.
        self.forcedLanguage = None
        # When no translation is available in some language, Appy will fall back
        # to translations in this language.
        self.fallbackLanguage = 'en'
        # If you want to distinguish a test site from a production site, set the
        # "test" parameter to some text (lie "TEST SYSTEM" or
        # "VALIDATION ENVIRONMENT". This text will be shown on every page. This
        # parameter can also hold a function that will accept the tool as single
        # argument and returns the message.
        self.test = None
        # CK editor configuration. Appy integrates CK editor via CDN (see
        # http://cdn.ckeditor.com). Do not change "ckVersion" hereafter,
        # excepted if you are sure that the customized configuration files
        # config.js, contents.css and styles.js stored in
        # appy/ui/static/ckeditor will be compatible with the version you want
        # to use.
        self.ckVersion = '4.17.2'
        # ckDistribution can be "basic", "standard", "standard-all", "full" or
        # "full-all" (see doc in http://cdn.ckeditor.com).
        # CK toolbars are not configurable yet. So toolbar "Appy", defined in
        # appy/ui/static/ckeditor/config.js, will always be used.
        self.ckDistribution = 'standard'
        # The tool may be configured in write-access only for a technical
        # reason, ie, for allowing user self-registration. Indeed, in that case,
        # anonymous users must be granted the ability to add a User instance in
        # Ref tool.users. In that case, we don't want to show the icon allowing
        # to access the tool to anyone having write-access to it. For these
        # cases, a specific function may be defined here for determining
        # showability of the tool's icon in the UI. This function will receive
        # the tool as unique arg.
        self.toolShow = True
        # Attribute "showRootPages" determines if the "links" allowing to hit
        # root, selectable pages (=every page being in tool.pages, flagged as
        # "selectable"), located in the page header, must be shown or not. It
        # can be a function accepting the tool as unique arg.
        self.showRootPages = True
        # "links" to root pages can be rendered in 2 ways: either as explicit
        # "a" tags, or in a "select" HTML control, as options. The number
        # defined hereafter determines how many "links" will be rendered as
        # explicit "a" tags. The remaining pages (if any) will thus appear as
        # options in a "select" HTML control. Note that, on a mobile device,
        # this number is ignored: in order to save space, all pages will appear
        # in a "select" HTML control.
        self.expandedRootPages = 3
        # Attribute "showUserLink" determines if the link to logged user's
        # profile, located in the page header, must be show or not. It can be a
        # function accepting the tool as unique arg.
        self.showUserLink = True
        # When "showUserLink" is True, but the following attribute "userLink" is
        # False, the user's first name is unclickable.
        self.userLink = True
        # If you want to prefix the user's first name by some word, like
        # "welcome", set here a i18n label that will be used to produce this
        # word (like standard label "welcome").
        self.userPrefix = None

        # If you want to suffix the user's first name link with the user's full
        # title, set the following attribute to True. Works only when
        # p_self.headerShow is "portlet".
        self.userTitle = False
        # In the page header, there is an icon allowing to go back to the user's
        # home page, as defined by method tool.computeHomePage(). You can define
        # the visibility of this icon via the following attribute. It can hold a
        # function that will receive the tool as unique arg. Note that, if
        # p_self.headerShow is "portlet", the home icon is not shown, because
        # replaced with the portlet logo.
        self.showHomeIcon = True
        # When link "login" is shown (i, discreet login is enabled), must an
        # icon be shown besides the link ?
        self.showLoginIcon = True
        # Must text "Disconnect" be renderer besides the "logout" icon ?
        # Defaults to "no".
        self.logoutText = False
        # Attribute "discreetLogin" determines the app's home page and
        # visibility of the login box. If its value is...
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # False   | (the default), users will hit the app on the default home
        #         | page (see attribute "home") containing a login box inviting
        #         | them to connect. The login box is not "discreet": 
        #         | authentication is a prerequisite to most actions to perform
        #         | with the app;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # True    | users will hit the app on tool/public. The first contact
        #         | with the app will be via public page(s); the login box will
        #         | only be shown after the users clicks on a discreet icon (=
        #         | the "login icon"). A click on this icon will show the login
        #         | box as a popup.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # "home"  | similar to the previous case (True), but when users click on
        #         | the "login icon", they are redirected to the default home
        #         | page (see attribute "home") instead of getting the login box
        #         | as a popup.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.discreetLogin = False

    def formatDate(self, tool, date, format=None, withHour=True, language=None):
        '''Returns p_date formatted as specified by p_format, or self.dateFormat
           if not specified. If p_withHour is True, hour is appended, with a
           format specified in self.hourFormat.'''
        fmt = format or self.dateFormat
        # Resolve Appy-specific formatting symbols used for getting translated
        # names of days or months:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  %dt  | translated name of day
        #  %DT  | translated name of day, capitalized
        #  %mt  | translated name of month
        #  %MT  | translated name of month, capitalized
        #  %dd  | day number, but without leading '0' if < 10
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        if ('%dt' in fmt) or ('%DT' in fmt):
            day = tool.translate('day_%s' % date._aday, language=language)
            fmt = fmt.replace('%dt', day.lower()).replace('%DT', day)
        if ('%mt' in fmt) or ('%MT' in fmt):
            month = tool.translate('month_%s' % date._amon, language=language)
            fmt = fmt.replace('%mt', month.lower()).replace('%MT', month)
        if '%dd' in fmt: fmt = fmt.replace('%dd', str(date.day()))
        # Resolve all other, standard, symbols
        r = date.strftime(fmt)
        # Append hour
        if withHour and (date._hour or date._minute):
            r += ' (%s)' % date.strftime(self.hourFormat)
        return r

    def getHeaderText(self, tool):
        '''Get the permanent text that must appear in the page header'''
        # Get the text via config attribute "test"
        r = self.test
        if callable(r): r = test(tool)
        return r or ''

    def getBackground(self, px, ctx, type, popup=None):
        '''Return the CSS properties allowing to include this background p_image
           when appropriate.'''
        # Do not generate any background image when appropriate
        if px.name == 'home':
            # Only the home background must be shown on the home page
            stop = type != 'home'
        elif px.name == 'public':
            # The base or home backgrounds must not be shown on the public page
            stop = type != 'header'
        elif px.name == 'homes':
            # Specific multiple backgrounds will be set outside this function
            stop = True
        else:
            # On any other page, allow any background, home excepted
            stop = type == 'home'
        if stop: return ''
        if type in ('home', 'base', 'popup'):
            # The background image for the home page or any other page
            image, repeat, size = self.cget('%sBackground' % type, ctx)
            if not image: return
            attrs = 'background-size:%s' % size
        elif type == 'header':
            # The background for the page header
            image, repeat, position = self.cget('headerBackground', ctx)
            if not image: return
            attrs = 'background-position: %s' % position
        base = self.images.get(image) or 'appy'
        return 'background-image: url(%s/static/%s/%s); background-repeat: ' \
               '%s; %s' % (ctx.siteUrl, base, image, repeat, attrs)

    def _show(self, elem, px, context, popup):
        ''''In any case, hide p_elem in the popup. In any other situation, use
            the UI attribute defining visibility for p_elem.'''
        #if popup or (px.name.startswith('home')): return
        if popup: return
        # Use the corresponding config attribute
        r = getattr(self, '%sShow' % elem)
        return r(px, context) if callable(r) else r

    def tget(self, name, tool):
        '''Get, on p_self, attribute named p_name. If the attribute value is
           callable, call it, with the p_tool as unique arg.'''
        # "tget" stands for "get, with the *t*ool as arg".
        r = getattr(self, name)
        return r(tool) if callable(r) else r

    def cget(self, name, ctx):
        '''Get, on p_self, attribute named p_name. If the attribute value is
           callable, call it, with the current root PX and its context as
           args.'''
        # "cget" stands for "get, with the current root PX and its *c*context
        # as args".
        r = getattr(self, name)
        return r(ctx._px_, ctx) if callable(r) else r

    def showHeader(self, px, context, popup):
        return self._show('header', px, context, popup)

    def showFooter(self, px, context, popup):
        return self._show('footer', px, context, popup)

    def getClass(self, part, px, context):
        '''Get the CSS classes that must be defined for some UI p_part, if
           any.'''
        # Apply default CSS classes
        if part == 'main':
            compact = ' mainC' if self.compact or context.popup else ''
            r = 'main rel%s' % compact
        else:
            r = ''
        # Add specific classes when relevant
        if self.css:
            add = self.css(part, px, context)
            if not add: return r
            r = add if not r else ('%s %s' % (r, add))
        return r

    def getFontsInclude(self):
        '''If Google Fonts are in use, return the link to the CSS include
           allowing to use it.'''
        families = '|'.join(self.googleFonts)
        return 'https://fonts.googleapis.com/css?family=%s' % families

    def showTool(self, tool):
        '''Show the tool icon to anyone having write access to the tool,
           excepted if a specific function is defined.'''
        if callable(self.toolShow):
            # A specific function has been defined
            r = self.toolShow(tool)
        else:
            # No specific function: show the icon to anyone having write access
            # to the tool.
            r = tool.allows('write')
        return r

    def patchCss(self, css):
        '''Replaces variables possibly defined in this p_css code with values
           from p_self.'''
        return Variables.replace(css, self)

    def getUserText(self, user):
        '''Get the text to show within the user link'''
        r = user.getFirstName()
        if self.userPrefix:
            r = '%s %s' % (user.translate(self.userPrefix), r)
        return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class LinkTarget:
    '''Represents information about the target of an HTML "a" tag'''

    def __init__(self, class_=None, back=None, popup=None, forcePopup=False):
        '''The HTML "a" tag must lead to a page for viewing or editing an
           instance of some p_class_. If this page must be opened in a popup
           (depends on p_popup, if not None, or attribute p_class_.popup else),
           and if p_back is specified, when coming back from the popup, we will
           ajax-refresh a DOM node whose ID is specified in p_back.'''
        # The link leads to a instance of some Python p_class_ (the true Python
        # class, not the metaclass)
        self.class_ = class_
        # Does the link lead to a popup ?
        if popup or forcePopup:
            toPopup = True
        elif popup == False:
            toPopup = False
        else:
            toPopup = class_ and hasattr(class_, 'popup')
        # Determine the target of the "a" tag
        self.target = 'appyIFrame' if toPopup else '_self'
        # If the link leads to a popup, a "onClick" attribute must contain the
        # JS code that opens the popup.
        if toPopup:
            # Create the chunk of JS code to open the popup
            size = popup or getattr(class_, 'popup', '350px')
            if isinstance(size, str):
                params = "%s,null" % size[:-2] # Width only
            else: # Width and height
                params = "%s,%s" % (size[0][:-2], size[1][:-2])
            # If p_back is specified, included it in the JS call
            if back: params += ",null,'%s'" % back
            self.onClick = "openPopup('iframePopup',null,%s)" % params
        else:
            self.onClick = ''

    def getOnClick(self, back, o=None):
        '''Gets the "onClick" attribute, taking into account p_back DOM node ID
           that was unknown at the time the LinkTarget instance was created.'''
        # If we must not come back from a popup, return an empty string
        r = self.onClick
        if not r: return r
        if o:
            # Get a specific CSS class to apply to the popup
            css = o.class_.getCssFor(o, 'popup')
            css = css if css == 'popup' else ('%s popup' % css)
            css = "'%s'" % css
        else:
            css = 'null'
        return r[:-1] + ",%s,'%s')" % (css, back)

    def __repr__(self):
        return '<LinkTarget for=%s,target=%s,onClick=%s>' % \
               (self.__class__.__name__, self.target, self.onClick or '-')

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Collapsible:
    '''Represents a chunk of HTML code that can be collapsed/expanded via
       clickable icons.'''

    @classmethod
    def get(class_, zone, align, req):
        '''Gets a Collapsible instance for showing/hiding some p_zone
           ("portlet" or "sidebar").'''
        icons = 'showHide' if align == 'left' else 'showHideInv'
        return Collapsible('appy%s' % zone.capitalize(), req,
                           default='expanded', icons=icons, align=align)

    # Various sets of icons can be used. Each one has a CSS class in appy.css
    iconSets = {'expandCollapse': O(expand='expand', collapse='collapse'),
                'showHide':       O(expand='show',   collapse='hide'),
                'showHideInv':    O(expand='hide',   collapse='show')}

    # Icon allowing to collapse/expand a chunk of HTML
    px = Px('''
     <img var="coll=collapse; icons=coll.icons"
          id=":'%s_img' % coll.id" align=":coll.align" class=":coll.css"
          onclick=":'toggleCookie(%s,%s,%s,%s,%s)' % (q(coll.id), \
                    q(coll.display), q(coll.default), \
                    q(icons.expand), q(icons.collapse))"
       src=":coll.expanded and svg(icons.collapse) or svg(icons.expand)"/>''',

     css='''
      .expandCollapse { cursor:pointer; width:|ecWidth| }
      .showHide { position: absolute; top: 10px; left: 0px; cursor: pointer }
      .showHideInv { position: absolute; top: 10px; right: 0px; cursor: pointer}
     ''')

    def __init__(self, id, req, default='collapsed', display='block',
                 icons='expandCollapse', align='left'):
        '''p_display is the value of style attribute "display" for the XHTML
           element when it must be displayed. By default it is "block"; for a
           table it must be "table", etc.'''
        self.id = id # The ID of the collapsible HTML element
        self.default = default
        self.display = display
        self.align = align
        # Must the element be collapsed or expanded ?
        self.expanded = (req[id] or default) == 'expanded'
        self.style = 'display:%s' % (self.display if self.expanded else 'none')
        # The name of the CSS class depends on the set of applied icons
        self.css = icons
        self.icons = self.iconSets[icons]

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Sidebar:
    '''The Appy sidebar'''

    @classmethod
    def show(class_, tool, o, layout, popup):
        '''The sidebar must be shown when p_o declares to use the sidebar. If
           it must be shown, its width is returned.'''
        if not o: return
        sidebar = getattr(o.class_.python, 'sidebar', None)
        if not sidebar: return
        if callable(sidebar): sidebar = sidebar(tool)
        if not sidebar: return
        if sidebar.show in (True, layout):
            # Complete user info
            sidebar.width = sidebar.width or '320px'
            sidebar.minWidth = sidebar.minWidth or '320px'
            return sidebar

    @classmethod
    def getStyle(class_, sidebar, collapse):
        '''Gets the CSS properties to apply to the sidebar'''
        return '%s;width:%s;min-width:%s' % \
               (collapse.style, sidebar.width, sidebar.minWidth)

    px = Px('''
     <div var="page,grouped,css,js,phases=o.getGroupedFields('main','sidebar');
               collapse=ui.Collapsible.get('sidebar', dright, req)"
          id=":collapse.id" class="sidebar"
          style=":ui.Sidebar.getStyle(showSidebar, collapse)">
      <x>::ui.Includer.getSpecific(tool, css, js)</x>
      <x var="layout='view'">:o.pxFields</x>
     </div>''',

     css='''.sidebar { padding:|sbPadding|; position:sticky; top:0;
                       overflow-y:auto; overflow-x:auto }''')

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Breadcrumb:
    '''A breadcrumb allows to display the "path" to a given object, made of the
       object title, prefixed with titles of all its container objects.'''

    def __init__(self, o, popup):
        # The concerned p_o(bject)
        self.o = o
        # The "sup" part may contain custom HTML code, retrieved by app method
        # o.getSupBreadCrumb, to insert before the breadcrumb.
        self.sup = None
        # The "sub" part may contain custom HTML code, retrieved by app method
        # o.getSubBreadCrumb, to insert after the breadcrumb.
        self.sub = None
        # The breadcrumb in itself: a list of of parts, each one being an Object
        # having 2 attributes:
        # - "title" is the title of the object represented by this part;
        # - "url"   is the URL to this object.
        self.parts = None
        # The CSS classes to apply to the main breacrumb tag
        self.css = 'pageTitle breadTitle'
        if popup: self.css += ' pageTitleP'
        # No breadcrumb is computed for the tool
        if o != o.tool:
            self.compute(popup=popup)

    def compute(self, o=None, popup=False):
        '''Computes the breadcrumb to p_self.o, or add the part corresponding to
           p_o if p_o is given. If p_popup is True, the produced URLs are a
           bit different.'''
        # If we are recursively computing the breadcrumb on p_self.o's container
        # (or its super-container, etc), "recursive" is True.
        recursive = o is not None
        o = o or self.o
        # We must compute a complete breadcrumb for p_self.o. But must a
        # breadcrumb be shown for it ?
        python = o.getClass().python
        show = getattr(python, 'breadcrumb', True)
        if callable(show): show = show(o)
        # Return an empty breadcrumb if it must not be shown
        if not show: return
        # Compute "sup" and "sub"
        if not recursive:
            if hasattr(python, 'getSupBreadCrumb'):
                self.sup = o.getSupBreadCrumb()
            if hasattr(python, 'getSubBreadCrumb'):
                self.sub = o.getSubBreadCrumb()
        # Compute and add the breadcrumb part corresponding to "o"
        part = O(url=o.getUrl(popup=popup), title=o.getShownValue(),
                 view=o.allows('read'))
        if self.parts is None:
            self.parts = [part]
        else:
            self.parts.insert(0, part)
        # In a popup (or if "show" specifies it), limit the breadcrumb to the
        # current object.
        if popup or (show == 'title'): return
        # Insert the part corresponding to the container if appropriate
        container = o.container
        if container and (container.id != 'tool'):
            # The tool itself can never appear in breadcrumbs
            self.compute(container)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Button:
    '''Manages rendering of XHTML buttons'''

    @classmethod
    def getCss(class_, label, small=True, render='button', iconOut=False):
        '''Gets the CSS class(es) to set on a button, given its l_label, size
           (p_small or not) and rendering (p_render).'''
        # p_iconOut being True means that the button icon is rendered outside
        # the button. If it is the case, an additional CSS class must be applied
        # to it.
        prefix = 'noIcon ' if iconOut else ''
        if small:
            # CSS for a small button. No minimum width applies: small buttons
            # are meant to be small.
            part = 'Icon' if render == 'icon' else 'Small'
            return '%sbutton button%s' % (prefix, part)
        # CSS for a normal button. A minimum width (via buttonFixed) is defined
        # when the label is small: it produces ranges of buttons of the same
        # width (excepted when labels are too large), which is more beautiful.
        if len(label) < 15: return '%sbuttonFixed button' % prefix
        return '%sbutton' % prefix

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Footer:
    '''Footer for all (non-popup) pages'''

    px = Px('''<div class="footer">
     <div class="footerContent">::_('footer_text')</div></div>''',

     css='''
      .footer { width:100%; height:|footerHeight|; text-align:|footerAlign|;
                position:fixed; bottom:0; background-color:|footerBgColor|;
                border-top:|footerBgTop|; z-index:10; font-size:|footerFontSz| }
      .footerContent { padding: 5px 1em 0 0 }''')

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Browser:
    '''Determines if the browser is compatible with Appy'''

    # Main regex, allowing to extract browser name & version from the user agent
    rex = re.compile('([a-zA-Z]+)(?:/|\s+)(\d+\.\d+)')

    # Here are some examples. Trident corresponds to IE 11.
    #   MSIE 6.0
    #   Trident/7.0
    #   Firefox/103.0
    #   Chrome/103.0
    #   ...

    # Internet Explorer is not supported, any version
    unsupported = asDict(('Trident', 'MSIE'))

    # Supported browsers
    supported = asDict(('Firefox', 'Seamonkey', 'Chrome', 'Chromium', 'Safari',
                        'OPR', 'Opera'))

    # If several browser names are included in the user agent, these ones take
    # precedence over others.
    precedes = asDict(('Firefox', 'Chrome', 'Chromium'))

    # Browser names and minimal versions as supported by Appy
    versions = {'Chrome': 87.0, 'Chromium': 87.0, 'Firefox': 90.0}

    @classmethod
    def getIncompatibilityMessage(class_, tool, handler):
        '''Return an error message if the browser in use is not compatible
           with Appy.'''
        # Get the "User-Agent" request header
        agent = handler.headers.get('User-Agent')
        if not agent: return
        # Get all (name, version) pairs as carried by the user agent
        pairs = class_.rex.findall(agent)
        if not pairs: return
        # Keep only the relevant pair
        name = version = None
        for n, v in pairs:
            # Directly dismiss unsupported browsers
            if n in class_.unsupported:
                return tool.translate('wrong_browser')
            elif n in class_.supported:
                # A supported browser has been found
                if name:
                    if n in class_.precedes:
                        # We have 2 names: keep the most appropriate one
                        name = n
                        version = v
                    break
                name = n
                version = v
        # Issue a warning if the browser version is unsupported
        if version:
            minimal = class_.versions.get(name)
            if minimal and float(version) < minimal:
                map = {'name': name, 'version': version, 'minimal':minimal}
                return tool.translate('old_browser', mapping=map)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
