#!/usr/bin/env python

""" Main package supporting processing.

These modules contain most of the code that actually processes ROOT files.
Everything is configured by the settings in config.yaml

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University
"""

__all__ = [
           "mergeFiles",
           "processRuns",
           "processingClasses",
           "pluginManager"
          ]
