#!/usr/bin/env python

""" Minimal executable to launch processing.

``__main__`` is implemented to allow for this function to be executed directly,
while ``run()`` is defined to allow for execution via ``entry_points`` defined
in the python package setup.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

import datetime
import logging
import os
import pprint
import timeit

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

# Config
from overwatch.base import config
from overwatch.base import utilities
(processingParameters, filesRead) = config.readConfig(config.configurationType.processing)
print("Configuration files read: {filesRead}".format(filesRead = filesRead))
print("processingParameters: {processingParameters}".format(
    processingParameters = pprint.pformat(processingParameters)))

# By not setting a name, we get everything!
logger = logging.getLogger("")
# Alternatively, we could set processRuns to get everything derived from that
#logger = logging.getLogger("processRuns")

# Setup logging
utilities.setupLogging(logger = logger,
                       logLevel = processingParameters["loggingLevel"],
                       debug = processingParameters["debug"])
# Log settings
logger.info(processingParameters)

# Setup sentry to create alerts for warning level messages.
sentry_logging = LoggingIntegration(level = logging.WARNING, event_level = None)
# Usually, we want the module specific DSN, but we will take the general one if it's the only one available.
sentry_sdk.init(dsn = os.getenv("SENTRY_DSN_PROCESSING") or os.getenv("SENTRY_DSN"), integrations = [sentry_logging])

# Imports are below here so that they can be logged
from overwatch.processing import processRuns

def run():
    """ Main entry point for starting ``processAllRuns()``.

    This function will run on an interval determined by the value of ``processingTimeToSleep``
    (specified in seconds). If the value is 0 or less, the processing will only run once.

    Note:
        The sleep time is defined as the time between when ``processAllRuns()`` finishes and
        when it is started again.

    Args:
        None.
    Returns:
        None.
    """
    handler = utilities.handleSignals()
    sleepTime = processingParameters["processingTimeToSleep"]
    logger.info("Starting processing with sleep time of {sleepTime}.".format(sleepTime = sleepTime))
    while not handler.exit.is_set():
        # Note both the time that the processing started, as well as the execution time.
        logger.info("Running processing at {time}.".format(time = datetime.datetime.now()))
        start = timeit.default_timer()
        # Run the actual executable.
        processRuns.processAllRuns()
        end = timeit.default_timer()
        logger.info("Processing complete in {time} seconds".format(time = end - start))
        # Only execute once if the sleep time is <= 0. Otherwise, sleep and repeat.
        if sleepTime > 0:
            handler.exit.wait(processingParameters["processingTimeToSleep"])
        else:
            break

if __name__ == "__main__":
    run()
