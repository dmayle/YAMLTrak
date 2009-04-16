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

def restore_distutils_install_script(self, dist, script_name, script_text, dev_path=None):
    """\
    Monkey patch setuptools with an install_script function that restores
    distutils behavior."""
    spec = str(dist.as_requirement())
    is_script = is_python_script(script_text, script_name)

    if is_script and dev_path:
        script_text = get_script_header(script_text) + (
            "# EASY-INSTALL-DEV-SCRIPT: %(spec)r,%(script_name)r\n"
            "__requires__ = %(spec)r\n"
            "from pkg_resources import require; require(%(spec)r)\n"
            "del require\n"
            "__file__ = %(dev_path)r\n"
            "execfile(__file__)\n"
        ) % locals()
    elif is_script:
        script_text = get_script_header(script_text) + (
            "# EASY-INSTALL-SCRIPT: %(spec)r,%(script_name)r\n"
            "__requires__ = %(spec)r\n"
            "import pkg_resources\n"
            "pkg_resources.run_script(%(spec)r, %(script_name)r)\n"
        ) % locals()
    self.write_script(script_name, script_text, 'b')

def install_script(self, dist, script_name, script_text, dev_path=None):
    import pdb; pdb.set_trace()
    self.write_script(script_name, script_text, 'b')

def hybrid_setup(**kwargs):
    # In a hybrid approach, we don't want setuptools handling script install,
    # unless on windows, as pkg_resource scans have too much overhead.
    if sys.platform != 'win32':
        # On most platforms, we'll use both approaches.
        if 'setuptools' in sys.modules:
            # Someone used easy_install to run this.  I really want the correct
            # script installed.
            import setuptools.command.easy_install
            setuptools.command.easy_install.install_script = install_script
            setuptools.command.install_script = install_script

        if 'develop' in sys.argv:
            sys.argv[sys.argv.index('develop')] = 'install'
            dutils_setup(**kwargs)
            sys.argv[sys.argv.index('install')] = 'develop'

            # Now that we've installed our script using distutils, we'll strip it
            # out of the arguments and call setuptools for the rest.
            if 'scripts' in kwargs:
                del(kwargs['scripts'])

            from setuptools import setup as stools_setup
            stools_setup(**kwargs)
        else:
            dutils_setup(**kwargs)



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
