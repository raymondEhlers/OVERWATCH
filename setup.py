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
    name="aliceoverwatch",
    version="1.0",

    description="ALICE OVERWATCH: Online Monitoring via the HLT",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="Raymond Ehlers",
    author_email="raymond.ehlers@cern.ch",

    url="https://github.com/raymondEhlers/OVERWATCH",
    license="MIT",

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Science/Research',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ],

    # What does your project relate to?
    keywords='HEP ALICE',

    packages=find_packages(exclude=("deploy", ".git", "tests")),

    # Rename scripts to the desired executable names
    # See: https://stackoverflow.com/a/8506532
    entry_points = {
        "console_scripts" : [
            # Note that the flask apss only run the flask development server through these scripts
            # because they will be launched directly via uwsgi (ie not through these scripts)
            "overwatchDQMReceiver = overwatch.receiver.run:runDevelopment",
            "overwatchWebApp = overwatch.webApp.run:runDevelopment",
            # The processing will be launched this way in both production and development, so it 
            # points to a different type of function
            "overwatchProcessing = overwatch.processing.run:run",
            # Deployment script
            "overwatchDeploy = overwatch.base.deploy:run",
            # Utility script to update the database users
            "overwatchUpdateUsers = overwatch.base.updateDBUsers:updateDBUsers",
            ],
        },

    # Required packages.
    # Optional dependencies are defined below
    install_requires = [
        "aenum",
        "future",
        "ruamel.yaml",
        "numpy",
        # rootpy is only used peripherally and it's installation process is sometimes difficult,
        # so although it's a strictly speaking a requirement, we leave it out here.
        # Plus, this allows us to build the docs.
        #"rootpy",
        "werkzeug",
        "flask",
        "Flask-Login",
        "Flask-Assets",
        "Flask-RESTful",
        "ZODB",
        # Install `Flask-ZODB` from git repo to support the newer hook and py 3
        # git+https://github.com/SpotlightKid/flask-zodb.git
        # Unfortunately, we can't install this directly from git, so it has to be handled directly.
        "zodburi",
        "bcrypt",
        "Flask-Bcrypt",
        "requests",
        "uwsgi",
    ],

    # Include additional files
    include_package_data=True,

    extras_require = {
        "tests" : [
            "pytest",
            "pytest-cov",
            "pytest-mock",
        ],
        "docs" : [
            "sphinx",
            # Allow markdown files to be used
            "recommonmark",
        ]
    }
  )
