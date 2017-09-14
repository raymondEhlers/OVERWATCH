#!/usr/bin/env python

# For python 3 support
from __future__ import print_function

# Python logging system
import logging

#from overwatch.base import config
## For configuring logger
#from overwatch.base import utilities
#(receiverParameters, filesRead) = config.readConfig(config.configurationType.dqmReceiver)

# Setup logger
# When imported, we just want it to take on it normal name
logger = logging.getLogger(__name__)
# Alternatively, we could set "overwatch.receiver" to get everything derived from that
#logger = logging.getLogger("overwatch.receiver")

from flask import Flask, url_for, request, render_template, redirect, flash, send_from_directory, Markup, jsonify, session
import flask_restful
from flask_zodb import ZODB

app = Flask(__name__)
api = flask_restful.Api(app)

#app.config["ZODB_STORAGE"] = serverParameters["databaseLocation"]
#db = ZODB(app)

class Runs(flask_restful.Resource):
    def get(self, run = None):
        print("run: {0}".format(run))
        if not run:
            # List runs
            return "Get no args"
        # Return information on a particular run
        return "Get with run {0}".format(run)

    def put(self, run):
        # NOT IMPLEMENTED
        pass

class FilesAccess(flask_restful.Resource):
    def get(self, run, subsystem, filename = None):
        # Return the filename for the particular run

        if not filename:
            # Return the combined file
            return "No filename passed"
            
        return "Filename : {0}".format(filename)
        pass

    def put(self, run, filename):
        # NOT IMPLEMENTED
        pass

api.add_resource(FilesAccess, "/rest/api/v1/files/<int:run>/<string:subsystem>",
                              "/rest/api/v1/files/<int:run>/<string:subsystem>/<string:filename>")
# Redundant view
#api.add_resource(FilesAccess, "/rest/api/v1/files/<int:run>")
api.add_resource(Runs, "/rest/api/v1/runs",
                       "/rest/api/v1/runs/<int:run>")
#api.add_resource(Run, "/rest/api/v1/runs/<int:run>")

if __name__ == "__main__":
    app.run(debug = True)
