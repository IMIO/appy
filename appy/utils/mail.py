'''Functions for sending emails'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from email.utils import formatdate
from email.message import EmailMessage
import smtplib, socket, time, mimetypes

from .string import Variables
from appy.database.operators import or_
from appy.model.utils import Object as O

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
NO_CONFIG  = 'Must send mail but no SMTP server configured.'
NO_SERVER  = 'no mailhost defined'
DISABLED   = 'Mail disabled%s :: Should send mail from %s to %d recipient(s):' \
             ' %s.'
REPLY_TO   = 'reply to: %s'
MSG_SUBJ   = 'Subject :: %s'
MSG_BODY   = 'Body :: %s'
MSG_ATTS   = '%d attachment(s) :: %s.'
MSG_SEND   = 'Sending mail from %s to %s (subject: %s).'
MAIL_R_KO  = 'Could not send mail to some recipients. %s'
MAIL_SENT  = "Mail sent in %.2f''."
MAIL_NSENT = '%s :: Mail sending failed (%s).'
CONNECT_OK = "Connected to %s in %.2f''."
NO_G_U     = 'Inexistent %s(s) %s.'
NO_REC     = 'No mail recipient for "%s".'
NO_RECS    = 'No recipient for sending mail about %s %s with %s(s) %s.'
SP_VARS_KO = 'sendMailIf called with split=False and non empty variables. ' \
             'Indeed, variables come into play when sending individual mails.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Config:
    '''Parameters for connecting to a SMTP server'''

    # Currently we don't check the connection to the SMTP server at startup
    testable = False

    def __init__(self, fromName=None, fromEmail='info@appyframe.work',
                 replyTo=None, server='localhost', port=25, secure=False,
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
        name = self.fromName
        return f'{name} <{self.fromEmail}>' if name else self.fromEmail

    def connect(self):
        '''Connects to the SMTP server and returns it'''
        server = smtplib.SMTP(self.server, port=self.port)
        if self.secure:
            server.ehlo()
            server.starttls()
        if self.login:
            server.login(self.login, self.password)
        return server

    def __repr__(self):
        '''Short string representation of this mail config, for logging and
           debugging purposes.'''
        auth = f' (login as {self.login})' if self.login else ''
        r = f'‹MailConfig {self.server}:{self.port}{auth}›'
        return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Mailer:
    '''Sends mail'''

    def __init__(self, config, log=None):
        # An instance of class appy.utils.mail.Config hereabove
        self.config = config
        # p_log can be a function accepting 2 args:
        # - the message to log (as a string);
        # - the second must be named "type" and will receive string
        #   "info", "warning" or "error".
        self.logFun = log
        # The following attribute will hold an instance of class
        # email.message.EmailMessage, that will be used to build the mail parts.
        # Even if several emails must be sent by the current Mailer object
        # (p_self), a unique EmailMessage object will be used: parts being
        # specific to each mail will be replaced within this unique object.
        self.message = None
        # The sender
        self.from_ = config.getFrom() if config else None
        # The recipients
        self.to = None
        # The reply-to address, if any
        self.replyTo = None
        # The mail subject, body and attachments
        self.subject = self.body = self.attachments = None
        # Must a distinct mail be sent for every recipient ?
        self.split = None
        # The object representing the SMTP server will be stored here
        self.server = None

    def init(self, to, subject, body, attachments, replyTo, split):
        '''Late initialisation'''
        config = self.config
        # Standardize p_to to a list of recipients, even when there is a single
        # recipient.
        if to:
            self.to = [to] if isinstance(to, str) else to
        # p_self may already have been late-initialised: set attributes only
        # for not-empty parameters.
        if replyTo:
            # Get the reply-to address, if any
            self.replyTo = replyTo
        elif self.replyTo is None:
            self.replyTo = config.replyTo
        # Get the mail subject and body
        if subject:
            self.subject = subject
        if body:
            self.body = body
        # Get attachments
        if attachments:
            self.attachments = attachments
        # Must a distinct mail be sent for every recipient ?
        if split is not None:
            self.split = split

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

    def log(self, message, type='info'):
        '''Logs a message, if a log function has been defined'''
        fun = self.logFun
        if fun:
            fun(message, type=type)

    def logShipment(self, error, start):
        '''A mail has been sent at this p_start time. Log the fact that it has
           been successfully sent or not (depending on the boolean p_error
           parameter).'''
        log = self.logFun
        if not log: return
        if error:
            log(MAIL_R_KO % str(r), type='warning')
        else:
            log(MAIL_SENT % (time.time() - start))

    def configError(self):
        '''Return True if the config is missing or wrong'''
        if not self.config:
            self.log(NO_CONFIG)
            return True

    def mailDisabled(self):
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
        toLog = DISABLED % (msg, self.from_, len(to), ', '.join(to))
        if self.replyTo:
            rText = REPLY_TO % self.replyTo
            toLog = f'{toLog} ({rText}).'
        log(toLog)
        log(MSG_SUBJ % self.subject)
        log(MSG_BODY % self.body)
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

    def createMessage(self):
        '''Creates the EmailMessage object as a way to build the mail to send'''
        self.message = m = EmailMessage()
        m['Subject'] = self.subject
        m['From'] = self.from_
        # The "To" and potential "Bcc" headers will be added afterwards
        m['Date'] = formatdate(localtime=True)
        m.set_content(self.body)
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

    def buildMessage(self):
        '''Create or update the EmailMessage object from data as stored on
           p_self.'''
        m = self.message
        if m is None:
            # Create a new one
            self.createMessage()
        else:
            # Recycle the existing one. What may have changed is the mail body
            # and subject.
            del m['Subject']
            m['Subject'] = self.subject
            # Change the body. If the message has attachments (is multipart),
            # the part corresponding to the body must be found and updated.
            if m.is_multipart():
                # The assumption is that the first part having type text/plain
                # is the mail body.
                for part in m.walk():
                    if part.get_content_type() == 'text/plain':
                        part.set_content(self.body)
            else:
                m.set_content(self.body)

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
                # Send a unique mail to everybody
                if 'To' in m: del m['To']
                if 'Bcc' in m: del m['Bcc']
                if one:
                    m['To'] = to[0]
                else:
                    m['To'] = self.from_
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

    def send(self, to, subject=None, body=None, attachments=None, replyTo=None,
             split=None, disconnect=True):

        '''Sends a mail, via the SMTP server defined in p_self.config. Returns
           True if the mail(s) has(ve) been successfully sent.'''

        # Sends a mail to p_to, being a single email recipient or a list of
        # recipients. Every recipient must be expressed as a string that can
        # hold an email address or a string of the form "[name] <[email]>".

        # p_subject and p_body must be strings containing the mail subject and
        # body.

        # p_attachments must be a list or tuple whose elements can have 2 forms:
        # 1. a tuple (fileName, fileContent): "fileName" is the name of the file
        #    as a string; "fileContent" is the file content, expressed as bytes;
        # 2. an instance of class appy.model.fields.file.FileInfo ;
        # 3. a tuple (fileName, fileInfo), where an instance of class
        #    appy.model.fields.file.FileInfo is in use, but with an alternate
        #    file name, specified in the first tuple element.

        # A p_replyTo mail address or recipient can be specified

        # If p_split is True, an individual mail will be sent to each recipient.
        # Else, a unique mail will be send to all repicients, listed in field
        # Bcc.

        # By default, p_disconnect is True: after sending the mail(s), the SMTP
        # connection will be closed: no more call to p_send will work. By
        # setting p_disconnect to True, the SMTP connection stays open, and
        # successive calls to m_send may take place (there is one limitation,
        # though, as explained below). In that case, you have to close yourself
        # the SMTP connection, once all the m_send calls will be over, by
        # calling method mailer::disconnect. For example, this is what m_sendIf
        # does (via its call to m_walkUsers).

        # ⚠️ If you use a Mailer object directly (ie, not via wrapper methods
        #    tool.sendMail or tool.sendMailIf), note that if you call m_send
        #    several times within the same connection (with p_disconnect being
        #    False), the same internal EmailMessage object will be recycled
        #    again and again; in that case, only p_to, p_subject and p_body will
        #    be updated in it, but not p_attachments.
        #    In other words, if you plan to send several mails with different
        #    attachments for each mail, use a different Mailer object for each
        #    one, or use the hereabove-mentioned wrapper methods on the tool.

        # Ensure everything is correctly configured
        if self.configError(): return

        # Late-initialise p_self
        self.init(to, subject, body, attachments, replyTo, split)

        # Don't send a mail if the mail server is disabled or does not exist
        # (but possibly log info about the mail that would have been sent).
        if self.mailDisabled(): return

        # Log the start of the process
        self.log(MSG_SEND % (self.from_, ', '.join(self.to), self.subject))

        # Create or update the EmailMessage object
        self.buildMessage()

        # Send the created message
        return self.sendMessage(disconnect)

    def getVariablesObject(self, user, variables):
        '''Returns an object containing values for p_variables as applied to
           this p_user.'''
        r = O()
        for name in variables:
            value = getattr(user, name)
            if callable(value): value = value()
            r[name] = value
        return r

    def sendOne(self, recipient, user, variables):
        '''Sends a mail to this p_recipient, corresponding to that p_user.
           p_self must already have been late-initialised. If p_variables are
           passed, replace them within p_self.subject and p_self.body before
           sending the mail.'''
        if variables:
            # Remember the currently stored subject and body, that represent
            # templates that must now be instantiated.
            templateSubject = self.subject
            templateBody = self.body
            # Get the p_user-specific variables in an object
            varS = self.getVariablesObject(user, variables)
            self.subject = Variables.replace(self.subject, varS)
            self.body = Variables.replace(self.body, varS)
        # Send the mail to this p_recipient
        self.send(recipient, disconnect=False)
        if variables:
            # Reset the template subject and body
            self.subject = templateSubject
            self.body = templateBody

    def collectUsers(self, o, privilege, privilegeType):
        '''Collect users having this p_privilege on this p_o(bject). If
           privilegeType is "role" or "permission", all active users are
           returned; they will be filtered by the called method.'''
        # To be more precise, the return value is a tuple ([users], s_checkPR),
        # where s_checkPR indicates if the called method must further filter
        # users according to a *p*ermission (s_checkPR holds 'permission') or
        # *r*ole (s_checkPR holds 'role').
        pt = privilegeType
        if pt in ('group', 'user'):
            checkPR = None
            logins = (privilege,) if isinstance(privilege, str) else privilege
            objs = o.search(pt.capitalize(), login=or_(*logins), state='active')
            if not objs:
                raise Exception(NO_G_U % (pt, ', '.join(logins)))
            if pt == 'user':
                users = objs
            else:
                # Get active users from all retrieved groups
                users = set()
                for group in objs:
                    for user in group.users:
                        if user.state == 'active':
                            users.add(user)
        else:
            # Get all users
            users = o.search('User', state='active')
            checkPR = pt
        return users, checkPR

    def walkUsers(self, users, o, excludeExpression, checkPR, privilege,
                  userMethod, variables):
        '''In non-split mode, this method collects and returns a list of valid
           mail recipients based on appropriate users among p_users. In split
           mode, for every such recipient, it directly sends a mail.'''
        r = None
        split = self.split
        for user in users:
            # Evaluate the "exclude expression"
            if eval(excludeExpression): continue
            # Check if the user has p_privilege on this object (only applicable
            # if the privilege does not represent a group).
            if checkPR:
                has = user.hasRole if checkPR == 'role' else user.hasPermission
                if isinstance(privilege, str):
                    # Check a single permission or role
                    if not has(privilege, o): continue
                else:
                    # Several permissions or roles are mentioned. Having a
                    # single permission or role is sufficient.
                    hasOne = False
                    for priv in privilege:
                        if has(priv, o):
                            hasOne = True
                            break
                    if not hasOne: continue
            # Execute the "user method" when specified
            if userMethod and not getattr(user, userMethod)(o): continue
            # Get the mail recipient for this user
            recipient = user.getMailRecipient()
            if not recipient:
                # Do not add this user: it does not have e-mail. Log this
                # problem only if the user is not special.
                if not user.isSpecial():
                    user.log(NO_REC % user.login, type='warning')
                continue
            # We have here a valid v_recipient
            if split:
                # Directly send a mail
                self.sendOne(recipient, user, variables)
            else:
                # Add the recipient to v_r
                if r is None: r = []
                r.append(recipient)
        if split:
            # We must now disconnect from the SMTP server. Indeed, all the
            # individual mails being sent via this method were done via a single
            # SMTP connection.
            self.disconnect()
        return r

    def sendIf(self, o, privilege, subject, body, attachments=None,
               privilegeType='permission', excludeExpression='False',
               userMethod=None, replyTo=None, split=False, variables=None):

        '''Sends a mail related to this p_o(bject) to any active user having
           this p_privilege on it.'''

        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # If p_privilegeType...
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # is...        | p_privilege is a (list or tuple of)...
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # 'permission' | permission(s)
        # 'role'       | role(s)
        # 'group'      | group login(s)
        # 'user'       | user login(s)
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

        # p_excludeExpression will be evaluated on every selected user. Users
        # for which the expression will produce True will not become mail
        # recipients. The expression is evaluated with variable "user" in its
        # context.

        # p_userMethod may be the name of a method on class User. If specified,
        # beyond p_privilege checking, a user will receive a mail if this method
        # returns True. p_userMethod must accept p_o as unique arg.

        # p_subject and p_body must be strings containing the mail subject and
        # body. If p_variables are not empty, p_subject and/or p_body may
        # contain variable parts (more explanations below, when describing
        # p_variables).

        # In the case of individual mails (p_split is True), p_variables, if
        # passed, must be a list or tuple of attribute or method names, that
        # must be defined on the User object corresponding to each recipient. In
        # this case, p_subject and p_body are supposed to contain variables
        # surrounded by pipes, like |attr1| or |method1|. When sending the mail
        # to each recipient, variables in p_subject and p_body will be replaced
        # by the corresponding values as found on the User object corresponding
        # to the recipient (in the example, user.attr1 or user.method1()). If
        # the name corresponds to a method, it will be called without any arg.

        # For any other parameter, check documentation on method m_send: their
        # homonymm parameters on this method have the same meaning as here.

        # Check parameters coherence
        if not split and variables: raise Exception(SP_VARS_KO)

        # Late-initialise p_self
        self.init(None, subject, body, attachments, replyTo, split)

        # Collect users having this p_privilege on this p_o(bject)
        users, checkPR = self.collectUsers(o, privilege, privilegeType)

        # Walk p_users
        recipients = self.walkUsers(users, o, excludeExpression, checkPR,
                                    privilege, userMethod, variables)

        # Stop here if we are in p_split mode: mails have already been sent
        if split: return

        # Non-split mode: send the unique mail
        if recipients:
            self.send(recipients)
        elif self.logFun:
            # Log the absence of v_recipients
            if isinstance(privilege, (list, tuple)):
                privilege = ', '.join(privilege)
            self.log(NO_RECS % (o.class_.name.lower(), o.id, privilegeType,
                                privilege), type='warning')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
