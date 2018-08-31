#!/usr/bin/env python

""" Main OVERWATCH package.

Configuration is handled by ``config.yaml`` files in the corresponding folders.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

__all__ = [
    "base",
    "receiver",
    "processing",
    "webApp",
]

# Provide easy access to the version
# __version__ is the version string, while version_info is a tuple with an entry per point in the verion
from overwatch.version import __version__   # NOQA
from overwatch.version import version_info  # NOQA
