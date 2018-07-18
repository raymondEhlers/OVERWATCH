#!/usr/bin/env python
""" WSGI Server for handling POST requests containing DQM data.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

# For python 3 support
from __future__ import print_function
from future.utils import iteritems

# Python logging system
import logging

from overwatch.base import config
# For configuring logger
from overwatch.base import utilities
(receiverParameters, filesRead) = config.readConfig(config.configurationType.dqmReceiver)

# Setup logger
# When imported, we just want it to take on it normal name
logger = logging.getLogger(__name__)
# Alternatively, we could set "overwatch.receiver" to get everything derived from that
#logger = logging.getLogger("overwatch.receiver")

from flask import Flask, url_for, request, render_template, redirect, flash, send_from_directory, Markup, jsonify, session
from werkzeug.utils import secure_filename

import os
import time
import functools
import ROOT
# Fix Flask debug mode with ROOT 5 issue.
# See: https://root-forum.cern.ch/t/pyroot-and-spyder-re-running-error/20926/5
ROOT.std.__file__ = "ROOT.std.py"
#import rootpy.io
#import rootpy.ROOT as ROOT

#app = Flask(__name__, static_url_path=serverParameters.staticURLPath, static_folder=serverParameters.staticFolder, template_folder=serverParameters.templateFolder)
app = Flask(__name__)

# Configuration
# Ensure the folder to write to exists
if not os.path.exists(receiverParameters["dataFolder"]):
    os.makedirs(receiverParameters["dataFolder"])

# From: http://flask.pocoo.org/docs/0.12/patterns/apierrors/
class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code = None, payload = None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

def checkForToken(func):
    # wraps is necessary to ensure that function names don't collide.
    # See: https://stackoverflow.com/a/42254713 and the comments
    @functools.wraps(func)
    def decoratedCheckToken(*args, **kwargs):
        """ Continue with the request if it's a valid token """
        if "token" not in request.headers:
            raise InvalidUsage("Must pass a token!")

        # Execute if the token matches
        logger.debug("Token: {0}".format(request.headers["token"]))
        if request.headers["token"] == receiverParameters["apiToken"]:
            return func(*args, **kwargs)

        # Note that it is invalid otherwise
        raise InvalidUsage("Invalid token!")
    return decoratedCheckToken

@app.route("/", methods=["GET", "POST"])
@checkForToken
def index():
    """ Redirect everything else. """
    raise InvalidUsage("Not implemented")

