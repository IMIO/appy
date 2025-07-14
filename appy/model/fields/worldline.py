#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import datetime, hmac, hashlib, base64

from appy.model.fields import Field
from appy.utils.client import Resource

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
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
    baseUrl = "https://payment.%s.direct.worldline-solutions.com"

    # URL part, depending on the target environment (test or prod)
    urlParts = {'test': 'preprod', 'prod': 'prod'}

    # The base path for non-JS calls
    baseSuffix = 'v2'

    # The date format to use for transmitting dates (RFC1123)
    dateFormat = '%a, %d %b %Y %H:%M:%S %Z'

    def __init__(self, env='test', pspid=None, apiKey=None, apiSecret=None):
        # self.env refers to the target environment: can be "test" or "prod"
        self.env = env
        # You merchant Worldline ID
        self.pspid = pspid
        # Your Worldline API key and secret
        self.apiKey = apiKey
        self.apiSecret = apiSecret
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
        print('String to hash is', s)
        # The API secret and p_s must be converted to bytes
        hash_ = hmac.new(self.apiSecret.encode(), s.encode(), hashlib.sha512)
        return base64.b64encode(hash_.digest()).decode('utf-8')

    def __repr__(self):
        '''p_self's short representation'''
        return f'‹{self.env}@Worldline - PSPID {self.pspid}›'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Worldline(Field):
    '''This field allows to perform online payments with the Worldline system'''

    # Some elements will be traversable
    traverse = Field.traverse.copy()

    def __init__(self, show='view',
      renderable=None, page='main', group=None, layouts=None, move=0,
      readPermission='read', writePermission='write', width=None, height=None,
      colspan=1, master=None, masterValue=None, focus=False, mapping=None,
      generateLabel=None, label=None, view=None, cell=None, buttons=None,
      edit=None, custom=None, xml=None, translations=None):

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
        url = f'{base}/{config.baseSuffix}/{endpoint}'
        server = Resource(url)
        # Define headers, including the authorization header
        now = config.getNow()
        hash_ = config.getHash(endpoint, now, method)
        headers = {'Authorization': f'GCS v1HMAC:{config.apiKey}:{hash_}',
                   'Date': now, 'Content-Type': config.getContentType(method)}
        if method == 'POST':
            # Data to post is in dict p_data
            print('Headers are', headers)
            print('Data is', data)
            print('URL is', url)
            r = server.json(data, url, headers=headers)
        else:
            r = server.get(url, headers=headers)
        return r

    def createHostedTokenization(self, o):
        '''Call endpoint "hostedtokenizations", as a preamble to display the
           payment iframe, to retrieve a "hosted tokenization URL" that will be
           used by the Wordline form being shown in the iframe.'''
        # API documentation: https://docs.direct.worldline-solutions.com/en/
        #                     api-reference#tag/HostedTokenization/operation/
        #                     CreateHostedTokenizationApi
        data = {'locale': o.guard.userLanguage or 'en',
                'variant': '', 'tokens': ''}
        r = self.call(o, 'hostedtokenizations', data=data)
        breakpoint()
        # Example of returned error:
        # ‹O errorId='ee4bdfcc-128f-4e2b-addd-3318bc05e9df'
        #    errors=[‹O code='9007' id='ACCESS_TO_MERCHANT_NOT_ALLOWED'
        #               category='DIRECT_PLATFORM_ERROR'
        #               message='ACCESS_TO_MERCHANT_NOT_ALLOWED'
        #               httpStatusCode=403›] status=403›
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
