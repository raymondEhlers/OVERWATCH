#!/usr/bin/env python

# For python 3 support
from __future__ import print_function

import os
# Python logging system
import logging

# Configuration
from overwatch.base import config
## For configuring logger
from overwatch.base import utilities
(apiParameters, filesRead) = config.readConfig(config.configurationType.apiConfig)

# Setup logger
# When imported, we just want it to take on it normal name
logger = logging.getLogger(__name__)
# Alternatively, we could set "overwatch.receiver" to get everything derived from that
#logger = logging.getLogger("overwatch.receiver")

from flask import Flask, url_for, request, render_template, redirect, flash, send_from_directory, Markup, jsonify, session, make_response
import flask_restful
import flask_zodb
from werkzeug.utils import secure_filename

app = Flask(__name__)
api = flask_restful.Api(app)

app.config["ZODB_STORAGE"] = apiParameters["databaseLocation"]
#app.config["ZODB_STORAGE"] = "file://../../data/overwatch.fs"
db = flask_zodb.ZODB(app)
#dirPrefix = "dirPrefixPlaceholder"

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

def responseForSendingFile(filename = None, response = None, additionalHeaders = {}):
    if not filename and not response:
        raise InputError("Must pass filename or response")

    # Open file and make response if requested
    if filename and not response:
        response = make_response(send_from_directory(os.path.realpath(apiParameters["dirPrefix"]), filename))

    # Add requested filenames
    if "filenames" in additionalHeaders:
        additionalHeaders["filenames"] = ";".join(additionalHeaders["filenames"])

    # Add headers to response
    for k, v in additionalHeaders.iteritems():
        if k in response.headers.keys():
            print("WARNING: Header {} (value: {}) already exists in the response and will be overwritten".format(k, response.headers[k]))
        response.headers[k] = v

    return response

class FilesAccess(flask_restful.Resource):
    def get(self, run, subsystem, filename = None):
        # TODO: Validate

        # Return the filename for the particular run
        subsystemContainer = db["runs"]["Run{0}".format(run)].subsystems[subsystem]

        responseHeaders = {}
        responseHeaders["run"] = run
        responseHeaders["run"] = run
        responseHeaders["subsystem"] = subsystem
        responseHeaders["filenames"] = []
        if not filename:
            # Return the available files
            responseHeaders["filenames"] = [tempFile.filename.split("/")[-1] for tempFile in subsystemContainer.files.values()]
            return responseForSendingFile(response = make_response(), additionalHeaders = responseHeaders)
        elif filename == "combined":
            # Return the combined file
            responseHeaders["filenames"].append(os.path.join(apiParameters["dirPrefix"], subsystemContainer.combinedFile.filename))
            response = responseForSendingFile(filename = subsystemContainer.combinedFile.filename, additionalHeaders = responseHeaders)
            print("response: {}".format(response))
            return response
            #response["files"] = send_from_directory(os.path.realpath(apiParameters["dirPrefix"]), subsystemContainer.combinedFile.filename)
            #response = make_response(send_from_directory(os.path.realpath(apiParameters["dirPrefix"]), subsystemContainer.combinedFile.filename))
            #print(send_from_directory(os.path.realpath(apiParameters["dirPrefix"]), subsystemContainer.combinedFile.filename))
            #print("response: {}".format(response))
            #return jsonify(response)
            #for k, v in responseHeaders.iteritems():
            #    response.headers[k] = v
            #return response
            
        #requestedFile = next(fileContainer for fileContainer in subsystemContainer.files.values() if fileContainer.filename == filename)
        print(filename)
        print(subsystemContainer.files.itervalues().next().filename)
        try:
            requestedFile = next(fileContainer for fileContainer in subsystemContainer.files.values() if fileContainer.filename.split("/")[-1] == filename)
        except StopIteration as e:
            #responseHeaders["error"] = "Could not find requested file {0}".format(filename)
            response = responseForSendingFile(additionalHeaders = responseHeaders)
            response.body = "Error: Could not find requested file {0}".format(filename)
            return response

        responseHeaders["filenames"].append(os.path.join(apiParameters["dirPrefix"], requestedFile.filename))
        return responseForSendingFile(filename = requestedFile.filename, additionalHeaders = responseHeaders)
        #response = make_response(end_from_directory(apiParameters["dirPrefix"], requestedFile.filename))
        #for k, v in responseHeaders.iteritems():
        #    response.headers[k] = v
        #return response

    def put(self, run, subsystem, filename):
        # Validate input!

        # Store passed file

        # Just to be safe!
        filename = secure_filename(filename)

        print("request: ".format(request))

        savedFile = False
        if "file" in request.files:
            # Handle multi-part file request
            # This is the preferred method!

            # Get file
            logger.info("Handling file in form via form/multi-part")
            # NOTE: This means that the form object must be called "file"!
            payloadFile = request.files["file"]
            print("payloadFile: {}".format(payloadFile))

            # Save it out
            #payloadFile.save(outputPath)
            #savedFile = True

        return "True"

api.add_resource(FilesAccess, "/rest/api/v1/files/<int:run>/<string:subsystem>",
                              "/rest/api/v1/files/<int:run>/<string:subsystem>/<string:filename>")
# Redundant view
#api.add_resource(FilesAccess, "/rest/api/v1/files/<int:run>")
api.add_resource(Runs, "/rest/api/v1/runs",
                       "/rest/api/v1/runs/<int:run>")
#api.add_resource(Run, "/rest/api/v1/runs/<int:run>")

if __name__ == "__main__":
    app.run(debug = True)