@app.route("/rest/api/files", methods=["GET", "POST"])
@checkForToken
def dqm():
    """ Handle DQM data """
    response = dict()
    if request.method == "GET":
        availableFiles = [f for f in os.listdir(receiverParameters["dataFolder"]) if os.path.isfile(os.path.join(receiverParameters["dataFolder"], f))]
        response["files"] = availableFiles
        resp = jsonify(response)
        resp.status_code = 200
        return resp

    # Print received header information
    logger.info("Headers:")
    requestHeaders = dict()
    for header, val in iteritems(request.headers):
        logger.debug("\"{0}\":, \"{1}\"".format(header, val))
        requestHeaders[header] = val

    response["receivedHeaders"] = requestHeaders

    # TODO: Validate (in real production...)!
    # Get header information
    runNumber = request.headers.get("runNumber", -1)
    timestamp = request.headers.get("timeStamp", -1)
    # TODO: Figure out how to handle this. Should it be a discrete route?
    dataStatus = request.headers.get("dataStatus", -1)
    # Default to "DQM" if the agent cannot be found
    agent = request.headers.get("amoreAgent", "DQM")

    # Convert timestamp to desired format
    unixTime = float(timestamp)
    timeTuple = time.gmtime(unixTime)
    # Format is SUBSYSTEMhistos_runNumber_hltMode_time.root
    # For example, EMChistos_123456_B_2015_3_14_2_3_5.root
    # TString filename = TString::Format("%shistos_%d_%s_%d_%d_%d_%d_%d_%d.root", fSubsystem.c_str(), fRunNumber, fHLTMode.c_str(), timestamp->tm_year+1900, timestamp->tm_mon+1, timestamp->tm_mday, timestamp->tm_hour, timestamp->tm_min, timestamp->tm_sec);
    # NOTE: these values are zero padded! However, this should be fine.
    timeStr = time.strftime("%Y_%m_%d_%H_%M_%S", timeTuple)
    logger.info("timeStr: {0}".format(timeStr))

    # If the mode needs to be one letter, perhaps make it "Z" to make it obvious or "D" for DQM?
    filename = "{amoreAgent}histos_{runNumber}_{mode}_{timestamp}.root".format(amoreAgent = agent, runNumber = runNumber, mode = "DQM", timestamp = timeStr)
    # Just to be safe!
    filename = secure_filename(filename)
    # True file path
    outputPath = os.path.join(receiverParameters["dataFolder"], filename)

    # Handle body
    # For more details, see:
    # - http://flask.pocoo.org/docs/0.12/patterns/fileuploads/
    # - https://pythonhosted.org/Flask-Uploads/
    # - https://stackoverflow.com/questions/10434599/how-to-get-data-received-in-flask-request
    savedFile = False
    if "file" in request.files:
        # Handle multi-part file request
        # This is the preferred method!

        # Get file
        logger.info("Handling file in form via form/multi-part")
        # NOTE: This means that the form object must be called "file"!
        payloadFile = request.files["file"]

        # Save it out
        payloadFile.save(outputPath)
        savedFile = True
    else:
        # Get the payload 
        logger.info("Handling payload directly")
        # Can use request.stream to get the data in an unmodified way
        # Can use request.data to get the data as a string
        # Can use request.get_data() to get all non-form data as the bytes of whatever is in the body
        payload = request.get_data()
        logger.info("payload: {0}".format(payload[:100]))
        if payload:
            # Not opening as ROOT file since we are just writing the bytes to a file
            with open(outputPath, "wb") as fOut:
                fOut.write(payload.encode())

            savedFile = True

            # For handling serialized objects (later)
            # Write out the object to file
            #with rootpy.io.File.Open(filename, "RECREATE") as fOut:

                # For the future, how would we handle a more complex payload?
                #for hist in payload:
                #    pass
                    # Can eval be used here? Or the safer literal_eval? -> Can't use literal_eval because it is too simple
                    # Perhaps the easiest is TMessage::WriteObject() and TMessage::ReadObject()? -> But how do I reconstruct the TMessage??
                    # May need to a two line c++ program to take a string of bytes and reinterpret_cast<TH1 *>(). Could just use gROOT.ProcessLine(...)
                    # pyyaml can serialize entire objects. Perhaps we can use it??
                    #hist.Write()
        else:
            logger.warning("No payload...")

    if savedFile:
        # Extract received object info
        (infoSuccess, receivedObjects) = receivedObjectInfo(outputPath)
        if infoSuccess:
            response["status"] = 200
            response["message"] = "Successfully received file and extracted information"
            response["received"] = receivedObjects
        else:
            response["status"] = 400
            response["message"] = "Successfully received the file, but the file is not valid! Perhaps it was corrupted?"
            response["received"] = None

        # Same in both cases
        response["filename"] = filename
    else:
        response["status"] = 400
        response["message"] = "No file uploaded and the payload was empty"
        response["received"] = None

    # Properly set the status code
    resp = jsonify(response)
    resp.status_code = response["status"]

    # Print and return
    logger.info("Response: {0}, resp: {1}".format(resp, response))
    return resp

def receivedObjectInfo(outputPath):
    """ Print the objects in the received file """
    # Open the root file and print the object information
    success = False
    fOut = ROOT.TFile.Open(outputPath, "READ")
    keys = fOut.GetListOfKeys()

    receivedObjects = dict()
    for key in keys:
        obj = key.ReadObj()
        receivedObjects[key.GetName()] = "Obj name: {0}, Obj IsA() Name: {1}".format(obj.GetName(), obj.IsA().GetName())
        success = True

    # Print to log for convenience
    logger.info(receivedObjects)

    return (success, receivedObjects)

@app.route("/rest/api/files/<string:filename>", methods=["GET"])
@checkForToken
def returnFile(filename):
    """ Return the ROOT file. """
    filename = secure_filename(filename)
    return send_from_directory(receiverParameters["dataFolder"], filename)

if __name__ == "__main__":
    print("Run with overwatchDQMReceiver instead of directly!")
