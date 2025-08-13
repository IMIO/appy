'''Generation of QR codes'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import math

from .svg import Svg

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
VER_KO  = 'QR code version must be an integer from 1 to 40'
VER_WID = 'Version %d :: Width %d'
VER_DIM = f'{VER_WID} :: Align grid size is %s, axes at %s'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class QrCode:
    '''Allows to generate a QR code'''

    # Code dimensions, for each version. Every code is a square: the dimension
    # represents the width and height.
    dimensions = {i:21+(4*(i-1)) for i in range(1,41)}

    # Width of the quiet zone that surrounds the QR code
    quietWidth = 4

    # Types of patterns
    POSITION  = 0 # Position pattern
    ALIGNMENT = 1 # Alignment pattern

    # Pattern widths
    patternWidth = {POSITION: 7, ALIGNMENT: 5}

    def __init__(self, data, fill='black', empty='white', version=3):
        # The data to encode in the QR code
        self.data = data
        # The fill color, being black by default
        self.fill = fill
        # The background color, being white by default
        self.empty = empty
        # The QR code version determines the code size. It can be an integer
        # between 1 and 40.
        self.version = version
        self.checkVersion()
        # The Svg object being the result to build (will be created by
        # m_generate below).
        self.svg = None

    def checkVersion(self):
        '''Ensures p_self.version is correct'''
        if self.version not in QrCode.dimensions:
            raise Exception(VER_KO)

    def drawPattern(self, x, y, type=POSITION):
        '''Draws a position or alignment pattern (depending on p_type) whose
           top-right corner must be positioned at (p_x, p_y).'''
        QR = QrCode
        w = QR.patternWidth[type]
        # Draw the main square
        r = self.svg
        r.rect(x, y, w, w, fill=self.fill)
        # Draw the white line being inside it
        w -= 2
        r.rect(x+1, y+1, w, w, fill=self.empty)
        # Draw the smaller central rectangle
        w -= 2
        r.rect(x+2, y+2, w, w, fill=self.fill)

    def drawTimingPatterns(self):
        '''Draw the timing patterns'''
        # Timing patterns are one row (the 7th one) and one column (the 7th one)
        # of alternating black-and-white modules. These patterns allow readers
        # to understand the width of a single module.
        QR = QrCode
        delta = QR.quietWidth + QR.patternWidth[QR.POSITION] + 1
        for i in range(2):
            # i == 0 : the horizontal line is drawn
            # i == 1 : the vertical line is drawn
            x = delta # The axis whose value changes (x if i == 0)
            y = delta - 2 # The axis whose value is fixed
            r = self.svg
            last = r.width - delta
            # Put the row in a SVG group: that way, the fill color must not be
            # repeated on each rectangle.
            r.g(fill=self.fill)
            while x <= last:
                if i == 0:
                    xx = x
                    yy = y
                else:
                    xx = y
                    yy = x
                r.rect(xx, yy, 1, 1)
                x += 2
            r.g(start=False) # Close the group

    def getAlignmentInfo(self, version=None):
        '''Gets info about the grid of alignment patterns to render'''
        # The result is a 2-tuple:
        # - the first element is the size of the grid, as an integer value ;
        # - the second element is a list of the coordinates of the x axes onto
        #   which alignment patterns must be drawn.
        #
        # Get the width of the QR code (ignoring the quiet zone)
        version = version or self.version
        width = self.dimensions[version]
        # Compute the size of the grid of alignment patterns (width or height,
        # the grid is a square).
        # - 12 is the number of modules removed from the QR code width to obtain
        #   the grid size (6 modules removed on the left, 6 removed on the
        #   right).
        # - 6 is 4 + 2 : 4 is the number of modules between the grid and the
        #   border of the QR code; 2 is the distance between the border of an
        #   alignment pattern and its center.
        size = math.ceil((width - 12 - 1) / 28) + 1
        # Compute the x coordinate of every grid axis on which a pattern will be
        # drawn. The first will always be a the edge of the grid, at 6 modules
        # from the border of the QR code.
        axes = [6]
        gridWidth = width - 12
        # This is the delta to apply to obtain x coordinate for the next axis
        deltaX = gridWidth / (size-1)
        # Is this delta X close to the upper integer ?
        closeUp = deltaX % 1 > 0.5 # 0.5 is not considered being "close up"
        deltaX = int(deltaX)
        odd = deltaX % 2
        soFarWidth = 6 # The currently allocated width, starting from the left
                       # of the grid.
        for i in range(1, size):
            # v_deltaX must always be an even number. Determine a delta to apply
            # to it, in order to get it as an even number.
            delta = 0
            if odd:
                if i == 1:
                    if version == 30:
                        # For this version, a delta of -5 is applied. I don't
                        # know if my computation lacks precision or if the QR
                        # code spec is arbitrary.
                        delta = -5
                    else:
                        delta = -3 if size >= 4 and not closeUp else -1
                elif i > 1:
                    delta = 1
            # Same remark for these cases: arbitrary spec or my bad ?
            elif version == 32:
                delta = 2 if i == 1 else 0
            elif version in (36, 39):
                delta = -6 if i == 1 else 2
            # Compute the delta to apply
            deltaI = deltaX + delta
            x = soFarWidth + deltaI
            axes.append(x)
            # Update the width so far
            soFarWidth += deltaI
        return size, axes

    def drawAlignmentPatterns(self):
        '''Draw the alignment patterns'''
        # Alignment patterns are additional patterns spread at regular intervals
        # in the QR code. There is no alignment pattern for version 1.
        version = self.version
        if version == 1: return
        r = self.svg
        QR = QrCode
        # Determine the number of rows/columns of patterns to dump. The
        # constraints are the following.
        #
        # 1. An alignment pattern is not rendered if it overlaps a position
        #    pattern.
        # 2. Regarding the alignment patterns being on the edge of the grid,
        #    the distance between the border of the QR code (ignoring the
        #    quiet zone) and the left border of the pattern must be equal to
        #    4 modules.
        # 3. Alignment patterns must be positioned at equal distance from
        #    each other, on both axes.
        # 4. The distance between 2 alignment patterns must not be more than
        #    28 modules.
        #
        # Determine the number of rows/columns of the alignment pattern
        # grid, depending on the QR code width.
        size, axes = self.getAlignmentInfo()
        last = size - 1
        # Browse the axes onto which alignment patterns must be drawn
        for i in range(size):
            for j in range(size):
                # Don't draw alignment patterns that would overlap the
                # position patterns.
                if (i == 0 and (j == 0 or j == last)) or \
                   (i == last and j == 0):
                    continue
                # Draw an alignment pattern
                xc = axes[i] + QR.quietWidth
                yc = axes[j] + QR.quietWidth
                self.drawPattern(xc-2, yc-2, type=QR.ALIGNMENT)

    def drawDarkModule(self):
        '''The dark module is a single fixed module, positioned besides the
           bottom-left position pattern.'''
        QR = QrCode
        r = self.svg
        delta = QR.quietWidth + QR.patternWidth[QR.POSITION]
        x = delta + 1
        y = r.width - delta - 1
        r.rect(x, y, 1, 1, fill=self.fill)

    def printDimensions(self):
        '''Prints the dimensions for every version'''
        for version, width in QrCode.dimensions.items():
            if version == 1:
                text = VER_WID % (version, width)
            else:
                # Get the dimension of the grid of alignment patterns
                size, axes = self.getAlignmentInfo(version)
                text = VER_DIM % (version, width, size, str(axes))
            print(text)

    def generate(self, to=None, overwrite=None):
        '''Generates the QR code as a SVG graphic'''
        # If args are None, the method returns a string containing an inline SVG
        # graphic. If p_to is specified, it is a Path object: the SVG graphic
        # will be dumped in it, unless p_overwrite is False and the file exists.
        #
        # Determine the size of the graphic = the width as defined by
        # p_self.version + 2 times the width of the quiet zone that surrounds
        # the whole QR code.
        qwidth = self.quietWidth # *q*uiet zone width
        cwidth = self.dimensions[self.version] # *c*ode width
        width = qwidth + cwidth + qwidth
        r = self.svg = Svg(width, width)
        # Add the position patterns. Position patterns are the big squares to be
        # positioned in the top-left, top-right and bottom-left corners of the
        # QR code.
        draw = self.drawPattern
        QR = QrCode
        xy = qwidth + cwidth - QR.patternWidth[QR.POSITION]
        draw(qwidth, qwidth) # In the top-left corner
        draw(qwidth, xy)     # In the bottom-right corner
        draw(xy    , qwidth) # In the top-right corner        
        # Add the timing patterns
        self.drawTimingPatterns()
        # Add alignment patterns
        self.drawAlignmentPatterns()
        # Draw the dark module
        self.drawDarkModule()
        return r.generate(to=to, overwrite=overwrite)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
