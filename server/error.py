# -*- coding: utf-8 -*-

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from http import HTTPStatus

from appy.px import Px
from appy.ui.js import Quote
from appy.utils import Traceback
from appy.xml.escape import Escape
from appy.ui.template import Template
from appy.utils import MessageException

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Error:
    '''Represents a server error'''

    byCode = {
     # Error 404: page not found
     404: {'label': 'not_found', 'px':
       Px('''<div>::msg</div>
             <div if="not isAnon and not popup">
              <a href=":tool.computeHomePage()">:_('app_home')</a>
             </div>''', template=Template.px, hook='content')},

     # Error 403: unauthorized
     403: {'label': 'unauthorized', 'px':
       Px('''<div><img src=":svg('password')" class="iconERR"/>
                  <x>::msg</x></div>''', template=Template.px, hook='content')},

     # Error 500: server error
     500: {'label': 'server_error', 'px':
       Px('''<div><img src=":svg('warning')" class="iconERR"/>
                  <x>::msg</x></div>''', template=Template.px, hook='content')},

     # Error 503: service unavailable. This error code is used by Appy when, due
     # to too many conflict errors (heavy load), the server cannot serve the
     # request.
     503: {'label': 'conflict_error',
           'px': Px('''<div>::msg</div>''',
                    template=Template.px, hook='content')},

     # Return code 200: a logical error rendering a nice translated message to
     # the user, but not considered being an error at the HTTP level.
     200: {'px': Px('''<img src=":svg('warning')" class="iconERR"/>
                       <x>::msg</x>''', template=Template.px, hook='content')}
    }

    @classmethod
    def getTextFrom(class_, error):
        '''Extracts and returns the text explaining this p_error being an
           Exception instance.'''
        if error and error.args and error.args != (None,):
            r = str(error).strip()
        else:
            r = None
        return r

    @classmethod
    def getContent(class_, traversal, code, error, text, _):
        '''Get the textual content to render in the error page'''
        # Dump a traceback for a Manager
        if traversal.user.hasRole('Manager') and code == 500:
            r = Traceback.get(html=True)
        else:
            if isinstance(error, MessageException):
                r = _(text) if error.isLabel else text
            elif isinstance(error, traversal.handler.Guard.Error) and text:
                # Unauthorized. Do not display the standard message if a
                # specific message has been produced.
                r = Escape.xhtml(text)
            else:
                # Produce a standard message, completed with an optional
                # additional message (in p_text).
                r = _(Error.byCode[code]['label'])
                if text:
                    r += '<div class="discreet">%s</div>' % Escape.xhtml(text)
        return r

    @classmethod
    def get(class_, resp, traversal, error=None):
        '''A server error just occurred. Try to return a nice error page. If it
           fails (ie, the error is produced in the main PX template), dump a
           simple traceback.'''
        # When managing an error, ensure no database commit will occur
        handler = resp.handler
        handler.commit = False
        # Complete the handler when appropriate
        if not traversal: handler.complete()
        traversal = handler.traversal
        # Did the error occurred in the context of an Ajax request ?
        context = traversal.context
        ajax = (context and context.ajax) or handler.req.ajax == 'True'
        # Log the error
        code = resp.code if resp.code in Error.byCode else 500
        # Message exceptions are special errors being 200 at the HTTP level
        is200 = code == 200
        message = '%d on %s' % (code, handler.path)
        text = class_.getTextFrom(error)
        if text:
            message = '%s - %s' % (message, text)
        handler.log('app', 'warning' if is200 else 'error', message=message)
        if code in (500, 503):
            handler.log('app', 'error', Traceback.get().strip())
        # Compute the textual content that will be shown
        _ = handler.tool.translate
        content = class_.getContent(traversal, code, error, text, _)
        # If we are called by an Ajax request, return only the error message,
        # and set the return code to 200; else, browsers will complain.
        if ajax:
            resp.code = HTTPStatus.OK
            # Add a link to the referer, if any
            referer = handler.headers.get('referer')
            if referer:
                suffix = '<a href="%s">← %s</a>' % (referer, _('go_back'))
            else:
                suffix = ''
            # Thanks to the DOCTYPE preamble, the Ajax subsystem will understand
            # we are in a special context and will take care of rendering the
            # message appropriately.
            return '<!DOCTYPE html><p>%s</p>%s' % (content, suffix)
        # Return the PX corresponding to the error code. For rendering it, get
        # the last PX context, or create a fresh one if there is no context.
        if not context:
            # Remove some variables from the request to minimise the possibility
            # that an additional error occurs while creating the PX context.
            req = handler.req
            if 'search' in req: del(req.search)
            traversal.context = context = traversal.createContext()
        else:
            # Reinitialise PX counts. Indeed, we have interrupted a "normal"
            # page rendering that has probably already executed a series of PXs.
            # Without reinitialising counts, Appy will believe these PXs were
            # already executed and will not include CSS and JS code related to
            # these PXs.
            context['_rt_'] = {}
        context.msg = content
        try:
            return Error.byCode[code]['px'](context)
        except Exception as err:
            return '<p>%s</p>' % content
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
