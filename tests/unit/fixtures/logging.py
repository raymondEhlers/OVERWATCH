#!/usr/bin/env python

# Logging related fixtures to aid testing.
#
# author: Raymond Ehlers <raymond.ehlers@yale.edu>, Yale University
# date: 16 July 2018

import pytest
import logging

# Set logging level as a global variable to simplify configuration.
# This is not ideal, but fine for simple tests.
loggingLevel = logging.DEBUG

@pytest.fixture
def loggingMixin(caplog):
    """ Logging mixin to capture logging messages from modules.

    It logs at the debug level, which is probably most useful for when a test fails.
    """
    caplog.set_level(loggingLevel)


