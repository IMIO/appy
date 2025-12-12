'''Sort results produced by a catalog'''

# Code inspired by Zope's catalog

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from BTrees.IIBTree import intersection, difference

from appy.database.lazy import LazyCat, LazyValues

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Sorter:
    '''Sorts results as produced by a catalog'''

    # The sorter' input and output data structures are as follows.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # input   | A result set of object IIDs as computed by a catalog, as an
    #         | instance of IISet.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # output  | A sorted list of object IIDs, in the form of a Lazy data
    #         | structure (see appy/database/lazy.py). The sorter produces an
    #         | intermediary data structure that is more complex than a list.
    #         | Instead of directly and completely "flattening" this data
    #         | structure into a list of IIDs, we wrap it, for performance
    #         | reasons, into a Lazy data structure, that behaves like a list
    #         | and manipulates, behind the scenes, the more complex internal
    #         | structure.
    #- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def __init__(self, sortIndex, rs, reverse):
        # The index to use for sorting
        self.sortIndex = sortIndex
        # Must we reverse results ?
        self.reverse = reverse
        # The (unsorted) result set
        self.rs = rs
        self.rsLength = len(rs)

    def iterateByIndex(self, r):
        '''Fills list p_r with sorted entries from p_self.rs, by iterating over
           p_self.sortIndex.'''
        rs = self.rs
        length = 0
        subs = []
        for value, iids in self.sortIndex.byValue.items():
            # Object v_iids share the same index v_value. Intersect each set of
            # v_iids with the result set, and produce a sorted list of these
            # intersections.
            subset = intersection(rs, iids)
            if subset:
                # Add it to the list of created subsets
                subs.append(subset)
                # Add it to v_r
                r.append((value, subset.keys()))
                length += len(subset)
        if length < self.rsLength:
            # Some objects from v_rs are not in the sort index. Get them in an
            # additional entry with a value representing an empty value
            # according to the index. This technique is not ideal regarding
            # performance. Defining an empty index value on the field (see
            # attribute Field.emptyIndexValue) should be preferred (it forces
            # all objects to have a value in the sort index), but produces a
            # bigger index.
            value = self.sortIndex.valuesType()
            remain = rs
            for sub in subs:
                remain = difference(remain, sub)
            r.append((value, remain.keys()))
            length += len(remain)
        return length

    def iterateByResultSet(self, r):
        '''Fills list p_r with sorted entries from p_self.rs by iterating over
           p_self.rs.'''
        rs = self.rs
        index = self.sortIndex
        for iid in rs:
            value = index.byObject.get(iid)
            # p_value can be None if the object is not in the sort index. Don't
            # add None to the result, but a value being conform to the sort
            # index. Else, sorting v_r will raise an exception.
            if value is None:
                value = self.sortIndex.valuesType()
            r.append((value, iid))
        return len(r)

    def run(self):
        '''Returns a Lazy data structure containing object IIDs found in
           p_self.rs, sorted by p_self.sortIndex.'''
        r = []
        # Choose what method to use for sorting p_self.rs. It is more performant
        # to iterate over the index if shorter than the result set.
        rsLength = self.rsLength
        indexLength = len(self.sortIndex.byValue)
        algo = 'ByIndex' if rsLength > (indexLength * (rsLength / 100 + 1)) \
                         else 'ByResultSet'
        # Use the chosen algorithm to produce an intermediate result in p_r
        length = getattr(self, f'iterate{algo}')(r)
        # Sort p_r. Reverse the sort order when appropriate.
        r.sort(reverse=self.reverse)
        # Return the list as a "lazy" data structure (see appy/database/lazy.py)
        if algo == 'ByIndex':
            # Sort results are in the form of a list of sub-lists
            r = LazyCat(LazyValues(r), length=length)
        else:
            # Sort results are in the form of a simple list, but whose
            # sub-elements are (value, iid) tuples instead of simple IIDs.
            r = LazyValues(r)
        return r
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
