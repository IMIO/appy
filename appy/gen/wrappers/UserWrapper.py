# ------------------------------------------------------------------------------
from appy.px import Px
from appy.fields.string import String
from appy.gen import WorkflowOwner, Layouts, Show
from appy.gen.wrappers import AbstractWrapper
from appy.gen import utils as gutils
from appy.shared import utils as sutils

# Messages ---------------------------------------------------------------------
SSO_NO_PASSWORD = 'No password is stored for a SSO user.'
U_NO_ACL        = 'User "%s" has no corresponding Zope user.'
U_DELETED       = 'User "%s" deleted.'
U_NO_ZOPE       = 'ZODB user %s has no Zope user.'''

# ------------------------------------------------------------------------------
class UserWrapper(AbstractWrapper):
    workflow = WorkflowOwner
    # Users that are automatically logged in
    noLoginUsers = ('system', 'anon')
    specialUsers = noLoginUsers + ('admin',)
    layouts = Layouts.Page.summary

    # Display, in the user strip, links to the User instance of the logged user
    pxUserLink = Px('''
     <span class="userStripText">
      <a if="cfg.userLink" href=":user.url"><img src=":url('user')"/>
       <span style="padding: 0 3px">:user.getTitle()</span></a>
      <x if="not cfg.userLink">:user.getTitle()</x>
      <x var="ctx=cfg.authContext" if="ctx">:ctx.pxLogged</x>
     </span>''')

    def isSpecial(self, includeAdmin=True):
        '''Is this user a Appy-predefined user ?'''
        if includeAdmin:
            return self.login in self.specialUsers
        else:
            return self.login in self.noLoginUsers

    def isAnon(self):
        '''Is the logged user anonymous ?'''
        return self.login == 'anon'

    def getTitle(self, normalized=False, useName=True, nameFirst=False,
                 nameTransform=None, firstNameTransform=None):
        '''Returns a nice name for this user, based on available information:
           "first name"/"name" (if p_useName is True) or title or login. If
           p_normalized is True, special chars (like accents) are converted to
           ascii chars. When p_useName is True, if p_nameFirst is True, the
           result will be "name" / "first name", else it will be
           "first name" / "name".'''
        # A specified transform ("upper", "capitalize", etc) can be specified in
        # p_nameTransform and/or p_firstNameTransform.
        login = self.login
        res = None
        if useName:
            firstName = self.firstName
            name = self.name
            if firstName and name:
                # Apply a transform if requested
                if nameTransform: exec 'name = name.%s()' % nameTransform
                if firstNameTransform:
                    exec 'firstName = firstName.%s()' % firstNameTransform
                # Concatenate first and last names in the right order
                if nameFirst: res = '%s %s' % (name, firstName)
                else: res = '%s %s' % (firstName, name)
        if not res: res = self.title or login
        if not normalized: return res
        return sutils.normalizeString(res)

    def getFirstNameInitial(self, suffix='.', sep='-'):
        '''Gets the first name initial. Take care of composed first names.'''
        r = self.firstName
        if not r: return '?'
        # Work with unicode
        if isinstance(r, str): r = r.decode('utf-8')        
        if '-' in r:
            a, b = r.split('-', 1)
            r = u'%s%s%s%s%s' % (a[0], suffix, sep, b[0], suffix)
        else:
            r = u'%s%s' % (r[0], suffix)
        return r.encode('utf-8')

    def showLogin(self):
        '''When must we show the login field?'''
        if self.o.isTemporary(): return 'edit'
        # The manager has the possibility to change the login itself (local
        # users only).
        if self.user.has_role('Manager') and (self.source == 'zodb'):
            return True
        return Show.E_

    def showName(self):
        '''Name and first name, by default, can not be edited for non-local
           users.'''
        if (self.source != 'zodb'): return Show.E_
        return True

    def showEmail(self):
        '''In most cases, email is the login. Show the field only if it is not
           the case.'''
        # Is this user local ?
        isLocal = self.source == 'zodb'
        # Show the field nevertheless if it is not empty
        if isLocal and not self.isEmpty('email'): return True
        # Hide it if the login is an email
        login = self.login
        if login and String.EMAIL.match(login): return
        # Display the email (read-only if from an external source)
        if not isLocal: return Show.E_
        return True

    def showRoles(self):
        '''Global roles are not visible or editable under all circumstances'''
        # Local users can't be granted global roles
        if self.container != self.tool: return
        # Only a Manager is allowed to grant global roles
        user = self.user
        if user.hasRole('Manager'): return True
        # The user itself, owner of himself, can consult his roles
        if user.hasRole('Owner', self): return Show.E_

    def showResetPassword(self):
        '''Action "reset password" is available to anyone having write access to
           the user, excepted the user himself.'''
        if (self.source == 'zodb') and self.o.mayEdit() and \
           (self.user != self) and not self.isSpecial(includeAdmin=False):
            return 'buttons'

    def validateLogin(self, login):
        '''Is this p_login valid ?'''
        # 2 cases: (1) The user is being created and has no login yet, or
        #          (2) The user is being edited and has already a login, that
        #              can potentially be changed.
        if not self.login or (login != self.login):
            # A new p_login is requested. Check if it is valid and free.
            # Some logins are not allowed.
            if login in self.specialUsers:
                return self.translate('login_reserved')
            # Check that no user or group already uses this login.
            if self.count('User', noSecurity=True, login=login) or \
               self.count('Group', noSecurity=True, login=login):
                return self.translate('login_in_use')
        return True

    def validatePassword(self, password):
        '''Is this p_password valid?'''
        # Password must be at least 8 chars length
        if len(password) < 8:
            return self.translate('password_too_short', mapping={'nb': 8})
        # Ensure the password is not the same as the currently stored password
        # for this user, if any.
        zopeUser = self.getZopeUser()
        if zopeUser:
            from AccessControl.AuthEncoding import pw_validate
            if pw_validate(zopeUser.__, password):
                return self.translate('same_password')
        return True

    def showPassword12(self):
        '''Fields "password1" and "password2", used only for modifying a
           password on an existing user (on specific page "passwords"), must be
           shown only for the user that can modify his password.'''
        # On creation, fields "password3" and "password4" are used
        if self.o.isTemporary(): return
        # When the user itself (we don't check role Owner because a Manager can
        # also own a User instance) wants to edit information about himself.
        if (self.user.login == self.login) and (self.source == 'zodb'):
            return 'edit'

    def showPassword34(self):
        '''Fields "password3" and "password4", used only on the main page for
           entering a password when creating a new user, must be shown only when
           the object is temporary.'''
        if self.o.isTemporary(): return 'edit'

    def showCancel12(self):
        '''Do not show the "cancel" button on page "passwords" if the user is
           forced to change its password.'''
        return not self.changePasswordAtNextLogin

    def encryptPassword(self, clearPassword):
        '''Returns p_clearPassword, encrypted'''
        return self.o.getTool().acl_users._encryptPassword(clearPassword)

    def setPassword(self, newPassword=None, log=True, maxLength=9):
        '''Sets a p_newPassword for self. If p_newPassword is not given, we
           generate one (of p_maxLength chars). This method returns the
           generated password (or simply p_newPassword if no generation
           occurred).'''
        if newPassword is not None:
            msgPart = 'changed'
        else:
            # Take any password field for generating a new password
            fp2 = self.getField('password2')
            newPassword = fp2.generatePassword(maxLength=maxLength)
            msgPart = 'generated'
        login = self.login
        zopeUser = self.getZopeUser()
        tool = self.tool.o
        zopeUser.__ = self.encryptPassword(newPassword)
        req = getattr(tool, 'REQUEST', None)
        if req and hasattr(req, 'userLogin') and (req.userLogin == login):
            # The user for which we change the password is the currently logged
            # user. So update the authentication cookie, too.
            ctx = getattr(req, 'authContext', None)
            gutils.writeCookie(login, newPassword, ctx, self.request)
        if log:
            self.log('password %s for %s.' % (msgPart, login))
        return newPassword

    def doResetPassword(self, noSecurity=False):
        '''Triggered from the ui, this method defines a new, automatically
           generated password for this user and returns it in ui.'''
        if not noSecurity and not self.user.allows('write'):
            self.raiseUnauthorized()
        password = self.setPassword()
        self.changePasswordAtNextLogin = True
        self.say('New password for this user is %s.' % password)

    def setEncryptedPassword(self, encryptedPassword):
        '''Sets p_encryptedPassword for this user. m_setPassword above starts
           for a clear (given or generated) password. This one simply sets an
           already encrypted password for this user.'''
        self.getZopeUser().__ = encryptedPassword

    def getEncryptedPassword(self):
        '''Gets the encrypted password for this user'''
        if self.source == 'sso': raise Exception(SSO_NO_PASSWORD)
        zuser = self.getZopeUser()
        if zuser is None:
            self.log(U_NO_ZOPE % self.login, type='error')
            return
        return zuser._getPassword()

    def showEncryptedPassword(self):
        '''Allow to show encrypted password to admins only, via the xml
           layout.'''
        if self.user.hasRole('Manager') and (self.source != 'sso'): return 'xml'

    def checkPassword(self, clearPassword):
        '''Returns True if p_clearPassword is the correct password for this
           user.'''
        encryptedPassword = self.getZopeUser()._getPassword()
        from AccessControl.AuthEncoding import pw_validate
        return pw_validate(encryptedPassword, clearPassword)

    def getMailRecipient(self):
        '''Returns, for this user, the "recipient string" (first name, name,
           email) as can be used for sending an email.'''
        r = self.email or self.login
        # Ensure this is really an email
        if not String.EMAIL.match(r): return
        return '%s <%s>' % (self.getTitle(), r)

    def setLogin(self, oldLogin, newLogin, reindex=True):
        '''Changes the login of this user from p_oldLogin to p_newLogin'''
        self.login = newLogin
        # Update the corresponding Zope-level user
        aclUsers = self.o.acl_users
        zopeUser = aclUsers.data[oldLogin]
        zopeUser.name = newLogin
        del aclUsers.data[oldLogin]
        aclUsers.data[newLogin] = zopeUser
        # Update the email if the email corresponds to the login
        email = self.email
        if email == oldLogin:
            self.email = newLogin
        # Update the title
        self.updateTitle()
        # Browse all objects of the database and update potential local roles
        # that referred to the old login.
        context = {'nb': 0, 'total': 0, 'old': oldLogin, 'new': newLogin}
        for className in self.tool.o.getAllClassNames():
            self.compute(className, context=context, noSecurity=True,
                         expression="ctx['nb'] += obj.o.applyUserIdChange(" \
                                   "ctx['old'], ctx['new']); ctx['total'] += 1")
        self.log('login "%s" renamed to "%s".' % (oldLogin, newLogin))
        self.log('login change: local roles and/or history updated in %d/%d ' \
                 'object(s).' % (context['nb'], context['total']))
        # Reindex p_self, excepted if p_reindex is False
        if reindex: self.reindex()

    def getGrantableRoles(self):
        '''Returns the list of roles that the admin can grant to a user'''
        res = []
        for role in self.o.getProductConfig().grantableRoles:
            res.append( (role, self.translate('role_%s' % role)) )
        return res

    def validate(self, new, errors):
        '''Inter-field validation'''
        self.o._oldLogin = None
        # Check that passwords match, either on page "passwords" (passwords 1
        # and 2) or on page "main" (passwords 3 and 4).
        for i in (1, 3):
            passwordA = 'password%d' % i
            passwordB = 'password%d' % (i + 1)
            if hasattr(new, passwordA) and \
               (getattr(new, passwordA) != getattr(new, passwordB)):
                msg = self.translate('passwords_mismatch')
                setattr(errors, passwordA, msg)
                setattr(errors, passwordB, msg)
            # Remember the previous login
            if self.login: self.o._oldLogin = self.login
        return self._callCustom('validate', new, errors)

    def updateTitle(self):
        '''Sets a title for this user'''
        self.title = self.getTitle(nameFirst=True)

    def ensureAdminIsManager(self):
        '''User "admin" must always have role "Manager"'''
        if self.o.id == 'admin':
            roles = self.roles
            if 'Manager' not in roles:
                if not roles: roles = ['Manager']
                else: roles.append('Manager')
                self.roles = roles

    def getSupTitle(self, nav):
        '''Display a specific icon if the user is a local copy of an external
           (ldap/sso) user.'''
        res = self._callCustom('getSupTitle', nav) or ''
        if self.source == 'zodb': return res
        # For external users note the source and last synchronization date in
        # the icon's title.
        tool = self.o.getTool()
        if self.isEmpty('syncDate'):
            suffix = ''
        else:
            suffix = ' - sync@ %s' % tool.formatDate(self.syncDate)
        return '<img src="%s/ui/external.png" title="%s%s" class="help"/>%s' % \
               (tool.getSiteUrl(), self.source.upper(), suffix, res)

    def getZopeUser(self):
        '''Gets the Zope user corresponding to this user'''
        if self.source == 'zodb':
            return self.o.acl_users.data.get(self.login, None)
        return self.o._zopeUser

    def getLogins(self, groupsOnly=False):
        '''Gets all the logins that can "match" this user: it own login
           (excepted if p_groupsOnly is True) and the logins of all the groups
           he belongs to.'''
        # Try first to get those logins from a cache on the request, if this
        # user corresponds to the logged user.
        rq = self.request
        if hasattr(rq, 'userLogins') and (rq.userLogin == self.login):
            return rq.userLogins
        # Compute it
        res = [group.login for group in self.groups]
        if not groupsOnly: res.append(self.login)
        return res

    def getRoles(self):
        '''This method returns all the global roles for this user, not simply
           self.roles, but also "ungrantable roles" (like Anonymous or
           Authenticated) and roles inherited from group membership.'''
        # Try first to get those roles from a cache on the request, if this user
        # corresponds to the logged user.
        rq = self.request
        if hasattr(rq, 'userRoles') and (rq.userLogin == self.login):
            return rq.userRoles
        # Compute it
        res = list(self.roles)
        # Add ungrantable roles
        res.append(self.isAnon() and 'Anonymous' or 'Authenticated')
        # Add group global roles
        for group in self.groups:
            for role in group.roles:
                if role not in res: res.append(role)
        return res

    def getRolesFor(self, obj):
        '''Gets the roles the user has in the context of p_obj: its global roles
           + its roles which are local to p_obj.'''
        obj = obj.o
        # Start with user global roles
        res = self.getRoles()
        # Add local roles, granted to the user directly or to one of its groups
        localRoles = obj.appy().localRoles
        if not localRoles: return res
        # Gets the logins of this user and all its groups. Create a new list.
        # Indeed, "res" can be the actual list of global roles as cached in the
        # request or the currently logged user.
        res = list(res)
        logins = self.getLogins()
        for login, roles in localRoles.iteritems():
            # Ignore logins not corresponding to this user
            if login not in logins: continue
            for role in roles:
                if role not in res: res.append(role)
        return res

    def addRole(self, role):
        '''Adds p_role to the user's global roles'''
        roles = self.roles
        if role in roles: return
        roles = list(roles)
        roles.append(role)
        self.roles = roles
        self.getZopeUser().roles = roles

    def delRole(self, role):
        '''Remove p_role from the user's global roles'''
        roles = self.roles
        if role not in roles: return
        roles = list(roles)
        roles.remove(role)
        self.roles = roles
        self.getZopeUser().roles = roles

    def hasRole(self, role, obj=None):
        '''Has the logged user some p_role? If p_obj is None, check if the user
           has p_role globally; else, check if he has this p_role in the context
           of p_obj.

           p_role can also be a list/tuple of roles. In this case, the method
           returns True if the user has at least one of the listed roles.'''
        # Try first with the user's global roles, excepted if p_obj is in
        # "local" mode.
        noo = obj is None
        if noo or not obj.o.getLocalRolesOnly():
            r = sutils.stringIsAmong(role, self.getRoles())
            if noo or r: return r
        # Check now p_obj's local roles
        localRoles = obj.appy().localRoles
        if not localRoles: return
        logins = self.getLogins()
        for login, roles in localRoles.iteritems():
            if (login in logins) and sutils.stringIsAmong(role, roles):
                return True
    has_role = hasRole  # "has_role" will be removed in Appy 1.0

    def hasPermission(self, permission, obj):
        '''Has the logged user p_permission on p_obj ?'''
        obj = obj.o
        # What are the roles which are granted p_permission on p_obj?
        allowedRoles = obj.getRolesFor(permission)
        if not allowedRoles: return
        # Grant access based on global user roles (that include ungrantable
        # roles like Authenticated or Anonymous), excepted if p_obj is in
        # "local" mode.
        if not obj.getLocalRolesOnly():
            for role in self.getRoles():
                if role in allowedRoles: return True
        # Grant access based on local roles
        localRoles = obj.appy().localRoles
        if not localRoles: return
        # Gets the logins of this user and all its groups
        userLogins = self.getLogins()
        for login, roles in localRoles.iteritems():
            # Ignore logins not corresponding to this user
            if login not in userLogins: continue
            for role in roles:
                if role in allowedRoles: return True
    has_permission = hasPermission #"has_permission" will be removed in Appy 1.0

    def onEdit(self, created):
        '''Triggered when a User is created or updated'''
        login = self.login
        # Refresh the title, computed from other fields
        self.updateTitle()
        # Is it a local User or a LDAP User?
        isLocal = self.source == 'zodb'
        # Ensure correctness of some infos about this user
        if isLocal: self.ensureAdminIsManager()
        if created:
            # Create the corresponding Zope user
            from AccessControl.User import User as ZopeUser
            password = self.encryptPassword(self.password3)
            zopeUser = ZopeUser(login, password, self.roles, ())
            # Add it in acl_users if it is a local user
            if isLocal:
                self.o.acl_users.data[login] = zopeUser
                # If user creation was made by an admin, force the user to
                # change its password at its first login.
                if not self.isSpecial() and self.user.hasRole('Manager'):
                    self.changePasswordAtNextLogin = True
            # Add it in self.o._zopeUser if it is a LDAP or SSO user
            else: self.o._zopeUser = zopeUser
            # Remove our own password copies
            self.password3 = self.password4 = ''
        else:
            # Update the login itself if the user has changed it
            if hasattr(self.o.aq_base, '_oldLogin'):
                oldLogin = self.o._oldLogin
                if oldLogin and (oldLogin != login):
                    self.setLogin(oldLogin, login, reindex=False)
                del self.o._oldLogin
            # Update roles at the Zope level
            zopeUser = self.getZopeUser()
            zopeUser.roles = self.roles
            # Update the password if the user has entered new ones
            rq = self.request
            if rq.get('page', 'main') == 'passwords':
                self.setPassword(rq['password1'])
                self.password1 = self.password2 = ''
                self.changePasswordAtNextLogin = False
        # "self" must be owned by its Zope user
        self.addLocalRole(login, 'Owner')
        # If the user was created by anon|system, anon|system can't stay Owner
        self.deleteLocalRole(('anon', 'system'))
        return self._callCustom('onEdit', created)

    def convertTo(self, source):
        '''Convert a user as if, now, he would be of p_source, that is different
           from self.source.'''
        # p_self.source and p_source must be different
        origSource = self.source
        if origSource == source: return
        zopeUser = self.getZopeUser()
        # Perform the conversion
        if origSource == 'zodb':
            # Convert a local user to an external user.
            # Transfer the Zope user from acl_users to p_self.
            del self.o.acl_users.data[self.login]
            self.o._zopeUser = zopeUser
        else:
            # The user is external
            if source == 'zodb':
                # Convert an external user to a local user.
                # Transfer the Zope user from p_self to acl_users.
                self.o.acl_users.data[self.login] = zopeUser
                del self.o._zopeUser
        # Update p_self's parameters
        self.source = source
        from DateTime import DateTime
        self.syncDate = DateTime()
        # This flag is not relevant for external users
        if self.source != 'zodb':
            self.changePasswordAtNextLogin = False
        # Log the operation
        self.log('user %s converted from %s to %s.' % \
                 (self.login, origSource, source))

    def mayEdit(self):
        '''No one can edit users "system" and "anon"'''
        if self.o.id in ('anon', 'system'): return
        # Call custom "mayEdit" when present
        custom = self._getCustomMethod('mayEdit')
        if custom: return self._callCustom('mayEdit')
        return True

    def onDelete(self):
        '''Before deleting myself, I must delete the corresponding Zope user
           (for local users only).'''
        if self.source == 'zodb':
            try:
                del self.o.acl_users.data[self.login]
            except KeyError:
                self.log(U_NO_ACL % self.login, type='warning')
        self.log(U_DELETED % self.login)
        # Call a custom "onDelete" if any
        return self._callCustom('onDelete')

    def mayDelete(self):
        '''No one can delete special users'''
        if self.isSpecial(): return
        # Call custom "mayDelete" when present
        custom = self._getCustomMethod('mayDelete')
        if custom: return self._callCustom('mayDelete')
        return True
# ------------------------------------------------------------------------------
