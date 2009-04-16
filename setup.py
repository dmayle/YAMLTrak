# Copyright 2009 Douglas Mayle

# This file is part of YAMLTrak.

# YAMLTrak is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# YAMLTrak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with YAMLTrak.  If not, see <http://www.gnu.org/licenses/>.

import sys
from distutils.core import setup as dutils_setup

version = '0.5'

def hybrid_setup(**kwargs):
    # In a hybrid approach, we don't want setuptools handling script install,
    # unless on windows, as pkg_resource scans have too much overhead.
    if sys.platform != 'win32':
        print '%r' % sys.argv
        import pdb; pdb.set_trace()
        # On most platforms, we'll use both approaches.
        if sys.argv[-1] == 'develop':
            sys.argv[-1] = 'install'
            dutils_setup(**kwargs)
            sys.argv[-1] = 'develop'
        else:
            dutils_setup(**kwargs)

        # Now that we've installed our script using distutils, we'll strip it
        # out of the arguments and call setuptools for the rest.
        if 'scripts' in kwargs:
            del(kwargs['scripts'])

    from setuptools import setup as stools_setup
    stools_setup(**kwargs)

hybrid_setup(name='YAMLTrak',
      version=version,
      description="YAMLTrak ('yt is on top of hg'), the issue tracker that uses mercurial as a database",
      long_description="""\
      YAMLTrak provides a library and a command line interface to a YAML based
      issue tracker. Provides advanced features like auto-linking of edited
      files and issues, the ability to guess which issue you're working on, and
      burndown charts (in the library).  All of this in a distributed version
      control system, so issue changes follow code changes, and you always have
      an up to date view of your project.
""",
      classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.5',
        'Topic :: Software Development :: Bug Tracking',
      ], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Douglas Mayle',
      author_email='douglas.mayle.org',
      url='http://douglas.mayle.org',
      license='LGPLv3',
      packages=['yamltrak'],
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          # -*- Extra requirements: -*-
          "PyYaml==3.08",
          "argparse>=0.9.0", # Once my issue is fixed, specify the version instead of 0.9.0
          "Mercurial>=1.2",
          "termcolor==0.1.1",
      ],
      scripts=['scripts/yt'],
      )
