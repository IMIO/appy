'''The scheduler manages cron-like actions being programmed and automatically
   executed by the Appy server, as "virtual" requests.'''

# Important notes  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#
# I. The scheduler runs in "best effort" mode. Everytime a series of jobs must
#    be run according to the current time, they are ran, sequentially, in the
#    order of their definition. If their execution takes several minutes, during
#    this period, the scheduler will not trigger any other job.

#    Example
#    The scheduler is configured with 3 jobs, in that order:
#    - job A must be run at midnight     (cron syntax: 0   0 * * *) ;
#    - job B must be run every 3 minutes (cron syntax: */3 * * * *) ;
#    - job C must be run at 00:15        (cron syntax: 15  0 * * *).

#    At midnight, the scheduler determines that both jobs A and B must be run.
#    - job A is ran at 00:00 and takes 34 minutes to execute ;
#    - job B is ran at 00:34 and takes 30 seconds ;
#    - job B's next execution is at 00:36, then at 00:39, etc.

#    Analysis
#    a) The first execution of job B didn't occur at 00:00, neither at 00:03,
#       but after job A has completely terminated.
#    b) From 00:00 to 00:34, job B was not executed, although, according to its
#       timedef, it should have run every 3 minutes during this period.
#    c) Job C was not executed at all. Indeed, at 00:15, the scheduler was busy
#       with the execution of job A and was blocked, preventing him to detect
#       any other job execution. Job C's next execution will be the day after,
#       at 00:15, excepted if, again, execution of jobs A + B takes more than 15
#       minutes.
#    d) When the scheduler "wakes up" at 00:34, after having executed job A, he
#       does not "look backwards" to check whether other jobs should have been
#       run in the meanwhile, executing job C once, and job B as many times as
#       required between 00:00 and 00:34. No. Instead, he executes the other job
#       (job B) tha was also planned at midnight, he ignores everything
#       scheduled between 00:00 and 00:34 and continues to check for jobs,
#       starting at 00:35.

# II. The scheduler delays any incoming HTTP request. While jobs are executed by
#     the scheduler, the infinite server loop, used by the server to check for
#     incoming HTTP requests, is paused. The next HTTP request will be handled
#     after all currently running jobs have ended.

#     So, it is preferable to "size" your jobs into a series of "short-term"
#     jobs, triggered at regular intervals, rather than defining "long-lasting"
#     jobs, excepted if you are sure these latter are run when no web user is
#     there, ie, during the night.

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import time

from appy.server.handler import VirtualHandler

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
MIN_KO   = 'Config attribute "jobs.minutes" must be an integer being higher ' \
           'or equal to 1.'
