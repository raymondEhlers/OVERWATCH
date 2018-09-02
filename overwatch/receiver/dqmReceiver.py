#!/usr/bin/env python
""" WSGI Server for handling POST requests containing DQM data.

This module defines a REST API for receiving files via POST request. It is a relatively simple module.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

# For python 3 support
from __future__ import print_function
from future.utils import iteritems

import os
import time
import functools
import logging
logger = logging.getLogger(__name__)

from overwatch.base import config
(receiverParameters, filesRead) = config.readConfig(config.configurationType.receiver)

from flask import Flask, request, send_from_directory, jsonify, url_for
from werkzeug.utils import secure_filename

import ROOT
# Fix Flask debug mode with ROOT 5 issue.
# See: https://root-forum.cern.ch/t/pyroot-and-spyder-re-running-error/20926/5
ROOT.std.__file__ = "ROOT.std.py"
#import rootpy.io
#import rootpy.ROOT as ROOT

app = Flask(__name__)

# Ensure the folder to write to exists.
if not os.path.exists(receiverParameters["dataFolder"]):
    os.makedirs(receiverParameters["dataFolder"])

# From: http://flask.pocoo.org/docs/0.12/patterns/apierrors/
class InvalidUsage(Exception):
    """ Provide an expressive error message for invalid REST API usage.

    This allows us to raise an exception which contains a message, as well as a possible payload,
    returning that information to inform them about the issue.

    Args:
        message (str): Message to accompany the error.
        status_code (int): HTTP status code which should be returned. Default: 400.
        payload (dict): Additional information relevant to the error that should be provided.

    Attributes:
        status_code (int): The HTTP status code to return. We send 400, as this class corresponds to an error.
    """
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
def handleInvalidUsage(error):
    """ Error handler which converts the ``InvalidUsage`` exception into a response.

    The idea here is that an exception is not meaningful for flask - it doesn't know how to return
    it to the user. To address this issue, this function converts the ``InvalidUsage`` into something
    that is understandable and can be returned to the user.

    Args:
        error (InvalidUsage): The exception which we want to raise.
    Returns:
        Response: Response containing information about the error.
    """
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

def checkForToken(func):
    """ Check for a special token in the request header to identify it as a known request.

    This basically serves as a rudimentary identification function. However, it doesn't need
    to be sophisticated for our purposes.

    Args:
        func (function): Routing function to be wrapped.
    Returns:
        Any: Wrapped function.
    """
    # While using ``wraps`` is good practice, it also serves another purpose here.
    # In particular, ``wraps`` is necessary to ensure that function names don't collide.
    # See: https://stackoverflow.com/a/42254713 and the comments for more information.
    @functools.wraps(func)
    def decoratedCheckToken(*args, **kwargs):
        """ Check for a special token in the request header to identify it as a known request.

        The token must exist in the header, and it also must match the expected token value set
        in the configuration. The name of the field in the header is ``token``.

        Args:
            *args (list): Arguments to be passed to the function if the token is valid.
            **kwargs (dict): Arguments to be passed to the function if the token is valid.
        Returns:
            Any: Executes the function with the given arguments if the token is valid, or
                if not, it raises an exception.

        Raises:
            InvalidUsage: If the token is missing or is invalid.
        """
        if "token" not in request.headers:
            raise InvalidUsage("Must pass a token!")

        # Execute the function if the token matches.
        logger.debug("Token: {token}".format(token = request.headers["token"]))
        if request.headers["token"] == receiverParameters["apiToken"]:
            return func(*args, **kwargs)

        # Notify that the request was invalid due to an invalid token.
        # Note that it is invalid otherwise.
        raise InvalidUsage("Received token, but it is invalid!")

    return decoratedCheckToken

@app.route("/", methods = ["GET", "POST"])
@checkForToken
def index():
    """ General redirect if a request is sent to the root route.

    It is an invalid request, so we just notify the user. Note that a token is still required
    to get to the invalid usage redirect. This means it can be a useful way to check if the
    token is being passed properly.

    Args:
        None.
    Returns:
        None.

    Raises:
        InvalidUsage: Any request here is invalid, so it is always raised.
    """
    raise InvalidUsage("Not implemented")

@app.route("/rest/api/files", methods = ["GET", "POST"])
@checkForToken
def dqm():
    """ Receive files from the DQM system.

    For further information on the REST API (which is partially defined here), see
    :doc:`the DQM receiver README </dqmReceiverReadme>`__. It contains a comprehensive description of the
    APIs described here.

    Args:
        None. A complex set of header is required, as is the file. For more information on these requirements,
            see the API reference.
    Returns:
        Response: ``JSON`` based response which contains information about the file received, or the error messages.
            See the API reference for a comprehensive description of the possible responses.
    """
    response = {}
    # Handle the "GET request"
    if request.method == "GET":
        availableFiles = [f for f in os.listdir(receiverParameters["dataFolder"]) if os.path.isfile(os.path.join(receiverParameters["dataFolder"], f) and "DQM" in f)]
        response["files"] = availableFiles
        resp = jsonify(response)
        resp.status_code = 200
        return resp

    # From here, we handle the POST request.
    # Print received header information to aid in understand the request from the log.
    logger.info("Headers:")
    requestHeaders = {}
    for header, val in iteritems(request.headers):
        logger.debug("\"{header}\":, \"{val}\"".format(header = header, val = val))
        requestHeaders[header] = val

    # Return the header to aid the user in understanding the request they made.
    response["receivedHeaders"] = requestHeaders

    # Get header information
    # Rudimentary validation is provided by attempting to convert to the proper types.
    # More sophisticated validation would be better, but as of August 2018, this is fine.
    try:
        runNumber = int(request.headers.get("runNumber", -1))
        timestamp = int(request.headers.get("timeStamp", -1))
        # TODO: Fully implement `dataStatus`. For now, we retrieve it, but don't take advantage of it.
        dataStatus = int(request.headers.get("dataStatus", -1))  # NOQA
        # Default to "DQM" if the agent cannot be found
        agent = str(request.headers.get("amoreAgent", "DQM"))
    except ValueError as e:
        # If one of the types is wrong, pass on the error message to the user
        response["message"] = e.args
        response["received"] = None
        resp = jsonify(response)
        resp.status_code = 400
        return resp

    # Convert timestamp to desired format.
    # Format is "SUBSYSTEMhistos_runNumber_hltMode_time.root".
    # For example, "EMChistos_123456_B_2015_3_14_2_3_5.root".
    unixTime = float(timestamp)
    timeTuple = time.gmtime(unixTime)
    # NOTE: these values are zero padded! However, this should be fine.
    timeStr = time.strftime("%Y_%m_%d_%H_%M_%S", timeTuple)
    logger.info("timeStr: {timeStr}".format(timeStr = timeStr))

    # Determine the filename
    # For now, the file mode is hard-coded here to be "DQM".
    # If the mode needs to be one letter, perhaps make it "Z" to make it obvious or "D" for DQM?
    filename = "{amoreAgent}histos_{runNumber}_{mode}_{timestamp}.root".format(amoreAgent = agent, runNumber = runNumber, mode = "DQM", timestamp = timeStr)
    # Just to be safe!
    filename = secure_filename(filename)
    outputPath = os.path.join(receiverParameters["dataFolder"], filename)

    # Handle body.
    # While apparently simple, there can be quite a large number of details to consider.
    # For further information, see:
    # - http://flask.pocoo.org/docs/0.12/patterns/fileuploads/
    # - https://pythonhosted.org/Flask-Uploads/
    # - https://stackoverflow.com/questions/10434599/how-to-get-data-received-in-flask-request
    savedFile = False
    if "file" in request.files:
        # Handle multi-part file request. This is the preferred method!
        # We expect the file to be sent under the key "file".

        # Get file
        logger.info("Handling file in form via form/multi-part")
        payloadFile = request.files["file"]

        # Save it out
        payloadFile.save(outputPath)
        savedFile = True
    else:
        # Get the payload by hand. This is strongly disfavored, such that it isn't documented
        # in the API reference.
        logger.info("Handling payload directly")
        # Can use request.stream to get the data in an unmodified way
        # Can use request.data to get the data as a string
        # Can use request.get_data() to get all non-form data as the bytes of whatever is in the body
        payload = request.get_data()
        logger.info("payload: {payload}".format(payload = payload[:100]))
        if payload:
            # Not opening as ROOT file since we are just writing the bytes to a file
            with open(outputPath, "wb") as fOut:
                fOut.write(payload)

            savedFile = True
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

    print(url_for("returnFile", filename = "test_val.root"))

    # Print and return
    logger.info("Response: {response}, resp: {resp}".format(response = response, resp = resp))
    return resp

def receivedObjectInfo(outputPath):
    """ Print the ROOT objects in a received file.

    Helper function to confirm that the file was transferred successfully by reading the objects
    contained within.

    Args:
        outputPath (str): Name of the file.
    Returns:
        tuple: (bool, dict). The bool is ``True`` if we were successful in opening the file. The dict contains
            information on the objects available in the file. The keys (str) are the object names, while the
            values (str) are descriptions of the objects in the file, including the filename and the type of object.
    """
    # Setup.
    success = False
    fOut = ROOT.TFile.Open(outputPath, "READ")
    keys = fOut.GetListOfKeys()

    # Iterate over the available objects.
    receivedObjects = {}
    for key in keys:
        obj = key.ReadObj()
        receivedObjects[key.GetName()] = "Obj name: {}, Obj IsA() Name: {}".format(obj.GetName(), obj.IsA().GetName())
        success = True

    # Print to log for convenience
    logger.info(receivedObjects)

    return (success, receivedObjects)

@app.route("/rest/api/files/<string:filename>", methods = ["GET"])
@checkForToken
def returnFile(filename):
    """ Return the ROOT file which was previously sent to the receiver.

    For further information on the REST API (which is partially defined here), see
    :doc:`the DQM receiver README </dqmReceiverReadme>`__. It contains a comprehensive description of the
    APIs described here.

    Args:
        filename (str): Name of desired file.
    Returns:
        Response: The requested file.
    """
    filename = secure_filename(filename)
    logger.debug("filename: {}".format(filename))
    # It is extremely important that the directory be an absolute path!
    return send_from_directory(os.path.realpath(receiverParameters["dataFolder"]), filename)

if __name__ == "__main__":
    # This module shouldn't be executed this way.
    raise RuntimeError("Run with overwatchDQMReceiver instead of directly!")
