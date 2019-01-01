#!/usr/bin/env python

""" Minimal executable wrapper to update users in the ZODB database.

``__main__`` is implemented to allow for this function to be executed directly,
while ``updateDBUsers()`` is defined to allow for execution via ``entry_points``
defined in the python package setup.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

# Server configuration
from overwatch.base import config
(serverParameters, filesRead) = config.readConfig(config.configurationType.webApp)

# Get the most useful fucntions
from overwatch.base import utilities

import logging
# By not setting a name, we get everything!
logger = logging.getLogger("")
# Alternatively, we could set processRuns to get everything derived from that
#logger = logging.getLogger("processRuns")
import pprint

# Setup logging
utilities.setupLogging(logger = logger,
                       logLevel = serverParameters["loggingLevel"],
                       debug = serverParameters["debug"])
# Log settings
logger.info("Settings: {serverParameters}".format(serverParameters = pprint.pformat(serverParameters)))

def updateDBUsers():
    """ Updates users in the database based on the current configuration.

    Args:
        None
    Returns:
        None
    """
    (db, connection) = utilities.getDB(serverParameters["databaseLocation"])
    utilities.updateDBSensitiveParameters(db = db)

    # Close the database connection
    connection.close()

if __name__ == "__main__":
    updateDBUsers()
