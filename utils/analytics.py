'''Management of Google Analytics'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

# The code to inject into any page to enable Analytics - - - - - - - - - - - - -
code = '''
<script async src="https://www.googletagmanager.com/gtag/js?id=%s"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', '%s');
</script>
'''

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Analytics:
    '''Manage the use of Google Analytics within your Appy site'''

    def  __init__(self, id):
        # The ID received from Google
        self.id = id

    def get(self, tool):
        '''Return the chunk of code to inject in every page to enable
           Analytics.'''
        # Disable it when the site is in debug mode
        if tool.H().server.mode == 'fg': return
        # Get the code, configured with the ID
        return code % (self.id, self.id)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
