#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy import Config
from appy.model.base import Base
from appy.model.user import User
from appy.model.fields import Show
from appy.ui.layout import Layouts
from appy.model.fields.ref import Ref
from appy.model.fields.string import String
from appy.model.workflow import standard as workflows
from appy.model.fields.select import Select, Selection
from appy.model.fields.group import Group as FieldGroup

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Group(Base):
    '''Base class representing a group'''

    workflow = workflows.Owner

    m = {'group': FieldGroup('main', style='grid', hasLabel=False),
         'width': 25, 'indexed': True, 'layouts': Layouts.g, 'label': 'Group'}

    # CSS class to apply to every group title in a list of groups
    styles = {'title': 'titlet'}

    @staticmethod
    def update(class_):
        title = class_.fields['title']
        title.group = Group.m['group']
        title.layouts = Layouts.g

    def showLogin(self):
        '''When must we show the login field ?'''
        return 'edit' if self.isTemp() else Show.TR

    def showGroups(self):
        '''Only the admin can view or edit roles'''
        return self.user.hasRole('Manager')

    def validateLogin(self, login):
        '''Is this p_login valid ?'''
        return True

    login = String(multiplicity=(1,1), show=showLogin,
                   validator=validateLogin, **m)

    # Field allowing to determine which roles are granted to this group
    roles = Select(validator=Selection(lambda o: o.model.getGrantableRoles(o)),
                   render='checkbox', multiplicity=(0,None), **m)

    users = Ref(User, multiplicity=(0,None), add=False, link='popup',
      height=15, back=Ref(attribute='groups', show=User.showRoles,
                          multiplicity=(0,None), label='User'),
      showHeaders=True, shownInfo=('title', 'login', 'state*100px|'),
      actionsDisplay='inline', label='Group', group=m['group'])

    def getMailRecipients(self):
        '''Gets the list of mail recipients for every group member'''
        r = []
        for user in self.users:
            recipient = user.getMailRecipient()
            if recipient:
                r.append(recipient)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
