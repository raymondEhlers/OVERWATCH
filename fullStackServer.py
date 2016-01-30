#!/usr/bin/env python
""" Full stack server to serve the web app via WSGI.

This effectively lets us simulate having an Apache or Nginx front facing server, which would then direct requests to the flask app via WSGI.
It also handles serving the files in the "/static" directory.

Heavily relied on (to get logging right): https://fgimian.github.io/blog/2012/12/08/setting-up-a-rock-solid-python-development-web-server/

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

# General
import os
import cherrypy
from paste.translogger import TransLogger

# Config
from config.serverParams import serverParameters

# Flask app
from webApp import app

if __name__ == "__main__":
    if serverParameters.debug == True:
        # Enable WSGI access logging using paste
        appLogged = TransLogger(app)
    
    # Setup cherrypy to serve the flask app
    cherrypy.tree.graft(app, "/hello")

    # THe mount documentation is unclear, so it is explained here:
    # cherrypy.tree.mount(app - usually a cherrypy app but we will start it later, location to mount, configuration)
    #
    # staticPath here must start with a slash
    # absoluteStaticPath must be an absolute path. This will adapt to wherever the file is located.
    staticPath = os.path.join("/", serverParameters.staticFolder)
    absoluteStaticPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), serverParameters.staticFolder)
    print "staticPath = \"%s\", absoluteStaticPath = \"%s\"" % (staticPath, absoluteStaticPath)
    # This serves the url "/static". The "/" is mounted at absoluteStaticPath, 
    # so whenever "/static" is hit, then it goes to files in absoluteStaticPath.
    cherrypy.tree.mount(None, "/static", {
                     "/" : {
                        "tools.staticdir.on": True,
                        "tools.staticdir.dir": absoluteStaticPath
                     }
                })

    # Configure the server properties
    serverConfig = {
        "server.socket_host": serverParameters.ipAddress,
        "server.socket_port": serverParameters.port
    }

    # Configure debug and logging properties
    if serverParameters.debug == True:
        serverConfig["engine.autoreload.on"] = True
        serverConfig["log.screen"] = True
    else:
        serverConfig["engine.autoreload.on"] = False

    # Update the server configuration
    cherrypy.config.update(serverConfig)

    # Start the server
    cherrypy.engine.start()
    cherrypy.engine.block()
