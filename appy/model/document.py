#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.model.base import Base
from appy.model.fields import Show
from appy.ui.layout import Layouts
from appy.xml.escape import Escape
from appy.model.fields.file import File
from appy.model.fields.list import List
from appy.model.fields.color import Color
from appy.model.fields.action import Action
from appy.model.fields.string import String
from appy.model.fields.select import Select, Selection
from appy.model.workflow.standard import TooPermissive

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Document(Base):
    '''Base class representing a binary document: image, file, etc.'''

    # Use the TooPermissive standard workflow, complemented by methods
    # m_mayView, m_mayEdit and m_mayDelete defined hereafter.
    workflow = TooPermissive

    # Documents are not indexed by default
    indexable = False
    popup = ('500px', '500px')
    listColumns = ('thumb*60px|', 'title')

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                               The file
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    do = {'label': 'Document'}

    def getMaxWidth(self):
        '''Get the maximum width for uploaded images. If the image is larger
           than this, it will be resized.'''
        # The size may be defined on the container
        try:
            container = self.container or self.initiator.o
        except AttributeError:
            # There is no container yet if the image is uploaded via ckeditor
            container = self.traversal.o
        width = container.maxWidth if hasattr(container, 'maxWidth') else 700
        return '%dpx' % width

    def getViewWidth(self):
        '''The width of the image as shown on the "view" layout varies depending
           on the it to be rendered in the popup or no.'''
        return '450px' if self.req.popup == 'True' else '700px'

    file = File(multiplicity=(1,1), isImage=True, resize=True, cache=True,
                width=getMaxWidth, viewWidth=getViewWidth, nameStorer='title',
                thumbnail='thumb', **do)

    # Its thumbnail
    thumb = File(isImage=True, resize=True, width='100px', show=Show.VE_, **do)

    def getCarousel(self):
        '''Returns the carousel into which this document is included'''
        container = self.container
        if container and container.class_.name == 'Carousel':
            return container

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                  Elements to render on top of the file
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # When used in a carousel, elements may be specified, that must be shown
    # on top of the document.

    elementTypes = ('title', 'underTitle', 'buttonA', 'buttonB')

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                          Action "duplicate"
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # [Carousel-specific] This action creates a clone B from a document A, and
    #                     adds B to A's container, at the end of the same Ref
    #                     linking the container to A.

    def showDocAction(self):
        '''Shows this action only to the user being allowed to edit the
           document's container.'''
        carousel = self.getCarousel()
        return 'buttons' if carousel and carousel.allows('write') else None

    def doDuplicate(self):
        '''Creates a clone from p_self and links it to p_self's container'''
        container, name = self.getContainer(forward=True)
        clone = container.createFrom(name, self)
        self.say(self.translate('action_done'))
        return True, self.referer

    duplicate = Action(show=showDocAction, action=doDuplicate, confirm=True,
                       result='redirect', **do)

    @classmethod
    def listElementTypes(class_, o):
        '''Lists the possible types for elements' entries'''
        return [(typ, o.translate(f'et_{typ}')) for typ in class_.elementTypes]

    sub = (
      ('type', Select(validator=Selection(lambda o: o.listElementTypes(o)),
                      multiplicity=(1,1))),
      ('text', String(multiplicity=(1,1))),
      ('position', String(multiplicity=(1,1), width=6, default='40% 5%')),
      ('url', String()) # No URL validator: JS code is allowed (javascript:...)
    )
    elements = List(sub, show=lambda o: o.container.class_.name == 'Carousel',
                    layouts=Layouts.td, **do)

    def getElementLink(self, carousel, element, text):
        '''Returns the compete "a" tag for a clickable element'''
        # Get link attributes from the p_carousel, if any
        attributes = carousel.linkAttributes
        target = onClick = params = None
        if attributes and (element.type in attributes):
            attrs = attributes[element.type]
            target = attrs.target
            onClick = attrs.onClick
            params = attrs.params
        target = (' target="%s"' % target) if target else ''
        onClick = (' onClick="%s"' % onClick) if onClick else ''
        url = element.url
        if params:
            sep = '&' if '?' in url else '?'
            url += sep + params
        return '<a href="%s"%s%s>%s</a>' % (url, target, onClick, text)

    def getElements(self, carousel):
        '''Returns, as a list of chunks of XHTML code, the list of elements from
           field "elements", ready to be dumped on top of p_self in this
           p_carousel.'''
        r = []
        if self.isEmpty('elements'): return r
        for element in self.elements:
            # Compute the element's position, relative to s_self's top left
            # corner.
            top, left = element.position.split(' ')
            # Get the CSS class to apply
            css = carousel.getCssName(element.type)
            # Get the text to display
            text = Escape.xhtml(element.text)
            if element.url:
                # Wrap the text in a clickable link
                text = self.getElementLink(carousel, element, text)
            # Produce the complete chunk of XHTML for this element
            html = '<div class="%s" style="top:%s;left:%s">%s</div>' % \
                   (css, top, left, text)
            r.append(html)
        return r

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                          Actions "(un)publish"
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # [Carousel-specific] Actions for (un)publishing a document in a carousel

    pp = {'confirm': True, 'result': 'redirect', **do}

    def showPublish(self, unpublish=False):
        '''Show the "(un)publish" action to allowed users, when p_self is in the
           appropriate ref.'''
        container, name = self.getContainer(forward=True)
        if container.class_.name != 'Carousel' or \
           not container.allows('write'): return
        ref = 'documents' if unpublish else 'unpublished'
        return 'sub' if name == ref else None

    def doPublish(self, unpublish=False):
        '''(Un)publishes p_self'''
        # Determine the source and target refs for moving p_self
        if unpublish:
            source = 'documents'
            target = 'unpublished'
        else:
            source = 'unpublished'
            target = 'documents'
        self.container.relink(source, target, self)
        self.say(self.translate('action_done'))
        return True, self.referer

    publish = Action(action=doPublish, show=showPublish, **pp)
    unpublish = Action(action=lambda o: o.doPublish(unpublish=True),
                       show=lambda o: o.showPublish(unpublish=True), **pp)

    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                            Main methods
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def validate(self, new, errors):
        '''Validate elements'''
        elements = new.elements
        if not elements: return
        i = -1
        for element in elements:
            i += 1
            # Validate the position
            parts = element.position.split(' ')
            if len(parts) != 2:
                message = self.translate('position_ko')
                setattr(errors, 'elements*position*%d' % i, message)

    def mayView(self):
        '''This document is viewable if its container is'''
        return self.container.allows('read')

    def mayEdit(self):
        '''This document is editable if its container is'''
        # The container is not present just before the newly created document is
        # tied to its initiator.
        container = self.container
        return not container or container.allows('write')

    def mayDelete(self):
        '''This document can be deleted if its container can be edited'''
        return self.container.allows('write')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
