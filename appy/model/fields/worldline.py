#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from DateTime import DateTime
import datetime, hmac, hashlib, base64

from appy import n
from appy.px import Px
from appy.model.fields import Field
from appy.utils import formatNumber
from appy.utils.client import Resource
from appy.model.utils import Object as O
from appy.ui.layout import LayoutF, Layouts

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
CALL_MIS   = 'A method must be placed in attribute "%s".'

API        = 'Worldline API ::'
TOKEN_ID   = f'{API} %s :: Got tokenization ID %s'
CO_ID      = f'{API} %s :: Got checkout ID %s'
INIT_KO    = f'Payment init (hostedtokenizations) failed.'
PAY_KO     = f'Payment response error :: %s.'
PAY_TOK_KO = f'{API} %s :: Payment aborted :: No token in the request.'
PAY_STATUS = f'{API} %s :: Payment %s (%s).'
RECEIPT_KO = f'{API} %s:%s :: Empty payment :: Cannot generate receipt.'
CONF_KO    = f'{API} %s :: Worldline /confirm redirect without payment ID.'
CONF_WRONG = f'{API} %s :: Worldline messy /confirm redirect.'
CONF_IDKO  = f'{API} %s :: Worldline /confirm payment ID mismatch: ours is ' \
             f'%s, WL is %s.'
BACK_KO    = f'{API} %s :: Worldline /back redirect without hosted checkout ID.'
BACKM_KO   = f'{API} %s :: Worldline /back redirect without RETURNMAC.'
BACK_WRONG = f'{API} %s :: Worldline messy /back redirect.'
BACK_IDKO  = f'{API} %s :: Worldline /back hosted checkout ID and/or ' \
             f'RETURNMAC mismatch: ours are %s/%s, WL is %s/%s.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
