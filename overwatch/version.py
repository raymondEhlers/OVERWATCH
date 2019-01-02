#!/usr/bin/env python

""" Define the Overwatch version in a single location.

Inspired by method 3 `here <https://packaging.python.org/guides/single-sourcing-package-version/#single-sourcing-the-version>`__,
as well as ``uproot`` (which more or less implements this pattern). Further discussion is available
`here <https://stackoverflow.com/questions/458550/standard-way-to-embed-version-into-python-package>`__.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

import re

# Provide the version as a string
__version__ = "1.3.1"
version = __version__
# As provide as a tuple, with each value as it's own entry.
# ie. "1.0" -> `("1", "0")`
version_info = tuple(re.split(r"[-\.]", __version__))

del re
