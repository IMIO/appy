'''Tools related to the objects dumped as pickles on the database'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import pickletools, io

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Reader:
    '''Reads a pickled object as stored in a ZODB database'''

    # Separator between 2 entries in a pickle
    sep = b'\x80\x03'

    @classmethod
    def read(class_, o, formatted=True):
        '''Reads the stored data, in pickle format, corresponding to that
           p_o(bject), and returns a nicely formatted representation of it, or
           raw bytes if p_formatted is False.'''
        # p_o is not necessarily a Appy object: it can be any persistent object,
        # having a OID in the ZODB dabatase, as available in o._p_oid.
        #
        # Get the data stored about p_o
        pic, _ = o._p_jar.db().storage.load(o._p_oid, '')
        if not formatted:
            return pic
        # Several entries can coexist within a single pickle
        parts = pic.split(class_.sep)
        r = io.StringIO()
        for part in parts:
            if not part: continue
            pickletools.dis(class_.sep + part, out=r)
        return r.getvalue()
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
