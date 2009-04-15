from setuptools import setup, find_packages
import sys, os

version = '0.5'

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
      url='http://douglas.mayle.org',
      license='LGPLv3',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          # -*- Extra requirements: -*-
          "PyYaml==3.08",
          "argparse>=0.9.0", # Once my issue is fixed, specify the version instead of 0.9.0
          "Mercurial>=1.2",
          "termcolor==0.1.1",
      ],
      entry_points="""
      # -*- Entry points: -*-
        [console_scripts]
        yt=yamltrak.commands:main
      """,
      )
