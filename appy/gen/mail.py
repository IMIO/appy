'''Functions for sending emails'''
import smtplib, socket, time
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import formatdate
from email import Encoders
from email.Header import Header
from appy.shared.utils import sequenceTypes

# ------------------------------------------------------------------------------
class MailConfig:
    '''Parameters for connecting to a SMTP server'''
    # Currently we don't check the connection to the SMTP server at startup
    testable = False

    def __init__(self, fromName=None, fromEmail='info@appy.org', replyTo=None,
                 server='localhost', port=25, secure=False,
                 login=None, password=None, enabled=True):
        # The name that will appear in the "from" part of the messages
        self.fromName = fromName
        # The mail address that will appear in the "from" part of the messages
        self.fromEmail = fromEmail
        # The optional "reply-to" mail address
        self.replyTo = replyTo
        # The SMTP server address and port
        if ':' in server:
            self.server, port = server.split(':')
            self.port = int(port)
        else:
            self.server = server
            self.port = int(port) # That way, people can specify an int or str
        # Secure connection to the SMTP server ?
        self.secure = secure
        # Optional credentials to the SMTP server
        self.login = login
        self.password = password
        # Is this server connection enabled ?
        self.enabled = enabled

    def init(self, tool): pass
    def getFrom(self):
        '''Gets the "from" part of the messages to send.'''
        if self.fromName: return '%s <%s>' % (self.fromName, self.fromEmail)
        return self.fromEmail

    def __repr__(self):
        '''Short string representation of this mail config, for logging and
           debugging purposes.'''
        r = '%s:%d' % (self.server, self.port)
        if self.login: r += ' (login as %s)' % self.login
        return r

# ------------------------------------------------------------------------------
def sendMail(config, to, subject, body, attachments=None, log=None,
             replyTo=None):
    '''Sends a mail, via the SMTP server defined in the p_config (an instance of
       appy.gen.mail.MailConfig above), to p_to (a single email recipient or a
       list of recipients). Every (string) recipient can be an email address or
       a string of the form "[name] <[email]>".

       p_attachments must be a list or tuple whose elements can have 2 forms:
         1. a tuple (fileName, fileContent): "fileName" is the name of the file
            as a string; "fileContent" is the file content, also as a string;
         2. a appy.fields.file.FileInfo instance.

       p_log can be a function accepting 2 args:
        - the message to log (as a string);
        - the second must be named "type" and will receive string
          "info", "warning" or "error".

       A p_replyTo mail address or recipient can be specified.
    '''
    start = time.time()
    if isinstance(to, str): to = [to]
    if not config:
        if log: log('Must send mail but no smtp server configured.')
        return
    # Just log things if mail is disabled
    fromAddress = config.getFrom()
    replyTo = replyTo or config.replyTo
    if not config.enabled or not config.server:
        if not config.server:
            msg = ' (no mailhost defined)'
        else:
            msg = ''
        if log:
            toLog = 'mail disabled%s: should send mail from %s to %d ' \
                    'recipient(s): %s.' % (msg, fromAddress, len(to),
                    ', '.join(to))
            if replyTo: toLog += ' (Reply to: %s).' % replyTo
            log(toLog)
            log('subject: %s' % subject)
            log('body: %s' % body)
        if attachments and log: log('%d attachment(s).' % len(attachments))
        return
    if log: log('sending mail from %s to %s (subject: %s).' % \
                (fromAddress, str(to), subject))
    # Create the base MIME message
    body = MIMEText(body, 'plain', 'utf-8')
    if attachments:
        msg = MIMEMultipart()
        msg.attach(body)
    else:
        msg = body
    # Add the header values
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = fromAddress
    msg['Date'] = formatdate(localtime=True)
    if replyTo: msg.add_header('reply-to', replyTo)
    if len(to) == 1:
        msg['To'] = to[0]
    else:
        msg['To'] = fromAddress
        msg['Bcc'] = ', '.join(to)
    # Add attachments
    if attachments:
        for attachment in attachments:
            # 2 possible forms for an attachment
            if isinstance(attachment, tuple) or isinstance(attachment, list):
                fileName, fileContent = attachment
            else:
                # a FileInfo instance
                fileName = attachment.uploadName
                f = file(attachment.fsPath, 'rb')
                fileContent = f.read()
                f.close()
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(fileContent)
            Encoders.encode_base64(part)
            part.add_header('Content-Disposition',
                            'attachment; filename="%s"' % fileName)
            msg.attach(part)
    # Send the email
    try:
        smtpServer = smtplib.SMTP(config.server, port=config.port)
        if config.secure:
            # The next line is only required for Python > 2.6, that calls it
            # within method "starttls" below.
            smtpServer.ehlo()
            smtpServer.starttls()
            # The next line is only required for Python < 2.5: more recent
            # Pythons call it again after the TLS connection has been
            # established, at the end of method "starttls".
            smtpServer.ehlo()
        if config.login:
            smtpServer.login(config.login, config.password)
        r = smtpServer.sendmail(fromAddress, to, msg.as_string())
        smtpServer.quit()
        if log:
            if r:
                log('could not send mail to some recipients. %s' % str(r),
                    type='warning')
            else:
                log('mail sent in %.2f secs.' % (time.time()-start))
    except smtplib.SMTPException, e:
        if log:
            log('%s: mail sending failed (%s)' % (config, str(e)), type='error')
    except socket.error, se:
        if log:
            log('%s: mail sending failed (%s)' % (config, str(se)),type='error')
# ------------------------------------------------------------------------------
