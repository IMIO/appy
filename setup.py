import os
from distutils.core import setup


def find_packages():
    res = []
    for dir, dns, fns in os.walk('appy'):
        res.append(dir.replace('/', '.'))
    return res

setup(name="appy",
      version="0.9dev",
      description="The Appy framework",
      long_description="Appy builds simple but complex web Python apps.",
      author="Gaetan Delannay",
      author_email="gaetan.delannay AT geezteem.com",
      license="GPL",
      platforms="all",
      url='http://appyframework.org',
      packages=find_packages(),
      package_data={'': ["*.*"]})
