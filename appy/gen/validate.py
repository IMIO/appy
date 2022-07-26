'''Validation-related stuff'''

# ------------------------------------------------------------------------------
from appy.px import Px
from appy import Object as O
from appy.shared import utils as sutils

# ------------------------------------------------------------------------------
class Validator:
    '''Class responsible for validating data encoded by the user in the UI'''
    FIELD_NOT_FOUND = 'field %s::%s was not found.'

    # PX rendering the "yellow box" containing validation errors
    pxErrors = Px('''
     <table class="small" width="100%">
      <tr><th>:_('field_name')</th><th>:_('error_name')</th></tr>
      <tr for="labels, message in validator.getGroupedErrors()">
       <td>::labels</td><td>:message</td></tr>
     </table>''')

    def __init__(self, obj):
        # A validator is created every time an p_obj(ect) is created or updated
        # from the UI via a web form.
        self.obj = obj
        # The (sub/standard/switch) fields whose widgets have received data from
        # the UI.
        self.fields = []
        self.fieldsByName = {}
        # The field values extracted from the request and converted
        self.values = O() # ~{O(s_fieldName=fieldValue)}~
        # When validation errors are encountered, they are stored in the
        # following dict. For example, if an error occurs on field named
        # "field1", an entry at key "field1" will be stored on this instance,
        # holding the translated error message.
        self.errors = O() # ~{O(s_fieldName=s_errorMessage)}~

    def intraFieldValidation(self, fields=None):
        '''This method performs field-specific validation for every field from
           the page that is being created or edited. For every field whose
           validation generates an error, we add an entry in p_self.errors. For
           every field, we add in p_self.values an entry with the
           "ready-to-store" field value.

           Il p_fields are given, we use them instead of getting currently
           edited fields on the current page for p_self.obj. ie, p_fields can be
           fields from a switch.
        '''
        obj = self.obj
        rq = obj.REQUEST
        page = rq.form.get('page')
        for field in obj.getAppyTypes('edit', page, fields=fields):
            if not field.validable or not field.isClientVisible(obj): continue
            value = field.getRequestValue(obj)
            # Perform individual field validation
            message = field.validate(obj, value)
            if message:
                setattr(self.errors, field.name, message)
            else:
                setattr(self.values, field.name,
                        field.getStorableValue(obj, value))
            # Store this field
            self.fields.append(field)
            self.fieldsByName[field.name] = field
            # Validate inner fields within outer fields
            if field.outer: field.subValidate(obj, value, self.errors)
            # Validate fields inside switch fields
            if field.type == 'Switch':
                fieldset, subFields = field.getChosenFields(obj, fieldset=value)
                if subFields:
                    self.intraFieldValidation(fields=subFields)

    def interFieldValidation(self):
        '''This method is called when individual validation of all fields
           succeeds (when editing or creating an object, see
           m_intraFieldValidation). Then, this method performs inter-field
           validation. This way, the user must first correct individual fields
           before being confronted to potential inter-field validation
           errors.'''
        obj = self.obj.appy()
        if not hasattr(obj, 'validate'): return
        msg = obj.validate(self.values, self.errors)
        # Those custom validation methods may have added fields in the given
        # p_errors object. Within this object, for every error message that is
        # not a string, we replace it with the standard validation error for the
        # corresponding field.
        for k, v in self.errors.d().iteritems():
            if not isinstance(v, basestring):
                setattr(self.errors, k, obj.translate('field_invalid'))
        return msg

    def addMessage(self, r, messages, label, message):
        '''Used by m_getErrors, this method adds, in p_r, the error p_message
           about a field whose label is p_label. Indexes of messages already
           stored in p_r are in dict p_messages.'''
        if message in messages:
            # We have already encountered this message
            r[messages[message]][0] += '<br/>%s' % label
        else:
            r.append([label, message])
            messages[message] = len(r) - 1

    def getGroupedErrors(self):
        '''Returns the list of all errors, grouped by message: if the same error
           message concerns several fields, a single entry is inserted in the
           list.'''
        _ = self.obj.o.translate
        obj = self.obj.appy()
        # A list of tuples (labels, message): "labels" being the list of field
        # labels whose error is described in "message".
        r = []
        # Remember, for every message stored in p_r, its index
        messages = {} # ~{s_message: i_index}~
        # Walk fields in the order of their definition, via self.fields
        for field in self.fields:
            # Is there an error for this field ?
            message = self.errors.get(field.name)
            if not message: continue
            label = _('label', field=field)
            self.addMessage(r, messages, label, message)
        # Add summarized messages for compound fields
        compound = []
        summaryMessage = _('validation_sub_error')
        for name, message in self.errors.d().iteritems():
            # Ignore already-managed, not-compound fields
            if '*' not in name: continue
            name = name.split('*', 1)[0]
            # Ignore already-encountered compound (sub-)fields
            if name in compound: continue
            compound.append(name)
            # Get the label for this compound field
            field = self.fieldsByName.get(name)
            if not field:
                label = name
                obj.log(Validator.FIELD_NOT_FOUND % (obj.klass.__name__, name),
                        type='error')
            else:
                label = _('label', field=field)
            self.addMessage(r, messages, label, summaryMessage)
        return r

    def getJsErrors(self):
        '''Generates the definition of a JavaScript associative array
           containing all errors collected in p_self.errors.'''
        return self.errors and sutils.getStringFrom(self.errors.d()) or 'null'
# ------------------------------------------------------------------------------
