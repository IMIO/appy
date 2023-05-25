#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import re, urllib.parse
from DateTime import DateTime

from appy.utils import string as sutils

# Importing database operators is required when evaluating criteria expressions
from appy.database.operators import and_, or_, in_, not_

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
FILT_KO   = 'Criteria :: unparsable filters :: %s'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Criteria:
    '''Represents a set of search criteria manipulated from the UI'''

    def __init__(self, tool):
        self.tool = tool
        # This attribute will store the dict of search criteria, ready to be
        # injected in a Search class for performing a search in the catalog.
        self.criteria = None

    @classmethod
    def evaluate(class_, criteria):
        '''Evaluate the criteria as carried in the request'''
        try:
            r = eval(criteria)
        except SyntaxError:
            # It may be URL-encoded
            r = eval(urllib.parse.unquote(criteria))
        return r

    @classmethod
    def readFromRequest(class_, handler):
        '''Unmarshalls, from request key "criteria", a dict that was marshalled
           from a dict similar to the one stored in attribute "criteria" in
           Criteria instances.'''
        # Get the cached criteria on the handler if found
        cached = handler.cache.criteria
        if cached: return cached
        # Criteria may be absent from the request
        criteria = handler.req.criteria
        if not criteria: return
        # Criteria are present but not cached. Get them from the request,
        # unmarshal and cache them.
        r = class_.evaluate(criteria)
        # Copy aims at keeping key "_ref" that may be removed
        handler.cache.criteria = r.copy()
        return r

    # The HTML tag representing an highlighted zone
    highlighted = '<span class="highlight">%s</span>'

    # The regex template representing highlithed text
    highlightedRex = '(?<= |\(|\>)?%s'

    @classmethod
    def getKeywords(class_, handler):
        '''Get the potential keywords to highlight'''
        # Are such keywords present within search criteria ?
        criteria = class_.readFromRequest(handler)
        if criteria and 'searchable' in criteria:
            r = criteria['searchable']
            if isinstance(r, str):
                # Highlighting operators is not supported yet
                return handler.req.w_searchable or r
        # Are such keywords present within search filters ?
        filters = handler.req.filters
        if filters:
            try:
                filters = sutils.getDictFrom(filters)
            except ValueError:
                # Filters are unparsable
                handler.log('app', 'error', FILT_KO % filters)
                filters = {}
            if 'searchable' in filters:
                return filters['searchable'].rstrip('*')

    @classmethod
    def highlight(class_, handler, text):
        '''Highlights parts of p_text if we are in the context of a search whose
           keywords must be highlighted.'''
        if not text: return ''
        # Must we highlight something ? Keywords to highlight may come, either
        # from search criteria, or from search filters.
        keywords = class_.getKeywords(handler)
        if not keywords: return text
        # Highlight every variant of every keyword
        for word in keywords.strip().split():
            for variant in (word, word.capitalize(), word.lower()):
                text = re.sub(class_.highlightedRex % variant,
                              class_.highlighted % variant, text)
        return text

    def getFromRequest(self, class_):
        '''Retrieve search criteria from the request after the user has filled
           an advanced search form and store them in p_self.criteria.'''
        r = {}
        req = self.tool.req
        # Retrieve criteria from the request
        for name, value in req.items():
            # On search form, every search field is prefixed with "w_"
            if not name.startswith('w_'): continue
            name = name[2:]
            # Get the corresponding field
            field = class_.fields.get(name)
            # Ignore this value if it is empty or if the field is inappropriate
            # for a search.
            if not field or not field.indexed or field.searchValueIsEmpty(req):
                continue
            # We have a(n interval of) value(s) that is not empty for a given
            # field. Get it.
            r[name] = field.getSearchValue(req)
        # Complete criteria with Ref info if the search is restricted to
        # referenced objects of a Ref field.
        info = req.ref
        if info: r['_ref'] = info
        self.criteria = r

    def asString(self):
        '''Returns p_self.criteria, marshalled in a string'''
        return sutils.getStringFrom(self.criteria, stringify=False, c='"')
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -