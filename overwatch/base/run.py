#!/usr/bin/env python

""" Minimal executable to launch processing.

``__main__`` is implemented to allow for this function to be executed directly,
while ``run()`` is defined to allow for execution via ``entry_points`` defined
in the python package setup.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

import pprint
import time
import logging
# We want to log everything, so we give it empty quotes.
logger = logging.getLogger("")

# Config
from overwatch.base import config
from overwatch.base import utilities
(parameters, filesRead) = config.readConfig(config.configurationType.processing)
print("Configuration files read: {filesRead}".format(filesRead = filesRead))
print("parameters: {parameters}".format(
    parameters = pprint.pformat(parameters)))

# Setup logging
utilities.setupLogging(logger = logger,
                       logLevel = parameters["loggingLevel"],
                       debug = parameters["debug"],
                       logFilename = "receiverDataHandling")
# Log settings
logger.info(parameters)

# Imports are below here so that they can be logged
from overwatch.base import dataHandling

def runReceiverDataHandling():
    """ Run function for handling and transfering receiver data. """
    killer = utilities.gracefulKiller()
    while True:
        time.sleep(parameters["dataHandlingTimeToSleep"])
        dataHandling.processReceivedFiles()
        # Exit out if we received the signal.
        if killer.killNow is True:
            break

if __name__ == "__main__":
    runReceiverDataHandling()
