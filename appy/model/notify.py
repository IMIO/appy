#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from DateTime import DateTime
from persistent.list import PersistentList

from .utils import Object
from ..database.operators import or_
from ..utils.string import Variables

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
SP_VARS_KO = 'Notifier::sendIf is wrongly called with split=False and non ' \
             'empty variables. Indeed, variables come into play when sending ' \
             'individual mails.'
IN_ATT_KO  = 'The notifier named "%s" cannot join attachments to notifications.'
NO_G_U     = 'Inexistent %s(s) %s.'
NOTIF_S    = 'Notification about "%s" :: '
NOTIF_NIL  = f'{NOTIF_S}Sent to nobody.'
NOTIF_OK   = f'{NOTIF_S}Sent to %d user·s.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Config:
    '''Configuration about notifications'''

    def __init__(self):
        '''Initialise parameters about user notifications'''
        # The maximum number of notifications one may find in a field
        # User.notifications. If, when a notification is added, this max is
        # reached, the oldest notification is deleted.
        self.maxPerUser = 30

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Notification(Object):
    '''Represents a notification sent by Appy to a user'''

    # Instances of this class are used as rows of data on List field
    # User::notifications.

    @classmethod
    def getEmpty(class_, o):
        '''Gets the text to display when there is no notification yet for a
           user.'''
        return o.translate('user_no_notif')

    @classmethod
    def computeUnread(class_, user):
        '''Compute the number of unread notifications in p_user.notifications'''
        r = 0
        notifs = user.notifications
        if notifs:
            for notif in notifs:
                if not notif.read:
                    r += 1
        return r

    @classmethod
    def createFor(class_, user, notifier):
        '''Adds a notification for that p_user, as prepared by this
           p_notifier.'''
        # Create the Notification object
        subject, body = notifier.getTexts(user)
        notif = Notification(sender=notifier.sender, date=DateTime(),
                             read=False, subject=subject, body=body)
        # Add it among p_users' notifications
        notifs = user.notifications
        if notifs is None:
            notifs = user.notifications = PersistentList()
        notifs.insert(0, notif)
        # Remove the oldest notification, if the maximum number of notifications
        # has been reached.
        if len(notifs) > user.config.notify.maxPerUser:
            notifs.pop()
        # Reindex the number of unread notifications
        user.reindex(fields=('unread',))

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Notifier:
    '''Creates Notification objects within fields User.notifications, and serve
       as base class for other notification methods, like mail sending.'''

    # Does this notifier allow attachments ?
    attachmentsAllowed = False

    # By default, add log at the start of the process
    logInit = True

    # Error messages
    NO_CONFIG = 'Must send a notification, but there is no config in ' \
                'config.notify.'
    NOTIF_INI = 'Generating notification "%s" from "%s"...'

    def __init__(self, config, log=None):
        # The related Config object allowing to customize the notification
        # process.
        self.config = config
        # p_log can be a function accepting 2 args:
        # - the message to log (as a string);
        # - the second must be named "type" and will receive string
        #   "info", "warning" or "error".
        self.logFun = log
        # The count of notifications that will be sent
        self.count = 0

    def init(self, sender, subject, body, attachments, replyTo, split):
        '''Late initialisation, possibly overriden by child classes'''
        self.sender = sender
        self.subject = subject
        self.body = body
        self.attachments = attachments
        self.replyTo = replyTo
        self.split = split
        if self.logInit:
            self.log(self.NOTIF_INI % (subject, sender))

    def checkAttributes(self):
        '''Ensure p_self's attributes are valid'''
        # In non-split mode, variables cannot be used
        if not self.split and self.variables:
            raise Exception(SP_VARS_KO)
        # Check if the presence of attachments is a problem
        if self.attachments and not self.attachmentsAllowed:
            raise Exception(IN_ATT_KO % self.__class__.__name__)

    def configError(self):
        '''Return True if the config is missing'''
        if not self.config:
            self.log(self.NO_CONFIG)
            return True

    def log(self, message, typE='info'):
        '''Logs a message, if a log function has been defined'''
        fun = self.logFun
        if fun:
            fun(message, type=typE)

    def onceWalked(self):
        '''A sub-class may override this to perform some action once all users
           have been walked.'''

    def finalize(self):
        '''A sub-class may override this to perform some final action'''
        # Log the number of notifications having been sent
        count = self.count
        if count == 0:
            text = NOTIF_NIL % self.subject
            typE = 'warning'
        else:
            text = NOTIF_OK % (self.subject, count)
            typE ='info'
        self.log(text, typE)

    def getVariablesObject(self, user):
        '''Returns an object containing values for p_variables as applied to
           this p_user.'''
        r = Object()
        for name in self.variables:
            value = getattr(user, name)
            if callable(value): value = value()
            r[name] = value
        return r

    def getTexts(self, user):
        '''Returns, as a 2-tuple, the notification subject and body, potentially
           patched with p_user-related p_self.variables.'''
        if self.variables:
            # Get the p_user-specific variables in an object
            varS = self.getVariablesObject(user)
            subject = Variables.replace(self.subject, varS)
            body = Variables.replace(self.body, varS)
        else:
            subject = self.subject
            body = self.body
        return subject, body

    def collectUsers(self):
        '''Collect users having this p_privilege on this p_o(bject)'''
        # If p_privilegeType is "role" or "permission", all active users are
        # returned; they will be filtered by the called method.
        #
        # To be more precise, the return value is a tuple ([users], s_checkPR),
        # where s_checkPR indicates if the called method must further filter
        # users according to a *p*ermission (s_checkPR holds 'permission') or
        # *r*ole (s_checkPR holds 'role').
        o = self.o
        pt = self.privilegeType
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

    def walkUsers(self, users, checkPR):
        '''Walk all p_users and send a notification to each appropriate one'''
        checkRole = checkPR == 'role'
        # Unwrap useful attributes
        o = self.o
        priv = self.privilege
        privType = self.privilegeType
        userMethod = self.userMethod
        exclude = self.excludeExpression
        split = self.split
        # Walk p_users
        for user in users:
            # Check if the user has this p_self.privilege on p_self.o
            if checkPR:
                has = user.hasRole if checkRole else user.hasPermission
                if isinstance(priv, str):
                    # Check a single permission or role
                    if not has(priv, o): continue
                else:
                    # Several permissions or roles are mentioned. Having a
                    # single permission or role is sufficient.
                    hasOne = False
                    for pri in priv:
                        if has(pri, o):
                            hasOne = True
                            break
                    if not hasOne: continue
            # Evaluate the v_exclude expression
            if exclude and eval(exclude): continue
            # Execute the v_userMethod when specified
            if userMethod and not getattr(user, userMethod)(o): continue
            # A notification must (a priori) be sent to that v_user
            self.count += self.sendOne(user)
        # Perform some final step once all users have been walked
        self.onceWalked()

    def sendOne(self, user):
        '''Creates a notification for that p_user and return the number of
           created notifications: 0 or 1.'''
        # Indeed, for some special users, no notification will occur
        if user.isSpecial(includeAdmin=False):
            r = 0
        else:
            # Create the notification
            subject, body = self.getTexts(user)
            Notification.createFor(user, self)
            notif = Notification(sender=self.sender, date=DateTime(), )
            r = 1
        return r

    def sendIf(self, o, privilege, subject, body, attachments=None,
               privilegeType='permission', excludeExpression=None,
               userMethod=None, sender=None, replyTo=None, split=True,
               variables=None):

        '''Sends a notification related to this p_o(bject) to any active user
           having this p_privilege on it.'''

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

        # p_excludeExpression, if passed, will be evaluated on every selected
        # user. Users for which the expression will produce True will not be
        # notified. The expression is evaluated with variables "user" and
        # "o" in its context. Use this with care, as it makes use of the eval
        # function, being not performant nor secure.

        # p_userMethod may be the name of a method on class User. If specified,
        # beyond p_privilege checking, a user will be notified if this method
        # returns True. p_userMethod must accept p_o as unique arg.

        # p_subject and p_body must be strings containing the mail subject and
        # body. If p_variables are passed, p_subject and/or p_body may contain
        # variable parts (more explanations below, when describing p_variables).

        # p_attachments refer to mail attachments. It may not be possible to
        # join such attachments to any type of notification. For example,
        # internal notifications can't be flanked by attachments, while email
        # notification can.

        # The p_sender is a string that represents the person or group that is
        # identified as the notification sender. It can be the software in
        # itself (via its name, ie, o.translate('app_name_raw')), or the name of
        # a group or person in the name of which you want the notification to be
        # sent. Some notifiers may prevent you to define such a sender. This is
        # the case for the mail notifier, that will retrieve the sender from the
        # mail config.

        # p_replyTo, only used in the context of a mail notifier, allows to
        # define an email address that wil be used as recipient if the user
        # responds to the received mail.

        # In the vast majority of cases, individual notifications are sent (one
        # per user). The notification is "splitted" in several notifications,
        # one per user (p_split is True). Some notifiers, like the mail
        # notifier, can nevertheless decide to group notificatios (ie, send a
        # single mail with everyboby in Bcc). If that is the case, set p_split
        # to False. Note that, in that case, p_variables (see below) can't be
        # used.

        # p_variables, if passed, must be a list or tuple of attribute or method
        # names, that must be defined on the User object corresponding to each
        # recipient. In this case, p_subject and p_body are supposed to contain
        # variables surrounded by pipes, like |attr1| or |method1|. When sending
        # the notification to each recipient, variables in p_subject and p_body
        # will be replaced by the corresponding values as found on the User
        # object corresponding to the recipient (in the example, user.attr1 or
        # user.method1()). If the name corresponds to a method, it will be
        # called without any arg.

        # Ensure everything is correctly configured
        if self.configError(): return

        # Late-initialise p_self
        self.o = o
        self.privilege = privilege
        self.privilegeType = privilegeType
        self.excludeExpression = excludeExpression
        self.userMethod = userMethod
        self.variables = variables
        self.init(sender, subject, body, attachments, replyTo, split)

        # Check attributes' coherence
        self.checkAttributes()

        # Collect v_users having this p_privilege on this p_o(bject)
        users, checkPR = self.collectUsers()

        # Walk p_users, sending a notification to relevant users
        self.walkUsers(users, checkPR)

        # Perform potential final steps
        self.finalize()
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
