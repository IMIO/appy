#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Progress:
    '''Implements a progress bar for object actions or workflow transitions that
       last a long time.'''

    # How does it work ? If an Action field or a workflow transition will
    # probably take a long time, place, in his "progress" attribute, an instance
    # of this class. Within the code that implements the action or transition,
    # once you have progress-related info, call method m_set on the Progress
    # instance. This method must be called with 2 args:

    # 1) an integer number between 1 and 100 that represents the progress
    #    percentage ;
    # 2) a translated text, that will be shown in the user interface.

    def __init__(self, label=None, interval=5):
        # This i18n p_label, if specified, will be used to show the initial text
        # around the progress bar, before the first progress request is made.
        # If p_label is None, a default text will be shown.
        self.label = label or 'progress_init'
        # The interval, in seconds, between 2 client requests for progress
        self.interval = interval
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
