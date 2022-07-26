# ~license~
# ------------------------------------------------------------------------------
import time

# ------------------------------------------------------------------------------
NO_LEAVE_TIME = 'I cannot compute duration of this call, the leaveTime is ' \
                'unknown.'
CALL_STACK_ERROR = "Problem with the method call stack: we did not enter any " \
                   "method, so we can't leave a method now."

# ------------------------------------------------------------------------------
class MethodCall:
    '''Stores information about a method call'''
    def __init__(self, methodName, enterTime, method=None):
        self.methodName = methodName # The name of the called method
        self.method = method # The method
        self.enterTime = enterTime # Whe did we enter the method ?
        self.leaveTime = None # When did we leave the method ?

    def duration(self):
        '''How long did the call lasted (in seconds) ?'''
        if not self.leaveTime:
            raise Profiler.Error(NO_LEAVE_TIME)
        return self.leaveTime - self.enterTime

class Profiler:
    '''Counts the time spent in some of your code's methods'''

    class Error(Exception): pass
    
    def __init__(self, obj, mustLog=True, mustPrint=False):
        self.obj = obj
        # Must I log profiling results via p_obj.log ?
        self.mustLog = obj and mustLog
        self.mustPrint = mustPrint # Must I print profiling results to stdout?
        self.init()
        self.log('profiler in use.')

    def init(self):
        '''(re-)initialize this profiler's data structures'''
        self.callStack = [] # Stack of profiled method calls
        self.durations = {} # ~{m_methodName: f_totalTimeInMethod}~
        
    def log(self, msg):
        # First, indent the message for readability
        blanks = ' ' * 2 * len(self.callStack)
        message = blanks + msg
        if self.mustLog:
            self.obj.log(message)
        if self.mustPrint:
            print(message)

    def enter(self, method):
        '''Is called when entering a given method'''
        enterTime = time.time()
        if isinstance(method, basestring):
            methodName = method
            theMethod = None
        else:
            methodName = method.__name__
            theMethod = method
        if not self.callStack:
            self.log('entering %s...' % methodName)
        self.callStack.append(MethodCall(methodName, enterTime, theMethod))
        if not self.durations.has_key(methodName):
            self.durations[methodName] = 0

    def leave(self):
        '''Is called when leaving a given method'''
        if not self.callStack:
            raise Profiler.Error(CALL_STACK_ERROR)
        methodCall = self.callStack.pop()
        methodCall.leaveTime = time.time()
        self.durations[methodCall.methodName] += methodCall.duration()
        if not self.callStack:
            self.log('leaving %s.' % methodCall.methodName)
            self.log('total durations in methods:')
            durations = self.durations.items()
            # Sort methods by total duration
            durations.sort(key=lambda x: x[1])
            for methodName, duration in durations:
                self.log('  %s: %f second(s)' % (methodName, duration))
            # Reinitialise the profiler
            self.init()
# ------------------------------------------------------------------------------
