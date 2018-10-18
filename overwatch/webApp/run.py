#!/usr/bin/env python

""" Minimal executable to the web app development server.

``__main__`` is implemented to allow for this function to be executed directly,
while ``run()`` is defined to allow for execution via ``entry_points`` defined
in the python package setup.

Note:
    This should only be used for the development server!! Actualy deployments
    should be performed using `uwsgi`.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

import logging
import socket
import os
import pprint

# Config
from overwatch.base import config
# For configuring logger
from overwatch.base import utilities
(serverParameters, filesRead) = config.readConfig(config.configurationType.webApp)
print("Configuration files read: {filesRead}".format(filesRead = filesRead))
print("serverParameters: {serverParameters}".format(serverParameters = pprint.pformat(serverParameters)))

# By not setting a name, we get everything!
logger = logging.getLogger("")
# Alternatively, we could set "webApp" to get everything derived from that
#logger = logging.getLogger("webApp")

# Setup logger
utilities.setupLogging(logger = logger,
                       logLevel = serverParameters["loggingLevel"],
                       debug = serverParameters["debug"])
# Log server settings
logger.info(serverParameters)

# Imports are below here so that they can be logged
from overwatch.webApp.webApp import app

# Get the secret key for the web app
if not serverParameters["debug"]:
    # Connect to database ourselves and grab the secret key
    (dbRoot, connection) = utilities.getDB(serverParameters["databaseLocation"])
    if "secretKey" in dbRoot["config"] and dbRoot["config"]["secretKey"]:
        logger.info("Setting secret key from database!")
        secretKey = dbRoot["config"]["secretKey"]
    else:
        # Set secret_key based on sensitive param value
        logger.error("Could not retrieve secret_key in db! Instead setting to random value!")
        secretKey = str(os.urandom(50))

    # Note the changes in values
    logger.debug("Previous secretKey: {key}".format(key = app.config["SECRET_KEY"]))
    logger.debug("     New secretKey: {key}".format(key = secretKey))
    # Update it with the new value
    app.config.update(SECRET_KEY = secretKey)
    logger.debug("     After setting: {key}".format(key = app.config["SECRET_KEY"]))

    # Usually we close the db connection here!
    # Even though we just created a new db connection, if we close it here, then it will interfere with the web app
    # Instead, we just leave it up to flask_zodb to manage everything
    #connection.close()

def runDevelopment():
    """ Main entry point for running the web app development server.

    Args:
        None.
    Returns:
        None.
    """
    if "pdsf" in socket.gethostname():
        from flup.server.fcgi import WSGIServer
        logger.info("Starting flup WSGI app")
        WSGIServer(app, bindAddress = ("127.0.0.1", 8851)).run()
    elif "sgn" in socket.gethostname():
        from flup.server.fcgi import WSGIServer
        logger.info("Starting flup WSGI app on sciece gateway")
        WSGIServer(app, bindAddress = ("127.0.0.1", 8851)).run()
    else:
        logger.info("Starting flask app")
        # Careful with threaded, but it can be useful to test the status page, since the post request succeeds!
        app.run(host = serverParameters["ipAddress"],
                port = serverParameters["port"],
                #threaded=True
                )

if __name__ == "__main__":
    runDevelopment()
