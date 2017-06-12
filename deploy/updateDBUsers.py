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
from overwatch.base import config
(serverParameters, filesRead) = config.readConfig(config.configurationType.processing)

# Get the most useful fucntions
from overwatch.base import utilities

import logging
# By not setting a name, we get everything!
logger = logging.getLogger("")
# Alternatively, we could set processRuns to get everything derived from that
#logger = logging.getLogger("processRuns")

# Setup logging
utilities.setupLogging(logger, serverParameters["loggingLevel"], serverParameters["debug"], "updateDBUsers")
# Log settings
logger.info("Settings: {0}"pprint.pformat(serverParameters))

if __name__ == "__main__":
    (db, connection) = utilities.getDB(serverParameters["databaseLocation"])
    utilities.updateDBSensitiveParameters(db = db, debug = serverParameters["debug"])

    # Close the database connection
    connection.close()
