#!/usr/bin/env python

""" Tests for the DQM receiver module.

Note that these tests are not quite ideal, as they rely on the default implementation
for the configuration and modules (which can change), but using this implementation
takes much less time than mocking objects.

.. code-author: Raymond Ehlers <raymond.ehlers@yale.edu>, Yale University
"""

from future.utils import iteritems

import pytest
import os
import io
import logging
logger = logging.getLogger(__name__)

from overwatch.receiver.dqmReceiver import app
import overwatch.receiver.dqmReceiver as receiver

@pytest.fixture
def client(loggingMixin, mocker):
    """ Setup the flask client for testing.

    For further information, see the `flask docs <http://flask.pocoo.org/docs/1.0/testing/>`__. However, note that
    they will need to be supplemented by further information because their API doc isn't entirely comprehensive.
    (For example, adding headers is not super well documented).
    """
    # Basic client
    app.config['TESTING'] = True
    client = app.test_client()

    # Use local files in the receiver test directory.
    receiver.receiverParameters["dataFolder"] = os.path.join(os.path.dirname(os.path.realpath(__file__)), "testFiles")
    # Grab the valid token dynamically
    validToken = receiver.receiverParameters["apiToken"]

    yield (client, validToken)

    # Could perform clean-up if necessary

@pytest.mark.parametrize("headers, expectedMessage, expectedStatusCode", [
    ({}, "Must pass a token!", 400),
    ({"token": "123456"}, "Received token, but it is invalid!", 400),
    (None, "Not implemented", 400),
], ids = ["No token", "Invalid token", "Valid token"])
def testTokenVerification(client, headers, expectedMessage, expectedStatusCode):
    """ Test token verification and it's possible failure modes.

    In the case of a valid token, we continue with the request to `/`, which will then respond
    with "Not implemented".
    """
    client, validToken = client
    if headers is None:
        headers = {"token": validToken}

    # Send the request
    rv = client.get("/", headers = headers)
    rvDict = rv.get_json()

    # Check the response
    assert rvDict["message"] == expectedMessage
    assert rv.status_code == expectedStatusCode

def testGetFileListing(client):
    """ Test GET requests for file listing. """
    client, validToken = client

    rv = client.get("/rest/api/files", headers = {"token": validToken})
    rvDict = rv.get_json()

    # This explicitly ignores the other file in the directory, as expected.
    assert rvDict["files"] == ["EMChistos_123456_DQM_1970_01_02_16_07_24.root"]

def testGetFile(client):
    """ Test retrieving a file. """
    # Setup.
    client, validToken = client
    basePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "testFiles")
    # Filename for the file that we receive.
    filename = "EMChistos_123456_DQM_1970_01_02_16_07_24.root"
    # Determine the content that we expect. We are just going to look at the binary
    # bytes from the ROOT file.
    with open(os.path.join(basePath, filename), "rb") as f:
        expectedText = f.read()

    # Make the request and handle the received file.
    rv = client.get("/rest/api/files/{filename}".format(filename = filename), headers = {"token": validToken})
    # The file contents are just available as the data from the response.

    assert rv.data == expectedText

@pytest.fixture
def sendPostRequest(client):
    """ Setup the objects needed to make a successful POST request.

    This includes opening the ROOT file that will be sent and formatting it in the proper
    way within the dictionary. When the test is finished, the fixture then restores the
    to be certain that we haven't corrupted our test file when overwriting it.
    """
    client, validToken = client
    basePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "testFiles")
    # We take the contents of a ROOT file, send that file, and then compare against it.
    # This file will be overwritten when the file is received in the POST request, but
    # this fine because we can compare to the contents that we extract here. It can be
    # checked at the end of the test.
    filename = "EMChistos_123456_DQM_1970_01_02_16_07_24.root"
    # Create a dict to hold the file contents.
    with open(os.path.join(basePath, filename), "rb") as f:
        fileText = f.read()
    # For the file to be sent correctly, it is required that the file contents are
    # wrapped in `BytesIO`!
    data = {"file": (io.BytesIO(fileText), "file")}

    # Header information
    headers = {
        "runNumber": 123456,
        "timeStamp": 140844,
        "amoreAgent": "EMC",
        "dataStatus": 1,
        "token": validToken,
    }

    yield (client, validToken, basePath, filename, fileText, data, headers)

    # Restore the original (possibly overwritten) file once we are done to be certain
    # that the original file is intact!
    with open(os.path.join(basePath, filename), "wb") as f:
        f.write(fileText)

def testPostFile(sendPostRequest):
    """ Test sending a file via post. """
    # Setup.
    client, validToken, basePath, filename, fileText, data, headers = sendPostRequest

    # Make the request.
    rv = client.post("/rest/api/files",
                     content_type = "multipart/form-data",
                     data = data,
                     headers = headers)
    rvDict = rv.get_json()

    # Check message details.
    assert rv.status_code == 200
    assert rvDict["message"] == "Successfully received file and extracted information"
    assert rvDict["filename"] == "EMChistos_123456_DQM_1970_01_02_16_07_24.root"
    assert rvDict["received"] == {"test": "Obj name: test, Obj IsA() Name: TH1F"}

    # Check that the file didn't get mangled in transit but comparing the contents
    # before sending with the contents after.
    # NOTE: Although the filename is the same, the file has actually been overwritten
    #       by sending the POST request. So we are effectively opening a "new" file and
    #       this comparison is actually meaningful.
    with open(os.path.join(basePath, filename), "rb") as f:
        comparisonText = f.read()
    assert comparisonText == fileText

@pytest.mark.parametrize("data, expectedMessage, addToHeaders", [
    ({}, "No file uploaded and the payload was empty", {}),
    ({"file": (io.BytesIO(b"Hello world"), "file")}, "Successfully received the file, but the file is not valid! Perhaps it was corrupted?", {}),
    ({}, ["invalid literal for int() with base 10: 'Hello world'"], {"runNumber": "Hello world"}),  # The data here doesn't matter, so we leave it blank.
    ({}, ["invalid literal for int() with base 10: 'Hello world'"], {"timeStamp": "Hello world"}),  # The data here doesn't matter, so we leave it blank.
    ({}, ["invalid literal for int() with base 10: 'Hello world'"], {"dataStatus": "Hello world"}),  # The data here doesn't matter, so we leave it blank.
], ids = ["Empty data", "Non-ROOT (text) file", "Invalid run number header value", "Invalid time stamp header value", "Invalid data status header value"])
def testPostFileErrors(sendPostRequest, data, expectedMessage, addToHeaders):
    """ Test possible errors that could occur when sending the file.

    This also checks for validation of passed header values.
    """
    # Setup.
    client, validToken, basePath, filename, fileText, _, headers = sendPostRequest
    for k, v in iteritems(addToHeaders):
        headers[k] = v

    # First, we test no payload.
    rv = client.post("/rest/api/files",
                     content_type = "multipart/form-data",
                     data = data,
                     headers = headers)
    rvDict = rv.get_json()

    # Check error message details.
    assert rv.status_code == 400
    assert rvDict["message"] == expectedMessage

