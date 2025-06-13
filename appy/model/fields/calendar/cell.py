#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Cell:
    '''Information about a cell (text content, style) as rendered in a tabular
       view (like the "monthMulti" view).'''

    def __init__(self, text=None, color=None, title=None, bgColor=None,
                 style=None):
        # The cell's background color
        self.bgColor = bgColor
        # The text to display. It must be short: typically, a single letter
        self.text = text
        # The color for this text
        self.color = color
        # Any CSS property not being the background or text color can be defined
        # in p_style, as a classic semi-colon-separated list of CSS properties
        # (ie, "color:white;font-size:90%").
        self.style = style
        # A longer text can be defined in p_title: it will be used as "title"
        # attribute for the cell's "td" tag. Appy will also use it at other
        # places: this is why the attribute is not named "title": it can
        # represent a more generic "name".
        self.name = title
        # The following attributes will be filled by Appy
        #
        # The related event will be added by Appy here
        self.event = None
        # The tied appy.model.fields.calendar.Gradient object
        self.gradient = None

    def clone(self):
        '''Returns p_self's clone'''
        r = Cell()
        for k, v in self.__dict__.items():
            setattr(r, k, v)

    def getStyles(self):
        '''Return CSS styles as defined by p_self'''
        r = []
        # Render the background-color, potentially combined with a gradient
        if self.bgColor:
            if self.gradient:
                prop = self.gradient.getStyle(self.bgColor)
            else:
                prop = f'background-color:{self.bgColor}'
            r.append(prop)
        # Render the color
        if self.color:
            r.append(f'color:{self.color}')
        if self.style:
            r.append(self.style)
        return ';'.join(r)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
