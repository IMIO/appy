'''Generation of SVG graphics'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from pathlib import Path

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
TO_PATH_KO = 'Svg.generate(to=...) :: Value for arg "to" must be a ' \
             'pathlib.Path object.'''
TO_EXISTS  = 'File %s already exists. Use Svg.generate(overwrite=True) to ' \
             'overwrite existing files.'
bn         = '\n'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Svg:
    '''Allows to build a SVG graphic'''

    # XML prolog
    prolog = '<?xml version="1.0" encoding="utf-8"?>'

    # Main SVG tag template
    mainTag = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s">'
 
    def __init__(self, width, height):
        self.width = width
        self.height = height
        # p_self.parts will collect all graphical components to render into
        # the SVG graphic. Start by dumping the root SVG tag in it
        self.parts = [self.mainTag % (width, height)]

    def rect(self, x, y, width, height, fill=None):
        '''Draws a rectangle and adds it in p_self.content'''
        fill = f' fill="{fill}"' if fill else ''
        r = f'<rect x="{x}" y="{y}" width="{width}" height="{height}"{fill}/>'
        self.parts.append(r)

    def g(self, start=True, fill=None):
        '''Returns the p_start or end tag of a group'''
        # Generate an end tag
        if not start: return '</g>'
        # Generate a start tag
        fill = f' fill="{fill}"' if fill else ''
        return f'<g{fill}>'

    def generate(self, to=None, overwrite=None):
        '''Generates the SVG graphic corresponding to p_self'''
        # If args are None, the method returns a string containing an inline SVG
        # graphic. If p_to is specified, it is a Path object: the SVG graphic
        # will be dumped in it, unless p_overwrite is False and the file exists.
        parts = self.parts
        if to:
            # Ensure this is a Path object
            if not isinstance(to, Path):
                raise Exception(TO_PATH_KO)
            # Raise an error if the file already exists and must not be
            # overwritten.
            if not overwrite and to.exists():
                raise Exception(TO_EXISTS % to)
            # Dump the XML prolog
            parts.insert(0, self.prolog)
        # Add the main end tag
        parts.append('</svg>')
        # Get the whole result as a string
        r = bn.join(parts)
        # Write it into the p_to file or return it
        if to:
            with open(str(to), 'w') as f:
                f.write(r)
        else:
            return r
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
