#/usr/bin/env python

# Setup OVERWATCH
# Derived from the setup.py in aliBuild
#  and based on: https://python-packaging.readthedocs.io/en/latest/index.html

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

# Get the long description from the README file
here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="alice_overwatch",
    version="0.9",

    description="ALICE OVERWATCH: Online Monitoring via the HLT",
    long_description=long_description,

    author="Raymond Ehlers",
    author_email="raymond.ehlers@cern.ch",

    url="https://github.com/raymondEhlers/OVERWATCH",

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2.7'
    ],

    # What does your project relate to?
    keywords='HEP ALICE',

    packages=[
        processRuns,
        webApp
    ],

    install_requires=[
        flask,
        Flask-Login,
        Flask-ZODB,
        Flask-Bcrypt
    ],

    # Include additional files
    include_package_data=True
  )
