#!/usr/bin/env python

import logging
import socket

# TEMP
#import sys
#import os
#print("sys.path: {0}".format(sys.path))
#print("os.environ[PYTHONPATH]: {}".format(os.environ["PYTHONPATH"]))
# END TEMP

# Config
from config.serverParams import serverParameters
# For configuring logger
from processRuns import utilities

# By not setting a name, we get everything!
logger = logging.getLogger("")
# Alternatively, we could set "webApp" to get everything derived from that
#logger = logging.getLogger("webApp")

# Setup logger
utilities.setupLogging(logger, serverParameters.loggingLevel, serverParameters.debug, "webApp")
# Log server settings
logger.info(serverParameters.printSettings())

# Imports are below here so that they can be logged
from webApp.webApp import app

# Support both the WSGI server mode, as well as standalone
#app.run(host="0.0.0.0")
if __name__ == "__main__":
    if "pdsf" in socket.gethostname():
        logger.info("Starting flup WSGI app")
        WSGIServer(app, bindAddress=("127.0.0.1",8851)).run()
    elif "sgn" in socket.gethostname():
        logger.info("Starting flup WSGI app on sciece gateway")
        WSGIServer(app, bindAddress=("127.0.0.1",8851)).run()
    else:
        logger.info("Starting flask app")
        # Careful with threaded, but it can be useful to test the status page, since the post request succeeds!
        app.run(host=serverParameters.ipAddress,
                port=serverParameters.port)#, threaded=True)
