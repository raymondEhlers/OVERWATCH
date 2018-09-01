#!/usr/bin/env python

""" Minimal executable to launch processing.

``__main__`` is implemented to allow for this function to be executed directly,
while ``run()`` is defined to allow for execution via ``entry_points`` defined
in the python package setup.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

import logging
import pprint

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
                       debug = processingParameters["debug"],
                       logFilename = "processRuns")
# Log settings
logger.info(processingParameters)

# Imports are below here so that they can be logged
from overwatch.processing import processRuns

def run():
    # Process all of the run data
    processRuns.processAllRuns()
    # Function calls that be used for debugging

    ## Test processTimeSlices()
    ## TEMP
    #(dbRoot, connection) = utilities.getDB(processingParameters["databaseLocation"])
    #runs = dbRoot["runs"]
    ## ENDTEMP

    #logging.info("\n\t\t0-4:")
    #returnValue = processTimeSlices(runs, "Run300005", 0, 4, "EMC", {})
    #logging.info("0-4 UUID: {returnValue}".format(returnValue = returnValue))

    #logging.info("\n\t\t0-3:")
    #returnValue = processTimeSlices(runs, "Run300005", 0, 3, "EMC", {})
    #logging.info("0-3 UUID: {returnValue}".format(returnValue = returnValue))

    #logging.info("\n\t\t0-3 repeat:")
    #returnValue = processTimeSlices(runs, "Run300005", 0, 3, "EMC", {})
    #logging.info("0-3 repeat UUID: {returnValue}".format(returnValue = returnValue))

    #logging.info("\n\t\t1-4:")
    #returnValue = processTimeSlices(runs, "Run300005", 1, 4, "EMC", {})
    #logging.info("1-4 UUID: {returnValue}".format(returnValue = returnValue))

    #logging.info("\n\t\t1-3:")
    #returnValue = processTimeSlices(runs, "Run300005", 1, 3, "EMC", {})
    #logging.info("1-3 UUID: {returnValue}".format(returnValue = returnValue))

if __name__ == "__main__":
    run()