bn = '\n'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Config:
    '''Configuration for performing payments from an Appy app to the Worldline
       payment system.'''

    # This module implements 2 distinct integration methods with Worldline:

    # 1. the "Hosted Tokenization Page" integration method, where the payment
    #    form is embedded in an iframe on the called site ;

    #    See https://docs.direct.worldline-solutions.com/en/integration/
    #     basic-integration-methods/hosted-tokenization-page

    # 2. the "Hosted Checkout Page" integration method, where the user is
    #    redirected to a payment page hosted @ Worldline.

    #    See https://docs.direct.worldline-solutions.com/en/integration/
    #     basic-integration-methods/hosted-checkout-page

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #             How to integrate a Worldline field in your app ?
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # As a preamble, set an instance of this Config class in attribute
    # config.worldline (v_config being your app's main configuration class).

    # In your app, you must have an Appy class representing the notion of
    # order / registration / basket / ... This class will be named
    # "Registration" in the remainder of this explanation. On that class, define
    # the Worldline field corresponding to the chosen payment method (hosted
    # tokenization or hosted checkout). Here is an example for hosted
    # tokenization.
    #
    # from appy.model.fields.worldline import Worldline
    # ...
    # class Registration:
    #     ...
    #     onlinePayment = Worldline.Tokenization()
    #     ...
    #
    # If you prefer to use hosted checkout, use this field instead:
    #     ...
    #     onlinePayment = Worldline.Checkout()
    #     ...

    # Do not touch the field's "show" attribute: the field will know when to
    # render himself. Once a registration (self) is ready for online payment,
    # initialise the payment process, typically in its m_onEdit method, by
    # calling:

    # r = self.getField('onlinePayment').initialise(self)

    # When using hosted tokenization, this call will return a translated
    # message, inviting the user to pay (use it as return value for m_onEdit):
    # the user will then be redirected to /view, where the Worldline field will
    # be rendered as an iframe, inviting the user to enter card details.

    # When using hosted checkout, this call does not return anything, but the
    # user will be redirected to the payment page @ Worldline.

    # In both cases, ensure your code in m_onEdit does not set any redirection.

    # In both cases, on your selected Worldline field:
    # 1. set, in attributes "onSuccess" and "onFailure", methods that will
    #    execute your custom code for managing a payment success or failure ;
    # 2. set attribute "amount" that will define the amount to pay (and the
    #    related currency).
    # Read the field constructor for more information.

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

    def __init__(self, env='test', pspid=n, apiKey=n, apiSecret=n,
                 algo='sha256', timeout=20):
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
        # Timeout, in seconds, for server-2-server requests
        self.timeout = timeout

    def getContentType(self, method):
        '''Define the content type for the HTTP request payload'''
        return self.contentType if method == 'POST' else ''

    def getNow(self):
        '''Returns the current date and time, as a RFC1123-compliant string'''
        tz = datetime.timezone(datetime.timedelta(hours=0), 'GMT')
        dt = datetime.datetime.now(tz)
        return dt.strftime(self.dateFormat)

    def getStringToHash(self, endpoint, now, method, pspid):
        '''Get the string to hash, required to authenticate to this Worldline
           p_endpoint.'''
        contentType = self.getContentType(method)
        # Define the URL endpoint
        url = f'/{self.baseSuffix}/{pspid}/{endpoint}'
        return f'{method}{bn}{contentType}{bn}{now}{bn}{url}{bn}'

    def getHash(self, endpoint, now, method, pspid, apiSecret):
        '''Get the hash to include as authorization token in a call to this
           Worldline p_endpoint.'''
        # Get the string to hash, made of various parts
        s = self.getStringToHash(endpoint, now, method, pspid)
        # The API secret and p_s must be converted to bytes
        algo = getattr(hashlib, self.algo)
        enc = 'utf-8'
        hash_ = hmac.new(apiSecret.encode(enc), s.encode(enc), algo)
        return base64.b64encode(hash_.digest()).decode(enc).rstrip(bn)

    def getBaseUrl(self):
        '''Get the base URL for the Worldline API'''
        return Config.baseUrl % Config.urlParts[self.env]

    def __repr__(self):
        '''p_self's short representation'''
        return f'‹{self.env}@Worldline - PSPID {self.pspid}›'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Worldline(Field):
    '''Abstract field being the base for concrete fields, each implementing a 
       specific payment method.'''

    class Layouts(Layouts):
        '''Worldline-specific layouts'''

        f = Layouts(view=LayoutF('f=', direction='column'))
        defaults = {'normal': f, 'grid': f}

    def __init__(self, show=False, renderable=n, page='main', group=n,
      layouts=n, move=0, readPermission='read', writePermission='write',
      width=n, height=n, colspan=1, master=n, masterValue=n, masterSnub=n,
      focus=False, mapping=n, generateLabel=n, label=n, view=n, cell=n,
      buttons=n, edit=n, custom=n, xml=n, translations=n, amount=None,
      onSuccess=None, onFailure=None, credentials=None, variant=None):

        # p_amount must hold a method accepting no arg and returning the amount
        # to pay, as a tuple (f_amount, s_currencyCode). Supported currency
        # codes are "EUR", "KWD" and "JPY".
        self.amount = amount
        self.checkCallable('amount')

        # p_onSuccess must hold a method that will be executed once the payment
        # has been accepted. It will be called with no arg and must return a
        # 2-tuple containing:
        # - the URL the user must be redirected to ;
        # - a translated message to show in the UI.
        self.onSuccess = onSuccess
        self.checkCallable('onSuccess')

        # p_onFailure must hold a method that will be executed if the payment
        # was not successful. It will be called with a single arg: an integer
        # code representing the reason for the failure. Constants PAY_SUC to
        # PAY_CAN as defined below represent all possible codes. p_onFailure
        # must return a 2-tuple being similar to p_onSuccess' return value (see
        # above).
        self.onFailure = onFailure
        self.checkCallable('onFailure')

        # If your app uses several PSPIDs and/or API keys for connecting to
        # Worldline, instead of using attributes config.pspid, config.apiKey and
        # config.apiSecret, one may define a method in the following attribute.
        # This method must must return a 3-tuple of strings:
        #
        #                   (pspid, apiKey, apiSecret)
        #
        # If the method is set but returns None, or if None is found at any
        # position in the returned tuple, the corresponding fallback value is
        # retrieved from the config.
        self.credentials = credentials

        # Variant for customizing the payment popup
        self.variant = variant

        # Call the base constructor
        super().__init__(n, (0,1), n, n, show, renderable, page, group, layouts,
          move, False, True, n, n, False, n, n, readPermission, writePermission,
          width, height, n, colspan, master, masterValue, masterSnub, focus,
          False, mapping, generateLabel, label, n, n, n, n, False, False, view,
          cell, buttons, edit, custom, xml, translations)

        # Concrete class init complement
        self.concreteInit()

    def concreteInit(self):
        '''To be overridden by child classes when appropriate'''

    def checkCallable(self, name):
        '''Ensure the attribute having this p_name is there and is callable'''
        value = getattr(self, name)
        if value is None or not callable(value):
            raise Exception(CALL_MIS % name)

    def getCredentials(self, o):
        '''Get the Worldline credentials: PSPID, API key and API secret'''
        c = o.config.worldline
        r = None
        if self.credentials:
            r = self.credentials(o)
            if r and None in r:
                # Ensure credentials are complete
                r = r[0] or c.pspid, r[1] or c.apiKey, r[2] or c.apiSecret
        else:
            r = c.pspid, c.apiKey, c.apiSecret
        return r

    def call(self, o, endpoint, method='POST', data=n):
        '''Calls this Worldline p_endpoint, with this HTTP m_method, in the
           context of a payment about this p_o(bject), that represents a
           shopping basket or registration.'''
        # Authenticating to a Wordline endpoint is described in
        # https://docs.direct.worldline-solutions.com/en/integration/
        #         api-developer-guide/authentication#authenticatewithoutsdks
        # Create a Resource object representing the distant server
        config = o.config.worldline
        base = config.baseUrl % config.urlParts[config.env]
        # Get credentials
        pspid, apiKey, apiSecret = self.getCredentials(o)
        url = f'{base}/{config.baseSuffix}/{pspid}/{endpoint}'
        server = Resource(url, timeout=config.timeout)
        # Define headers, including the authorization header
        now = config.getNow()
        hash_ = config.getHash(endpoint, now, method, pspid, apiSecret)
        headers = {'Authorization': f'GCS v1HMAC:{apiKey}:{hash_}', 'Date': now,
                   'Content-Type': config.getContentType(method)}
        try:
            if method == 'POST':
                # Data to post is in dict p_data
                r = server.json(data, url, headers=headers)
            else:
                r = server.get(url, headers=headers)
        except Resource.Error as err:
            # A network error occurred: abort the payment and return None
            req = o.req
            req.code = self.PAY_WRO
            req.reason = str(err)
            self.abort(o)
            r = None
        return r

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

    # Factors to apply to payment amounts, in order to get Wordline-compliant
    # integer amounts.

    currencyFactors = {
      'EUR': 100,
      'KWD': 1000,
      'JPY': 1
    }

    # Symbols for currencies
    currencySymbols = {
      'EUR': '€',
      'JPY': '¥',
    }

    # If the currency is not in this list, the default factor will be this one
    defaultFactor = 100

    def getAmount(self, o):
        '''Retrieve the amount to pay, with its currency, from, p_self.amount.
           Format it according to Worldline requirements.'''
        amount, currency = self.amount(o)
        factor = self.currencyFactors.get(currency, self.defaultFactor)
        amount = int(amount * factor)
        return O(amount=amount, currencyCode=currency)

    def getFormattedAmount(self, amount):
        '''Returns this p_amount, formatted'''
        currency = amount.currencyCode
        factor = self.currencyFactors.get(amount.currencyCode)
        factor = factor or self.defaultFactor
        r = formatNumber(amount.amount / factor)
        symbol = self.currencySymbols.get(currency) or currency
        return f'{symbol} {r}'

    def addReceiptRow(self, o, rows, label, value):
        '''Adds a new row of data into the receipt computed by m_getReceipt'''
        text = o.translate(f'payment_{label}')
        value = value if isinstance(value, str) else str(value)
        row = f'<tr><th>{text}</th><td>{value}</td></tr>'
        rows.append(row)

    def getReceipt(self, o):
        '''Return, as a XHTML table, info about the payment transaction'''
        # Info about the payment is normally stored on the p_o(bject)
        info = o.values.get(self.name)
        if not info:
            raise Exception(RECEIPT_KO % (o.strinG(path=False), self.name))
        rows = []
        add = self.addReceiptRow
        # Get the paid amount (with currency)
        if info.createdPaymentOutput: # A hosted checkout response
            payment = info.createdPaymentOutput.payment
        else: # A hosted tokenization response
            payment = info.payment
        payOut = payment.paymentOutput
        amount = payOut.amountOfMoney
        add(o, rows, 'amount', self.getFormattedAmount(amount))
        # Get the payment date as transmitted by Worldline
        date = payOut.transactionDate
        if date:
            add(o, rows, 'date', o.tool.formatDate(DateTime(date)))
        # Add the payment ID
        add(o, rows, 'id', payment.id)
        # Add the (partially masked) card number and card type
        cardData = payment.paymentOutput.cardPaymentMethodSpecificOutput
        if cardData:
            card = cardData.card
            add(o, rows, 'masked_card', card.cardNumber)
            cardType = card.cardScheme or card.cardProductName or \
                       card.issuerName
            if cardType:
                add(o, rows, 'card_type', cardType)
        # Build the complete receipt
        title = o.translate('payment_details')
        descr = o.translate('payment_accepted')
        return f'<table class="small"><tr><th colspan="2">{title}</th></tr>' \
               f'<tr><td colspan="2" style="background-color:green">{descr}' \
               f'</td></tr>{bn.join(rows)}</table>'

    # Final payment statuses, allowing to categorise concrete statuses as
    # received by m_pay. Intermediary statuses, such as the one received when
    # the user must be redirected to an additonal page due to a 3DS check, are
    # not of interest here, and considered wrong, if received. Indeed, our
    # interest here is to know what action must be performed to finalize the
    # payment. Everything about statuses is documented here:

    # https://docs.direct.worldline-solutions.com/en/integration/
    #  api-developer-guide/statuses.

    PAY_SUC  = 0 # The payment was successful
    PAY_REJ  = 1 # The payment has been rejected
    PAY_WRO  = 2 # The payment status is wrong: it has no sense as final step
    PAY_UNK  = 3 # The payment status is unknown / uncertain

    # The following status code is Appy-specific
    PAY_CAN  = 4 # The payment process has been cancelled by the end user

    # Codes for which the full Worldline response will be logged
    detailCodes = PAY_WRO, PAY_UNK

    # Codes representing rejected, wrong or cancelled payments
    failureCodes = PAY_REJ, PAY_WRO, PAY_CAN

    # Short texts for every payment status
    paymentTexts = {
      PAY_SUC: 'successful',
      PAY_REJ: 'rejected',
      PAY_WRO: 'aborted (technical problem)',
      PAY_UNK: 'uncertain / unknown',
      PAY_CAN: 'cancelled by the end user'
    }

    # Note that the previous statuses are also used as possible status codes as
    # passed to app/ext method "onFailure". In that context, PAY_WRO is recycled
    # to denote any technical problem.

    # Concrete codes for the 3 first hereabove-mentioned payment status
    # categories. Any code that would not fall into these categories will be
    # considered belonging to the last one: unknown / uncertain.

    paymentCodes = {
      PAY_SUC: (
        # Successful, completely captured payment
        9,
      ),
      PAY_REJ: (
        # Statuses considered as "cancelled" (maybe due to a technical problem?)
        6, 61, 62, 64, 75, 96,
        # Statuses considered as "rejected"
        2, 57, 59, 73, 83, 93
      ),
      PAY_WRO : (
        # The payment object has just been created. After m_pay has been called,
        # this status has no sense: we are, in any case, further in the payment
        # process.
        0,
        # The following statuses correspond to intermediary statuses, where
        # "capturing" the payment has still to be done. Because we work in
        # "Direct sale" mode, receiving these statuses is considered as an
        # error.
        5, 56,
        # The following statuses are those received when the user is redirected
        # to a 3DS-related additional page. It cannot be received as a final
        # step.
        46, 50, 51, 55
      ),
      PAY_CAN : (
        # Cancelled by the end user
        1,
      )
    }

    def getErrorType(self, resp, full=True):
        '''Returns the error type and message that corresponds to the error as
           returned by this Worldline p_resp(onse).'''
        # Get the payment status
        status = resp.paymentResult.payment if full else resp
        # Get the payment status code
        try:
            code = status.statusOutput.statusCode
        except AttributeError:
            # The response is incomplete: note a technical problem
            return self.PAY_WRO, str(resp)
        # Determine our v_failCode based on the Worldline p_code
        paymentCodes = self.paymentCodes
        found = False
        for failCode in self.failureCodes:
            if code in paymentCodes[failCode]:
                found = True
                break
        # The failure code could not be found: an uncertain payment
        if not found:
            failCode = self.PAY_UNK
        # Determine the error text
        text = str(resp) if failCode in self.detailCodes else f'WL={code}'
        return failCode, text

    def onError(self, o, resp, full=True):
        '''Manages a non successful payment = a Worldline p_resp(onse) with an
           errorId.'''
        # Something went wrong: abort the payment. Find the error type.
        req = o.req
        req.code, req.reason = self.getErrorType(resp, full=full)
        # Clean any payment info possibly stored on p_o regarding p_self
        if self.name in o.values:
            del o.values[self.name]
        self.abort(o)

    def onInitError(self, o, endpoint):
        '''Manage an error that occurred when calling this initial p_endpoint'''
        # Abort the payment
        req = o.req
        req.code = self.PAY_WRO
        req.reason = INIT_KO % endpoint
        self.abort(o)

    def onFinal(self, o, status):
        '''Called by m_pay or m_confirm, this method analyses this final payment
           p_status and finalizes the payment, be it a success or not.'''
        # Get the payment status code. If the payment was successful, payment
        # information encoded so far is satisfying: there is no need to redirect
        # the user to an additional page.
        code = status.statusOutput.statusCode
        paymentCodes = self.paymentCodes
        if code not in paymentCodes[self.PAY_SUC]:
            # The payment wasn't successful: abort it
            self.onError(o, status, full=False)
            return
        # The payment has been accepted
        text = self.paymentTexts[self.PAY_SUC]
        o.log(PAY_STATUS % (o.strinG(path=False), text,
                            f'{self.PAY_SUC}/WL={code}'))
        # Trigger app/ext code
        url, message = self.onSuccess(o)
        o.resp.fleetingMessage = False
        o.goto(url, message, fromAjax=o.H().isAjax())

    def abort(self, o):
        '''Aborts the payment after an error occurred'''
        # A database commit is required
        o.H().commit = True
        # Several error cases are possible and are listed in v_paymentTexts.
        # Retrieve the code corresponding to the current case.
        req = o.req
        code = req.code or self.PAY_UNK
        # The code may be found in the request
        if isinstance(code, str): code = int(code)
        # More textual details may be found in v_req.reason
        text = self.paymentTexts[code]
        if req.reason:
            text = f'{text} ({req.reason})'
        o.log(PAY_STATUS % (o.strinG(path=False), text, code))
        # Trigger app/ext code
        url, message = self.onFailure(o, code)
        # Redirect the end user and show her a translated message
        o.resp.fleetingMessage = False
        o.goto(url, message, fromAjax=o.H().isAjax())

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Tokenization(Worldline):
    '''Implements the "hosted tokenization page" payment method'''

    # Some elements will be traversable
    traverse = Field.traverse.copy()

    # m_abort can be called from the iframe
    traverse['abort'] = 'perm:read'

    # The ID of the div tag containing the iframe
    divId = 'div-hosted-tokenization'

    # This PX includes the Worldline iframe
    view = Px('''
     <!-- Being in an Ajax request means that we are already further in the
          process: don't show this initialisation PX. -->
     <x if="not ajax">

      <!-- This div will host the iframe -->
      <div id=":field.divId" class="divWL"></div>

      <!-- "Pay" and "Cancel" buttons -->
      <div class="flex1">

       <!-- Submit the form -->
       <input type="button" class="buttonFixed button" value=":_('pay')"
              onclick=":f'submitWLForm(`{tagId}`)'"/>

       <!-- Cancel the payment -->
       <div>
        <script>:f'var cancelText=`{o.translate("pay_cancel_text")}`;'</script>
        <input type="button" class="buttonFixed button"
               value=":_('object_cancel')" var="cancelJs=field.getAbortJs(o,4)"
               onclick=":f'askConfirm(`script`,`{cancelJs}`,cancelText)'"/>
       </div>
      </div>

      <!-- This JS file contains the methods needed for tokenization -->
      <script var="baseUrl=config.worldline.getBaseUrl()"
              src=":f'{baseUrl}/hostedtokenization/js/client/tokenizer.min.js'">
      </script>

      <!-- Get the JS code that will initialise the iframe -->
      <script>::field.getFrameInit(o)</script>
     </x>''',

     css=''' .divWL { margin: 1em 0.2em }''',

     js = '''
       function submitWLForm(hook){
         tokenizer.submitTokenization().then((result) => {
           /* Ajax-refresh the payment field, triggering or canceling (depending
              on p_result) the payment via a server-2-server request. */
           const [objectId, fieldName] = hook.split('_'),
                 objectUrl = `${siteUrl}/${objectId}`, params = {};
           if (result.success) {
             params['action'] = 'pay';
             params['token'] = result.hostedTokenizationId;
           }
           else {
             params['action'] = 'abort';
             params['code'] = '2';
             params['reason'] = result.error.message;
           }
           askField(hook, objectUrl, 'view', params);
         });
       }''')

    def showIt(self, o, field):
        '''Show the payment widget only if initialisation data has been stored
           on the corresponding object.'''
        if o.H().isAjax(): return
        data = getattr(o, self.name, None)
        # p_data can also store the final payment response. Show the payment
        # widget only if v_data corresponds to initialisation data.
        if data and data.hostedTokenizationId:
            return 'view'

    def concreteInit(self):
        '''Tokenization-specific init steps'''
        # Showing this field consists in showing the Worldline iframe
        self.show = self.showIt

    def isOngoing(self, o):
        '''Returns True if the payment is ongoing = the iframe is currently
           shown.'''
        show = self.show
        if not show:
            r = False
        elif not callable(show):
            r = bool(show)
        else:
            r = bool(self.show(o, self))
        return r

    def isRenderableOn(self, layout):
        '''This field may only be rendered on "view"'''
        return layout == 'view'

    def getAbortJs(self, o, code, fromInit=False):
        '''Return the JS code to call to abort a payment (with a specific reason
           p_code) via a HTTP POST request.'''
        # If p_fromInit is True, the JS code is called from the iframe
        # initialisation step ("handshake").
        iparam = ",'reason':reason" if fromInit else ''
        # Get the URL to hit
        url = f'{o.siteUrl}/{o.iid}/{self.name}/abort'
        # Get the POST parameters
        params = f"{{'code':'{code}'{iparam}}}"
        # Return the call to Form.post
        return f"Form.post('{url}',{params})"

    def getFrameInit(self, o):
        '''Get the JS code allowing to initialise the iframe'''
        # Create a Tokenizer object. Retrieve the hosted tokenization URL from
        # p_self's value on this p_o(bject).
        url = getattr(o, self.name).hostedTokenizationUrl
        # Invoking tokenizer.initialize() will add the <iframe> inside the
        # div tag whose ID is p_self.divId.
        abortJs = self.getAbortJs(o, 2, fromInit=True)
        return f"var tokenizer=new Tokenizer('{url}','{self.divId}'," \
               f" {{hideCardholderName:false}});{bn}tokenizer.initialize()" \
               f".then(() => {{}}).catch(reason => {{{abortJs}}})"

    def initialise(self, o):
        '''Call endpoint "hostedtokenizations", as a preamble to display the
           payment iframe. The endpoint returns a "hosted tokenization URL" that
           will be used by the Worldline form being shown in the iframe.'''
        # API documentation:
        # https://docs.direct.worldline-solutions.com/en/api-reference#tag/
        #  HostedTokenization/operation/CreateHostedTokenizationApi
        data = O(locale=self.getLocale(o), askConsumerConsent=False)
        if self.variant:
            data.variant = self.variant
        endpoint = 'hostedtokenizations'
        resp = self.call(o, endpoint, data=data)
        if resp:
            if resp.errors: # Abort the payment process
                self.onInitError(o, endpoint)
            else:
                # Store, as field value, the complete endpoint response
                o.values[self.name] = resp
                # Log
                tid = resp.hostedTokenizationId
                o.log(TOKEN_ID % (o.strinG(path=False), tid))
                # Invite the user to pay
                _ = o.translate
                payText = _('pay')
                message = _('please_pay', mapping={'pay': payText})
                o.resp.fleetingMessage = False
                return f'<div class="focus">{message}</div>'

    def onPay(self, o, resp):
        '''Manages a p_resp(onse) retrieved from the m_pay method'''
        # Regardless of the payment status, a database commit is required
        o.H().commit = True
        if resp.errorId:
            # Something went wrong: abort the payment
            self.onError(o, resp)
        else:
            # Store p_resp on p_o
            o.values[self.name] = resp
            # Continue the payment process
            action = resp.merchantAction
            if action and action.actionType == 'REDIRECT':
                # The user must be redirected to a page where he will give more
                # info about his identity as card holder (3DS check).
                url = action.redirectData.redirectURL
                o.goto(url, fromAjax=True)
            else:
                # The payment should have been accepted: finalize it
                self.onFinal(o, resp.payment)

    traverse['pay'] = 'perm:read'
    def pay(self, o):
        '''Trigger a server-2-server payment request, after the user has entered
           card details, as tokenized in the request, at key 'token'.'''
        # API documentation:
        # https://docs.direct.worldline-solutions.com/en/api-reference#tag/
        #  Payments/operation/CreatePaymentApi
        #
        # If there is no token in the request, abort the payment
        req = o.req
        token = req.token
        if not token:
            req.code = self.PAY_WRO
            req.reason = PAY_TOK_KO  % o.strinG(path=False)
            return self.abort(o)
        # Build the request
        config = o.config.worldline
        # Define redirection data, in case the user must perform an additional
        # step due to a 3D Secure card.
        returnUrl = f'{o.url}/{self.name}/confirm'
        secure3D = O(redirectionData=O(returnUrl=returnUrl),
                     skipAuthentication=False)
        # Create an Order object, containing browser info and payment details
        headers = o.H().headers
        tzOffset = str(int(DateTime().tzoffset() / 60))
        customer = O(device=O(acceptHeader=headers['Accept'],
                              userAgent=headers['User-Agent'],
                              locale=self.getLocale(o),
                              timezoneOffsetUtcMinutes=tzOffset))
        order = O(amountOfMoney=self.getAmount(o), customer=customer)
        # Build the complete request. The "Direct sale" authorization mode is
        # applied. See documentation at:
        #   https://docs.direct.worldline-solutions.com/en/integration/
        #     api-developer-guide/authorisation-and-directsale
        data = O(hostedTokenizationId=token, order=order,
                 cardPaymentMethodSpecificInput=O(authorizationMode='SALE',
                                                  threeDSecure=secure3D))
        resp = self.call(o, 'payments', data=data)
        # v_resp is None if a network error (like a timeout) occurred
        if resp:
            self.onPay(o, resp)

    def confirmIsCorrect(self, o):
        '''Ensure the redirection to /confirm (see m_confirm) is correct. If
           yes, it returns the payment ID.'''
        req = o.req
        paymentId = req.paymentId
        if not paymentId:
            # Info carried in the redirect is wrong. Hack ?
            req.code = self.PAY_WRO
            req.reason = CONF_KO % o.strinG(path=False)
            self.abort(o)
            return
        try:
            ours = getattr(o, self.name).payment.id
        except AttributeError:
            # p_self is not in a valid state for accepting a payment
            # confirmation. Abort it.
            req.code = self.PAY_WRO
            req.reason = CONF_WRONG % o.strinG(path=False)
            self.abort(o)
            return
        if paymentId != ours:
            # The payment ID does not match: abort the payment
            req.code = self.PAY_WRO
            req.reason = CONF_IDKO % (o.strinG(path=False), ours, paymentId)
            self.abort(o)
            return
        # Everything seems correct
        return paymentId

    traverse['confirm'] = 'perm:read'
    def confirm(self, o):
        '''Confirm the payment after the user went through an additional,
           3D-secure-related, confirmation page.'''
        # Worldline has redirected the user to here. Ensure the mentioned
        # payment ID matches ours.
        paymentId = self.confirmIsCorrect(o)
        if not paymentId: return # Messy /confirm
        # The payment ID is correct. Get the payment status. API documentation:
        # https://docs.direct.worldline-solutions.com/en/api-reference#tag/
        #   Payments/operation/GetPaymentDetailsApi
        resp = self.call(o, f'payments/{paymentId}/details', method='GET')
        if resp:
            o.H().commit = True
            # This v_resp(onse) is similar to the part of the response
            # concerning the payment, as returned by m_pay.
            self.onFinal(o, resp.data)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Checkout(Worldline):
    '''Implements the "hosted checkout page" payment method'''

    # Some elements will be traversable
    traverse = Field.traverse.copy()

    def isRenderableOn(self, layout):
        '''This field is never renderable'''
        return

    def isOngoing(self, o):
        '''The payment is ongoing as soon as a Worldline response is stored on
           p_o.'''
        return not o.isEmpty(self.name)

    def initialise(self, o):
        '''Call endpoint "hostedcheckouts", to retrieve the URL of the page
           @Worldline, where the user will be redirected to.'''
        # API documentation:
        # https://docs.direct.worldline-solutions.com/en/api-reference#tag/
        #  HostedCheckout/operation/CreateHostedCheckoutApi
        backUrl = f'{o.url}/{self.name}/back'
        # Input :: Part "hostedCheckoutSpecificInput"
        inputHC = O(locale=self.getLocale(o), returnUrl=backUrl)
        if self.variant:
            inputHC.variant = self.variant
        # Input :: Part "order"
        order = O(amountOfMoney=self.getAmount(o))
        # Input :: Part "cardPaymentMethodSpecificInput". The "Direct sale"
        #          authorization mode is applied. See documentation at:
        #          https://docs.direct.worldline-solutions.com/en/integration/
        #           api-developer-guide/authorisation-and-directsale
        inputCP = O(authorizationMode='SALE')
        # Build the complete parameters and call the endpoint
        data = O(hostedCheckoutSpecificInput=inputHC, order=order,
                 cardPaymentMethodSpecificInput=inputCP)
        endpoint = 'hostedcheckouts'
        resp = self.call(o, endpoint, data=data)
        if resp:
            if resp.errors: # Abort the payment process
                self.onInitError(o, endpoint)
            else:
                # Store, as field value, the complete endpoint response
                o.values[self.name] = resp
                # Log
                o.log(CO_ID % (o.strinG(path=False), resp.hostedCheckoutId))
                # Redirect the user to the hosted checkout page
                o.goto(url=resp.redirectUrl)

    def backIsCorrect(self, o):
        '''Ensure the redirection to /back (see m_back) is correct. If yes, it
           returns the hosted checkout ID.'''
        req = o.req
        iD = req.hostedCheckoutId
        if not iD: # Info carried in the redirect is wrong. Hack ?
            req.code = self.PAY_WRO
            req.reason = BACK_KO % o.strinG(path=False)
            self.abort(o)
            return
        mac = req.RETURNMAC
        if not mac:
            req.code = self.PAY_WRO
            req.reason = BACKM_KO % o.strinG(path=False)
            self.abort(o)
            return
        # Compare the checkout ID and MAC with ours
        try:
            ours = getattr(o, self.name)
            ourId = ours.hostedCheckoutId
            ourMac = ours.RETURNMAC
        except AttributeError:
            # p_self is not in a valid state for accepting a payment. Abort it.
            req.code = self.PAY_WRO
            req.reason = BACK_WRONG % o.strinG(path=False)
            self.abort(o)
            return
        if iD != ourId or mac != ourMac:
            # Request info doesn't match ours: abort the payment
            req.code = self.PAY_WRO
            req.reason = BACK_IDKO % (o.strinG(path=False),
                                      ourId, ourMac, iD, mac)
            self.abort(o)
            return
        # Everything seems correct
        return iD

    traverse['back'] = 'perm:read'
    def back(self, o):
        '''Called by Worldline to redirect the user to our app once the payment
           process has ended.'''
        # Ensure request data is correct and corresponds to ours
        iD = self.backIsCorrect(o)
        if not iD: return # Messy /back
        # The hosted checkout v_iD is correct. Get the payment status. API doc:
        # https://docs.direct.worldline-solutions.com/en/api-reference#tag/
        #  HostedCheckout/operation/GetHostedCheckoutApi
        resp = self.call(o, f'hostedcheckouts/{iD}', method='GET')
        if resp:
            o.H().commit = True
            # Store p_resp.data on p_o
            o.values[self.name] = resp.data
            # Manage this final p_resp(onse)
            self.onFinal(o, resp.data.createdPaymentOutput.payment)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
Worldline.Tokenization = Tokenization
Worldline.Checkout = Checkout
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
