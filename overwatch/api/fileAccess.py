#!/usr/bin/env python

# For python 3 support
from __future__ import print_function
from future.utils import iteritems
from future.utils import itervalues

import os
# Python logging system
import logging

# Configuration
from overwatch.base import config
## For configuring logger
from overwatch.base import utilities
from overwatch.base import storageWrapper
(apiParameters, filesRead) = config.readConfig(config.configurationType.api)

# Setup logger
# When imported, we just want it to take on it normal name
logger = logging.getLogger(__name__)
# Alternatively, we could set "overwatch.receiver" to get everything derived from that
#logger = logging.getLogger("overwatch.receiver")

from flask import Flask, url_for, request, render_template, redirect, flash, send_file, send_from_directory, Markup, jsonify, session, make_response, stream_with_context, Response
import flask_restful
import flask_zodb
from io import StringIO
from werkzeug.utils import secure_filename

app = Flask(__name__)
api = flask_restful.Api(app)

app.config["ZODB_STORAGE"] = apiParameters["databaseLocation"]
#app.config["ZODB_STORAGE"] = "file://../../data/overwatch.fs"
db = flask_zodb.ZODB(app)
#dirPrefix = "dirPrefixPlaceholder"

# Handle storage
openFile = storageWrapper.defineFileAccess("data")

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
        response = make_response()

    # Open file and make response if requested
    if filename and not response:
        # TODO: Handle various file sources
        # TODO: Use safe_join
        #response = make_response(send_from_directory(os.path.realpath(apiParameters["dirPrefix"]), filename))
        print("About to open file with new function")
        with openFile(filename, "r") as f:
            response = make_response(send_file(f, attachment_filename = filename, as_attachment = True))

    # Add requested filenames
    if "filenames" in additionalHeaders:
        additionalHeaders["filenames"] = ";".join(additionalHeaders["filenames"])

    # Add headers to response
    for k, v in iteritems(additionalHeaders):
        if k in response.headers.keys():
            print("WARNING: Header {} (value: {}) already exists in the response and will be overwritten".format(k, response.headers[k]))
        response.headers[k] = v

    return response

class FilesAccess(flask_restful.Resource):
    def get(self, run, subsystem, filename = None):
        # TODO: Validate
        responseHeaders = {}
        responseHeaders["run"] = run
        responseHeaders["subsystem"] = subsystem
        responseHeaders["filenames"] = []

        # Return the filename for the particular run
        subsystemContainer = db["runs"]["Run{0}".format(run)].subsystems[subsystem]

        # Handle special cases
        if not filename:
            # Return the available files
            responseHeaders["filenames"] = [tempFile.filename.split("/")[-1] for tempFile in subsystemContainer.files.values()]
            return responseForSendingFile(additionalHeaders = responseHeaders)
        elif filename == "combined":
            # Return the combined file
            responseHeaders["filenames"].append(os.path.join(apiParameters["dirPrefix"], subsystemContainer.combinedFile.filename))
            response = responseForSendingFile(filename = subsystemContainer.combinedFile.filename, additionalHeaders = responseHeaders)
            print("response: {}".format(response))
            return response

        #filename = secure_filename(filename)

        # Look for the file
        print(next(itervalues(subsystemContainer.files)).filename)
        try:
            requestedFile = next(fileContainer for fileContainer in subsystemContainer.files.values() if fileContainer.filename.split("/")[-1] == filename)
        except StopIteration as e:
            print("Stop iteration error!")
            response = responseForSendingFile(additionalHeaders = responseHeaders)
            response.headers["error"] = "Could not find requested file {0}".format(filename)
            response.status_code = 404
            return response

        print("filename for requested file: {}".format(os.path.join(apiParameters["dirPrefix"], requestedFile.filename)))
        responseHeaders["filenames"].append(os.path.join(apiParameters["dirPrefix"], requestedFile.filename))
        #f = open(os.path.join(apiParameters["dirPrefix"], requestedFile.filename))
        #return make_response(send_file(f, as_attachment = True, attachment_filename = filename))
        #with open(os.path.join(apiParameters["dirPrefix"], requestedFile.filename)) as f:
        with openFile(requestedFile.filename, "rb") as f:
            # If StringIO is not used here then the file will go out of scope and be closed before the
            # response is completed, which leads to "ValueError: I/O operation on closed file".
            # I cannot seem to find a way around this. However, the file cannot just be opened, as otherwise
            # it will leak memory.
            # For more, see: https://stackoverflow.com/q/13344538 (no definitive solution)
            #                https://stackoverflow.com/a/25150805 (gave me the idea to just create a new StringIO)
            # StringIO was selected based on https://stackoverflow.com/a/37463095
            return make_response(send_file(StringIO.StringIO(f.read()), as_attachment = True, attachment_filename = filename))

        #with openFile(requestedFile.filename, "rb") as f:
        #    f.seek(0)
        #    def readFile(*args, **kwargs):
        #        for chunk in iter(lambda: f.read(4096), b''):
        #            yield chunk
        #    return Response(stream_with_context(readFile()))
            #return make_response(send_file(f, attachment_filename = filename, as_attachment = True))
        #return responseForSendingFile(filename = requestedFile.filename, additionalHeaders = responseHeaders)

    def put(self, run, subsystem, filename):
        # Decided on put based on https://stackoverflow.com/a/630475
        # TODO: Validate input!

        # Just to be safe!
        filename = secure_filename(filename)

        # Store passed file
        savedFile = False
        if "file" in request.files:
            # Handle multi-part file request
            # This is the preferred method!

            # Get file
            logger.info("Handling file in form via form/multi-part")
            # NOTE: This means that the form object must be called "file"!
            payloadFile = request.files["file"]
            print("payloadFile: {}".format(payloadFile))
            # Read for notes and then reset to the start
            #print("payloadFile.read: {}".format(payloadFile.read()))
            #payloadFile.seek(0)

            # Save it out
            # TODO: Handle writing to the proper source
            outputPath = os.path.join("Run{0}".format(run), subsystem, filename)
            #payloadFile.save(outputPath)

            with openFile(outputPath, "w+") as f:
                f.write(payloadFile.read().encode())

            savedFile = True
        else:
            savedFile = False
            raise Exception("No valid file passed.")

        return savedFile

api.add_resource(FilesAccess, "/rest/api/v1/files/<int:run>/<string:subsystem>",
                              "/rest/api/v1/files/<int:run>/<string:subsystem>/<string:filename>")
# Redundant view
#api.add_resource(FilesAccess, "/rest/api/v1/files/<int:run>")
api.add_resource(Runs, "/rest/api/v1/runs",
                       "/rest/api/v1/runs/<int:run>")
#api.add_resource(Run, "/rest/api/v1/runs/<int:run>")

if __name__ == "__main__":
    #app.run(debug = True)
    app.run(use_reloader = True)
