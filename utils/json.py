#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
UNREADABLE = 'Unreadable JSON string: %s'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from appy.utils.string import Normalize
from appy.model.utils import Object as O

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Decoder:
    '''Converts JSON data into Python data structures'''

    # Boolean and None values are different in JSON and Python
    context = {'true': True, 'false': False, 'null': None}
    

    @classmethod
    def convertDict(class_, d):
        '''Returns a appy.Object instance representing dict p_d'''
        r = O()
        for name, value in d.items():
            # Ensure "name" will be a valid attribute name for a Python object
            n = Normalize.alphanum(name, keepUnderscore=True)
            setattr(r, n, class_.convertValue(value))
        return r

    @classmethod
    def convertList(class_, l):
        '''Every item being a dict in p_l is converted to an object'''
        i = len(l) - 1
        while i >= 0:
            l[i] = class_.convertValue(l[i])
            i -= 1

    @classmethod
    def convertValue(class_, val):
        '''Converts a JSON p_val into a Python value'''
        if isinstance(val, list):
            class_.convertList(val)
            r = val
        elif isinstance(val, dict):
            r = class_.convertDict(val)
        else:
            # In all other cases, no conversion is needed
            r = val
        return r

    @classmethod
    def decode(class_, jsonData):
        '''Converts JSON data received in a string (p_jsonData) to a Python data
           structure. JSON dicts are converted to Python objects.'''
        try:
            return class_.convertValue(eval(jsonData, class_.context))
        except SyntaxError:
            # The presence of char "\r" may pose problem
            jsonData = jsonData.replace('\r', '')
            try:
                return class_.convertValue(eval(jsonData, class_.context))
            except SyntaxError as err:
                raise Exception(UNREADABLE % jsonData)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
