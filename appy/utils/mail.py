'''Functions for sending emails'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from email.utils import formatdate
from email.message import EmailMessage
import smtplib, socket, time, mimetypes

from appy.model.notify import Notifier

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
NO_SERVER  = 'no mailhost defined'
DISABLED   = 'Mail disabled%s :: Should send mail from %s to %d recipient(s):' \
             ' %s.'
SENDER_NO  = "Don't specify any sender when sending mails: the Mailer gets " \
             "it from the mail config."
REPLY_TO   = 'reply to: %s'
MSG_SUBJ   = 'Subject :: %s'
MSG_BODY   = 'Body :: %s'
MSG_ATTS   = '%d attachment(s) :: %s.'
MSG_SEND   = 'Sending mail from %s to (%d recipient·s) %s (subject: %s).'
MAIL_R_KO  = 'Could not send mail to some recipients. %s'
MAIL_SENT  = "Mail sent in %.2f''."
MAIL_NSENT = '%s :: Mail sending failed (%s).'
CONNECT_OK = "Connected to %s in %.2f''."
NO_REC     = 'No mail recipient for "%s".'
NO_RECS    = 'No recipient for sending mail about %s %s with %s(s) %s.'


#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Config:
    '''Parameters for connecting to a SMTP server'''

    # Currently we don't check the connection to the SMTP server at startup
    testable = False

    def __init__(self, fromName=None, fromEmail='info@appyframe.work',
                 replyTo=None, server='localhost', port=None, secure=False,
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
            if port:
                port = int(port) # That way, people can specify an int or str
            else:
                port = 465 if secure else 25
            self.port = port
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
        name = self.fromName
        return f'{name} <{self.fromEmail}>' if name else self.fromEmail

    def connect(self):
        '''Connects to the SMTP server and returns it'''
        class_ = smtplib.SMTP_SSL if self.secure else smtplib.SMTP
        server = class_(self.server, port=self.port)
        if self.login:
            server.login(self.login, self.password)
        return server

    def __repr__(self):
        '''Short string representation of this mail config, for logging and
           debugging purposes.'''
        auth = f' (login as {self.login})' if self.login else ''
        ssl = '·SSL' if self.secure else ''
        r = f'‹MailConfig {self.server}:{self.port}{auth}{ssl}›'
        return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Mailer(Notifier):
    '''Sends mail'''

    # A mail is a specific kind of notification a user may receive. Class
    # Notifier groups all stuff being common to all types of notifications.

    # Does this notifier allow attachments ?
    attachmentsAllowed = True

    # Don't log the start of the process: this notifier has his own log
    logInit = False

    # Error message when a mailer is called without config
    NO_CONFIG  = 'Must send mail but no SMTP server configured in config.mail.'

    def __init__(self, config, log=None):
        # Call the base constructor. p_config must be an instance of class
        # appy.utils.mail.Config as defined hereabove.
        super().__init__(config, log)
        # The following attribute will hold an instance of class
        # email.message.EmailMessage, that will be used to build the mail parts.
        # Even if several emails must be sent by the current Mailer object
        # (p_self), a unique EmailMessage object will be used: parts being
        # specific to each mail will be replaced within this unique object.
        self.message = None
        # The object representing the SMTP server will be stored here
        self.server = None
        # The mail recipient(s)
        self.to = None
        # Has p_self been late-initialized ?
        self.lateInit = False

    def init(self, sender, subject, body, attachments, replyTo, split):
        '''Late initialisation'''
        # Call the base method
        super().init(sender, subject, body, attachments, replyTo, split)
        # Get the sender
        config = self.config
        if sender:
            # The mailer gets the sender from the mail config
            raise Exception(SENDER_NO)
        self.sender = config.getFrom() if config else None
        # Get the reply-to info from the config if not passed in p_replyTo
        if replyTo is None and config:
            self.replyTo = config.replyTo
        # Note that late initialisation was done
        self.lateInit = True

    def connect(self):
        '''Connects to the SMTP server and store, in p_self.server, an object
           representing it, if not already done.'''
        # Returns a tuple (self.server, b_new). b_new is False if the server
        # already existed.
        #
        # Returns the existing server, if any
        server = self.server
        if server: return server, False
        # Create a new connection
        self.server = server = self.config.connect()
        return server, True

    def disconnect(self):
        '''Disconnects from p_self.server'''
        server = self.server
        # If the server is disabled (as set on the config), it may not be there
        if server:
            server.quit()

    def logShipment(self, error, start):
        '''A mail has been sent at this p_start time. Log the fact that it has
           been successfully sent or not (depending on the boolean p_error
           parameter).'''
        log = self.logFun
        if not log: return
        if error:
            log(MAIL_R_KO % str(error), type='warning')
        else:
            log(MAIL_SENT % (time.time() - start))

    def mailDisabled(self, subject, body):
        '''Returns True if no mail must be send because the SMTP server is
           disabled or is not specified. Log when appropriate.'''
        # Return False if an enabled server is found
        config = self.config
        if config.enabled and config.server: return
        # Return True now if no log function is found
        log = self.logFun
        if not log: return True
        # Log info about the mail that could have been sent
        msg = '' if config.server else f' ({NO_SERVER})'
        to = self.to
        toLog = DISABLED % (msg, self.sender, len(to), ', '.join(to))
        if self.replyTo:
            rText = REPLY_TO % self.replyTo
            toLog = f'{toLog} ({rText}).'
        log(toLog)
        log(MSG_SUBJ % subject)
        log(MSG_BODY % body)
        # Log info about the attachments, if any
        attachs = self.attachments
        if attachs:
            # Every attachment can be a tuple or a FileInfo object
            names = []
            for attach in attachs:
                if isinstance(attach, (list, tuple)):
                    names.append(attach[0])
                else:
                    names.append(attach.uploadName)
            log(MSG_ATTS % (len(attachs), ', '.join(names)))
        return True

    def createMessage(self, subject, body):
        '''Creates the EmailMessage object as a way to build the mail to send'''
        self.message = m = EmailMessage()
        m['Subject'] = subject
        m['From'] = self.sender
        # The "To" and potential "Bcc" headers will be added afterwards
        m['Date'] = formatdate(localtime=True)
        m.set_content(body)
        if self.replyTo:
            m['reply-to'] = self.replyTo
        # Add attachments
        attachs = self.attachments
        if attachs:
            for attach in attachs:
                # Get the file name and content. Every attachment can be of
                # various forms.
                if isinstance(attach, (tuple, list)):
                    fileName, theFile = attach
                else:
                    theFile = attach
                    fileName = attach.uploadName
                if isinstance(theFile, bytes):
                    fileContent = theFile
                else: # a FileInfo object
                    with open(theFile.fsPath, 'rb') as f: fileContent = f.read()
                # Get the MIME type
                mimeType = mimetypes.guess_type(fileName)[0]
                main, sub = mimeType.split('/', 1)
                m.add_attachment(fileContent, maintype=main, subtype=sub,
                                 filename=fileName)

    def buildMessage(self, subject, body):
        '''Create or update the EmailMessage object from data as stored on
           p_self.'''
        m = self.message
        if m is None:
            # Create a new one
            self.createMessage(subject, body)
        else:
            # Recycle the existing one. What may have changed is the mail body
            # and subject.
            del m['Subject']
            m['Subject'] = subject
            # Change the body. If the message has attachments (is multipart),
            # the part corresponding to the body must be found and updated.
            if m.is_multipart():
                # The assumption is that the first part having type text/plain
                # is the mail body.
                for part in m.walk():
                    if part.get_content_type() == 'text/plain':
                        part.set_content(body)
            else:
                m.set_content(body)

    def sendMessage(self, disconnect=True):
        '''Send the mail as built in p_self.message; return True upon success'''
        config = self.config
        to = self.to
        try:
            # Connect to the SMTP server, if not already done
            start = time.time()
            server, new = self.connect()
            split = self.split
            m = self.message
            one = len(to) == 1
            if split and not one:
                # Send one mail per recipient. In this case, log the time spent
                # while connecting.
                if new:
                    self.log(CONNECT_OK % (config.server, time.time() - start))
                for recipient in to:
                    start = time.time()
                    if 'To' in m:
                        del m['To']
                    m['To'] = recipient
                    r = server.send_message(m)
                    self.logShipment(r, start)
            else:
                # Send a unique mail ...
                if 'To' in m: del m['To']
                if 'Bcc' in m: del m['Bcc']
                if one:
                    # ... to a single person
                    m['To'] = to[0]
                else:
                    # ... to everybody
                    m['To'] = self.sender
                    m['Bcc'] = ', '.join(to)
                r = server.send_message(m)
                self.logShipment(r, start)
            # Disconnect from the server, if appropriate
            if disconnect:
                server.quit()
            return True
        except smtplib.SMTPException as e:
            self.log(MAIL_NSENT % (config, str(e)), type='error')
        except socket.error as se:
            self.log(MAIL_NSENT % (config, str(se)), type='error')

    def standardize(self, to):
        '''Standardize p_to to a list of mail recipients'''
        # Indeed, p_to may be a single recipient
        return [to] if isinstance(to, str) else to

    def send(self, to, subject, body, attachments=None, replyTo=None,
             split=None, disconnect=True):

        '''Sends a mail, via the SMTP server defined in p_self.config. Returns
           True if the mail(s) has(ve) been successfully sent.'''

        # Sends a mail to p_to, being a single email recipient or a list of
        # recipients. Every recipient must be expressed as a string that can
        # hold an email address or a string of the form "[name] <[email]>".

        # p_subject and p_body must be strings containing the mail subject and
        # body.

        # p_attachments, if passed, must be a list or tuple whose elements can
        # have 2 forms:
        # 1. a tuple (fileName, fileContent): "fileName" is the name of the file
        #    as a string; "fileContent" is the file content, expressed as bytes;
        # 2. an instance of class appy.model.fields.file.FileInfo ;
        # 3. a tuple (fileName, fileInfo), where an instance of class
        #    appy.model.fields.file.FileInfo is in use, but with an alternate
        #    file name, specified in the first tuple element.

        # A p_replyTo mail address or recipient can be specified.

        # If p_split is True, an individual mail will be sent to each recipient.
        # Else, a unique mail will be send to all recipients, listed in field
        # Bcc.

        # By default, p_disconnect is True: after sending the mail(s), the SMTP
        # connection will be closed: no more call to p_send will work. By
        # setting p_disconnect to False, the SMTP connection stays open, and
        # successive calls to m_send may take place (there is one limitation,
        # though, as explained below). In that case, you have to close yourself
        # the SMTP connection, once all the m_send calls will be over, by
        # calling method mailer::disconnect. For example, this is what method
        # Notifier.sendIf does (see m_onceWalked, called by it).

        # ⚠️ If you use a Mailer object directly (ie, not via wrapper methods
        #    tool.sendMail or tool.sendMailIf), note that if you call m_send
        #    several times with the same connection (with p_disconnect being
        #    False), the same internal EmailMessage object will be recycled ;
        #    in that case, only p_to, p_subject and p_body will be updated in
        #    it, but not p_attachments. In other words, if you plan to send
        #    several mails with different attachments for each mail, create a
        #    different Mailer object for each one, or use the hereabove-
        #    mentioned wrapper methods on the tool.

        # Ensure everything is correctly configured
        if self.configError(): return

        # Late-initialise p_self, if not done yet
        if not self.lateInit:
            self.init(None, subject, body, attachments, replyTo, split)

        # Ensure p_self.to is a list of recipients
        self.to = to = self.standardize(to)

        # Don't send a mail if the mail server is disabled or does not exist
        # (but possibly log info about the mail that would have been sent).
        if self.mailDisabled(subject, body): return

        # Log the start of the process
        self.log(MSG_SEND % (self.sender, len(to), ', '.join(to), subject))

        # Create or update the EmailMessage object
        self.buildMessage(subject, body)

        # Send the created message
        return self.sendMessage(disconnect)

    def sendOne(self, user):
        '''Tries to send a mail to that p_user and return the number of mails
           sent (1 or 0).'''
        # Get the mail recipient for that p_user
        recipient = user.getMailRecipient()
        if not recipient:
            # Do not send anything to that user: it does not have e-mail. Log
            # this problem only if the user is not special.
            if not user.isSpecial():
                user.log(NO_REC % user.login, type='warning')
            return 0
        # We have here a valid v_recipient
        if self.split:
            # Directly send a mail
            subject, body = self.getTexts(user)
            self.send(recipient, subject, body, disconnect=False)
            r = 1
        else:
            # Don't sent a mail now and add the recipient to p_self.to
            to = self.to
            if to is None:
                to = self.to = []
            to.append(recipient)
            r = 0 # No mail was sent so far
        return r

    def onceWalked(self):
        '''Close the connection to the SMTP server when appropriate'''
        if self.split:
            # We must now disconnect from the SMTP server. Indeed, once all
            # users have been walked, all the individual mails were sent via a
            # single SMTP connection.
            self.disconnect()

    def finalize(self):
        '''Sends the unique mail if we are not in split mode'''
        if self.split: return
        # Non-split mode: send the unique mail
        if self.recipients:
            self.send(self.to, self.subject, self.body)
        elif self.logFun:
            # There is no recipient at all: no mail can be sent. Log this.
            priv = self.privilege
            pri = ', '.join(priv) if isinstance(priv, (list, tuple)) else priv
            self.log(NO_RECS % (o.class_.name.lower(), o.id, privilegeType,
                                pri), type='warning')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
