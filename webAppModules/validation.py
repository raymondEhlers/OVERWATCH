""" Contains validation functions.

These functions are important to ensure that only valid values are passed to the processing functions.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University 

"""

# General
import json
from flask import request

# Config
from config.serverParams import serverParameters

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
        username = request.form["username"]
        password = request.form["password"]
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

        print("error: {0}".format(error))

        # Retrieve subsystem
        if subsystemName in run.subsystems.keys():
            subsystem = run.subsystems[subsystemName]
        else:
            error.setdefault("subsystem", []).append("Subsystem name {0} is not available in {1}!".format(subsystemName, run.prettyName))

        # Check times
        if minTime < 0:
            error.setdefault("minTime", []).append("{0} less than 0!".format(minTime))
        if maxTime > subsystem.runLength:
            error.setdefault("maxTime", []).append("Max time of {0} greater than the run length of {1}".format(maxTime, subsystem.runLength))
        if minTime > maxTime:
            error.setdefault("minTime", []).append("minTime {0} is greater than maxTime {1}".format(minTime, maxTime))

        # Validate histGroup and histName
        # It could be valid for both to be None!
        if histGroup:
            print("histGroup: {0}".format(histGroup))
            #if histGroup in [group.selectionPattern for group in subsystem.histGroups]:
            foundHistGroup = False
            for i, group in enumerate(subsystem.histGroups):
                print("group.selectionPattern: {0}".format(group.selectionPattern))
                if histGroup == group.selectionPattern:
                    foundHistGroup = True
                    if histName and histName not in subsystem.histGroups[i].histList:
                        error.setdefault("histName", []).append("histName {0} is not available in histGroup {1} in {2}".format(histName, histGroup, run.prettyName))

                    # Found group - we don't need to look at any more groups
                    break

            if not foundHistGroup:
                error.setdefault("histGroup", []).append("histGroup {0} is not available in {1}".format(histGroup, run.prettyName))
        else:
            if histName and histName not in subsystem.histList:
                error.setdefault("histName", []).append("histName {0} is not available in {1}".format(histName, run.prettyName))

    # Handle an unexpected exception
    except Exception as e:
        error.setdefault("generalError", []).append("Unknown exception! " + str(e))

    return (error, minTime, maxTime, runDir, subsystemName, histGroup, histName)

###################################################
def validateQAPostRequest(request, runList):
    """ Validates the QA POST request.

    Args:
        request (Flask.request): The request object from Flask.
        runList (list): List of all available runs, with entries in the form of "Run#" (str).

    Returns:
        tuple: Tuple containing:

            error (dict): Dict containing errors. Allows appending so that now errors are lost.
                Ex: ``errors = {'hello2': ['world', 'world2', 'world3'], 'hello': ['world', 'world2']}``

            firstRun (str): The first (ie: lowest) run in the form "Run#". Ex: "Run123"
            
            lastRun (str): The last (ie: highest) run in the form "Run#". Ex: "Run123"
            
            subsystem (str): The current subsystem by three letter, all capital name (ex. ``EMC``).

            qaFunction (str): Name of the QA function to be executed.

    """
    error = {}
    try:
        firstRun = request.form["firstRun"]
        lastRun = request.form["lastRun"]
        subsystem = request.form["subsystem"]
        qaFunction = request.form["qaFunction"]
    # See: https://stackoverflow.com/a/23139085
    except KeyError as e:
        # Format is:
        # errors = {'hello2': ['world', 'world2'], 'hello': ['world', 'world2']}
        # See: https://stackoverflow.com/a/2052206
        error.setdefault("keyError", []).append("Key error in " + e.args[0])

    # Validate values
    try:
        if firstRun not in runList:
            error.setdefault("firstRun", []).append(firstRun + " not in run list!")
        if lastRun not in runList:
            error.setdefault("lastRun", []).append(lastRun + " not in run list!")
        if int(firstRun.replace("Run","")) > int(lastRun.replace("Run", "")):
            error.setdefault("runNumberOrder", []).append(firstRun + " is greater than " + lastRun)
        #if subsystem not in serverParameters.subsystemList:
        #    error.setdefault("subsystem", []).append("subsystem " + subsystem + " is not valid")
        #if any(qaFunction not in funcNames for funcNames in serverParameters.qaFunctionsList.values()):
        #    error.setdefault("qaFunction:", []).append(qaFunction + " is not a QA function defined for subsystem %s!" % subsystem)
        if subsystem not in serverParameters.qaFunctionsList:
            error.setdefault("qaFunction:", []).append("Subsystem " + subsystem + " not available in the QA function list!")
        else:
            if qaFunction not in serverParameters.qaFunctionsList[subsystem]:
                error.setdefault("qaFunction:", []).append(qaFunction + " not usable with subsystem " + subsystem)
    # Handle an unexpected exception
    except Exception as e:
        error.setdefault("generalError", []).append("Unknown exception! " + str(e))

    return (error, firstRun, lastRun, subsystem, qaFunction)

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
    paramValue = request.args.get(paramName, False, type=str)
    if paramValue != False:
        paramValue = json.loads(paramValue)
    print("{0}: {1}".format(paramName, paramValue))

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
    print("{0}: {1}".format(paramName, paramValue))
    if paramValue == "" or paramValue == "None" or paramValue == None:
        paramValue = None
    print("{0}: {1}".format(paramName, paramValue))

    return paramValue
