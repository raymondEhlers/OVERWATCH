""" Contains validation functions.

These functions are important to ensure that only valid values are passed to the processing functions.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University 

"""

# General
import json
from flask import request
# Parse GET parameters
try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

# Config
#from config.serverParams import serverParameters
from ..base import config
(serverParameters, filesRead) = config.readConfig(config.configurationType.webApp)

# Logging
import logging
# Setup logger
logger = logging.getLogger(__name__)

###################################################
def validateLoginPostRequest(request):
    """ Validates the login POST request.
    
    Note:
        The error format is different here. Instead of a list in a dict, we simply have a string.

    Args:
        request (Flask.request): The request object from Flask.

    Return
        tuple: Tuple containing:

            errorValue (str): Contains the error that occured.

            username (str): Username extracted from POST request.

            password (str): Password extracted from POST request.

    """
    errorValue = None
    try:
        username = request.form.get("username", type=str)
        password = request.form.get("password", type=str)
    except KeyError as e:
        errorValue = "Key error in " + e.args[0] + ". Please enter a username and password in the form."

    return (errorValue, username, password)

###################################################
def validateTimeSlicePostRequest(request, runs):
    """ Validates the time slice POST request.

    Args:
        request (Flask.request): The request object from Flask.

    Returns:
        tuple: Tuple containing:

            errorValue (dict): Dict containing errors. Allows appending so that now errors are lost.
                Ex: ``errors = {'hello2': ['world', 'world2', 'world3'], 'hello': ['world', 'world2']}``

            minTime (float): The minimum time for the partial merge.

            maxTime (float): The maximum time for the partial merge.

            runDir (str): The run for which the partial merge should be performed.

            subsystemName (str): The current subsystem by three letter, all capital name (ex. ``EMC``).

            scrollAmount (float): The amount to scroll down the page to return to precisely where the user was previously.

    """
    error = {}
    try:
        minTime = request.form.get("minTime", -1, type=float)
        maxTime = request.form.get("maxTime", None, type=float)
        runDir = request.form.get("runDir", None, type=str)
        subsystemName = request.form.get("subsystem", None, type=str)
        scaleHists = request.form.get("scaleHists", False, type=str)
        hotChannelThreshold = request.form.get("hotChannelThreshold", -1, type=int)
        histGroup = convertRequestToStringWhichMayBeEmpty("histGroup", request.form)
        histName = convertRequestToStringWhichMayBeEmpty("histName", request.form)
    # See: https://stackoverflow.com/a/23139085
    except KeyError as e:
        # Format is:
        # errors = {'hello2': ['world', 'world2'], 'hello': ['world', 'world2']}
        # See: https://stackoverflow.com/a/2052206
        error.setdefault("keyError", []).append("Key error in " + e.args[0])

    # Validate values
    try:
        # Retrieve run
        if runDir in runs.keys():
            run = runs[runDir]
        else:
            error.setdefault("runDir", []).append("Run dir {0} is not available in runs!".format(runDir))
            # Invalidate and we cannot continue
            return (error, None, None, None, None, None, None, None, None)

        # Retrieve subsystem
        if subsystemName in run.subsystems.keys():
            subsystem = run.subsystems[subsystemName]
        else:
            error.setdefault("subsystem", []).append("Subsystem name {0} is not available in {1}!".format(subsystemName, run.prettyName))
            # Invalidate and we cannot continue
            return (error, None, None, None, None, None, None, None, None)

        # Check times
        if minTime < 0:
            error.setdefault("minTime", []).append("{0} less than 0!".format(minTime))
        if maxTime > subsystem.runLength:
            error.setdefault("maxTime", []).append("Max time of {0} greater than the run length of {1}".format(maxTime, subsystem.runLength))
        if minTime > maxTime:
            error.setdefault("minTime", []).append("minTime {0} is greater than maxTime {1}".format(minTime, maxTime))

        # Validate histGroup and histName
        # It could be valid for both to be None!
        validateHistGroupAndHistName(histGroup, histName, subsystem, run, error)

        # Processing options
        inputProcessingOptions = {}
        # Ensure scaleHists is a bool
        if scaleHists != False:
            scaleHists = True
        inputProcessingOptions["scaleHists"] = scaleHists

        # Check hot channel threshold
        # NOTE: The max hot channel threshold (hotChannelThreshold) is also defined here!
        if hotChannelThreshold < 0 or hotChannelThreshold > 1000:
            error.setdefault("hotChannelThreshold", []).append("Hot channel threshold {0} is outside the possible range of 0-1000!".format(hotChannelThreshold))
        inputProcessingOptions["hotChannelThreshold"] = hotChannelThreshold

    # Handle an unexpected exception
    except Exception as e:
        error.setdefault("generalError", []).append("Unknown exception! " + str(e))

    return (error, minTime, maxTime, runDir, subsystemName, histGroup, histName, inputProcessingOptions)

