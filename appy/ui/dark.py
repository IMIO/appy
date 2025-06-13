'''Dark theme management'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.px import Px

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Config:
    '''Configuration about the dark theme'''

    def __init__(self):
        # Allow the user to switch to the dark mode ?
        self.enabled = False
        # If the dark mode is enabled, it it the default mode ?
        self.default = True
        # Background colors for the dark theme
        self.bgColor = '#222222' # Really dark
        self.bgColorL = '#333333' # A bit lighter
        self.bgColorB = '#c7c6c6' # More lighter (*b*right)
        # Lighter color used as separator between other elements
        self.sepColor = '#555555'
        # Font color
        self.fontColor = '#e2e2e2'
        # Dark font color
        self.fontColorD = '#111111'
        # Lighter font color
        self.fontColorL = '#ababab'
        # Brighter font color
        self.fontColorB = '#666666'
        # Background colors for tables
        self.thBg = '#272822'
        self.tdBg = '#282828'
        # Showy color
        self.showyColor = '#abab4e'

    def getJsParams(self, c):
        '''Returns the Javascript parameters to pass to the JS Dark object'''
        default = 'true' if self.default else 'false'
        _ = c._
        lighten = _('to_light')
        darken = _('to_dark')
        q = c.q
        return f'{default},{q(lighten)},{q(darken)}'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Dark:
    '''Management of the Appy dark mode'''

    # The mode switcher
    switcher = Px('''
     <script>:f'const dark = new Dark({cfg.dark.getJsParams(_ctx_)})'</script>
     <div id="darkSwitcher" class="clickable" onClick="dark.switch()"></div>
     <script>dark.setMode()</script>''',

    css='''
     .dark .content, .dark .dropdown, body.dark, .dark .lsSearch .dropdown {
       background-color:|bgColor| }
     .dark .portlet { background-color:|bgColorL|;
                      box-shadow:none; border-right: 4px solid |sepColor| }
     .dark, .dark .phase a, .dark a, .dark .portlet a, .dark a:visited,
       .dark .portlet a:visited, .dark label, .dark select,
       .dark input, .dark input.button, .dark input.buttonPortlet,
       .dark .phase .navText, .dark .portletGroup { color:|fontColor| }
     .dark .portletSearch a:hover { background-color:|fontColorB|;
                                    color:|bgColor| }
     .dark select[multiple] option, .dark .navText { color:|fontColorL| }
     .dark .topBase { background-color:|sepColor| }
     .dark .language { color:|fontColor|; border-color:|sepColor| }
     .dark .pzone { border-bottom:1px solid |sepColor| }
     .dark .phase > div { background-color:|sepColor|; color:|fontColor| }
     .dark .currentPage { background-color:|bgColorL| !important }
     .dark .list>tbody>tr>th, .dark .list>thead>tr>th,
       .dark .history>tbody>tr>th { background-color:|thBg|;
                                    border-bottom:2px solid |showyColor| }
     .dark .list>tbody>tr>th, .dark .list>thead>tr>th,
       .dark .list>tbody>tr>td, .dark .list>tbody>tr>th,
       .dark .list>thead>tr>th { color:|fontColor|}
     .dark .list>tbody>tr:nth-child(even), .dark .fdown > :nth-child(even),
       .dark .gridG>tbody>tr:nth-child(even), .dark .subTitle table>tbody>tr>td,
       .dark .history>tbody>tr:nth-child(even), .dark pre, .dark .python
       { background-color:transparent }
     .dark .list>tbody>tr:nth-child(odd), .dark .fdown > :nth-child(odd),
       .dark .gridG>tbody>tr:nth-child(odd),
       .dark .history>tbody>tr:nth-child(odd) { background-color:|tdBg| }
     .dark .grid>tbody>tr>th, .dark .grid>thead>tr>th, .dark .small th,
       .dark .xhtml th { background-color:|thBg| }
     .dark .popup, .dark a.bref, .dark a.bref:visited { background-color:|tdBg|}
     .dark textarea, .dark input[type=date], .dark input[type=number] {
       background-color:|bgColorL|; border:none; color:|fontColor| }
     .dark .discreet, .dark .subTitle { color:|fontColorL| }
     .dark .focus { box-shadow:none; background-color:|bgColorL|;
                    color:|fontColor| }
     .dark select:not([multiple]) option { background-color:|bgColorB| }
     .dark .tab { background-color:|thBg| }
     .dark .tabCur { border:none; background-color:|bgColorL|}
     .dark .message { background-color:|thBg|; border:1px solid |showyColor| }
     .dark .header { border:none; background-color:transparent }
     .dark .cke_top, .dark .cke_bottom { background-color:lightgrey }
     .dark .small>tbody>tr>th { border:1px solid |showyColor| }
     .dark .lsSelected { background-color:|bgColorL| }
     .dark .toolbar { background-color:#7e7e7e}
     .dark .xhtmlE { background-color:|bgColor|}''',

    # Use the Dark config as base object for CSS variables replacements, instead
    # of the global config object.
    cssVars = 'cfg.dark',

    js='''
     class Dark {
       // Icons representing dark (true) and normal (false) modes
       static icons = {true: '🌘', false:'🌖'};

       constructor(darkDefault, lightenText, darkenText) {
         // Is the dark mode enabled ?
         this.enabled = this.getEnabled(darkDefault);
         // Translated texts for the switch button
         this.texts = {false: lightenText, true: darkenText};
       }

       getEnabled(darkDefault) {
         /* Determine if the dark mode is enabled or not by reading session
            storage key "dark". Initialises it if not done yet. */
         let enabled = sessionStorage.getItem('dark');
         if (enabled === null) {
           // Initialize session storage
           enabled = (darkDefault)? '1': '0';
           sessionStorage.setItem('dark', enabled);
         }
         return enabled === '1';
       }

       setMode() {
         // Sets the correct icon for the "switch" button
         const button = document.getElementById('darkSwitcher');
         button.innerText = Dark.icons[!this.enabled];
         button.title = this.texts[!this.enabled];
         // Sets the correct CSS class on tag body
         const body = document.body;
         if (this.enabled) {
           body.classList.add('dark');
           body.style['color-scheme'] = 'dark';
         }
         else {
           body.classList.remove('dark');
           body.style['color-scheme'] = 'normal';
        }
       }

       switch() {
         // Switch the mode
         this.enabled = !this.enabled;
         const mode = (this.enabled)? '1': '0';
         sessionStorage.setItem('dark', mode);
         this.setMode();
       }
     }''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
