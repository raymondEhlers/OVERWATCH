#!/usr/bin/env python

import os
import sys

# Make it execute like it is the parent directory instead of in /deploy
# See: https://stackoverflow.com/a/1432949 and https://stackoverflow.com/a/6098238
parentFolder = os.path.realpath("../")
print("parentFolder: ", parentFolder)
# Adds to the import path
sys.path.insert(0, parentFolder)
# Sets the execution folder
os.chdir(parentFolder)

# Server configuration
from config.processingParams import processingParameters
from config import sensitiveParams

# Get the most useful fucntions
from processRuns import utilities

import logging
# By not setting a name, we get everything!
logger = logging.getLogger("")
# Alternatively, we could set processRuns to get everything derived from that
#logger = logging.getLogger("processRuns")

# Setup logging
utilities.setupLogging(logger, processingParameters["loggingLevel"], processingParameters["debug"], "processRuns")
# Log settings
logger.info(processingParameters)

if __name__ == "__main__":
    (db, connection) = utilities.getDB(processingParameters["databaseLocation"])
    utilities.updateDBSensitiveParameters(db = db, debug = processingParameters["debug"])

    # Close the database connection
    connection.close()
