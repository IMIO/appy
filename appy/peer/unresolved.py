'''Manages links between objects while importing a web of objects from one site
   to another.'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

# During the process of importing of a web of interconnected objects from one
# site to another, at a given moment in time, an object may need to be linked to
# another one that has not been imported yet.

# Class "Unresolved" stores those "unresolved" links, that are collected in a
# first import step. In a second step, once the missing objects will have been
# imported, unresolved links will actually be "reified".

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import copy

from appy.model.utils import Object as O

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
RES_START   = 'Resolving links for %d objects (and inner links for %d ' \
              'objects), based on a total of %d imported objects...'
RES_END     = '%d links resolved and %d unresolved.'
UNRESOLVED  = 'Unresolved object with ID "%s" mentioned in %s:%s:%s.'
MIS_CUS_FUN = 'Custom entries to resolve have been found but no function has ' \
              'been specified to resolve them (in peer.unresolved.customFun).'
CUS_START   = 'Starting custom resolution of %d entries...'
CUS_END     = 'Custom resolution done.'
FIN_START   = 'Resolver: calling the "final" function...'
FIN_END     = 'Final job done.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Unresolved:
    '''Manage unresolved links between objects'''

    def __init__(self, peer):
        self.peer = peer
        # Dict "unresolved" stores, for every local object and every forward Ref
        # defined on it, the list of distant IDs for which no local object
        # exists yet.
        self.unresolved = {} # ~{Base: {s_fwdRefFieldName: [s_distantId]}}~
        # Dict "unresolvedI" stores similar information, for Refs being
        # *I*nside outer fields. s_outerInnerField keys, as mentioned below, are
        # of the form <outerFieldName>*<innerFieldName>.
        self.unresolvedI = {} # ~{Base: {s_outerInnerField: [s_distantId]}}~
        # Beyond this dict of "standard" unresolved entries, an app may store
        # custom data structures in Custom fields, requiring specific
        # resolution. For such cases, user the following dict.
        # - It must be filled by a custom Importer (appy.peer.importer.Importer
        #   sub-class) defined in your app and registered in the peer's
        #   "importers" attribute.
        # - Everytime your custom importer finds the content of a custom field
        #   containing elements to be resolved at the end of the process, it
        #   must add or update an entry in dict "custom" below, via method
        #   m_addCustom below.
        self.custom = {} # ~{Base: [s_customFieldName]}~
        # - At the end of the import process, after having performed standard
        #   resolving using p_self.unrevolved, custom resolving will be
        #   launched. For every object and custom field stored in p_self.custom,
        #   the custom function you must specify in the following attribute,
        #   will be called, with, as args:
        #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  peer  | The currently runnning Peer instance ;
        #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  o     | one of the objects from p_self.custom ;
        #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        #  name  | the name of one of the custom fields mentioned in
        #        | p_self.custom at key "o".
        #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.customFun = None
        # At the very end of the resolving process, a custom method can be ran.
        # It will receive the peer instance and the tool as args.
        self.finalFun = None

    def add(self, o, field, distantId):
        '''Adds an unresolved link between this local p_o(bject) and a missing
           distant object whose ID is p_distantId, via this forward Ref
           p_field.'''
        # p_field may be a tuple (outerField, innerField), in case the Ref field
        # is within an outer field.
        # ~ ~ ~
        inner = isinstance(field, tuple)
        dname = 'unresolvedI' if inner else 'unresolved'
        d = getattr(self, dname)
        # Get or create the sub-dict related to p_o
        if o in d:
            sub = d[o]
        else:
            sub = d[o] = {}
        # Insert the ID in the appropriate list
        name = field[1].name if inner else field.name
        if name in sub:
            sub[name].append(distantId)
        else:
            sub[name] = [distantId]

    def addCustom(self, o, field):
        '''Adds a custom entry in p_self.custom'''
        name = field.name
        if o in self.custom:
            self.custom[o].append(name)
        else:
            self.custom[o] = [name]

    def resolve(self, tool):
        '''Reify links between objects for which links could not be done earlier
           in the import process.'''
        counts = O(resolved=0, unresolved=0)
        peer = self.peer
        byId = peer.localObjects
        tool.log(RES_START % (len(self.unresolved), len(self.unresolvedI),
                              len(byId)))
        # Browse links to resolve, object per object, from p_self.unresolved
        for o, links in self.unresolved.items():
            # Browse links to resolve, Ref by Ref starting from this object
            for name, distantIds in links.items():
                for id in distantIds:
                    # Find the local object corresponding to this ID
                    tied = byId.get(id)
                    if tied is None:
                        # Still unresolved
                        counts.unresolved += 1
                        tool.log(UNRESOLVED % (id, o.class_.name, o.id, name))
                    else:
                        # Tied object found, perform the link
                        o.link(name, tied, executeMethods=False)
                        counts.resolved += 1
        # Browse links to resolve from p_self.unresolvedI
        for o, links in self.unresolvedI.items():
            # Within v_links, values (=distant IDs) will not be retrieved, it is
            # useless. We will walk the value on p_o for field named p_name and
            # try to convert any found distant ID to a local object.
            for name in links:
                # Split the names of the outer and inner fields
                outer, inner = name.split('*', 1)
                # Get the value containing the unresolved IDs
                value = getattr(o, outer)
                i = -1
                for row in value:
                    i += 1
                    innerVal = row[inner]
                    if innerVal is None: continue
                    rowChanged = False
                    j = len(innerVal)-1
                    while j >= 0:
                        ival = innerVal[j]
                        # Ignore sub-values already converted to local objects
                        if isinstance(ival, str):
                            # This is an unresolved distant ID
                            tied = byId.get(ival)
                            if tied is None:
                                # Still unresolved
                                tool.log(UNRESOLVED % (ival, o.class_.name,
                                                       o.id, name))
                                del innerVal[j]
                                counts.unresolved += 1
                            else:
                                # Tied object found. Replace the ID with the
                                # object.
                                innerVal[j] = tied
                                counts.resolved += 1
                            # In both cases, the rows has changed
                            rowChanged = True
                        j -= 1
                    # Ensure changes will be detected by the ZODB
                    if rowChanged:
                        value[i] = copy.deepcopy(row)
        tool.log(RES_END % (counts.resolved, counts.unresolved))
        # Perform custom resolution when relevant
        if self.custom:
            if not self.customFun:
                raise Exception(MIS_CUS_FUN)
            tool.log(CUS_START % len(self.custom))
            for o, names in self.custom.items():
                for name in names:
                    self.customFun(peer, o, name)
            tool.log(CUS_END)
        # Call the final function if present
        if self.finalFun:
            tool.log(FIN_START)
            self.finalFun(peer, tool)
            tool.log(FIN_END)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -