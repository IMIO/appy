# ~license~
# ------------------------------------------------------------------------------
from appy.px import Px
from appy.fields import Field

# ------------------------------------------------------------------------------
class Switch(Field):
    '''Complex field made of several sub-sets of fields among which only one is
       chosen. This field allows to have a part of a form being variable.
       The selected sub-set depends on a master/slave relationship that must be
       established between a Switch field and some other master field.
    '''
    pxView = pxEdit = pxCell = Px('''
     <x var="fieldset,fields=field.getChosenFields(zobj)" if="fields">
      <!-- Remember the chosen fieldset in this hidden input field -->
      <input if="layoutType == 'edit'" type="hidden"
             name=":field.name" value=":fieldset"/>
      <x var="fieldName=None;
              groupedFields=zobj.getGroupedFields(layoutType, field.pageName,
                              cssJs=None, fields=fields)">:obj.pxFields</x>
     </x>''')
    pxSearch = ''

    def __init__(self, fields, validator=None, show=True, page='main',
      group=None, layouts=None, move=0, specificReadPermission=False,
      specificWritePermission=False, width=None, height=None, maxChars=None,
      colspan=1, master=None, masterValue=None, focus=False, mapping=None,
      generateLabel=None, label=None, scolspan=1, swidth=None, sheight=None,
      inlineEdit=False, view=None, cell=None, edit=None, xml=None,
      translations=None):
        # p_fields must be a tuple of fieldsets of the form
        #                        ~((s_name, fields),)~
        # Within this tuple, every "fields" entry is itelf a tuple of the form
        #                         ~((s_name, Field),)~
        self.fields = fields
        # Call the base Field constructor
        Field.__init__(self, validator, (0,1), None, None, show, page, group,
          layouts, move, False, True, None, False, specificReadPermission,
          specificWritePermission, width, height, None, colspan, master,
          masterValue, focus, False, mapping, generateLabel, label, False,
          scolspan, swidth, sheight, True, inlineEdit, view, cell, edit, xml,
          translations)

    def getChosenFields(self, obj, layoutType='view', fieldset=None):
        '''Returns, among self.fields, the chosen sub-set, as a "flat" list of
           Field instances.

           More precisely, r_ is a tuple (name, fields), "name" being the name
           of the chosen fieldset and "fields" being the flat list of
           corresponding fields.
        '''
        req = obj.REQUEST
        # Determine the name of the chosen fieldset. Get it from p_fieldset or
        # from the request.
        master = self.master
        if not fieldset:
            # Determine the fieldset... 
            if master and master.valueIsInRequest(obj, req):
                # ... via the master value if present in the request
                requestValue = master.getRequestValue(obj)
                masterValue = master.getStorableValue(obj, requestValue,
                                                      complete=True)
                fieldset = self.masterValue(obj.appy(), masterValue)
            else:
                # ... via the stored value
                fieldset = self.getValue(obj)
                if not fieldset and not master:
                    # ... or via the first fieldset, considered as the default
                    # one if the switch has not master.
                    fieldset = self.fields[0][0]
        # Return an empty list of fields if we haven't a fieldset
        if not fieldset: return fieldset, ()
        # Get the list of fields corresponding to the chosen fieldset
        for name, fields in self.fields:
            if name == fieldset:
                return fieldset, [field for name, field in fields]
        return fieldset, ()

    def injectFields(self, klass):
        '''In order to be able to access the value of every switch sub-field as
           any other p_klass field, via expression

                               instance.[field name]

           this method, called at server startup, injects all switch sub-fields
           as p_klass attributes.
        '''
        # Note that Switch sub-fields are not added in p_klass.__fields__: only
        # "root" fields are in this attribute. So when Appy gets all fields of
        # some p_klass, it will not retrieve Switch sub-fields. So mechanisms
        # like checking fields showability and validation are performed on
        # "root" fields only, and, when relevant, on the chosen fieldset within
        # Switch fields. This is more performant and elegant. Moreover, if
        # Switch sub-fields were considered "root" fields, we would have to
        # determine global showability for it, that would be a mess.
        for fieldset, fields in self.fields:
            for name, field in fields:
                setattr(klass, name, field)
# ------------------------------------------------------------------------------
