#!/usr/bin/env python

# For python 3 support
from __future__ import print_function

import os
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

app.config["ZODB_STORAGE"] = "file://../../data/overwatch.fs"
#app.config["ZODB_STORAGE"] = serverParameters["databaseLocation"]
db = ZODB(app)
dirPrefix = "dirPrefixPlaceholder"

class Runs(flask_restful.Resource):
    def get(self, run = None):
        # TODO: Validate
        print("run: {0}".format(run))

        runs = db["runs"]
        response = {}
        if not run:
            # List runs
            response["runs"] = list(runs.keys())
            print("response: {0}".format(response))
            return response

        # Return information on a particular run
        response["run"] = run
        response["subsystems"] = list(runs["Run{0}".format(run)].subsystems.keys())
        return response

    def put(self, run):
        # NOT IMPLEMENTED
        pass

class FilesAccess(flask_restful.Resource):
    def get(self, run, subsystem, filename = None):
        # TODO: Validate

        # Return the filename for the particular run
        subsystemContainer = db["runs"]["Run{0}".format(run)].subsystems[subsystem]

        # TODO: Return response?
        response = {}
        response["run"] = run
        response["subsystem"] = subsystem
        if not filename:
            # Return the available files
            response["files"] = [tempFile.filename.split("/")[-1] for tempFile in subsystemContainer.files.values()]
            return response
        elif filename == "combined":
            # Return the combined file
            return os.path.join(dirPrefix, subsystemContainer.combinedFile.filename)
            
        #requestedFile = next(fileContainer for fileContainer in subsystemContainer.files.values() if fileContainer.filename == filename)
        print(filename)
        print(subsystemContainer.files.itervalues().next().filename)
        try:
            requestedFile = next(fileContainer for fileContainer in subsystemContainer.files.values() if fileContainer.filename.split("/")[-1] == filename)
        except StopIteration as e:
            response["error"] = "Could not find requested file {0}".format(filename)
            return response
        return os.path.join(dirPrefix, requestedFile.filename)

    def put(self, run, filename):
        # NOT IMPLEMENTED
        # TODO: Can the DQM receiver be implemented here?
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
