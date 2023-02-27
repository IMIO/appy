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
        # When marshalling File fields via the XML layout, binary content is, by
        # default, included as a series of fixed size Base64-encoded chunks
        # wrapped in "part" tags. If the target site has access to this site's
        # filesystem, an alternative is to marshall the disk location of the
        # binary file instead of its content. If you want to enable this latter
        # behaviour, set the following attribute to False.
        self.marshallBinaries = True

    def set(self, appFolder):
        '''Sets site-specific configuration elements'''
        # The absolute path to the app as a pathlib.Path instance
        self.appPath = pathlib.Path(appFolder)
        # The application name
        self.appName = self.appPath.name

    def get(self, config, logger=None, appOnly=False):
        '''Creates and returns a Model instance (see below)'''
        from appy.model.loader import Loader
        return Loader(self, config, logger, appOnly).run()
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
