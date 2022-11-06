'''Functions for sending emails'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import smtplib, socket, time
from email import encoders
from email.header import Header
from email.utils import formatdate
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from appy.database.operators import or_

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
NO_CONFIG  = 'Must send mail but no SMTP server configured.'
NO_SERVER  = 'no mailhost defined'
DISABLED   = 'Mail disabled%s: should send mail from %s to %d recipient(s): %s.'
REPLY_TO   = 'reply to: %s'
MSG_SUBJ   = 'Subject: %s'
MSG_BODY   = 'Body: %s'
MSG_ATTS   = '%d attachment(s): %s.'
MSG_SEND   = 'Sending mail from %s to %s (subject: %s).'
MAIL_R_KO  = 'Could not send mail to some recipients. %s'
MAIL_SENT  = "Mail sent in %.2f''."
MAIL_NSENT = '%s: mail sending failed (%s).'
CONNECT_OK = "Connected to %s in %.2f''."
NO_G_U     = 'Inexistent %s(s) %s.'
NO_REC     = 'No mail recipient for "%s".'
NO_RECS    = 'No recipient for sending mail about %s %s with %s(s) %s.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Config:
    '''Parameters for connecting to a SMTP server'''

    # Currently we don't check the connection to the SMTP server at startup
    testable = False

    def __init__(self, fromName=None, fromEmail='info@appyframework.org',
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
        if self.fromName: return '%s <%s>' % (self.fromName, self.fromEmail)
        return self.fromEmail

    def __repr__(self):
        '''Short string representation of this mail config, for logging and
           debugging purposes.'''
        r = 'mail: %s:%d' % (self.server, self.port)
        if self.login: r += ' (login as %s)' % self.login
        return r

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def logMailSent(r, start, log):
    '''A mail a just been sent. Log its success or failure (depending on p_r)'''
    if not log: return
    if r:
        log(MAIL_R_KO % str(r), type='warning')
    else:
        log(MAIL_SENT % (time.time() - start))

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def sendMail(config, to, subject, body, attachments=None, log=None,
             replyTo=None, split=False):
    '''Sends a mail, via the SMTP server defined in the p_config. Returns True
       if the mail has been successfully sent.'''

    # p_config is an instance of class appy.utils.mail.Config hereabove.

    # This function sends a mail to p_to (a single email recipient or a list of
    # recipients). Every (string) recipient can be an email address or a string
    # of the form "[name] <[email]>".

    # p_attachments must be a list or tuple whose elements can have 2 forms:
    # 1. a tuple (fileName, fileContent): "fileName" is the name of the file
    #    as a string; "fileContent" is the file content, also as a string;
    # 2. an instance of class appy.model.fields.file.FileInfo ;
    # 3. a tuple (fileName, fileInfo), where an instance of class
    #    appy.model.fields.file.FileInfo is in use, but with an alternate file,
    #    specified in the first tuple element.

    # p_log can be a function accepting 2 args:
    # - the message to log (as a string);
    # - the second must be named "type" and will receive string
    #   "info", "warning" or "error".

    # A p_replyTo mail address or recipient can be specified

    # If p_split is False, a single mail will be send to all repicients
    # specified at once in field "To". Else, a distinct mail will be sent to
    # every recipient defined in p_to.

    to = [to] if isinstance(to, str) else to
    if not config:
        if log: log(NO_CONFIG)
        return
    # Just log things if mail is disabled
    fromAddress = config.getFrom()
    replyTo = replyTo or config.replyTo
    if not config.enabled or not config.server:
        msg = '' if config.server else ' (%s)' % NO_SERVER
        if log:
            toLog = DISABLED % (msg, fromAddress, len(to), ', '.join(to))
            if replyTo: toLog += ' (%s).' % (REPLY_TO % replyTo)
            log(toLog)
            log(MSG_SUBJ % subject)
            log(MSG_BODY % body)
        if attachments and log:
            # Every attachment can be a tuple or a FileInfo instance
            fileNames = []
            for attach in attachments:
                if isinstance(attach, (list, tuple)):
                    fileNames.append(attach[0])
                else:
                    fileNames.append(attach.uploadName)
            log(MSG_ATTS % (len(attachments), ', '.join(fileNames)))
        return
    if log: log(MSG_SEND % (fromAddress, ', '.join(to), subject))
    # Create the base MIME message
    body = MIMEText(body, 'plain')
    if attachments:
        msg = MIMEMultipart()
        msg.attach(body)
    else:
        msg = body
    # Add the header values
    msg['Subject'] = Header(subject)
    msg['From'] = fromAddress
    msg['Date'] = formatdate(localtime=True)
    if replyTo: msg.add_header('reply-to', replyTo)
    # Add attachments
    if attachments:
        for attachment in attachments:
            # Every attachment can be of various forms
            if isinstance(attachment, (tuple, list)):
                fileName, theFile = attachment
            else:
                theFile = attachment
                fileName = attachment.uploadName
            if isinstance(theFile, bytes):
                fileContent = theFile
            else: # a FileInfo instance
                with open(theFile.fsPath, 'rb') as f: fileContent = f.read()
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(fileContent)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition',
                            'attachment; filename="%s"' % fileName)
            msg.attach(part)
    # Send the mail(s)
    try:
        start = time.time()
        # Connect to the SMTP server
        smtpServer = smtplib.SMTP(config.server, port=config.port)
        if config.secure:
            smtpServer.ehlo()
            smtpServer.starttls()
        if config.login:
            smtpServer.login(config.login, config.password)
        # Log the time spent while connecting, if we perform a single connection
        # for sending several mails.
        if split and log:
            log(CONNECT_OK % (time.time()-start))
        # Precompute the mail body if a single mail must be sent
        if not split:
            msg['To'] = ', '.join(to)
            body = msg.as_string()
        # Send the mail(s)
        if split:
            for recipient in to:
                start = time.time()
                msg['To'] = recipient
                body = msg.as_string()
                r = smtpServer.sendmail(fromAddress, [recipient], body)
                logMailSent(r, start, log)
        else:
            r = smtpServer.sendmail(fromAddress, to, body)
            logMailSent(r, start, log)
        # Disconnect from the server
        smtpServer.quit()
        return True
    except smtplib.SMTPException as e:
        if log: log(MAIL_NSENT % (config, str(e)), type='error')
    except socket.error as se:
        if log: log(MAIL_NSENT % (config, str(se)), type='error')

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def sendMailIf(config, o, privilege, subject, body, attachments=None,
               privilegeType='permission', excludeExpression='False',
               userMethod=None, log=None, replyTo=None, split=False):
    '''Sends a mail related to this p_o(bject) to any active user having
       p_privilege on it.'''

    # If p_privilegeType...
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # is...         | p_privilege is a (list or tuple of)...
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # "permission"  | permission(s)
    # "role"        | role(s)
    # "group"       | group login(s)
    # "user"        | user login(s)
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # p_excludeExpression will be evaluated on every selected user. Users for
    # which the expression will produce True will not become mail recipients.
    # The expression is evaluated with variable "user" in its context.
    # ~
    # p_userMethod may be the name of a method on class User. If specified,
    # beyond p_privilege checking, a user will receive a mail if this method
    # returns True. p_userMethod must accept p_self as unique arg.
    # ~
    # Determine the set of users to work with
    checkPermissionOrRole = False
    pt = privilegeType
    if pt in ('group', 'user'):
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
        checkPermissionOrRole = True
    # Determine the list of recipients based on active users having p_privilege
    # on p_self.
    recipients = []
    for user in users:
        # Evaluate the "exclude expression"
        if eval(excludeExpression): continue
        # Check if the user has p_privilege on this object (only applicable if
        # the privilege does not represent a group).
        if checkPermissionOrRole:
            hasPrivilege = user.hasPermission if pt == 'permission' \
                                              else user.hasRole
            if isinstance(privilege, str):
                # Check a single permission or role
                if not hasPrivilege(privilege, o): continue
            else:
                # Several permissions or roles are mentioned. Having a single
                # permission or role is sufficient.
                hasOne = False
                for priv in privilege:
                    if hasPrivilege(priv, o):
                        hasOne = True
                        break
                if not hasOne: continue
        # Execute the "user method" when specified
        if userMethod and not getattr(user, userMethod)(o): continue
        # Get the mail recipient for this user
        recipient = user.getMailRecipient()
        if not recipient:
            # Do not add this user: it does not have e-mail. Log this problem
            # only if the user is not special.
            if not user.isSpecial():
                user.log(NO_REC % user.login, type='warning')
            continue
        recipients.append(recipient)
    if recipients:
        sendMail(config, recipients, subject, body, attachments, log=log,
                 replyTo=replyTo)
    elif log:
        if isinstance(privilege, (list, tuple)):
            privilege = ', '.join(privilege)
        log(NO_RECS % (o.class_.name.lower(), o.id, pt, privilege),
                       type='warning')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
