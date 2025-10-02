'''Management of the model behind a Appy application'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
import pathlib

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Config:
    '''Model configuration'''

    def __init__(self):
        # The "root" classes are those that will get their menu in the user
        # interface. Put their names in the list below. If you leave the list
        # empty, all classes will be considered root classes (the default). If
        # rootClasses is None, no class will be considered as root.
        self.rootClasses = []
        # People having one of these roles will be able to create instances
        # of classes defined in your application.
        self.defaultCreators = ['Manager']
        # Roles in use in a Appy application are identified at make time from
        # workflows or class attributes like "creators": it is not needed to
        # declare them somewhere. If you want roles that Appy will be unable to
        # detect, add them in the following list. Every role can be a Role
        # instance or a string.
        self.additionalRoles = []
        # Who is allowed to see field User:roles on edit and, consequently, set
        # or update a user's roles ?
        self.roleSetters = ['Manager']
        # When marshalling File fields via the XML layout, binary content is, by
        # default, included as a series of fixed size Base64-encoded chunks
        # wrapped in "part" tags. If the target site has access to this site's
        # filesystem, an alternative is to marshall the disk location of the
        # binary file instead of its content. If you want to enable this latter
        # behaviour, set the following attribute to False.
        self.marshallBinaries = True
        # If p_self.marshallBinaries is False, as previously said, the target
        # site will access binaries via the filesystem. If both the source and
        # target sites are on the same machine, the base folder for binaries is
        # simply the standard binaries folder where actual source files are
        # stored (as configured in config.database.binariesFolder, typically,
        # <site>/var). Suppose now that the target site is on another machine,
        # and may access the source machine's filesystem via a mountpoint. In
        # that case, the base folder may be different, because seen via the
        # mountpoint: specify it via the following attribute. Leaving this
        # latter to None will be equivalent to specifying the standard binaries
        # folder. The attribute value may be a string or a pathlib.Path object.
        self.marshallFolder = None
        # Part of the configuration being specific to pages
        from .page import Config as PageConfig
        self.page = PageConfig()

    def set(self, appFolder):
        '''Sets site-specific configuration elements'''
        # The absolute path to the app as a pathlib.Path object
        self.appPath = pathlib.Path(appFolder)
        # The application name
        self.appName = self.appPath.name
        # The absolute path to the ext, if it exists, will be set at server
        # startup, as a pathlib.Path object.
        self.extPath = None

    def getAppExt(self):
        '''Returns a string containing the app (and, if defined, ext) name(s)'''
        r = self.appName
        if self.extPath:
            r = f'{r} · Ext::{self.extPath.name}'
        return r

    def get(self, config, logger=None, appOnly=False):
        '''Creates and returns an instance of class appy.model.root.Model'''
        from appy.model.loader import Loader
        return Loader(self, config, logger, appOnly).run()
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
