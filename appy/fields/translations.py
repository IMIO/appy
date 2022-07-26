'''Classes for representing RAM translations'''

# ------------------------------------------------------------------------------
from appy import Object as O

# ------------------------------------------------------------------------------
class FieldTranslations:
    '''Translations, in all supported languages, for a given field'''

    # Map label types to label attributes
    labelAttrs = {'label': 'labels', 'descr': 'descriptions',
                  'help': 'helps', 'value': 'values'}

    def __init__(self, labels=None, descriptions=None, helps=None, values=None,
                 fallback='en'):
        # Attributes "labels", "descriptions" and "helps" store translations,
        # in every supported language, of the corresponding label type
        # (respectively, the main label, the description label or the help
        # label), and are each of the form:
        #
        #             ~O(en=s_translation, fr=s_translation,...)~
        #
        # Translations for the main field label
        self.labels = labels
        # Translations for the field description
        self.descriptions = descriptions
        # Translation for field helps
        self.helps = helps
        # Translations for possible values of the field. Relevant when a fixed
        # number of values is allowed. This must be a dict of the form:
        #
        #       ~{s_value: O(en=s_translation, fr=s_translation,...)}~
        #
        self.values = values
        # Language to use if the required language is not found
        self.fallback = fallback

    def get(self, label, language, mapping=None, value=None):
        '''Returns the translation, in p_language, of the given p_label type.
           A p_mapping may be given.'''
        # Get the set of translations corresponding to the given p_label type
        translations = getattr(self, FieldTranslations.labelAttrs[label])
        # When getting a field value, dig more deeply
        if value is not None: translations = translations[value]
        # Get, within it, the translation corresponding to p_language, or in the
        # fallback language if p_language is not found.
        r = getattr(translations, language, None) or \
            getattr(translations, self.fallback, '')
        # Todo: apply p_mapping when passed
        return r
# ------------------------------------------------------------------------------
