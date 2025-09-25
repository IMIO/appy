#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import random, hashlib, binascii

from appy import n
from appy.px import Px
from appy.model.fields import Field
from appy.model.utils import Object as O

#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class PasswordGenerator:
    '''Class used to generate passwords'''

    # No "0" or "1" that could be misinterpreted as letters "O" or "l"
    passwordDigits = '23456789'

    # No letters i, l, o (nor lowercase nor uppercase) that could be misread
    passwordLetters = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ'

    @classmethod
    def get(k, minLength=8, maxLength=9):
        '''Generates and r_eturns a password whose length is between p_minLength
           and p_maxLength.'''
        # Compute the actual length of the challenge to encode
        length = random.randint(minLength, maxLength)
        r = ''
        for i in range(length):
            j = random.randint(0, 1)
            chars = (j == 0) and k.passwordDigits or k.passwordLetters
            # Choose a char
            r += chars[random.randint(0,len(chars)-1)]
        return r

#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Password(Field):
    '''Field allowing to edit and store a password'''

    view = cell = buttons = Px('''<x>******</x>''')

    edit = Px('''
     <!-- Explain which rules the password must follow -->
     <div class="discreet topSpace" var="text=field.explainRules(o)"
          if="text">::text</div>

     <!-- Dump 2 fields: one standard and one confirmation field -->
     <x for="confirm in (False, True)"
        var2="placeholder=field.getPlaceholder(o, confirm);
              inputId=f'{name}_confirm' if confirm else name">
      <input type="password" id=":inputId" name=":inputId" data-state="hidden"
             data-showIcon="👀" data-hideIcon="🫣"
             data-showTitle=":_('password_show')"
             data-hideTitle=":_('password_hide')"
             size=":field.getInputSize()" style=":field.getInputSize(False)"
             maxlength=":field.maxChars" placeholder=":placeholder"
             autofocus=":field.autofocus"/>
      <span class="clickable" title=":_('password_show')"
            onClick="switchPasswordView(this)">👀</span>
      <br if="not confirm"/>
     </x>''',

     js='''
      function switchPasswordView(span) {
        const widget = span.previousSibling;
        if (widget.dataset.state === 'hidden') {
          widget.type = 'text'; // Show the password
          widget.dataset.state = 'shown';
          span.title = widget.dataset.hidetitle;
          span.innerText = widget.dataset.hideicon;
        }
        else {
          widget.type = 'password'; // Hide the password
          widget.dataset.state = 'hidden';
          span.title = widget.dataset.showtitle;
          span.innerText = widget.dataset.showicon;
        }
      }''')

    # Special chars
    specialChars = '&`|@"\'!°$*%€·£+~/\\#=()[]{}§µ'

    # Default minimum occurrences for every group of chars within a password
    defaultOccurrences = {
      'lower'  : 1, # Lowercase letters
      'upper'  : 0, # Uppercase letters
      'figure' : 1, # Figures
      'special': 0, # Special chars
    }

    # Ranges of ascii codes per group of chars
    charRanges = {
      'lower'  : (97, 122), 'upper'  : (65, 90),
      'figure' : (48, 57) , 'special': specialChars
    }

    def __init__(self, validator=n, multiplicity=(0,1), show=True,
      renderable=n, page='main', group=n, layouts=n, move=0,
      readPermission='read', writePermission='write', width='25em', height=n,
      maxChars=n, colspan=1, master=n, masterValue=n, masterSnub=n, focus=False,
      historized=False, mapping=n, generateLabel=n, label=n, sdefault='',
      scolspan=1, swidth=n, sheight=n, persist=True, placeholder=n, view=n,
      cell=n, buttons=n, edit=n, custom=n, xml=n, translations=n, minLength=8,
      occurrences=n, autofocus=False):
        # The minimum length for this password
        self.minLength = minLength
        # The minimum number of occurrences for each group of chars
        self.occurrences = occurrences or Password.defaultOccurrences
        # Must the first input field automatically receive focus on edit ?
        self.autofocus = autofocus
        # Call the base constructor
        super().__init__(validator, multiplicity, n, n, show, renderable,
          page, group, layouts, move, False, True, n, n, False, n,
          readPermission, writePermission, width, height, maxChars, colspan,
          master, masterValue, masterSnub, focus, historized, mapping,
          generateLabel, label, sdefault, scolspan, swidth, sheight, persist,
          False, view, cell, buttons, edit, custom, xml, translations)
        # A potential placeholder (see homonym attribute in string.py)
        self.placeholder = placeholder

    def getPlaceholder(self, o, confirm):
        '''Returns a placeholder for the field if defined'''
        if confirm:
            # Set a specific label as placeholder for the input field allowing
            # to confirm the password.
            r = o.translate('password_confirm')
        else:
            # Define the placeholder for the base field
            r = self.getAttribute(o, 'placeholder') or ''
            # Use the field label if a placeholder must be set but no label is
            # explicitly defined.
            r = o.translate(self.labelId) if r is True else r
        return r

    def explainRules(self, o):
        '''Produce a translated text explaining rules a password must respect'''
        _ = o.translate
        # Start with the password's minimum length
        text = _('pwd_min_length', mapping={'min': self.minLength})
        r = [f'<li>{text}</li>']
        # Explain minimum occurrences for groups of chars that must be found
        for name, min in self.occurrences.items():
            # Be silent on groups for which there is no constraint
            if min == 0: continue
            # Get the text part concerning this group
            textG = _(f'pwd_{name}')
            if name == 'special':
                # For special chars, include the list of all chars considered as
                # such.
                allChars = Password.specialChars
                textD = _('pwd_special_chars', mapping={'chars':allChars})
                detail = f'<br/><h4>{textD}</h4>'
            else:
                detail = ''
            map = {'group': textG, 'min': min, 'detail': detail}
            text = _('pwd_min', mapping=map)
            r.append(f'<li>{text}</li>')
        text = _('pwd_rules')
        bullets = '\n'.join(r)
        return f'💡 {text}<br/><br/><ul>{bullets}</ul>'

    def validateOccurrences(self, o, password):
        '''Ensure p_self.occurrences are respected within this p_password'''
        # Count occurrences for each group of chars within p_password
        counts = O()
        for char in password:
            code = ord(char) # The char's ascii code
            for name, min in self.occurrences.items():
                # It is useless to count chars for groups for which the min is 0
                if min == 0: continue
                range = Password.charRanges[name]
                if isinstance(range, str):
                    found = char in range
                else:
                    found = range[0] <= code <= range[1]
                if not found: continue
                # Count it
                if name not in counts:
                    counts[name] = 1
                else:
                    counts[name] += 1
        # Are minimum occurrences respected ?
        for name, min in self.occurrences.items():
            # Ignore groups for which there is no minimum
            if min == 0: continue
            # Get the count
            count = counts[name]
            if count is None or count < min:
                # Not enough chars from this group
                groupText = o.translate(f'pwd_{name}')
                map = {'group': groupText, 'found': count or 0, 'min': min}
                return o.translate('pwd_occur_ko', mapping=map)

    def validateValue(self, o, password):
        '''Is p_password valid ?'''
        # Password must have a minimum length
        if len(password) < self.minLength:
            return o.translate('password_too_short',
                               mapping={'nb': self.minLength})
        # Ensure the "confirm" value is filled and is the same as p_password
        if o.req[f'{self.name}_confirm'] != password:
            return o.translate('passwords_mismatch')
        # Check occurrences
        return self.validateOccurrences(o, password)

    def encrypt(self, password, prefix=True, salt=n):
        '''Encrypt clear p_password with the SSHA scheme. If p_prefix is True,
           the password is prefixed with the SSHA scheme ("${SSHA}"). If p_salt
           is not given, it will be computed.'''
        if salt is None:
            # Generate a salt made of 7 chars
            salt = ''
            for n in range(7):
                salt += chr(random.randrange(256))
            salt = salt.encode()
        # Use SHA-1 algorithm to encrypt the password
        r = hashlib.sha1(password.encode() + salt).digest() + salt
        # Base64-encode the result
        r = binascii.b2a_base64(r)[:-1]
        # Prefix the result with the SSHA prefix when appropriate
        if prefix:
            r = b'{SSHA}' + r
        return r

    def check(self, o, password):
        '''Return True if the clear p_password corresponds the password as
           encrypted for this field on p_o.'''
        # Get the encrypted password
        encrypted = o.values.get(self.name)
        if not encrypted: return
        # Remove the scheme prefix
        encrypted = encrypted[6:]
        # Base64-decode it
        try:
            base = binascii.a2b_base64(encrypted)
        except binascii.Error:
            # Not valid base64
            return
        # Encrypt p_password and compare it with the encrypted password
        return self.encrypt(password, prefix=False, salt=base[20:]) == encrypted

    def generate(self, maxLength=9):
        '''Generate a password of at most m_maxLength chars'''
        return PasswordGenerator.get(self.minLength, maxLength)

    def set(self, o, password=n, log=True, maxLength=9):
        '''Sets a p_password on p_o for this password field. If p_password is
           not given, a password will be generated, made of at most p_maxLength
           chars. This method returns the generated password (or simply
           p_password if no generation occurred).'''
        if password is None:
            # Generate one
            password = self.generate(maxLength)
            msgPart = 'generated'
        else:
            msgPart = 'changed'
        self.store(o, password)
        # Log the operation when requested
        if log: self.log('password %s for %s.' % (msgPart, login))
        return password

    def store(self, o, value):
        '''Encrypts the clear password given in p_value'''
        if not self.persist: return
        # If p_value is None, store it as is
        o.values[self.name] = None if value is None else self.encrypt(value)
#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
