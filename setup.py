import os
from setuptools import setup, find_packages

version = '0.8.4dev'

setup(name='appy',
      version=version,
      description="Applications in Python",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      classifiers=[],
      keywords='',
      author='Gaetan Delannay',
      author_email='gaetan.delannay@geezteem.com',
      url='http://launchpad.net/~appy',
      license='GPL',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      include_package_data=True,
      zip_safe=False)
