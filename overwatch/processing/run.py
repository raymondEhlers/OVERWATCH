#!/usr/bin/env python

import logging
import pprint

# Config
#from config.processingParams import processingParameters
from overwatch.base import config
from overwatch.base import utilities
(processingParameters, filesRead) = config.readConfig(config.configurationType.processing)
print("Configuration files read: {0}".format(filesRead))
print("processingParameters: {0}".format(pprint.pformat(processingParameters)))

# By not setting a name, we get everything!
logger = logging.getLogger("")
# Alternatively, we could set processRuns to get everything derived from that
#logger = logging.getLogger("processRuns")

# Setup logging
utilities.setupLogging(logger, processingParameters["loggingLevel"], processingParameters["debug"], "processRuns")
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
    #logging.info("0-4 UUID: {0}".format(returnValue))

    #logging.info("\n\t\t0-3:")
    #returnValue = processTimeSlices(runs, "Run300005", 0, 3, "EMC", {})
    #logging.info("0-3 UUID: {0}".format(returnValue))

    #logging.info("\n\t\t0-3 repeat:")
    #returnValue = processTimeSlices(runs, "Run300005", 0, 3, "EMC", {})
    #logging.info("0-3 repeat UUID: {0}".format(returnValue))

    #logging.info("\n\t\t1-4:")
    #returnValue = processTimeSlices(runs, "Run300005", 1, 4, "EMC", {})
    #logging.info("1-4 UUID: {0}".format(returnValue))

    #logging.info("\n\t\t1-3:")
    #returnValue = processTimeSlices(runs, "Run300005", 1, 3, "EMC", {})
    #logging.info("1-3 UUID: {0}".format(returnValue))

if __name__ == "__main__":
    run()
