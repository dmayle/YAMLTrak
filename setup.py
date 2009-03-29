from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='YAMLTrak',
      version=version,
      description="Bug tracker that uses versioned YAML for storage",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Douglas Mayle',
      author_email='',
      url='http://douglas.mayle.org',
      license='LGPL',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          # -*- Extra requirements: -*-
          "PyYaml",
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
