#!/usr/bin/env python

""" Minimal executable to launch base module functionality.

``__main__`` is implemented to allow for this function to be executed directly,
while ``run*()`` is defined to allow for execution via ``entry_points`` defined
in the python package setup.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

import os
import pendulum
import pprint
import shutil
import transaction
import logging
# We want to log everything, so we give it empty quotes.
logger = logging.getLogger("")

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

# Config
from overwatch.base import config
from overwatch.base import utilities
(parameters, filesRead) = config.readConfig(config.configurationType.base)
print("Configuration files read: {filesRead}".format(filesRead = filesRead))
print("parameters: {parameters}".format(
    parameters = pprint.pformat(parameters)))

# Setup logging
utilities.setupLogging(logger = logger,
                       logLevel = parameters["loggingLevel"],
                       debug = parameters["debug"])
# Log settings
logger.info(parameters)

# Setup sentry to create alerts for warning level messages. Those will include info level breadcrumbs.
sentry_logging = LoggingIntegration(level = logging.INFO, event_level = logging.WARNING)
# Usually, we want the module specific DSN, but we will take a generic one if it's the only one available.
sentryDSN = os.getenv("SENTRY_DSN_DATA_TRANSFER") or os.getenv("SENTRY_DSN")
if sentryDSN:
    # It's helpful to know that sentry is setup, but we also don't want to put the DSN itself in the logs,
    # so we simply note that it is enabled.
    logger.info("Sentry DSN set and integrations enabled.")
sentry_sdk.init(dsn = sentryDSN, integrations = [sentry_logging])

# Imports are below here so that they can be logged
from overwatch.base import dataTransfer
from overwatch.base import replay

def runReceiverDataTransfer():
    """ Run function for handling and transferring receiver data.

    We take advantage of the log of successfully transferred files to preform some rudimentary monitoring
    of the receivers. This function keep track of the time between when any file was transferred. If it's
    greater than 12 hours, then a warning is emitted, which will be picked up via sentry monitoring.
    """
    handler = utilities.handleSignals()
    # Keep track of the time between transfers.
    lastTransferTime = pendulum.now()
    logger.info("Starting receiver data handling and transfer.")
    while not handler.exit.is_set():
        successfullyTransferred, _ = dataTransfer.processReceivedFiles()
        if successfullyTransferred and len(successfullyTransferred) > 0:
            # Update the time of the last transfer
            lastTransferTime = pendulum.now()

        timeDifference = pendulum.now() - lastTransferTime
        # 12 hours = 43200 seconds
        if timeDifference.seconds > 43200:
            logger.warning("No data transfer in 12 hours. Check the ZMQ receivers!")
            # Update the last transfer time, or this will be emitted every loop (which could become annoying quickly).
            lastTransferTime = pendulum.now()

        handler.exit.wait(parameters["dataTransferTimeToSleep"])

def runReplayData():
    """ Replay Overwatch data that has already been processed.

    Although force reprocessing allows this to happen without having to move files,
    this type of functionality can be useful for replaying larger sets of data for
    testing the base functionality, trending, etc.

    The run directory is first moved to a temporary folder. Then, data is replayed from that folder
    so that it can be reprocessed file by file. If the run directory isn't moved, then even
    if we replay an early file, it could be ignored due to a later file being available to provide data.

    This function will run on an interval determined by the value of ``dataReplayTimeToSleep``
    (specified in seconds). If the value is 0 or less, the processing will only run once.

    Note:
        The sleep time is defined as the time between when ``moveFiles()`` finishes and
        when it is started again.

    Args:
        None.
    Returns:
        None.
    """
    # Basic validation to ensure that we only move data that we actually intend to move.
    baseDir = parameters["dataReplaySourceDirectory"]
    # Ensure that it is some sort of Run directory.
    if not baseDir or "Run" not in baseDir:
        raise ValueError("Source directory doesn't specify a run to replay. Please set it in your configuration. Current value: {baseDir}".format(baseDir = baseDir))

    # Move files from the run directory to the temporary folder so that we can replay from there.
    # If these files aren't moved, then even if we replay an early file, it could be ignored due
    # to a later file being available to provide data.
    temporaryDir = parameters["dataReplayTempStorageDirectory"]
    # We need to explicitly add this additional directory - otherwise ``move(...)`` will dump the directory
    # contents right into the dataReplayTempStorageDirectory directory.
    _, runDir = os.path.split(baseDir)
    temporaryRunDir = os.path.join(temporaryDir, runDir)
    # Need to remove the temporary run directory before moving if it exists. Otherwise ``move(...)`` will move
    # the directoy we are moving __inside__ of the existing directory...
    if os.path.exists(temporaryRunDir):
        shutil.rmtree(temporaryRunDir)
    # Now actually move the file.
    logger.debug("Moving existing runDir at {baseDir} to {temporaryRunDir}".format(baseDir = baseDir, temporaryRunDir = temporaryRunDir))
    shutil.move(baseDir, temporaryRunDir)

    # Attempt to remove the runDir from the database so that replay is successful (otherwise, it looks for entries
    # and files that don't exist since replay moved the files).
    logger.debug("Attempting to remove existing run directory {runDir} from the database.".format(runDir = runDir))
    (db, connection) = utilities.getDB(parameters["databaseLocation"])
    removedRun = db.get("runs", {}).pop(runDir, None)
    if removedRun:
        # Need to commit the change, as it hasn't been stored yet.
        transaction.commit()
        logger.debug("Successfully removed the existing run directory from the database.")

    # Now begin the actual replay.
    replay.runReplay(baseDir = temporaryRunDir,
                     destinationDir = parameters["dataReplayDestinationDirectory"],
                     nMaxFiles = parameters["dataReplayMaxFilesPerReplay"])

    # Cleanup the database connection.
    connection.close()

def runReplayDataTransfer():
    """ Handle moving files from processed Overwatch names to unprocessed names so they can be transferred.

    They will be transferred to Overwatch sites and EOS via the ``dataTransfer`` module.

    Args:
        None.
    Returns:
        None.
    """
    replay.runReplay(baseDir = parameters["dataReplaySourceDirectory"],
                     destinationDir = parameters["dataReplayDestinationDirectory"],
                     nMaxFiles = parameters["dataReplayMaxFilesPerReplay"])

if __name__ == "__main__":
    runReceiverDataTransfer()
