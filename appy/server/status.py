#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import sys

from DateTime import DateTime
from persistent import Persistent
from persistent.list import PersistentList

from appy.px import Px
from .handler import HttpHandler
from appy.utils import formatNumber
from appy.utils import path as putils
from .scheduler import Config as JobConfig

# Module resource.py is not available on some enshittified platforms - - - - - -
try:
    import resource
    hasResource = True
except ImportError:
    hasResource = False

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
JOB_SS   = 'Job tool/%s configured @ %s.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Status(Persistent):
    '''Stores the status of a Appy site (= server) at a given point in time'''

    # An instance of this class represents a snapshot of the server status at
    # time t. This status is made of several elements:
    # - the counts of threads being in each legal thread state (if the pool of
    #   threads is on, see appy/server/pool.py) ;
    # - information about the process running the Appy site:
    #   · the amount of RAM used ;
    #   · the CPU time consumed since the process has started ;
    # - information about the physical server running the Appy site, like:
    #   · available disk space ;
    #   · available RAM ;
    # - other, non-real-time-related server properties, like software versions.

    # Attribute tool.serverStatuses stores a persistent list of Status objects
    # (most recent first), at a rate defined by config.server.statusRate (the
    # highest sampling rate being 1 minute), with a maximum number of Status
    # objects being defined by config.server.statusMax.

    # An instance of this Status class is also built on-the-fly and marshalled
    # in the server response, when the monitoring URL tool/check?all is called.

    def __init__(self, tool):
        # The status date and time
        self.time = DateTime()
        # Stores counts about threads
        self.setThreadCounts(tool)
        # Get resource usage
        if hasResource:
            usage = resource.getrusage(resource.RUSAGE_SELF)
        else:
            usage = None
        # The RAM used (in bytes)
        self.setRamUsage(usage)
        # The CPU time consumed (in seconds as a float)
        self.setCpuUsage(usage)
        # The number of currently logged users
        self.users = len(HttpHandler.onlineUsers)
        # A link to the previous status
        self.previous = None

    def getRam(self, formatted=True, unbreakable=True):
        r = self.ram
        if formatted:
            r = putils.getShownSize(r, unbreakable=unbreakable)
        return r

    def getCpu(self, formatted=True):
        '''Returns p_self.cpu, possibly p_formatted'''
        r = self.cpu
        if formatted:
            r = f"{formatNumber(r)}''"
        return r

    def getCpuPercentage(self, tool):
        '''Gets the CPU percentage consumed by the current process since the
           last time we have recorded its status.'''
        # The last recorded status, before p_self, is stored in p_self.previous
        previous = self.previous
        if not previous: return '-'
        if previous.cpu > self.cpu:
            # There was a server restart between v_previous and p_self: it is
            # not possible that the CPU time decreases over time for the same
            # process.
            r = '-'
        else:
            # Compute the CPU time between the previous and the current
            # statuses. This is a float number of seconds.
            deltaCpu = self.cpu - previous.cpu
            # Compute, still in seconds, the real time that has elapsed
            timeElapsed = tool.config.server.statusRate * 60
            r = formatNumber((deltaCpu / timeElapsed) * 100)
            r = f'{r} %'
        return r

    def setRamUsage(self, usage):
        '''Sets, in p_self.ram, the quantity, in bytes, of RAM used by the
           current process.'''
        if usage:
            r = usage.ru_maxrss
            if sys.platform != 'darwin':
                # on MacOS, ram usage is expressed in bytes. On Linux, it is
                # expressed in Kb.
                r *= 1024
        else:
            r = 0
        self.ram = r

    def setCpuUsage(self, usage):
        '''Returns the total CPU time the process has consumed, in seconds as a
           float, both in user and system modes, since its start.'''
        self.cpu = (usage.ru_utime + usage.ru_stime) if usage else 0

    def addCount(self, state):
        '''Counts one more thread being in that p_state'''
        r = getattr(self, state, 0)
        setattr(self, state, r+1)

    def setThreadCounts(self, tool):
        '''Stores counts of threads, from the pool, on p_self'''
        # Counts of threads in each legal state. On p_self, one integer
        # attribute named after the thread state will store the count of threads
        # in that state (see ThreadPool.statuses).
        handler = tool.H()
        pool = handler.server.pool
        if pool:
            pool.getTracked(handler, formatted=False, statusObject=self)
        else:
            # Set any count to 0
            for status in tool.Server.Pool.statuses:
                setattr(self, status, 0)

    def serverRestartOccurred(self):
        '''Returns True if a server restart occurred between the moment p_self
           was recorded and the previous status was recorded
           (p_self.previous).'''
        # It can be detected if the total CPU consumed, as noted on p_self, is
        # lower than the one recorded on p_self.previous.
        previous = self.previous
        return previous and self.cpu < previous.cpu
        # Note that a server restart, whose first subsequent status records a
        # CPU consumption time that is higher than the cumulated CPU time from
        # the last server run, will not be detected. This case may occur on a
        # developer machine where the rate of server restarts may be high, but
        # it should never occur on a production site.

    @classmethod
    def showPage(class_, tool):
        '''Show page with server statuses if statuses' recording is enabled'''
        return 'view' if tool.config.server.statusRate else None

    @classmethod
    def runJob(class_, tool):
        '''Launches, when appropriate, the job that will regularly record server
           status.'''
        config = tool.config
        rate = config.server.statusRate # A number of minutes
        if rate:
            timeDef = f'*/{rate} * * * *'
            jobName = 'recordServerStatus'
            jobs = config.jobs
            if jobs is None:
                # Create the Config object that can host jobs
                jobs = config.jobs = JobConfig()
            jobs.add(timeDef, 'recordServerStatus', threaded=True)
            tool.log(JOB_SS % (jobName, timeDef))

    @staticmethod
    def record(tool):
        '''Creates a new Status object and add it into p_tool.serverStatuses'''
        # Create a new Status object
        status = Status(tool)
        # Get the list of server statuses. Create it if it does not exist yet.
        statuses = tool.serverStatuses
        if statuses is None:
            statuses = tool.serverStatuses = PersistentList()
        # Link the new v_status to the previous one, if any
        previous = statuses[0] if statuses else None
        if previous:
            status.previous = previous
        # Add the new status into the list
        statuses.insert(0, status)
        # Remove the oldest status if we have reached the limit
        if len(statuses) > tool.config.server.statusMax:
            statuses.pop()
            # Forget about the popped status
            if statuses:
                statuses[-1].previous = None
        # A commit is required
        tool.H().commit = True

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                   PX · View statuses in the admin zone
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Maximum number of shown statuses per page
    maxPerPage = 40

    # Navigate within server statuses

    px = Px('''
     <x var="statuses=tool.serverStatuses">

      <!-- No status to render yet -->
      <div if="not statuses"
           class="discreet">😴 There is no status to show yet.</div>

      <!-- A table of statuses, most recent first -->
      <x if="statuses"
         var2="Server=tool.Server;
               Status=Server.Status;
               threadStatuses=Server.Pool.statuses;
               pool=handler.server.pool;
               total=len(statuses);
               nav=tool.ui.ListNav(req, total, batchSize=Status.maxPerPage);
               slicE=statuses[nav.first:nav.getEndIndex()];
               x=nav.setCount(len(slicE));
               cols=5+len(threadStatuses) if pool else 5">

       <!-- Navigation -->
       <x>:nav.px</x>

       <table if="statuses" class="small">

        <!-- Headers -->
        <tr>
         <th>Time<div class="legend">Most recent first</div></th>
         <th if="pool" for="ts in threadStatuses">::pool.getStatusText(ts)</th>
         <th>RAM</th>
         <th>CPU<div class="legend">Since last server start</div></th>
         <th>CPU<div class="legend">% since last status</div></th>
         <th>#Users</th>
        </tr>

        <!-- Rows of statuses -->
        <x for="status in slicE">
         <tr>
          <td>:tool.formatDate(status.time)</td>
          <td if="pool" align="center"
              for="ts in threadStatuses">:getattr(status, ts, '-')</td>
          <td>:status.getRam()</td>
          <td align="center">:status.getCpu()</td>
          <td align="center">:status.getCpuPercentage(tool)</td>
          <td align="center">:status.users</td>
         </tr>
         <!-- Dump a special row indicating that a server restart occurred -->
         <tr if="status.serverRestartOccurred()">
          <th colspan=":cols" align="center" class="legend">
           ›› Server restart occurred ‹‹
          </th>
         </tr>
        </x>
       </table>
      </x>
     </x>''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
