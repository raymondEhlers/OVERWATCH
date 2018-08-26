#!/usr/bin/env python

""" Contains validation functions.

These functions are important to ensure that only valid values are passed to the processing functions.
Validation could likely be improved by moving WTForms, which Overwatch already depends upon for CSRF
protection.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University 
"""

# General
import json
from flask import request
# Used to parse GET parameters
try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

# Config
from ..base import config
(serverParameters, filesRead) = config.readConfig(config.configurationType.webApp)

# Logging
import logging
# Setup logger
logger = logging.getLogger(__name__)

def validateLoginPostRequest(request):
    """ Validates the login POST request.
    
    Note:
        The error format is different here. Instead of a list in a dict, we simply have a string.

    Args:
        request (Flask.request): The request object from Flask.
    Return
        tuple: (errorValue, username, password), where errorValue (str) contains the error that
            may have occurred, username (str) is the username extracted from POST request, and
            password (str) is the password extracted from POST request.
    """
    errorValue = None
    try:
        # We enforce the type as as string here
        username = request.form.get("username", type=str)
        password = request.form.get("password", type=str)
    except KeyError as e:
        errorValue = "Key error in " + e.args[0] + ". Please enter a username and password in the form."

    return (errorValue, username, password)

def validateTimeSlicePostRequest(request, runs):
    """ Validates the time slice POST request.

    The return tuple contains the validated values. The error value should always be checked first
    before using the other return values (they will be safe, but may not be meaningful).

    Warning:
        If an error occurs in determining the run or subsystem, we cannot retrieve the rest of the
        information necessary to validate the request, so the rest of the values in the return tuple are
        set to ``None``.

    Note:
        For the error format in ``errorValue``, see the :doc:`web app README </webAppReadme>`.

    Note:
        The listed args (after the first two) are provided through the flask ``request.form`` dictionary.

    Args:
        request (Flask.request): The request object from Flask.
        runs (BTree): Dict-like object which stores all run, subsystem, and hist information. Keys are the
            in the ``runDir`` format ("Run123456"), while the values are ``runContainer`` objects.
        minTime (float): Minimum time for the time slice.
        maxTime (float): Maximum time for the time slice.
        runDir (str): String containing the run number. For an example run 123456, it should be
            formatted as ``Run123456``.
        subsystemName (str): The current subsystem in the form of a three letter, all capital name (ex. ``EMC``).
        scaleHists (str): True if the hists should be scaled by the number of events. Converted from string to bool.
        hotChannelThreshold (int): Value of the hot channel threshold.
        histGroup (str): Name of the requested hist group. It is fine for it to be an empty string.
        histName (str): Name of the requested histogram. It is fine for it to be an empty string.
    Returns:
        tuple: (errorValue, minTime, maxTime, runDir, subsystemName, scrollAmount) where errorValue (dict)
            containers any possible errors, minTime (float) is the minimum time for the time slice,
            maxTime (float) is the maximum time for the time slice, runDir (str) is the run dir formatted
            string for which the time slice should be performed, subsystemName (str) is the current subsystem
            in the form of a three letter, all capital name (ex. ``EMC``), and scrollAmount (float) is the
            amount to scroll down the page to return to precisely where the user was previously.
    """
    error = {}
    try:
        # Enforce the particular types via ``get(...)``.
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

    # Validate values based on available runs.
    try:
        # Retrieve run
        if runDir in runs.keys():
            run = runs[runDir]
        else:
            error.setdefault("Run Dir", []).append("Run dir {0} is not available in runs!".format(runDir))
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
        # NOTE: It could be valid for both to be None!
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