MISSING  = 'Missing %s for a job.'
WRONG_TD = 'Wrong timedef "%s".'
TDEF_KO  = '%s. Must be of the form "m h dom mon dow".' % WRONG_TD

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Job:
    '''Represents a job that must be executed in the context of the scheduler'''

    def __init__(self, method):
        # Running a job consists in executing a method as defined on the tool.
        # m_method is the name of this method.
        method = method.strip() if method else method
        if not method: raise Exception(MISSING % 'method')
        self.method = method
        # This instance will also hold more information, stored by the Appy
        # server itself. For example, if this job is scheduled at regular
        # intervals, the date of the last execution will be stored on this Job
        # instance. Consequently, do not reuse the same job instance for several
        # config entries. In order to avoid name clashes, any attribute added by
        # Appy will start with an underscore.
        # ~~~
        # By default, the job will lead to a database commit. As for any other
        # method executed in the context of a UI request, if m_method must not
        # lead to a commit (either because the job, intrinsically, dos not
        # update any data in the database, or because an error occurred), the
        # method can access the currently running handler and set its "commit"
        # attribute, ie:
        # 
        #                      tool.H().commit = False

    def run(self, scheduler):
        '''Runs this job'''
        server = scheduler.server
        # Create a Virtual handler for that
        handler = VirtualHandler(server)
        # Run the job
        server.database.run(self.method, handler, scheduler.logger)
        # Unregister the virtual handler
        VirtualHandler.remove()

    def __repr__(self):
        '''p_self's string representation'''
        return '<Job %s>' % self.method

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class TimePart:
    '''Appy representation of a "time part", being any of the 5 parts of a time
       def (see class TimeDef).'''

    # Note that time part "*" will not be represented by a TimePart instance,
    # but as an entry whose value is None in dict TimeDef.parts.

    def __init__(self, part):
        # The "base" of a p_part can be:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # # |   Base      | Meaning: the part matches ...
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # 1 |     *       | any value for the corresponding measured element
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # 2 |   <int>     | if the value for the corresponding measured element
        #   |             | equals this number.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # 3 | <min>-<max> | if the value for the corresponding measured element
        #   |             | is within the [min, max] range of values.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

        # The "recurrence" of a p_part restricts the values matched by the base,
        # if this latter represents a set of values (cases #1 and #3 hereabove).
        # Recurrence is represented by suffix "/<int>" and means
        # "every >int> units". Here are some examples.
        #
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #    Example    | Meaning
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #      */3      | Every 3 units (0, 3, 6, 9 ...)
        #    10-20/3    | Every 3 units, between 10 and 20: 10, 13, 16, 19.
        #      1/2      | Illegal: recurrence can only restrict a base
        #               | representing a set of values, not a single value.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

        # You may say: what about notation 5,8 for example ? Such situations are
        # managed by a list of TimePart instances. In the example, 2 TimePart
        # instances would have be created, with bases 5 and 8, respectively.
        self.part = part

        # p_part will be broken down into these elements
        self.numA = None
        self.numB = None
        self.rec = None

        # Here is the correspondence between a p_part and its components
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #    Base     | Attribute values
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #      *      | numA is None,  numB is None
        #    <int>    | numA is <int>, numB is None
        # <min>-<max> | numA is <min>, numB is <max>
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # Attribute "rec" will be None if no recurrency is defined, or will
        # store the specified recurrence, as an integer number.
        self.parsePart()

    def parsePart(self):
        '''Parses p_part and get its components'''
        part = self.part
        if part == '*': return
        splitted = part.split('/', 1)
        # Manage the recurrence
        if len(splitted) == 2:
            # A "rec" part is present
            self.rec = int(splitted[1])
        # Manage the base
        base = splitted[0]
        if base == '*':
            pass # Nothing more to do
        elif base.isdigit():
            self.numA = int(base)
        else:
            A, B = base.split('-')
            self.numA = int(A)
            self.numB = int(B)

    def matches(self, value):
        '''Does this time part (p_self) match this p_value ?'''
        noneA = self.numA is None
        noneB = self.numB is None
        noneRec = self.rec is None
        # A single value
        if not noneA and noneB:
            return value == self.numA
        # Case: *
        elif noneA and noneB:
            if noneRec: return True
            # Take recurrence into account
            return value % self.rec == 0
        # An interval of values
        elif not noneA and not noneB:
            # The p_value must be included in it
            if value < self.numA or value > self.numB: return
            if noneRec: return True
            # Take the recurrence into account
            return (value - self.numA) % self.rec == 0

    def isNum(self):
        '''Return True if numA is an integer and numB and rec are None'''
        return isinstance(self.numA, int) and \
               self.numB is None and self.rec is None

    def __repr__(self):
        '''p_self's string representation'''
        rec = self.rec and ('/%d' % self.rec) or ''
        numA = self.numA
        numB = self.numB
        noneA = numA is None
        noneB = numB is None
        if noneA and noneB:
            r = '*'
        elif not noneA and not noneB:
            r = '%d-%d' % (numA, numB)
        else:
            r = str(numA)
        return '<TimePart %s%s>' % (r, rec)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class TimeDef:
    '''Internal Appy representation of a "time definition" as specified by the
       cron syntax.'''

    # A TimeDef instance represents a cron entry, whose "task" part has been
    # removed. Indeed, this "task" part is represented by class Job hereabove.

    # For example, cron entry
    #
    #                         30 0 * * * /my/script.sh
    #
    # is represented in the Appy scheduler as a tuple
    #
    #               (TimeDef('30 0 * * *'), Job('someToolMethod'))

    # Constants representing the 5 time parts in a timedef
    MM  = 0 # Minutes      (0-59)
    HH  = 1 # Hours        (0-23)
    dd  = 2 # Day of month (1-31)
    mm  = 3 # Month        (1-12)
    dow = 4 # Day of week  (0-6 = Sunday to Saturday; 7=also Sunday)

    # Shortcuts: predefined values, starting with @
    shortcuts = {
     'yearly'  : '0 0 1 1 *',
     'annually': '0 0 1 1 *',
     'monthly' : '0 0 1 * *',
     'weekly'  : '0 0 * * 0',
     'daily'   : '0 0 * * *',
     'midnight': '0 0 * * *',
     'hourly'  : '0 * * * *'
    }

    def __init__(self, timeDef):
        self.timeDef = timeDef.strip() if timeDef else None
        # The timedef will be stored as a dict ~{i_partID: None|[TimePart]}~
        # * Every key is one constant among MM, HH, dd, mm and dow as defined on
        #   this class.
        # * Every value can be one of the following.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   Value    | Meaning
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #    None    | It corresponds to a time part being the star, "*"
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # [TimePart] | For any other value, a list of TimePart instances will be
        #            | created (see hereabove). If the time part includes
        #            | several comma-separated values, there will be as many
        #            | TimePart instances. Else, the list will contain a single
        #            | TimePart instance.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.parts = {}
        self.parse()

    def parse(self):
        '''Parses p_self.timeDef'''
        # Ensure the timedef is not empty
        tdef = self.timeDef
        if not tdef: raise Exception(MISSING % 'timeDef')
        # Convert shortcuts
        if tdef.startswith('@'):
            tdef = TimeDef.shortcuts[tdef[1:]]
        # Split the timedef into parts
        sparts = tdef.split()
        # Ensure it includes 5 time parts
        if len(sparts) != 5:
            raise Exception(TDEF_KO % timeDef)
        # Store the parts as TimePart instances in dict p_self.parts
        i = 4
        parts = self.parts
        while i >= 0:
            # Get the "string" part
            spart = sparts[i]
            # Convert it to its appropriate internal structure
            if spart == '*':
                value = None
            else:
                value = []
                for sval in spart.split(','):
                    value.append(TimePart(sval))
            parts[i] = value
            i -= 1

    def getHour(self):
        '''Returns a tuple (i_hour, i_minute) if the hour and minute parts are
           noth simply defined by integer numbers. Else, the method returns
           None.'''
        r = []
        for i in (1, 0): # 1=hour, 0=minutes
            parts = self.parts[i]
            if len(parts) != 1: return
            part = parts[0]
            if not part.isNum(): return
            r.append(part.numA)
        return tuple(r)

    # Mapping between the parts of a timedef and the names of the corresponding
    # parts in the struct returned by time.localtime():
    #
    # - each key is the index of the value in the timedef ;
    # - each value is a tuple (j, delta, ifNegative):
    #
    #   * "j" is the index of the corresponding part in the data structure
    #     returned by time.localtime() ;
    #
    #   * "delta" is an optional value to add to the value as returned by
    #     time.localtime(). Indeed, Python values may differ from those defined
    #     by the crontab syntax. For example, according to Python, 0 is the
    #     number for Monday; according to cron, it is the number for Sunday
    #     (together with 7). By applying a delta of -1 to the Python value, a
    #     correct comparison may de done ;
    #
    #   * "ifNegative" is the number to add to the Python value, if negative,
    #     after the "delta" has been applied to it. In the previous example, if
    #     0 (Sunday) is specified, applying -1 produces -1, being negative.
    #     Adding 7 produces the correct corresponding Python value.
    codeMap = {
      dow: (6, -1, 7), # Day of the week - Monday is 0 (Python) or 1 (cron)
      mm:  (1,  0, 0), # Month number    - from 1 to 12
      dd:  (2,  0, 0), # Day number      - from 1 to 31
      HH:  (3,  0, 0), # Hour            - from 0 to 23
      MM:  (4,  0, 0)  # Minutes         - from 0 to 59
    }

    def mustRun(self, now):
        '''Does this timedef (p_self) match p_now ?'''
        # Walk parts from the last (dow) to the first part (minutes)
        parts = self.parts
        for i, info in TimeDef.codeMap.items():
            timeParts = parts[i]
            # A part being None (= *) always matches
            if timeParts is None: continue
            # Get the current time value, calibrated
            j, delta, ndelta = info
            fig = now[j] + delta
            if fig < 0:
                fig += ndelta
            # Does this time value match the time part(s) ?
            matches = False
            for timePart in timeParts:
                if timePart.matches(fig):
                    matches = True
                    break
            if not matches:
                return
        # If we are here, this timedef matches p_now
        return True

    def __repr__(self):
        '''p_self's string representation'''
        return '<TimeDef %s>' % self.parts

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Config:
    '''Scheduler configuration, defining the list of planned jobs'''

    def __init__(self):
        # The scheduler will be run every "minutes" minutes. It is not advised
        # to change this value, at the risk of being unable to conform to the
        # crontab semantics.
        # ~~~
        # For example, if you decide to set the value to 5, every timeDef entry
        # where the "minutes" part is not a multiple of 5 will never match.
        self.minutes = 1
        # Attribute "all" lists all the planned jobs. Every entry in this list
        # must be a tuple (TimeDef, Job).
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # timeDef | Refers to an instance of class TimeDef hereabove.
        #         |
        #         | TimeDef conforms to crontab syntax. In the future, it will
        #         | be extended to incorporate load-related definitions. The
        #         | goal is to implement behaviours like this one: "execute this
        #         | job if the system load was low during the last minutes".
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # Job     | A Job instance (see class Job hereabove), defining the
        #         | method to execute.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # Use method m_add below to add a job to this list.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.all = []

    def check(self, messages):
        '''Ensures the Scheduler config is correct'''
        # Check attribute "minutes"
        minutes = self.minutes
        if not isinstance(minutes, int) or (minutes < 1):
            raise Exception(MIN_KO)

    def add(self, timeDef, method):
        '''Adds a job to p_self.all, for running this m_method according to this
           p_timeDef.'''
        self.all.append( (TimeDef(timeDef), Job(method)) )

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Scheduler:
    '''The Appy scheduler'''

    def __init__(self, server):
        '''A unique Scheduler instance is created per Appy server'''
        # The Server instance
        self.server = server
        self.logger = server.loggers.app
        # The scheduler will run every "minutes" minutes. The minimum is 1.
        self.config = server.config.jobs
        self.minutes = self.config.minutes if self.config else None
        # Store, in attribute "last", the last minute corresponding to the last
        # scheduler execution. It allows to prevent several executions of the
        # same job(s) at the same minute.
        # ~
        self.last = time.localtime().tm_min
        # This attribute is initialised to the current minute. It means that, as
        # soon as the Appy server is started, the scheduler will not be able to
        # run until a minute elapses. This is very important in the context of
        # an automatic Appy server restart. Imagine a job that automatically
        # restarts the server. If the job takes less than one minute to execute,
        # the Appy server restarts, and, if "last" is empty, the job is executed
        # again... and again, as many times as it can within a minute.

    def runJobs(self):
        '''It's time to check if jobs must be run. Scan p_self.all and run
           jobs defined in it that must be run right now.'''
        jobs = self.config.all
        if not jobs: return
        now = time.localtime()
        for timeDef, job in jobs:
            if timeDef.mustRun(now):
                job.run(self)

    def scanJobs(self):
        '''This method is called by the server's infinite loop and checks
           whether jobs must be ran.'''
        # This method is called every "config.server.pollInterval" seconds. This
        # is too much: perform a real execution every "self.minutes" minutes.
        if not self.minutes: return
        current = time.localtime().tm_min
        if current % self.minutes or current == self.last: return
        # Run jobs that must be run
        self.last = current
        self.runJobs()
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -