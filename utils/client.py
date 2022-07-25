#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from base64 import encodebytes
from mimetypes import guess_type
import xml.sax, http.client, urllib.parse, ssl
import os, sys, re, stat, time, socket, random, hashlib, gzip

from appy.utils import json
from appy.utils import copyData
from appy.model.utils import Object
from appy.xml.marshaller import Marshaller
from appy.xml.unmarshaller import Unmarshaller

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
DUR_SECS  = ', got in %.4f seconds'
RESP_T    = '\n*Headers* %s\n*Body* %s\n'
RESP_R    = '<HttpResponse %s (%s)%s%s>'
D_ERR     = 'Distant server exception: %s'
XML_ERR   = 'Invalid XML response (%s)'
T_OUT_ERR = 'Timed out after %d second(s).'
RESS_R    = '<Resource at %s>'
CIC_ERR   = 'Check your Internet connection (%s)'
CONN_ERR  = 'Connection error (%s)'
URL_ERR   = 'Wrong URL: %s'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class FormDataEncoder:
    '''Allows to encode form data for sending it through a HTTP request'''

    def __init__(self, data):
        self.data = data # The data to encode, as a dict

    def marshalValue(self, name, value):
        if isinstance(value, str):
            return '%s=%s' % (name, urllib.parse.quote(value))
        elif isinstance(value, float):
            return '%s:float=%s' % (name, value)
        elif isinstance(value, int):
            return '%s:int=%s' % (name, value)
        elif isinstance(value, long):
            res = '%s:long=%s' % (name, value)
            if res[-1] == 'L':
                res = res[:-1]
            return res
        else:
            raise Exception('Cannot encode value %s' % str(value))

    def encode(self):
        r = []
        for name, value in self.data.items():
            r.append(self.marshalValue(name, value).encode())
        return b'&'.join(r)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class SoapDataEncoder:
    '''Allows to encode SOAP data for sending it through a HTTP request'''

    namespaces = {'s'  : 'http://schemas.xmlsoap.org/soap/envelope/',
                  'xsd': 'http://www.w3.org/2001/XMLSchema',
                  'xsi': 'http://www.w3.org/2001/XMLSchema-instance'}

    namespacedTags = {'Envelope': 's', 'Body': 's', '*': 'py'}

    def __init__(self, data, namespace='http://appyframework.org'):
        self.data = data
        # p_data can be:
        # - a string already containing a complete SOAP message
        # - a Python object, that we will convert to a SOAP message
        # Define the namespaces for this request
        self.ns = self.namespaces.copy()
        self.ns['py'] = namespace

    def encode(self):
        # Do nothing if we have a SOAP message already
        if isinstance(self.data, str): return self.data
        # self.data is here a Python object. Wrap it in a SOAP Body.
        soap = Object(Body=self.data)
        # Marshall it
        marshaller = Marshaller(rootTag='Envelope', namespaces=self.ns,
                                namespacedTags=self.namespacedTags)
        return marshaller.marshall(soap)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class DigestRealm:
    '''Represents information delivered by a server requiring Digest-based
       HTTP authentication.'''

    rex = re.compile('(\w+)="(.*?)"')

    # List of attributes whose values must not be quoted
    unquoted = ('algorithm', 'qop', 'nc')

    def md5(self, value):
        '''Produces the MD5 message digest for p_value, as a hexadecimal
           32-chars string.'''
        return hashlib.md5(str(value).encode()).hexdigest()

    def __init__(self, info):
        '''p_info is the content of header key WWW-Authenticate. This
           constructor parses it and unwraps data into self's attributes.'''
        for name, value in self.rex.findall(info):
            # For attribute "qpop", split values into a list
            if name == 'qop':
                value = value.split(',')
                for i in range(len(value)):
                    value[i] = value[i].strip()
            setattr(self, name, value)
        # Set some default values
        if not hasattr(self, 'algorithm'):
            self.algorithm = 'MD5'

    def buildCredentials(self, resource, uri, httpMethod='GET'):
        '''Builds credentials to transmit to the server'''
        login = resource.username
        realm = self.realm
        algorithm = self.algorithm
        nonce = self.nonce
        # Get the "path" part of the URI
        parsed = urllib.parse.urlparse(uri).path
        # Compute a client random nouce
        cnonce = self.md5(random.random())
        # Collect credentials info in a dict
        res = {'username': login, 'uri': uri, 'realm': realm, 'nonce': nonce,
               'algorithm': algorithm}
        # Add optional attribute "opaque"
        if hasattr(self, 'opaque'): res['opaque'] = self.opaque
        # Precompute the "HA1" part of the response, that depends on the
        # algorithm in use (MD5 or MD5-sess).
        ha1 = self.md5('%s:%s:%s' % (login, realm, resource.password))
        if algorithm == 'MD5-sess':
            ha1 = self.md5('%s:%s:%s' % (ha1, nonce, cnonce))
        # Take into account the quality of protection (qop)
        hasQop = hasattr(self, 'qop')
        if hasQop:
            qop = res['qop'] = self.qop[0]
            res['cnonce'] = cnonce
            res['nc'] = '00000001'
        else:
            qop = 'auth'
        # Precompute the "HA2" part of the response, that depends on qop
        if qop == 'auth-int':
            entity = self.md5('entity')
            ha2 = self.md5('%s:%s:%s' % (httpMethod, uri, entity))
        else:
            ha2 = self.md5('%s:%s' % (httpMethod, uri))
        # Compute the complete response
        if hasQop:
            response = self.md5('%s:%s:%s:%s:%s:%s' % \
                                (ha1, nonce, res['nc'], cnonce, qop, ha2))
        else:
            response = self.md5('%s:%s:%s' % (ha1, nonce, ha2))
        res['response'] = response
        # Convert the dict to a formatted list, quoting values when relevant
        attrs = []
        for name, value in res.items():
            if name not in self.unquoted:
                value = '"%s"' % value
            attrs.append('%s=%s' % (name, value))
        # Produce the final value
        return 'Digest %s' % ', '.join(attrs)

    def __repr__(self):
        pairs = ['%s=%s' % (k, v) for k, v in self.__dict__.items()]
        return '<Realm %s>' % ','.join(pairs)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class HttpResponse:
    '''Stores information about a HTTP response'''

    # Useful empty dict
    emptyDict = {}

    # Redirect HTTP codes
    redirectCodes = (302, 303)

    def __init__(self, resource, response, body, duration=None, utf8=True,
                 responseType=None, unmarshallParams=None):
        self.resource = resource
        self.code = response.status # The return code, ie 404, 200, 500...
        self.text = response.reason # Textual description of the code
        self.headers = response.msg # A dict-like object containing the headers
        self.body = body # The body of the HTTP response
        # p_duration, if given, is the time, in seconds, we have waited, before
        # getting this response after having sent the request.
        self.duration = duration
        self.utf8 = utf8
        # If data must be unmarshalled, customizing the unmarshalling process
        # can be done by specifying a dict of p_unmarshallParams.
        self.unmarshallParams = unmarshallParams
        # The following attribute may contain specific data extracted from
        # the previous fields. For example, when response if 302 (Redirect),
        # self.data contains the URI where we must redirect the user to.
        self.data = self.extractData(responseType)
        self.response = response

    def __repr__(self, complete=False):
        duration = suffix = ''
        if self.duration: duration = DUR_SECS % self.duration
        if complete:
            suffix = RESP_T %  (str(self.headers), str(self.body))
        return RESP_R % (self.code, self.text, duration, suffix)

    def get(self): return self.__repr__(complete=True)

    def getResponseUrl(self, url):
        '''Get the URL path'''
        parts = urllib.parse.urlparse(url)
        r = parts.path or '/'
        if parts.query:
            r += '?%s' % parts.query
        return r

    def extractContentType(self, contentType):
        '''Extract the content type from the HTTP header, potentially removing
           encoding-related data.'''
        i = contentType.find(';')
        if i != -1: return contentType[:i]
        return contentType

    def extractCookies(self, headers):
        '''Extract received cookies and put them in self.resource.headers'''
        if 'Set-Cookie' not in headers: return
        # Several "Set-Cookie" can be returned by the server, so do not access
        # the dict-like p_headers, into which only the first "Set-Cookie" will
        # be present: access the underlying p_headers._headers tuple.
        for key, value in headers._headers:
            if key != 'Set-Cookie': continue
            cookie = value.split(';')[0]
            name, value = cookie.split('=', 1)
            # Delete the cookie if it has expired
            if value.strip('"') == 'deleted':
                # Do not set this cookie, and remove it if already present
                if name in self.resource.cookies:
                    del(self.resource.cookies[name])
            else:
                self.resource.cookies[name] = value

    xmlHeaders = ('text/xml', 'application/xml', 'application/soap+xml')

    def extractData(self, responseType=None):
        '''This method extracts, from the various parts of the HTTP response,
           some useful information:
           * it will find the URI where to redirect the user to if self.code
             is 302 or 303;
           * it will return authentication-related data, if present, if
             self.code is 401;
           * it will unmarshall XML or JSON data into Python objects;
           * ...'''
        # Extract information from HTTP headers when relevant
        headers = self.headers
        self.extractCookies(headers)
        if self.code in self.redirectCodes:
            # The URL to redirect to is in header key 'location'
            return self.getResponseUrl(headers['location'])
        elif self.code == 401:
            authInfo = headers.get('WWW-Authenticate')
            return authInfo and DigestRealm(authInfo) or None
        # Determine the response type from the HTTP response, or, if not found,
        # use p_responseType that may have been given.
        responseType = headers.get('Content-Type')
        if not responseType: return
        # Apply some transform on the response content depending on its type
        contentType = self.extractContentType(responseType)
        # Manage JSON content
        if contentType == 'application/json':
            return json.Decoder.decode(self.body)
        # Manage XML content
        for xmlHeader in self.xmlHeaders:
            # Ensure this is XML
            if not contentType.startswith(xmlHeader): continue
            # Return an unmarshalled version of the XML content, for easy use
            try:
                params = self.unmarshallParams or HttpResponse.emptyDict
                parser = Unmarshaller(**params)
                r = parser.parse(self.body)
                if parser.rootTag == 'exception':
                    # This is an exception: v_r contains the traceback
                    raise Resource.Error(D_ERR % r)
                return r
            except xml.sax.SAXParseException as se:
                raise Resource.Error(XML_ERR % str(se))

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
urlRex = re.compile(r'(http[s]?)://([^:/]+)(:[0-9]+)?(/.+)?', re.I)
binaryRex = re.compile(r'[\000-\006\177-\277]')

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Resource:
    '''Every instance of this class represents some web resource accessible
       through HTTP.'''

    class Error(Exception): pass

    # Standard ports, by protocol
    standardPorts = {'http': 80, 'https': 443}

    def __init__(self, url, username=None, password=None, measure=False,
                 utf8=True, authMethod='Basic', timeout=10):
        self.username = username
        self.password = password
        self.authMethod = authMethod
        self.url = url
        self.utf8 = utf8
        # A timeout (in seconds) used when sending blocking requests to the
        # resource.
        self.timeout = timeout
        # If p_measure is True, we will measure, for every request sent, the
        # time we wait until we receive the response.
        self.measure = measure
        # If measure is True, we will store hereafter, the total time (in
        # seconds) spent waiting for the server for all requests sent through
        # this resource object.
        self.serverTime = 0
        # Split the URL into its components
        r = urlRex.match(url)
        if r:
            protocol, host, port, uri = r.groups()
            self.protocol = protocol
            self.host = host
            if port:
                self.port = int(port[1:])
            else:
                self.port = Resource.standardPorts[self.protocol]
            self.uri = uri or '/'
        else: raise self.Error(URL_ERR % str(url))
        # If some headers must be sent with any request sent through this
        # resource, you can store them in the following dict.
        self.headers = {'Host': self.getHeaderHost(), 'User-Agent': 'Appy',
                        'Connection': 'close', 'Accept': '*/*',
                        'Accept-Encoding': 'gzip, identity'}
        # Cookies defined hereafter will be included in self.headers at every
        # request.
        self.cookies = {}

    def getHeaderHost(self):
        '''Gets the content of header key "Host"'''
        # Insert the port number if not standard
        suffix = '' if self.port == Resource.standardPorts[self.protocol] \
                    else ':%d' % self.port
        return '%s%s' % (self.host, suffix)

    def __repr__(self):
        '''p_self's short string representation'''
        return RESS_R % self.url

    def completeHeaders(self, headers):
        # Get standard header values from self.headers if not defined in
        # p_headers
        if self.headers:
            for k, v in self.headers.items():
                if k not in headers:
                    headers[k] = v
        # Add cookies
        if self.cookies:
            headers['Cookie'] = '; '.join(['%s=%s' % (k, v) \
                                          for k, v in self.cookies.items()])
        # Add credentials-related headers when relevant
        if not (self.username and self.password): return
        if 'Authorization' in headers: return
        if self.authMethod == 'Basic':
            creds = ('%s:%s' % (self.username, self.password)).encode()
            authorization = '%s %s' % (self.authMethod,
                                       encodebytes(creds).strip().decode())
            headers['Authorization'] = authorization

    def readResponse(self, response):
        '''Reads the response content. Unzip the result when appropriate'''
        headers = response.headers
        if headers.get('Content-Encoding') == 'gzip':
            # Unzip the content
            f = gzip.GzipFile(fileobj=response)
        else:
            f = response
        # Read response bytes
        r = f.read()
        # Decode the response when relevant
        contentType = headers.get('Content-Type')
        if contentType and contentType.startswith('image/'):
            pass # No need to decode it
        else:
            try:
                r = r.decode()
            except UnicodeDecodeError:
                pass
        return r

    def send(self, method, uri, body=None, headers=None, bodyType=None,
             responseType=None, unmarshallParams=None):
        '''Sends a HTTP request with p_method, for p_uri'''
        hc = http.client
        # p_uri's protocol may be different from p_self.protocol: recompute the
        # protocol from p_uri.
        protocol = uri[:uri.index(':')]
        if protocol == 'https':
            context = ssl.SSLContext()
            context.verify_mode = ssl.CERT_NONE
            conn = hc.HTTPSConnection(self.host, self.port,
                                      timeout=self.timeout, context=context)
        else:
            conn = hc.HTTPConnection(self.host, self.port, timeout=self.timeout)
        try:
            conn.connect()
        except socket.gaierror as sge:
            raise self.Error(CIC_ERR % str(sge))
        except socket.timeout as se:
            raise self.Error(T_OUT_ERR % conn.timeout)
        except socket.error as se:
            raise self.Error(CONN_ERR % str(se))
        # Tell what kind of HTTP request it will be
        conn.putrequest(method, uri, skip_host=True)
        # Add HTTP headers
        if headers is None: headers = {}
        self.completeHeaders(headers)
        for k, v in headers.items(): conn.putheader(k, v)
        conn.endheaders()
        # Add HTTP body
        if body:
            if not bodyType: bodyType = 'string'
            copyData(body, conn, 'send', type=bodyType)
        # Send the request, get the reply
        if self.measure: startTime = time.time()
        try:
            response = conn.getresponse()
        except socket.timeout as te:
            raise self.Error(T_OUT_ERR % conn.timeout)
        if self.measure: endTime = time.time()
        body = self.readResponse(response)
        conn.close()
        # Return a smart object containing the various parts of the response
        duration = None
        if self.measure:
            duration = endTime - startTime
            self.serverTime += duration
        return HttpResponse(self, response, body, duration=duration,
                            utf8=self.utf8, responseType=responseType,
                            unmarshallParams=unmarshallParams)

    def mkdir(self, name):
        '''Creates a folder named p_name in this resource'''
        folderUri = self.uri + '/' + name
        #body = '<d:propertyupdate xmlns:d="DAV:"><d:set><d:prop>' \
        #       '<d:displayname>%s</d:displayname></d:prop></d:set>' \
        #       '</d:propertyupdate>' % name
        return self.send('MKCOL', folderUri)

    def delete(self, name):
        '''Deletes a file or a folder (and all contained files if any) named
           p_name within this resource.'''
        toDeleteUri = self.uri + '/' + name
        return self.send('DELETE', toDeleteUri)

    def add(self, path, name=''):
        '''Adds a file in this resource, whose p_path is passed'''
        size = os.stat(path)[stat.ST_SIZE]
        body = open(path, 'rb')
        name = os.path.basename(path)
        fileType, encoding = guess_type(path)
        fileUri = self.uri + '/' + name
        headers = {'Content-Length': str(size)}
        if fileType: headers['Content-Type'] = fileType
        if encoding: headers['Content-Encoding'] = encoding
        r = self.send('PUT', fileUri, body, headers, bodyType='file')
        body.close()
        return r

    def get(self, uri=None, headers=None, params=None, followRedirect=True,
            responseType=None, unmarshallParams=None):
        '''Perform a HTTP GET on the server. Parameters can be given as a dict
           in p_params. p_responseType will be used if no "Content-Type" key is
           found on the HTTP response. In the processs of unmarshalling received
           data, specific parameters can be passed in dict
           p_unmarshallParams. '''
        if not uri: uri = self.uri
        # Encode and append params if given
        if params:
            sep = '&' if '?' in uri else '?'
            uri = '%s%s%s' % (uri, sep, urllib.parse.urlencode(params))
        r = self.send('GET', uri, headers=headers, responseType=responseType,
                      unmarshallParams=unmarshallParams)
        # Follow redirect when relevant
        if r.code in r.redirectCodes and followRedirect:
            # Addition durations when "measure" is True
            duration = r.duration
            r = self.get(r.data, headers=headers)
            if self.measure: r.duration += duration
            return r
        # Perform Digest-based authentication when relevant
        if r.code == 401 and self.authMethod == 'Digest' and r.data:
            # Re-trigger the request with the correct authentication headers
            headers = headers or {}
            headers['Authorization'] = r.data.buildCredentials(self, uri)
            return self.get(uri=uri, headers=headers, params=params,
                       followRedirect=followRedirect, responseType=responseType)
        return r
    rss = get

    def post(self, data=None, uri=None, headers=None, encode='form',
             followRedirect=True):
        '''Perform a HTTP POST on the server. If p_encode is "form", p_data is
           considered to be a dict representing form data that will be
           form-encoded. Else, p_data will be considered as the ready-to-send
           body of the HTTP request.'''
        if not uri: uri = self.uri
        if headers is None: headers = {}
        # Prepare the data to send
        if encode == 'form':
            # Format the form data and prepare headers
            body = FormDataEncoder(data).encode()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            body = data
        headers['Content-Length'] = str(len(body))
        r = self.send('POST', uri, headers=headers, body=body)
        if r.code in r.redirectCodes and followRedirect:
            # Update headers
            for key in ('Content-Type', 'Content-Length'):
                if key in headers: del headers[key]
            # Addition durations when "measure" is True
            duration = r.duration
            r = self.get(r.data, headers=headers)
            if self.measure: r.duration += duration
        return r

    def soap(self, data, uri=None, headers=None, namespace=None,
             soapAction=None):
        '''Sends a SOAP message to this resource. p_namespace is the URL of the
           server-specific namespace. If header value "SOAPAction" is different
           from self.url, specify it in p_soapAction.'''
        if not uri: uri = self.uri
        # Prepare the data to send
        data = SoapDataEncoder(data, namespace).encode()
        if headers is None: headers = {}
        headers['SOAPAction'] = soapAction or self.url
        # Content-type could be 'text/xml'
        headers['Content-Type'] = 'application/soap+xml;charset=UTF-8'
        r = self.post(data, uri, headers=headers, encode=None)
        # Unwrap content from the SOAP envelope
        if hasattr(r.data, 'Body'):
            r.data = r.data.Body
        return r
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
