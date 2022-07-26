# ------------------------------------------------------------------------------
from appy.gen import Show, Pod, Table
from appy.shared.xml_parser import Escape
from appy.gen.wrappers import AbstractWrapper

# ------------------------------------------------------------------------------
EXPRESSION_ERROR = 'Page "%s" (%s): error while evaluating page expression ' \
                   '"%s" (%s)'

# ------------------------------------------------------------------------------
class PageWrapper(AbstractWrapper):

    def getSubBreadCrumb(self):
        '''Display an icon for downloading this page (and sub-pages if any) as a
           POD.'''
        if not self.isEmpty('parent'): return
        return self.getField('doc').doRender('view', self)

    def showSubPages(self):
        '''For non-writers, show sub-pages only if present'''
        if self.allows('write'): return True
        if not self.isEmpty('pages'): return 'view'

    def validate(self, new, errors):
        '''Inter-field validation.'''
        return self._callCustom('validate', new, errors)

    def showPortlet(self):
        '''Do not show the portlet for a page'''
        return

    def showExpression(self):
        '''Show the expression to managers only'''
        # Do not show it on "view" if empty
        if self.isEmpty('expression'): return Show.V_
        return self.user.hasRole('Manager')

    def showEditors(self):
        '''Show field "editors" only to Managers'''
        return self.user.hasRole('Manager')

    def mayView(self):
        '''In addition to the workflow, evaluating p_self.expression, if
           defined, determines p_self's visibility.'''
        expression = self.expression
        if not expression: return True
        user = self.user
        try:
            return eval(expression)
        except Exception, err:
            message = EXPRESSION_ERROR % (self.title, self.id,
                                          expression, str(err))
            self.log(message, type='error')
            return True

    def linkEditor(self, user, sub=True):
        '''Set this new editor as p_self's owner'''
        self.addLocalRole(user.login, 'Owner')
        if sub:
            for page in self.pages:
                page.linkEditor(user)

    def unlinkEditor(self, user, sub=True):
        '''ungrant to p_user the possibility to edit p_self'''
        if user.login != self.o.creator:
            self.deleteLocalRole(user.login, 'Owner')
        if sub:
            for page in self.pages:
                page.unlinkEditor(user)

    def setEditors(self, editors=None):
        '''Set editors and related local roles on this page (p_self) and
           sub-pages.'''
        # Set p_editors if passed
        if editors is not None:
            self.editors = editors
        else:
            editors = self.editors
        # Set local roles
        self.resetLocalRoles()
        for user in editors:
            self.linkEditor(user, sub=False)
        # Update sub-pages, too
        for page in self.pages:
            page.setEditors(editors)

    def onEdit(self, created):
        # Set local roles depending on page creator and editors
        self.setEditors()
        return self._callCustom('onEdit', created)

    def getMergedContent(self, level=1):
        '''Returns a chunk of XHTML code containing p_self's info (title and
           content) and, recursively, info about all its sub-pages.'''
        # Add p_self's title
        title = self.getValue('title', formatted='shown')
        r = ['<h%d>%s</h%d>' % (level, Escape.xhtml(title), level)]
        # Add p_self's content
        if not self.isEmpty('content'):
            r.append(self.getValue('content', formatted='shown'))
        # Add sub-pages
        if not self.isEmpty('pages'):
            for page in self.pages:
                r.append(page.getMergedContent(level=level+1))
        return ''.join(r)
# ------------------------------------------------------------------------------