###################################################
def validateRunPage(runDir, subsystemName, requestedFileType, runs):
    """ Validates requests to the run page (handling individual run pages and root files)

    """
    error = {}
    try:
        # Set and validate run
        if runDir in runs.keys():
            run = runs[runDir]
        else:
            error.setdefault("Run Dir", []).append("{0} is not a valid run dir! Please select a different run!".format(runDir))
            # Invalidate and we cannot continue
            return (error, None, None, None, None, None, None, None, None, None)

        # Set subsystem and validate
        if subsystemName in run.subsystems.keys():
            subsystem = runs[runDir].subsystems[subsystemName]
        else:
            error.setdefault("Subsystem", []).append("{0} is not a valid subsystem in {1}!".format(subsystemName, run.prettyName))
            # Invalidate and we cannot continue
            return (error, None, None, None, None, None, None, None, None, None)

        # Validate requested file type
        if requestedFileType not in ["runPage", "rootFiles"]:
            error.setdefault("Request Error", []).append("Requested: {0}. Must request either runPage or rootFiles!".format(requestedFileType))

        # Determine request parameters
        jsRoot = convertRequestToPythonBool("jsRoot", request.args)
        ajaxRequest = convertRequestToPythonBool("ajaxRequest", request.args)
        requestedHistGroup = convertRequestToStringWhichMayBeEmpty("histGroup", request.args)
        requestedHist = convertRequestToStringWhichMayBeEmpty("histName", request.args)

        # Retrieve time slice key and time slice object
        (timeSliceKey, timeSlice) = retrieveAndValidateTimeSlice(subsystem, error)
    except KeyError as e:
        # Format is:
        # errors = {'hello2': ['world', 'world2'], 'hello': ['world', 'world2']}
        # See: https://stackoverflow.com/a/2052206
        error.setdefault("keyError", []).append("Key error in " + e.args[0])
    except Exception as e:
        error.setdefault("generalError", []).append("Unknown exception! " + str(e))

    if error == {}:
        return (error, run, subsystem, requestedFileType, jsRoot, ajaxRequest, requestedHistGroup, requestedHist, timeSliceKey, timeSlice)
    else:
        return (error, None, None, None, None, None, None, None, None, None)

###################################################
def validateTrending():
    """
    Validate requests to the trending page.
    """
    error = {}
    try:
        # Determine request parameters
        jsRoot = convertRequestToPythonBool("jsRoot", request.args)
        ajaxRequest = convertRequestToPythonBool("ajaxRequest", request.args)
        # Reuse the hist group infrastructure for retrieving the subsystem
        requestedHistGroup = convertRequestToStringWhichMayBeEmpty("histGroup", request.args)
        subsystemName = requestedHistGroup
        requestedHist = convertRequestToStringWhichMayBeEmpty("histName", request.args)

        # subsystemName could be None, so we only check if it exists
        if subsystemName and not subsystemName in serverParameters["subsystemList"] + ["TDG"]:
            error.setdefault("Subsystem", []).append("{} is not a valid subsystem!".format(subsystemName))
    except KeyError as e:
        # Format is:
        # errors = {'hello2': ['world', 'world2'], 'hello': ['world', 'world2']}
        # See: https://stackoverflow.com/a/2052206
        error.setdefault("keyError", []).append("Key error in " + e.args[0])
    except Exception as e:
        error.setdefault("generalError", []).append("Unknown exception! " + str(e))

    if error == {}:
        return (error, subsystemName, requestedHist, jsRoot, ajaxRequest)
    else:
        return (error, None, None, None, None)

# Validate individual values

# bool (jsRoot and ajaxRequest)
###################################################
def convertRequestToPythonBool(paramName, source):
    """ Converts a requested parameter to a python bool
    
    Particularly useful for jsRoot and ajaxRequest.

    Args:
        paramName (str): Name of the parameter in which we are interested in.
        source (dict): Source of the information. Usually request.args or request.form.

    This function is fairly similar to `convertRequestToStringWhichMayBeEmpty`.
    """
    paramValue = source.get(paramName, False, type=str)
    #logger.info("{0}: {1}".format(paramName, paramValue))
    if paramValue != False:
        paramValue = json.loads(paramValue)
    logger.info("{0}: {1}".format(paramName, paramValue))

    return paramValue

