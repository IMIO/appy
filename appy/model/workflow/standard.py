'''Standard workflows'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.model.workflow import *
from appy.model.workflow.state import State
from appy.model.workflow.transition import Transition

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# WARNING | To be activated, any workflow defined here must be listed in
#         | appy.model.Model.baseWorkflows.
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class Anonymous:
    '''One-state workflow allowing anyone to consult and Manager + Owner(s) to
       edit.'''

    o = 'Owner'
    ma = 'Manager'
    pub = 'Publisher'

    editors = ma, o, pub
    everyone = 'Anonymous', 'Authenticated'

    active = State({r:everyone, w:editors, d:editors}, initial=True)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Authenticated:
    '''One-state workflow allowing authenticated users to consult and Manager
       to edit.'''

    o = 'Owner'
    ma = 'Manager'

    authenticated = ma, 'Authenticated'

    active = State({r:authenticated, w:(ma, o), d:(ma, o)}, initial=True)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Owner:
    '''Workflow granting read anw write permissions to owners, managers and
       publishers.'''

    # Roles in use
    o = 'Owner'
    ma = 'Manager'
    pub = 'Publisher'
    editors = o, ma, pub

    # States
    active = State({r:editors, w:editors, d:ma}, initial=True)
    inactive = State({r:editors, w:ma, d:ma})

    # Transitions
    tp = {'condition': ma, 'confirm': True}
    deactivate = Transition( (active, inactive), **tp)
    reactivate = Transition( (inactive, active), **tp)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class User:
    '''Workflow for the User class'''

    # Errors
    AD_D_ERR = 'Cannot deactivate admin.'

    # Roles in use
    o = 'Owner'
    ma = 'Manager'
    pub = 'Publisher'
    editors = o, ma
    everyone = o, ma, pub

    # States
    active = State({r:everyone, w:editors, d:ma}, initial=True)
    inactive = State({r:everyone, w:ma, d:ma})

    # Transitions

    tp = {'condition': ma, 'confirm': True}

    def doDeactivate(self, user):
        '''Prevent user "admin" from being deactivated'''
        if user.login == 'admin':
            raise WorkflowException(User.AD_D_ERR)

    deactivate = Transition( (active, inactive), action=doDeactivate, **tp)
    reactivate = Transition( (inactive, active), **tp)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class TooPermissive:
    '''If objects of class B must follow the security of their container object,
       of class A, define, on class B, this too permissive workflow. Actual
       security needs to be implemented, on class B, by object methods mayView,
       mayEdit and mayDelete that return what is allowed according to the
       container workflow (A).'''

    # As an example, consult standard class appy/model/document.py that uses
    # this worflow.

    everyone = 'Anonymous', 'Authenticated'
    created = State({r:everyone, w:everyone, d:everyone}, initial=True)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