def validateRunPage(runDir, subsystemName, requestedFileType, runs):
    """ Validates requests to the various run page types (handling individual run pages and root files).

    The return tuple contains the validated values. The error value should always be checked first
    before using the other return values (they will be safe, but may not be meaningful).

    Note:
        For the error format in ``error``, see the :doc:`web app README </webAppReadme>`.

    Note:
        The listed args (after the first four) are provided through the flask ``request.args`` dictionary.

    Args:
        runDir (str): String containing the run number. For an example run 123456, it should be
            formatted as ``Run123456``
        subsystemName (str): The current subsystem in the form of a three letter, all capital name (ex. ``EMC``).
        requestedFileType (str): Either "runPage", which corresponds to a standard run page or "rootFiles", which
            corresponds to the page displaying the available root files.
        runs (BTree): Dict-like object which stores all run, subsystem, and hist information. Keys are the
            in the ``runDir`` format ("Run123456"), while the values are ``runContainer`` objects. This should
            be retrieved from the database.
        jsRoot (bool): True if the response should use jsRoot instead of images.
        ajaxRequest (bool): True if the response should be via AJAX.
        requestedHistGroup (str): Name of the requested hist group. It is fine for it to be an empty string.
        requestedHist (str): Name of the requested histogram. It is fine for it to be an empty string.
    Returns:
        tuple: (error, run, subsystem, requestedFileType, jsRoot, ajaxRequest, requestedHistGroup, requestedHist, timeSliceKey, timeSlice)
            where error (dict) contains any possible errors, run (runContainer) corresponds to the current
            run, subsystem (subsystemContainer) corresponds to the current subsystem, requestedFileType (str)
            is the type of run page ("runPage" or "rootFiles"), jsRoot (bool) is True if the response should
            use jsRoot, ajaxRequest (bool) is true if the response should be as AJAX, requestedHistGroup (str)
            is the name of the requested hist group, requestedHist (str) is the name of the requested histogram,
            timeSliceKey (str) is the time slice key, and timeSlice (timeSliceContainer) is the time slice object.
            For more on the last two arguments, see ``retrieveAndValidateTimeSlice(...)``.
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

def validateTrending(request):
    """ Validate requests to the trending page.

    The return tuple contains the validated values. The error value should always be checked first
    before using the other return values (they will be safe, but may not be meaningful).

    Note:
        For the error format in ``error``, see the :doc:`web app README </webAppReadme>`.

    Note:
        Function args are provided through the flask ``request.args`` dictionary.

    Args:
        request (Flask.request): The request object from Flask.
        jsRoot (bool): True if the response should use jsRoot instead of images.
        ajaxRequest (bool): True if the response should be via AJAX.
        subsystemName (str): Name of the requested subsystem. It is fine for it to be an empty string.
            Provided via the ``histGroup`` field since it is treated identically, allowing us to avoid
            the need to define another field for this one case.
        histName (str): Name of the requested histogram. It is fine for it to be an empty string.
    Returns:
        tuple: (error, subsystemName, requestedHist, jsRoot, ajaxRequest), where where error (dict) contains
            any possible errors, subsystemName (str) corresponds to the current subsystem, subsystemName (str)
            is the requested subsystem in the form of a three letter, all capital name (ex. ``EMC``).
            jsRoot (bool) is True if the response should use jsRoot, ajaxRequest (bool) is true if the response
            should be as AJAX.
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

        # subsystemName could be None, so we first must check if it exists
        if subsystemName and not subsystemName in serverParameters["subsystemList"] + ["TDG"]:
            error.setdefault("Subsystem", []).append("{} is not a valid subsystem!".format(subsystemName))
    except KeyError as e:
        error.setdefault("keyError", []).append("Key error in " + e.args[0])
    except Exception as e:
        error.setdefault("generalError", []).append("Unknown exception! " + str(e))

    if error == {}:
        return (error, subsystemName, requestedHist, jsRoot, ajaxRequest)
    else:
        return (error, None, None, None, None)

## Validate individual values

def convertRequestToPythonBool(paramName, source):
    """ Converts a requested parameter to a python bool.
    
    The validation is particularly useful for jsRoot and ajaxRequest. Note that this function
    is fairly similar to `convertRequestToStringWhichMayBeEmpty`.

    Args:
        paramName (str): Name of the parameter in which we are interested in.
        source (dict): Source of the information. Usually request.args or request.form.
    Returns:
        bool: True if the retrieved value was True.
    """
    paramValue = source.get(paramName, False, type=str)
    #logger.info("{0}: {1}".format(paramName, paramValue))
    if paramValue != False:
        paramValue = json.loads(paramValue)
    logger.info("{0}: {1}".format(paramName, paramValue))

    return paramValue