# Hist name and hist group
###################################################
def convertRequestToStringWhichMayBeEmpty(paramName, source):
    """ Handle strings which may be empty or contain "None".
    
    Empty strings should be treated as "None". The "None" strings are from the timeSlicesValues
    div on the runPage.

    Args:
        paramName (str): Name of the parameter in which we are interested in.
        source (dict): Source of the information. Usually request.args or request.form.

    This function is fairly similar to `convertRequestToPythonBool`.
    """
    paramValue = source.get(paramName, None, type=str)
    #logger.info("{0}: {1}".format(paramName, paramValue))
    #if paramValue == "" or paramValue == "None" or paramValue == None:
    # If we see "None", then we want to be certain that it is None!
    # Otherwise, we will interpret an empty string as a None value!
    if paramValue == "" or paramValue == "None":
        paramValue = None

    # To get an empty string, we need to explicitly select one with this contrived value.
    # We need to do this because it is possible for the group selection pattern to be an empty string,
    # but that is not equal to no hist being selected in a request.
    if paramValue == "nonSubsystemEmptyString":
        paramValue = ""
    logger.info("{0}: {1}".format(paramName, paramValue))

    return paramValue

###################################################
def validateHistGroupAndHistName(histGroup, histName, subsystem, run, error):
    """ Validates hist group and hist name.

    NOTE:
        As of Sept 2016, this check is not performed on the run page because it seems unnecessary
        and I (rehlers) am concerned about performace. This should be revisited in the future when
        more is known about how the site performs.

    NOTE:
        It could be valid for both to be None!
    """
    if histGroup:
        #logger.info("histGroup: {0}".format(histGroup))
        #if histGroup in [group.selectionPattern for group in subsystem.histGroups]:
        foundHistGroup = False
        for i, group in enumerate(subsystem.histGroups):
            #logger.debug("group.selectionPattern: {0}".format(group.selectionPattern))
            if histGroup == group.selectionPattern:
                foundHistGroup = True
                if histName and histName not in subsystem.histGroups[i].histList:
                    error.setdefault("histName", []).append("histName {0} is not available in histGroup {1} in {2}".format(histName, histGroup, run.prettyName))

                # Found group - we don't need to look at any more groups
                break

        if not foundHistGroup:
            error.setdefault("histGroup", []).append("histGroup {0} is not available in {1}".format(histGroup, run.prettyName))
    else:
        if histName and histName not in subsystem.hists.keys():
            error.setdefault("histName", []).append("histName {0} is not available in {1}".format(histName, run.prettyName))

###################################################
def retrieveAndValidateTimeSlice(subsystem, error):
    """ Retrieves the time slice key and then returns the corresponding time slice (it is exists)
    
    """
    timeSliceKey = request.args.get("timeSliceKey", "", type=str)
    logger.info("timeSliceKey: {0}".format(timeSliceKey))
    if timeSliceKey == "" or timeSliceKey == "None":
        timeSlice = None
        timeSliceKey = None
    else:
        timeSliceKey = json.loads(timeSliceKey)

    # Select the time slice if the key is valid
    if timeSliceKey:
        #logger.debug("timeSlices: {0}, timeSliceKey: {1}".format(subsystem.timeSlices, timeSliceKey))
        # Filter out "fullProcessing"
        if timeSliceKey == "fullProcessing":
            timeSlice = None
        elif timeSliceKey in subsystem.timeSlices.keys():
            timeSlice = subsystem.timeSlices[timeSliceKey]
        else:
            error.setdefault("timeSliceKey", []).append("{0} is not a valid time slice key! Valid time slices include {1}. Please select a different time slice!".format(timeSliceKey, subsystem.timeSlices))
            timeSlice = None
    else:
        # Should be redundant, but left for completeness
        timeSlice = None

    return (timeSliceKey, timeSlice)

###################################################
def extractValueFromNextOrRequest(paramName):
    """ Extract value from the next parameter or directly from the request.
    
    """
    # Attempt to extract from the next parameter if it exists
    paramValue = ""
    if "next" in request.args:
        # Check the next paramter
        nextParam = request.args.get("next", "", type=str)
        #logger.debug("nextParam: {0}".format(nextParam))
        if nextParam != "":
            nextParam = urlparse.urlparse(nextParam)
            #logger.debug("nextParam: {0}".format(nextParam))
            # Get the actual parameters

            params = urlparse.parse_qs(nextParam.query)
            #logger.debug("params: {0}".format(params))
            try:
                # Has a one entry list
                paramValue = params.get(paramName, "")[0]
            except (KeyError, IndexError) as e:
                logger.warning("Error in getting {0}: {1}".format(paramName, e.args[0]))
                paramValue = ""

    # Just try to extract directly if it isn't in the next parameter
    if paramValue == "":
        paramValue = request.args.get(paramName, "", type=str)
    logger.info("{0}: {1}".format(paramName, paramValue))

    return paramValue
