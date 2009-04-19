# Copyright 2009 Douglas Mayle

# This file is part of YAMLTrak.

# YAMLTrak is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.

# YAMLTrak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with YAMLTrak.  If not, see <http://www.gnu.org/licenses/>.

import sys
from setuptools import setup


version = '0.6.2'

# We monkeypatch setuptools to perform script installs the way distutils does.
# Calling pkg_resources is too time intensive for a serious command line
# applications.
def install_script(self, dist, script_name, script_text, dev_path=None):
    self.write_script(script_name, script_text, 'b')

if sys.platform != 'win32' and 'setuptools' in sys.modules:
    # Someone used easy_install to run this.  I really want the correct
    # script installed.
    import setuptools.command.easy_install
    setuptools.command.easy_install.easy_install.install_script = install_script


setup(name='YAMLTrak',
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
      url='http://dvdev.org',
      license='LGPLv3',
      packages=['yamltrak'],
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          # -*- Extra requirements: -*-
          "PyYaml==3.08",
          #"argparse>=0.9.0", # Temporarily embedding a patched version that fixes the bugs I care about.
          "Mercurial>=1.2",
          "termcolor==0.1.1",
      ],
      scripts=['scripts/yt'],
      )
