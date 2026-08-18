#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from .pool import ThreadPool

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Status:
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

    def __init__(self):
        # Counts of threads in each legal state
        for status in ThreadPool.statuses:
            setattr(self, status, 0)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
