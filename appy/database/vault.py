'''The vault of IDs is a reservoir of database iids used as an alternative to
   incremental iids, in order to reduce conflict errors due to concurrent
   database object creations.'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import random

from BTrees.IIBTree import IITreeSet

from appy.px import Px
from appy.utils import br

# Appy uses incremental iids (*i*nteger *id*s) to identify objects to store in
# its database. This is a simple and easily understandable technique. Moreover,
# an object's iid gives an idea of when it has been created, compared to other
# database objects.

# That being said, on sites having a high rate of concurrent object creations,
# it can lead to conflict errors: concurrent transactions reserving the same
# iid, based on the last incremental iid.

# The vault has been created in order to overcome this problem. It consists in a
# reservoir of free iids that can be used to get an iid for creating a new
# object, instead of using the last incremental iid + 1.

# Several strategies exist for choosing what iids to store in the vault. Consult
# class Config below for more details.

# In the remainder of this file, the last incremental iid as defined in a Appy
# database will be named root.lastId, v_root being the root database object, and
# v_root.lastId being the attribute storing this last incremental iid.

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Config:
    '''Vault configuration'''

    # Possible strategies for "forward iids" = iids being stored in the vault
    # and being greater than root.lastId. Read the Config constructor prior to
    # reading this.

    FWD_NO  = 0 # No iid being greater than root.lastId is stored in the vault
    FWD_MOD = 1 # An iid for which iid % config.forwardMod = 0 will end up in
                # the vault. Here is an example. Suppose config.forwardMod is 2 
                # and v_root.lastId is 100.
                # - iid 101: 101 % 2 = 1 : will not end up in the vault
                # - iid 102: 102 % 2 = 0 : will end up in the vault

    def __init__(self):
        # iids being lower than root.lastId can be found. They correspond to
        # deleted objects: first-class objects or transient ones
        # having been created in the context of options to an Action field. Must
        # these iids be retrieved, stored in the vault and recycled for creating
        # new objects ?
        self.backward = False
        # Beyond "backward" iids, the vault may also store "forward" iids, being
        # greater than the last incremental iid. The following attributes
        # determine which "future" iids to reserve and store in the vault.
        self.forward = self.FWD_NO
        # When the FWD_MOD strategy is used (see constant documentation
        # hereabove), a subset of the forward iids will be reserved and stored
        # in the vault. Depending on p_self.forwardMod, this subset will
        # represent 1/2 of all future iids (forwardMod=2), 1/3 (forwardMod=3),
        # 1/4, etc.
        self.forwardMod = 4
        # All future iids will not be stored in the vault at once, until we
        # reach the last storable iid. On a regular basis, more iids will be
        # stored in the vault. The following attribute determines what quantity
        # of iids will be stored at each update. Let's take an example. If:
        # - root.lastId is 99 ;
        # - p_self.forwardMod is 4 ;
        # - p_self.forwardLimit is 10000 ;
        # All iids between 100 and 10000 for which iid % 4 = 0 will be added to
        # the vault. It represents 2500 iids:
        #
        #              [100, 104, 108, ..., 10084, 10088, 10092, 10096]
        #
        # "On a regular basis" means: when the backup is launched via a job. In
        # the following example, the backup is daily launched: a vault update
        # will be triggered at the same pace.
        #
        #                config.jobs.add('15 01 * * *', 'backup')
        #
        self.forwardLimit = 10000
        # The last (but not least) question is: which requests will pick up
        # their iids in the vault and which ones will pick them up based on
        # root.lastId ? In other words, who will be allowed to access the vault?
        # This is determined by the following attribute. If p_self.allowed is:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # None   | There is no restriction: every request could potentially
        #        | access to the vault. In that case, when reserving an iid,
        #        | Appy will randomly choose to get it from the vault or get it
        #        | based on root.lastId.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # <fun>  | If a function is placed in p_self.allowed, it will be called
        #        | with the currently logged user as unique arg and must return
        #        | True if the vault must be used.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.allowed = None

        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #                           Use case
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

        # Here is the use case that led to the creation of the vault.
        # A Appy site (AS) has 2 categories of users:
        # - human beings performing a mix of read and write operations on the
        #   database;
        # - an external system (EX) that performs, via web service calls, a high
        #   number of object creations and updates.
        # AS adds functionalities based on a sub-set of EX data: consequently,
        # this sub-set must be synchronized in real-time with the AS database.
        # Hence the high level of write operations, coming from a single user,
        # representing EX. For such a case, without a vault, conflict errors
        # occur very often: an object creation by a human user and an EX request
        # may request the same iid based on root.lastId.
        # One more precision: object creations by human beings are often made
        # via Action fields with options. It means that, for each such object
        # creation: 2 iids are reserved: the one granted to the transient
        # options object and the one granted to the created object.
        # Consequently, the number of free backward iids is high.

        # For this use case, here is a potential vault configuration.

        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # backward     |  True   | Indeed, because of human-driven object
        #              |         | creations via options objects, the number of
        #              |         | freed iids being lower than root.lastId is
        #              |         | high: it makes sense to recycle them.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # forward      | FWD_MOD | In complement to backward iids, it makes
        #              |         | sense to reserve forward iids as well: due to
        #              |         | the high pace of EX-driven object creations,
        #              |         | backward iids may all be reserved at a given
        #              |         | moment.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # forwardMod   |    2    | Due to the high volume of EX requests, it's
        #              |         | not a luxury to reserve one of every two iids
        #              |         | for the EX system.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # forwardLimit |  10000  | Not more than 5000 object creations by EX
        #              |         | are foreseen per day.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # allowed      |   fun   | Suppose the EX system connects to AS via
        #              |         | login "exuser": v_fun can be implemented that
        #              |         | way:
        #              |         |
        #              |         | def vaultAllows(user):
        #              |         |     return user.login == 'exuser'
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def isEnabled(self):
        '''Is the vault enabled ?'''
        return self.backward or self.forward

    def getForwardInfo(self):
        '''Returns info about the forward config, as a string'''
        forward = self.forward
        if forward == Config.FWD_NO:
            r = 'No'
        else:
            iidsMax = int(self.forwardLimit / self.forwardMod)
            r = f'MODULO {self.forwardMod}{br}Max. {iidsMax} iids'
        return r

    def allows(self, handler):
        '''Is the request currently managed by this p_handler allowed to access
           the vault ?'''
        allowed = self.allowed
        if allowed is None:
            # This special case implies a random use of the vault. It's like if
            # the request is sometimes allowed, sometimes not, depending on
            # randomness.
            r = random.randint(0,1)
        else:
            r = allowed(handler.guard.user)
        return r

    # Config details, as a PX. Variable v_cfg, in the context, is the main
    # database configuration.

    px = Px('''
     <tr>
      <th>Vault of IDs</th>
      <td var="vcfg=cfg.vault; enabled=vcfg.isEnabled()">
       <x>:'Enabled' if enabled else 'Disabled'</x>
       <table if="enabled" class="small bottomSpaceX">

        <!-- Backward enabled ? -->
        <tr><th>Backward</th><td>:vcfg.backward</td></tr>

        <!-- Forward enabled ? -->
        <tr><th>Forward</th><td>::vcfg.getForwardInfo()</td></tr>

        <!-- Number of iids currently in the vault -->
        <x var="size=database.Vault.getSize(root)">
         <tr>
          <th>#iids in the vault</th>
          <td>:size</td>
         </tr>
         <!-- Display the min and max integers stored in the vault -->
         <x if="size">
          <tr>
           <th>Min. iid</th>
           <td>:root.vault.minKey()</td>
          </tr>
          <tr>
           <th>Max. iid</th>
           <td>:root.vault.maxKey()</td>
          </tr>
         </x>
        </x>
       </table>
      </td>
     </tr>''')

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
UPD_BCK    = 'Vault update :: Backward :: Scanning objects before last iid ' \
             '%d...'
UPD_BCK_A  = '%d backward iid(s) added (first:%d, last:%d).'
UPD_BCK_NO = 'No backward iid has been added.'
UPD_FWD    = 'Vault update :: Forward :: Applying mod=%d, limit=%d from last ' \
             'id+1 %d to %d, in order to add %s of future iids to the vault...'
UPD_FWD_A  = '%d forward iid(s) added (first:%d, last:%d).'
UPD_FWD_NO = 'No forward iid has been added.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Vault:
    '''Manages the vault of database iids as stored as a IITreeSet in
       root.vault, v_root being the root database object.'''

    @classmethod
    def getSize(class_, root):
        '''Returns the number of iids currently stored in the vault'''
        return len(root.vault) if hasattr(root, 'vault') else 0

    @classmethod
    def use(class_, root, handler):
        '''Must the vault be used for getting a new iid for the currently
           handled request ?'''
        # No, if the vault is disabled
        config = handler.config.database.vault
        if not config.isEnabled(): return
        # No, if there is no vault or no iid in it
        vault = getattr(root, 'vault', None)
        if vault is None or len(vault) == 0: return
        # No, if the current request is not allowed to access the vault
        if not config.allows(handler): return
        # The vault must be used
        return True

    @classmethod
    def hasId(class_, root, iid):
        '''Is this p_iid in the vault ?'''
        vault = getattr(root, 'vault', None)
        if vault is None or len(vault) == 0: return
        return iid in vault

    @classmethod
    def popId(class_, root, handler):
        '''Pops an iid from the vault'''
        # An iid stored in the vault may not be free: it may happen in the case
        # of a future iid, after a vault configuration change. Consequently,
        # this method pops iids until it finds one that does not correspond to
        # an existing object. If, during this potentially multi-pop operation,
        # the vault is emptied, this method returns None.
        vault = root.vault
        length = len(vault)
        if length == 0: return
        database = handler.server.database
        while length > 0:
            # Pop an iid from the vault
            iid = vault.pop()
            if not database.exists(id=iid, root=root):
                # This iid is free: return it
                return iid
            length = len(vault)

    @classmethod
    def updateBackward(class_, tool, root, handler):
        '''Updates, in the vault, the iids being free before p_root.lastID'''
        # iids from the vault, when used, are popped from it in real-time, via
        # calls to m_popId. Consequently, when updating the vault via this
        # m_updateBackward method, the only thing that must be done is adding
        # iids that are detected as being free but are not in the vault yet.
        vault = root.vault
        lastId = root.lastId
        tool.log(UPD_BCK % lastId)
        database = tool.database
        added = 0 # Count the number of iids added into the vault
        first = last = None # The first and last iids that will be added to the
                            # vault in a few seconds.
        i = 2
        while i <= lastId:
            if not database.exists(id=i, root=root):
                # There is no object having this iid: add it to the vault.
                # Update, when relevant, v_first and v_last.
                if added == 0:
                    # This is the first added iid
                    first = i
                last = i # Will be updated until storing the last one
                added += vault.insert(i)
            i += 1
        # Log
        if added:
            text = UPD_BCK_A % (added, first, last)
        else:
            text = UPD_BCK_NO
        tool.log(text)

    @classmethod
    def updateForward(class_, tool, root, handler):
        '''Updates forward iids in the vault'''
        # The caller is supposed to have checked that forward strategy FWD_MOD
        # is applicable.
        vault = root.vault
        first = root.lastId + 1
        config = tool.config.database.vault
        limit = config.forwardLimit
        last = first + limit
        mod = config.forwardMod
        # The rate of forward iids that will be reserved for the vault
        rate = '1/%d' % mod
        tool.log(UPD_FWD % (mod, limit, first, last, rate))
        # Count the number of iids added into the vault
        added = 0
        # iids of the first and last iids that will be added to the vault
        firstAdded = lastAdded = None
        # Scan iids from v_first to v_last
        i = first
        while i < last:
            # Must iid v_i be stored in the vault ?
            if i % mod == 0:
                # Yes: add it, and also update v_firstAdded and v_lastAdded
                if added == 0:
                    firstAdded = i
                lastAdded = i
                added += vault.insert(i)
            i += 1
        # Log
        if added:
            text = UPD_FWD_A % (added, firstAdded, lastAdded)
        else:
            text = UPD_FWD_NO
        tool.log(text)

    @classmethod
    def update(class_, tool):
        '''Update the vault'''
        # Don't do anything if the vault is disabled
        config = tool.config.database.vault
        if not config.isEnabled(): return
        # Create the IITreeSet if not done yet (may occur on old databases)
        handler = tool.H()
        root = handler.dbConnection.root
        if not hasattr(root, 'vault'):
            root.vault = IITreeSet()
        # Update backward iids: walk free iids before p_root.lastId
        class_.updateBackward(tool, root, handler)
        # Update forward iids
        if config.forward:
            class_.updateForward(tool, root, handler)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
