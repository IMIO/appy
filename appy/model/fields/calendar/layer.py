#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy import n

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Layer:
    '''A layer is a set of additional data that can be activated or not on top
       of calendar data. Currently available for timelines only.'''

    def __init__(self, name, label, onCell, activeByDefault=False, legend=n,
                 merge=False):
        # p_name must hold a short name or acronym, unique among all layers
        self.name = name
        # p_label is a i18n label that will be used to produce the layer name in
        # the user interface.
        self.label = label
        # p_onCell must be a method that will be called for every calendar cell
        # and must return a 3-tuple (style, title, content). "style" will be
        # dumped in the "style" attribute of the current calendar cell, "title"
        # in its "title" attribute, while "content" will be shown within the
        # cell. If nothing must be shown at all, None must be returned.
        # This method must accept those args:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   date      | the currently walked day (a DateTime instance) ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   other     | the Other instance representing the currently walked
        #             | calendar ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   events    | the list of events (as a list of Calendar.Cell objects
        #             | whose attribute "event" points to an instance of class
        #             | appy.model.fields.calendar.event::Event) defined at that
        #             | day in this calendar ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   cache     | the result of Calendar.cache (see below). Not to be
        #             | confused with the cache from the Appy request handler.
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.onCell = onCell
        # Is this layer activated by default ?
        self.activeByDefault = activeByDefault
        # p_legend is a method that must produce legend items that are specific
        # to this layer. The method must accept no arg and must return a list of
        # objects (you can use class appy.model.utils.Object) having these
        # attributes:
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   name   | The legend item name as shown in the calendar ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #   style  | The content of the "style" attribute that will be applied
        #          | to the little square ("td" tag) for this item ;
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  content | The content of this "td" (if any).
        #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.legend = legend
        # When p_merge is False, if the layer contains info for a given day, the
        # base info will be hidden. Else, it will be merged.
        self.merge = merge
        # Layers will be chained: one layer will access the previous one in the
        # stack via attribute "previous". "previous" fields will automatically
        # be filled by the Calendar.
        self.previous = n

    def getCellInfo(self, o, activeLayers, date, other, events, cache):
        '''Get the cell info from this layer or one previous layer when
           relevant.'''
        # Take this layer into account only if active
        if self.name in activeLayers:
            info = self.onCell(o, date, other, events, cache)
            if info: return info
        # Get info from the previous layer
        if self.previous:
            return self.previous.getCellInfo(o, activeLayers, date, other,
                                             events, cache)

    def getLegendEntries(self, o):
        '''Returns the legend entries by calling method in self.legend'''
        return self.legend(o) if self.legend else n

    @classmethod
    def format(class_, layers):
        '''Chain these p_layers via attribute "previous", and returns these
           chained p_layers, or an empty tuple if there is no layer at all.'''
        if not layers: return ()
        i = len(layers) - 1
        while i >= 1:
            layers[i].previous = layers[i-1]
            i -= 1
        return layers

    @classmethod
    def getActive(class_, cal, req):
        '''Gets the layers being currently active in this p_cal(endar)'''
        if 'activeLayers' in req:
            # Get them from the request
            layers = req.activeLayers or ()
            r = layers if not layers else layers.split(',')
        else:
            # Get the layers being active by default
            r = [layer.name for layer in cal.layers if layer.activeByDefault]
        return r
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
