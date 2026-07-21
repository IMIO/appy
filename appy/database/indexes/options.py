#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

'''Customize the behaviour of database indexes via options'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Indexes are defined via a tree of classes, whose abstract root is
# appy.database.indexes.Index. Among these classes, some of them will possibly
# be customized via options. Options are similarly defined as a tree of classes,
# rooted at class Options, as defined hereafter. Note that, among Index sub-
# classes, only a minority has its companion Options class.

# Class Index defines a static attribute Index.options that is None. Then, each
# customizable Index sub-class will define, in that static attribute, an
# instance of the appropriate Options sub-class, that represents default
# options. For a specific field, these default options can be replaced by
# customized options, by placing an instance of the corresponding Options class
# in field attribute Field.indexOptions.

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Options:
    '''Abstract base class for any set of database index options'''
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
