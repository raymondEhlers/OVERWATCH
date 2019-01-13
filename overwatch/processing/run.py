#!/usr/bin/env python

""" Minimal executable to launch processing.

``__main__`` is implemented to allow for this function to be executed directly,
while ``run()`` is defined to allow for execution via ``entry_points`` defined
in the python package setup.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

import logging
import os
import pendulum
import pprint
import timeit

import sentry_sdk
from overwatch.database.factoryMethod import getDatabaseFactory
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

# Setup sentry to create alerts for warning level messages. Those will include info level breadcrumbs.
sentry_logging = LoggingIntegration(level = logging.INFO, event_level = logging.WARNING)
# Usually, we want the module specific DSN, but we will take a generic one if it's the only one available.
sentryDSN = os.getenv("SENTRY_DSN_PROCESSING") or os.getenv("SENTRY_DSN")
if sentryDSN:
    # It's helpful to know that sentry is setup, but we also don't want to put the DSN itself in the logs,
    # so we simply note that it is enabled.
    logger.info("Sentry DSN set and integrations enabled.")
sentry_sdk.init(dsn = sentryDSN, integrations = [sentry_logging])

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
    # Create connection information here so the processing doesn't attempt to access the database
    # each time that it runs during repeating processing, as such attempts will confuse the database lock.
    db = getDatabaseFactory().getDB()
    while not handler.exit.is_set():
        # Note both the time that the processing started, as well as the execution time.
        logger.info("Running processing at {time}.".format(time = pendulum.now()))
        start = timeit.default_timer()
        # Run the actual executable.
        processRuns.processAllRuns(db)
        end = timeit.default_timer()
        logger.info("Processing complete in {time} seconds".format(time = end - start))
        # Only execute once if the sleep time is <= 0. Otherwise, sleep and repeat.
        if sleepTime > 0:
            handler.exit.wait(sleepTime)
        else:
            break

    db.close_connection()

if __name__ == "__main__":
    run()