def convertRequestToStringWhichMayBeEmpty(paramName, source):
    """ Handle strings which may be empty or contain "None".
    
    This validation is particularly useful for validating hist names and hist groups
    request strings to ensure that they are valid strings before doing further validation.
    Empty strings should be treated as ``None``. The ``None`` strings are from the
    timeSlicesValues div on the runPage. Note that this function is fairly similar
    to `convertRequestToPythonBool`.

    Args:
        paramName (str): Name of the parameter in which we are interested in.
        source (dict): Source of the information. Usually request.args or request.form.
    Returns:
        str or None: Validated string or ``None`` if the string is empty or "None".
    """
    paramValue = source.get(paramName, None, type=str)
    #logger.info("{0}: {1}".format(paramName, paramValue))
    # If we see "None", then we want to be certain that it is ``None``!
    # Otherwise, we will interpret an empty string as a None value.
    if paramValue == "" or paramValue == "None":
        paramValue = None

    # To get an empty string, we need to explicitly select one with this contrived value.
    # We need to do this because it is possible for the group selection pattern to be an empty string,
    # but that is not equal to no hist being selected in a request.
    if paramValue == "nonSubsystemEmptyString":
        paramValue = ""
    logger.info("{0}: {1}".format(paramName, paramValue))

    return paramValue

def convertRequestToPositiveInteger(paramName, source):
    """ Converts a requested parameter into a positive integer.

    This function is somewhat similar to the other conversion and validation functions,
    although it is a bit simpler.

    Args:
        paramName (str): Name of the parameter in which we are interested in.
        source (dict): Source of the information. Usually request.args or request.form.
    Returns:
        int: The requested int or 0 if it was somehow invalid.
    """
    paramValue = source.get(paramName, default = 0, type = int)
    if paramValue < 0:
        paramValue = 0

    logger.info("{}: {}".format(paramName, paramValue))
    return paramValue

def validateHistGroupAndHistName(histGroup, histName, subsystem, run, error):
    """ Check that the given hist group or hist name exists in the subsystem.

    Look for the requested hist group or hist name within a given subsystem. It requires that the
    hist group and hist name have already been validated to ensure that they are valid strings
    or ``None``. Note that it could be perfectly valid for both to be ``None``!

    Note:
        As of Sept 2016, this check is not performed on the run page because it seems unnecessary
        to check every single value and there could be a substantial performance cost. This 
        should be revisited in the future if it becomes a problem.

    Note:
        For the error format in ``error``, see the :doc:`web app README </webAppReadme>`.

    Args:
        histGroup (str or None): Requested hist group.
        histName (str or None): Requested hist name.
        subsystem (subsystemContainer): Subsystem which should contain the hist group and hist name.
        run (runContainer): Run for which the hist group and hist name should exist.
        error (dict): Contains any possible errors following the defined error format. We will append
            any new errors to it.
    Returns:
        None: It will append an error to the error dict if there is a problem with the given hist
            group or hist nine. The error dict should be checked by the returning function
            to determine the result and decide how to proceed.
    """
    # The request with either be for a hist group or a hist name, so we can just use an if statement here.
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

def retrieveAndValidateTimeSlice(subsystem, error):
    """ Retrieves the time slice key and then returns the corresponding time slice (it is exists).

    This function safely retrieves a ``timeSliceContainer``. In the case of a valid time slice
    key, the corresponding object will be retrieved. However, in the case of "fullProcessing",
    the object will be ``None`` so we can immediately return the full object. Errors will be
    appended under the ``timeSliceKey`` key.

    Note:
        For the error format in ``error``, see the :doc:`web app README </webAppReadme>`.
    
    Args:
        subsystem (subsystemContainer): Subsystem for which the time slices request was made.
        error (dict): Contains any possible errors following the defined error format. We will append
            any new errors to it.
    Returns:
        tuple: (timeSliceKey, timeSlice) where timeSliceKey (str) is the key under which the time slice
            is stored or "fullProcessing" (which indicates full processing), and timeSlice (timeSliceContainer)
            is the corresponding time slice retrieved from the subsystem, or None if for any reason
            it could not be retrieved.
    """
    # Retrieve the key and validate.
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

def extractValueFromNextOrRequest(paramName, source):
    """ Extract the selected parameter from the next parameter or directly from the request.

    First attempt to extract the named parameter from the next parameter in the args of the
    request. If it isn't available, then attempt to extract it directly from the request args
    parameters. This is particularly useful for logging the user back in the case of a default
    username.

    Args:
        paramName (str): Name of the parameter to extract.
        source (dict): Source of the information. Usually request.args or request.form.
    Returns:
        str: Value of the extracted parameter.
    """
    # Attempt to extract from the next parameter if it exists
    paramValue = ""
    if "next" in source:
        # Check the next parameter
        nextParam = source.get("next", "", type=str)
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
        paramValue = source.get(paramName, "", type=str)
    logger.info("{0}: {1}".format(paramName, paramValue))

    return paramValue
