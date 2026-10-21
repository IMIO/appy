#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import time

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
NO_L_TIME = 'I cannot compute duration of this call, the leaveTime is unknown.'
C_ST_ERR  = "Problem with the method call stack: we did not enter any ' \
            'method, so we can't leave a method now."
PROF_ON   = 'Profiler :: In use.'
METH_IN   = 'Entering %s...'
METH_OUT  = 'Leaving %s.'
METH_TOT  = 'Total durations in methods:'
METH_DUR  = '  %s: %f second·s'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class MethodCall:
    '''Stores information about a method call'''

    def __init__(self, methodName, enterTime, method=None):
        # The name of the called method
        self.methodName = methodName
        # The method
        self.method = method
        # When did we enter the method ?
        self.enterTime = enterTime
        # When did we leave the method ?
        self.leaveTime = None

    def duration(self):
        '''How long did the call lasted (in seconds) ?'''
        if not self.leaveTime:
            raise Profiler.Error(NO_L_TIME)
        return self.leaveTime - self.enterTime

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Profiler:
    '''Counts the time spent in some of your code's methods'''

    class Error(Exception): pass

    def __init__(self, mustLog=True, mustPrint=False):
        # Must I log profiling results  ?
        self.mustLog = mustLog
        # Must I print profiling results to stdout ?
        self.mustPrint = mustPrint
        self.init()

    def init(self):
        '''(re-)initialize this profiler's data structures'''
        # Stack of profiled method calls
        self.callStack = []
        # ~{m_methodName: f_totalTimeInMethod}~
        self.durations = {}

    def enable(self, o):
        '''Enable the profiler'''
        self.o = o
        self.log(PROF_ON)

    def log(self, msg):
        # First, indent the message for readability
        blanks = ' ' * 2 * len(self.callStack)
        message = f'{blanks}{msg}'
        if self.mustLog:
            self.o.log(message)
        if self.mustPrint:
            print(message)

    def enter(self, method):
        '''Is called when entering a given method'''
        enterTime = time.time()
        if isinstance(method, str):
            methodName = method
            theMethod = None
        else:
            methodName = method.__name__
            theMethod = method
        if not self.callStack:
            self.log(METH_IN % methodName)
        self.callStack.append(MethodCall(methodName, enterTime, theMethod))
        if methodName not in self.durations:
            self.durations[methodName] = 0
        return self

    def leave(self):
        '''Is called when leaving a given method'''
        if not self.callStack:
            raise Profiler.Error(C_ST_ERR)
        methodCall = self.callStack.pop()
        methodCall.leaveTime = time.time()
        self.durations[methodCall.methodName] += methodCall.duration()
        if not self.callStack:
            self.log(METH_OUT % methodCall.methodName)
            self.log(METH_TOT)
            durations = list(self.durations.items())
            # Sort methods by total duration
            durations.sort(key=lambda x: x[1])
            for methodName, duration in durations:
                self.log(METH_DUR % (methodName, duration))
            # Reinitialise the profiler
            self.init()
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
