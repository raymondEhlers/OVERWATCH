#!/usr/bin/env python

import logging
import pprint

# Config
from overwatch.base import config
# For configuring logger
from overwatch.base import utilities
(receiverParameters, filesRead) = config.readConfig(config.configurationType.receiver)
print("Configuration files read: {filesRead}".format(filesRead = filesRead))
print("receiverParameters: {receiverParameters}".format(receiverParameters = pprint.pformat(receiverParameters)))

# By not setting a name, we get everything!
logger = logging.getLogger("")
# Alternatively, we could set "receiver" to get everything derived from that
#logger = logging.getLogger("reciever")

# Setup logger
utilities.setupLogging(logger = logger, 
        logLevel = receiverParameters["loggingLevel"],
        debug = receiverParameters["debug"],
        logFilename = "dqmReceiver")

# Imports are below here so that they can be logged
from overwatch.receiver.dqmReceiver import app

def runDevelopment():
    logger.info("Starting dqmReceiver app")
    # Turn on flask debugging
    app.debug = receiverParameters["debug"]
    # Careful with threaded, but it can be useful to test the status page, since the post request succeeds!
    app.run(host=receiverParameters["receiverIP"],
            port=receiverParameters["receiverPort"])#, threaded=True)

if __name__ == "__main__":
    runDevelopment()
