# ------------------------------------------------------------------------------
from appy.gen import *
Grp = Group # Avoid name clashes with the Group class below and appy.gen.Group
Pge = Page # Avoid name clashes with the Page class below and appy.gen.Page
from appy.fields.calendar import Calendar
from appy.gen.wrappers import AbstractWrapper
from appy.gen.wrappers.ToolWrapper import ToolWrapper as WTool
from appy.gen.wrappers.UserWrapper import UserWrapper as WUser
from appy.gen.wrappers.GroupWrapper import GroupWrapper as WGroup
from appy.gen.wrappers.TranslationWrapper import TranslationWrapper as WT
from appy.gen.wrappers.PageWrapper import PageWrapper as WPage
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
# Layouts for Translation fields
tfw = {"edit":"f","view":"f","search":"f"}
<!imports!>

<!User!>
<!Group!>
<!Translation!>
<!Page!>
autoref(Page, Page.pages)

<!Tool!>
<!wrappers!>
# ------------------------------------------------------------------------------
