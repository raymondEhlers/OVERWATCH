#!/usr/bin/env python

import logging

# Config
from config.processingParams import processingParameters
from processRuns import utilities

# By not setting a name, we get everything!
logger = logging.getLogger("")
# Alternatively, we could set processRuns to get everything derived from that
#logger = logging.getLogger("processRuns")

# Setup logging
utilities.setupLogging(logger, processingParameters.loggingLevel, processingParameters.debug, "processRuns")
# Log settings
logger.info(processingParameters.printSettings())

# Imports are below here so that they can be logged
from processRuns import processRuns

if __name__ == "__main__":
    # Process all of the run data
    processRuns.processAllRuns()
    # Function calls that be used for debugging
    #processQA("Run246272", "Run246980", "EMC", "determineMedianSlope")

    ## Test processTimeSlices()
    ## TEMP
    #storage_factory, dbArgs = zodburi.resolve_uri(processingParameters.databaseLocation)
    #storage = storage_factory()
    #db = ZODB.DB(storage, **dbArgs)
    #connection = db.open()
    #connection = ZODB.connection(processingParameters.databaseLocation)
    #dbRoot = connection.root()
    #runs = dbRoot["runs"]
    ## ENDTEMP

    #logging.info("\n\t\t0-4:")
    #returnValue = processTimeSlices(runs, "Run300005", 0, 4, "EMC")
    #logging.info("0-4 UUID: {0}".format(returnValue))

    #logging.info("\n\t\t0-3:")
    #returnValue = processTimeSlices(runs, "Run300005", 0, 3, "EMC")
    #logging.info("0-3 UUID: {0}".format(returnValue))

    #logging.info("\n\t\t0-3 repeat:")
    #returnValue = processTimeSlices(runs, "Run300005", 0, 3, "EMC")
    #logging.info("0-3 repeat UUID: {0}".format(returnValue))

    #logging.info("\n\t\t1-4:")
    #returnValue = processTimeSlices(runs, "Run300005", 1, 4, "EMC")
    #logging.info("1-4 UUID: {0}".format(returnValue))

    #logging.info("\n\t\t1-3:")
    #returnValue = processTimeSlices(runs, "Run300005", 1, 3, "EMC")
    #logging.info("1-3 UUID: {0}".format(returnValue))
