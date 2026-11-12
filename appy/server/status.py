#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import sys

from DateTime import DateTime
from persistent import Persistent
from persistent.list import PersistentList

from appy.px import Px
from .handler import HttpHandler
from appy.ui.template import Template
from appy.utils import path as putils
from .scheduler import Config as JobConfig
from appy.utils import formatNumber, executeCommand

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

    # Command used to get info about server processes (see m_setProcesses)
    psCommand = ['ps', 'aux', '--sort=-%%%s', '--no-headers']

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
        # Info about the processes using most RAM and CPU
        self.setProcesses(tool)
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

    def setProcesses(self, tool):
        '''Stores info about the processes, running on the server running this
           Appy site, that are most demanding in terms of RAM and CPU.'''
        # The following attribute stores, as a string being the output of Unix
        # command "ps", the list of processes using the most RAM on the server
        # running this Appy site. The number of stored processes is determined
        # by config.server.statusMaxProcesses.
        command = list(self.psCommand)
        sort = command[-2]
        command[-2] = sort % 'mem'
        r, err = executeCommand(command)
        maX = tool.config.server.statusMaxProcesses
        self.topRam = tuple(r.splitlines()[:maX])
        # The following attribute stores similar info, but with processes using
        # the most CPU instead or RAM. The number of stored processes is
        # determined by the same attribute as for p_self.topRam
        # (config.server.statusMaxProcesses).
        command[-2] = sort % 'cpu'
        r, err = executeCommand(command)
        self.topCpu = tuple(r.splitlines()[:maX])

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

    def getProcessesUrl(self, tool, i):
        '''Get the URL allowing to consult details about running processes
           (p_self.topRam and p_self.topCpu).'''
        url = tool.url
        # Get p_self's ZODB ID in a format that can be carried in a HTTP request
        oid = self._p_oid.hex()
        return f'{url}/Server/Status/pxTopProcesses?popup=True&i={i}&oid={oid}'

    def dumpProcessCell(self, info, i):
        '''Dumps the process-related cell p_info at cell whose index is p_i'''
        if 4<=i<=5:
            # A memory size expressed in Kb. Convert it to a nicer format.
            byteS = int(info) * 1024
            r = putils.getShownSize(byteS, unbreakable=True)
        elif i == 10:
            # Put the complete command path in a tooltip
            parts = info.rsplit('/', 1)
            if len(parts) == 1:
                r = info
            else:
                r = f'<abbr title="In {parts[0]}">{parts[1]}</abbr>'
        elif i == 11:
            # Command args: it can be long
            r = f'<div class="discreet">{Px.truncateText(info, width=35)}</div>'
        else:
            r = info
        return r

    @classmethod
    def showPage(class_, tool):
        '''Show page with server statuses if statuses' recording is enabled'''
        r = tool.forAdmin()
        return 'view' if r and tool.config.server.statusRate else None

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
        # Don't do anything if the last recorded status has been recorded less
        # than one minute ago. This can happen when long jobs are run and the
        # status record job has been delayed.
        statuses = tool.serverStatuses
        if statuses and ((DateTime() - statuses[0].time)*24*60) < 1: return
        # Create a new Status object
        status = Status(tool)
        # Create the list of server statuses it if it does not exist yet
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

    @classmethod
    def getAt(class_, tool, i, oid):
        '''Retrieve the Status object at index p_i, and ensure it has this ZODB
           p_oid.'''
        # Get all statuses
        statuses = tool.serverStatuses
        if not statuses or not (0 <= i < len(statuses)): return
        # Get the status at index p_i
        status = statuses[i]
        oid = bytes.fromhex(oid)
        # Ensure the found v_status has this p_oid
        if status._p_oid == oid:
            r = status
        else:
            r = None
            # One or several statuses have been recorded since the page showing
            # statuses, that has called us, has been generated. The status
            # having this p_oid is now somewhere at an index > p_i. Search for
            # that status in the 10 next indexes.
            j = i + 1
            trials = 10
            while j < len(statuses) and trials:
                nexT = statuses[j]
                if nexT._p_oid == oid:
                    r = nexT
                    break
                j += 1
                trials -= 1
        return r

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                   PX · View statuses in the admin zone
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # Maximum number of shown statuses per page
    maxPerPage = 40, 70, 100

    # Navigate within server statuses

    # A table of running processes and their characteristics
    pxProcesses = Px('''
      <table class="small">

       <!-- Headers -->
       <tr>
        <th>User</th><th>PID</th><th>%CPU</th><th>%MEM</th><th>VSZ</th>
        <th>RSS</th><th>TTY</th><th>STAT</th><th>START</th><th>TIME</th>
        <th>COMMAND</th><th>Args</th>
       </tr>

       <!-- Processes -->
       <tr for="process in processes" var2="parts=process.split(maxsplit=11)">
        <td for="part in parts">::status.dumpProcessCell(part,loop.part.nb)</td>
        <!-- Dump an empty cell if the command (=the last part) has no arg -->
        <td if="len(parts) == 11">-</td>
       </tr>
      </table>''')

    # Details about the top processes, in terms of RAM and CPU usage, as shown
    # in a popup.

    pxTopProcesses = Px('''
     <x var="status=tool.Server.Status.getAt(tool, int(req.i), req.oid)">
      <x if="status">
       <h3>Top processes @ <x>:tool.formatDate(status.time)</x></h3>

       <!-- Render 2 tables (top RAM and top CPU) in 2 tabs -->
       <table>
        <!-- First row: the tabs -->
        <tr class="tabRow"><td>
         <table id="tabs_tabs" class="tabs">
          <tr valign="middle">
           <td id="tab_tabs_ram" class="tabCur">
            <a onclick="showTab('tabs_ram')"
               class="clickable">In terms of RAM usage</a>
           </td>
           <td id="tab_tabs_cpu" class="tab">
            <a onclick="showTab('tabs_cpu')"
               class="clickable">In terms of CPU usage</a>
           </td>
          </tr>
         </table>
        </td></tr>

        <!-- Next row : the "top RAM" table -->
        <tr id="tabcontent_tabs_ram" style="display:table-row">
         <td var="processes=status.topRam">:status.pxProcesses</td>
        </tr>

        <!-- Next row : the "top CPU" table -->
        <tr id="tabcontent_tabs_cpu" style=":'display:none'">
         <td var="processes=status.topCpu">:status.pxProcesses</td>
        </tr>
       </table>
      </x>

      <!-- Show an error message if the status could not be retrieved -->
      <x if="not status">
       <div>🚫 Details about processes could not be retrieved.</div>
       <div class="topSpace">Try refreshing the page with server statuses.</div>
      </x>
     </x>''', template=Template.px, hook='content')

    # The link allowing to open the Appy iframe popup with details about the
    # running processes, via pxProcesses.

    pxProcessesLink = Px('''
     <td align="center">
      <a if="hasProcessInfo" target="appyIFrame"
         href=":status.getProcessesUrl(tool, nav.first+loop.status.nb)"
         onclick="openPopup('iframePopup',null,900,400,true)">👁</a>
      <x if="not hasProcessInfo">-</x>
     </td>''')

    # The RAM column header, also containing info about the status of the server
    # RAM: the total (T), free (F) and available (A) server RAM.

    pxRam = Px('''
     <th var="total,free,avail=handler.server.getRamInfo()">
       <div>RAM</div>
       <div class="tsmall">
        <abbr title="Total RAM on this machine">T · </abbr><x>:total</x>
       </div>
       <div class="tsmall">
        <abbr title="Free RAM on this machine">F · </abbr><x>:free</x>
       </div>
       <div class="tsmall">
        <abbr title="Available RAM on this machine">A · </abbr><x>:avail</x>
       </div>
     </th>''')

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
               nav=tool.ui.ListNav(req, total, batchSizes=Status.maxPerPage);
               slicE=statuses[nav.first:nav.getEndIndex()];
               x=nav.setCount(len(slicE));
               cols=6+len(threadStatuses) if pool else 6">

       <!-- Navigation -->
       <x>:nav.px</x>

       <table if="statuses" class="small">

        <!-- Headers -->
        <tr>
         <th>Time<div class="tsmall">Most recent first</div></th>
         <th if="pool" for="ts in threadStatuses">::pool.getStatusText(ts)</th>
         <x>:Status.pxRam</x>
         <th>CPU<div class="tsmall">Since last server start</div></th>
         <th>CPU<div class="tsmall">% since last status</div></th>
         <th>#Users</th>
         <th><abbr title="Details about server processes">P</abbr></th>
        </tr>

        <!-- Rows of statuses -->
        <x for="status in slicE"
           var2="hasProcessInfo=hasattr(status, 'topRam')">
         <tr>
          <td>:tool.formatDate(status.time)</td>
          <td if="pool" align="center"
              for="ts in threadStatuses">:getattr(status, ts, '-')</td>
          <td>:status.getRam()</td>
          <td align="center">:status.getCpu()</td>
          <td align="center">:status.getCpuPercentage(tool)</td>
          <td align="center">:status.users</td>
          <!-- A link to a popup showing details about processes -->
          <x>:Status.pxProcessesLink</x>
         </tr>
         <!-- Dump a special row indicating that a server restart occurred -->
         <tr if="status.serverRestartOccurred()">
          <th colspan=":cols" align="center" class="discreet">
           ›› Server restart occurred ‹‹
          </th>
         </tr>
        </x>
       </table>
      </x>
     </x>''')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
