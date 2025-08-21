#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import datetime, hmac, hashlib, base64

from appy.px import Px
from appy.model.fields import Field
from appy.utils.client import Resource
from appy.model.utils import Object as O
from appy.ui.layout import LayoutF, Layouts

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
API = 'Worldline API ::'
WL_HT_AUTH = f'{API} %s :: Got tokenization ID %s'
bn = '\n'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Config:
    '''If you plan, in your app, to perform on-line payments via Worldline,
       create an instance of this class in your app and place it in the
       'worldline' attr of your app's Config class.'''

    # This module implements the "Hosted Tokenization Page" integration method,
    # where the payment form is embedded in an iframe on the called site.
    # See https://docs.direct.worldline-solutions.com/en/integration/
    #     basic-integration-methods/hosted-tokenization-page

    # Content-type for POST requests to the Worldline endpoints
    contentType = 'application/json; charset=utf-8'

    # Generic URL for the Worldline endpoints. The dynamic part (%s) will be
    # replaced by the URL part corresponding to the precise environment, as
    # determined by dict v_urlParts below.
    baseUrl = "https://payment%s.direct.worldline-solutions.com"

    # URL part, depending on the target environment (test or prod)
    urlParts = {'test': '.preprod', 'prod': ''}

    # The base path for non-JS calls
    baseSuffix = 'v2'

    # The date format to use for transmitting dates (RFC1123)
    dateFormat = '%a, %d %b %Y %H:%M:%S %Z'

    def __init__(self, env='test', pspid=None, apiKey=None, apiSecret=None,
                 algo='sha256'):
        # self.env refers to the target environment: can be "test" or "prod"
        self.env = env
        # You merchant Worldline ID
        self.pspid = pspid
        # Your Worldline API key and secret
        self.apiKey = apiKey
        self.apiSecret = apiSecret
        # Hash algorithm to use
        self.algo = algo
        # Default language
        self.language = 'en_UK'

    def getContentType(self, method):
        '''Define the content type for the HTTP request payload'''
        return self.contentType if method == 'POST' else ''

    def getNow(self):
        '''Returns the current date and time, as a RFC1123-compliant string'''
        tz = datetime.timezone(datetime.timedelta(hours=0), 'GMT')
        dt = datetime.datetime.now(tz)
        return dt.strftime(self.dateFormat)

    def getStringToHash(self, endpoint, now, method):
        '''Get the string to hash, required to authenticate to this Worldline
           p_endpoint.'''
        contentType = self.getContentType(method)
        # Define the URL endpoint
        url = f'/{self.baseSuffix}/{self.pspid}/{endpoint}'
        return f'{method}{bn}{contentType}{bn}{now}{bn}{url}{bn}'

    def getHash(self, endpoint, now, method):
        '''Get the hash to include as authorization token in a call to this
           Worldline p_endpoint.'''
        # Get the string to hash, made of various parts
        s = self.getStringToHash(endpoint, now, method)
        # The API secret and p_s must be converted to bytes
        algo = getattr(hashlib, self.algo)
        enc = 'utf-8'
        hash_ = hmac.new(self.apiSecret.encode(enc), s.encode(enc), algo)
        return base64.b64encode(hash_.digest()).decode(enc).rstrip(bn)

    def getBaseUrl(self):
        '''Get the base URL for the Worldline API'''
        return Config.baseUrl % Config.urlParts[self.env]

    def __repr__(self):
        '''p_self's short representation'''
        return f'‹{self.env}@Worldline - PSPID {self.pspid}›'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Worldline(Field):
    '''This field allows to perform online payments with the Worldline system'''

    # Some elements will be traversable
    traverse = Field.traverse.copy()

    class Layouts(Layouts):
        '''Worldline-specific layouts'''

        f = Layouts(view=LayoutF('f=', direction='column'))
        defaults = {'normal': f, 'grid': f}

    # The ID of the div tag containing the iframe
    divId = 'div-hosted-tokenization'

    # This PX includes the Worldline iframe
    view = Px('''
     <!-- This div will host the iframe -->
     <div id=":field.divId" class="divWL"></div>

     <!-- Submit the form -->
     <input type="button" class="buttonFixed button" value=":_('pay')"
            onclick="submitWLForm()"/>

     <!-- This JS file contains the methods needed for tokenization -->
     <script var="baseUrl=config.worldline.getBaseUrl()"
             src=":f'{baseUrl}/hostedtokenization/js/client/tokenizer.min.js'">
     </script>

     <!-- Get the JS code that will initialise the iframe -->
     <script>::field.getFrameInit(o)</script>''',

     css=''' .divWL { margin: 1em 0.2em }''',

     js = '''
       function submitWLForm(){
         tokenizer.submitTokenization().then((result) => {
           if (result.success) {
             /* Proceed by storing the result.hostedTokenizationId from our
                platform to be used in subsequent steps */
           } else { // displayErrorMessage(result.error.message);
           }
         });
       }''')

    def show(self, o):
        '''Show the payment widget only if initialisation data has been stored
           on the corresponding object.'''
        # Normally, this method is supposed to belong to the object, not to the
        # field. Consequently, p_self is the object and p_o is the field.
        return None if self.isEmpty(o.name) else 'view'

    def __init__(self, show=show, renderable=None, page='main', group=None,
      layouts=None, move=0, readPermission='read', writePermission='write',
      width=None, height=None, colspan=1, master=None, masterValue=None,
      focus=False, mapping=None, generateLabel=None, label=None, view=None,
      cell=None, buttons=None, edit=None, custom=None, xml=None,
      translations=None):

        # Call the base constructor
        super().__init__(None, (0,1), None, None, show, renderable, page, group,
          layouts, move, False, True, None, None, False, None, readPermission,
          writePermission, width, height, None, colspan, master, masterValue,
          focus, False, mapping, generateLabel, label, None, None, None, None,
          False, False, view, cell, buttons, edit, custom, xml, translations)

    def call(self, o, endpoint, method='POST', data=None):
        '''Calls this Worldline p_endpoint, with this HTTP m_method, in the
           context of a payment about this p_o(bject), that represents a
           shopping basket or registration.'''
        # Authenticating to a Wordline endpoint is described in
        # https://docs.direct.worldline-solutions.com/en/integration/
        #         api-developer-guide/authentication#authenticatewithoutsdks
        # Create a Resource object representing the distant server
        config = o.config.worldline
        base = config.baseUrl % config.urlParts[config.env]
        url = f'{base}/{config.baseSuffix}/{config.pspid}/{endpoint}'
        server = Resource(url)
        # Define headers, including the authorization header
        now = config.getNow()
        hash_ = config.getHash(endpoint, now, method)
        headers = {'Authorization': f'GCS v1HMAC:{config.apiKey}:{hash_}',
                   'Date': now, 'Content-Type': config.getContentType(method)}
        if method == 'POST':
            # Data to post is in dict p_data
            r = server.json(data, url, headers=headers)
        else:
            r = server.get(url, headers=headers)
        return r

    def addXhtmlRow(self, rows, name=None, value=None):
        '''Add, to this current list of XHTML p_rows, a new one rendering this
           p_value for an attribute having this p_name.'''
        if name: # A standard row
            value = value or '?'
            row = f'<tr><th>{name}</th><td>{value}</td></tr>'
        else: # A separator row
            row = f'<tr><th colspan="2">· • ·</th></tr>'
        rows.append(row)

    def getErrorDetails(self, o, error, withTitle=True):
        '''Returns a XHTML table containing all details about the p_error that
           occurred while contacting the Worldline API.'''
        add = self.addXhtmlRow
        rows = []
        for k, v in error.items():
            if isinstance(v, list):
                # Sub-info: render every sub-item as a sub-table
                subs = []
                for sub in v:
                    subs.append(self.getErrorDetails(o, sub, withTitle=False))
                add(rows, k, bn.join(subs))
            else:
                add(rows, k, v)
        if withTitle:
            title = o.translate('error_name')
            rows.insert(0, f'<tr><th colspan="2">{title}</th></tr>')
        return f'<table class="small">{bn.join(rows)}</table>'

    # Currently supported locales
    locales = {'en': 'UK', 'fr': 'BE', 'nl': 'BE'}

    def getLocale(self, o):
        '''Returns the locale to use while calling the Worldline API'''
        lang = o.guard.getUserLanguage()
        locales = self.locales
        if lang in locales:
            r = f'{lang}_{locales[lang]}'
        else:
            r = 'en_UK'
        return r

    def initialise(self, o):
        '''Call endpoint "hostedtokenizations", as a preamble to display the
           payment iframe. The endpoint returns a "hosted tokenization URL" that
           will be used by the Wordline form being shown in the iframe.'''
        # API documentation: https://docs.direct.worldline-solutions.com/en/
        #                     api-reference#tag/HostedTokenization/operation/
        #                     CreateHostedTokenizationApi
        data = O(locale=self.getLocale(o), askConsumerConsent=False)
        resp = self.call(o, 'hostedtokenizations', data=data)
        if resp.errors:
            r = False
            message = self.getErrorDetails(o, resp)
        else:
            r = True
            _ = o.translate
            payText = _('pay')
            message = _('please_pay', mapping={'pay': payText})
            # Store, as field value, the complete endpoint response
            o.values[self.name] = resp
            tid = resp.hostedTokenizationId
            o.log(WL_HT_AUTH % (o.strinG(path=False), tid))
        return r, message

    def getFrameInit(self, o):
        '''Get the JS code allowing to initialise the iframe'''
        # Create a Tokenizer object. Retrieve the hosted tokenization URL from
        # p_self's value on this p_o(bject)
        url = getattr(o, self.name).hostedTokenizationUrl
        # Invoking tokenizer.initialize() will add the <iframe> inside the
        # div tag whose ID is p_self.divId.
        return f"var tokenizer=new Tokenizer('{url}','{self.divId}'," \
               f" {{hideCardholderName:false}});{bn}tokenizer.initialize()" \
               f".then(() => {{}}).catch(reason => {{}})"
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
