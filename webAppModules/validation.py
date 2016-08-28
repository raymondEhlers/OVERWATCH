""" Contains validation functions.

These functions are important to ensure that only valid values are passed to the processing functions.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University 

"""

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
    except KeyError, e:
        errorValue = "Key error in " + e.args[0] + ". Please enter a username and password in the form."

    return (errorValue, username, password)

###################################################
def validatePartialMergePostRequest(request):
    """ Validates the partial merge POST request.

    Args:
        request (Flask.request): The request object from Flask.

    Returns:
        tuple: Tuple containing:

            errorValue (dict): Dict containing errors. Allows appending so that now errors are lost.
                Ex: ``errors = {'hello2': ['world', 'world2', 'world3'], 'hello': ['world', 'world2']}``

            minTime (float): The minimum time for the partial merge.

            maxTime (float): The maximum time for the partial merge.

            runNumberOrder (int): The run for which the partial merge should be performed.

            subsystem (str): The current subsystem by three letter, all capital name (ex. ``EMC``).

            scrollAmount (float): The amount to scroll down the page to return to precisely where the user was previously.

    """
    error = {}
    try:
        minTime = float(request.form["minTime"])
        maxTime = float(request.form["maxTime"])
        runNumber = int(request.form["runNumber"])
        subsystem = request.form["subsystem"]
    # See: https://stackoverflow.com/a/23139085
    except KeyError as e:
        # Format is:
        # errors = {'hello2': ['world', 'world2'], 'hello': ['world', 'world2']}
        # See: https://stackoverflow.com/a/2052206
        error.setdefault("keyError", []).append("Key error in " + e.args[0])

    # Validate values
    try:
        if minTime < 0:
            error.setdefault("minTime", []).append(str(minTime) + " less than 0!")
        if maxTime < 0:
            error.setdefault("maxTime", []).append(str(maxTime) + " less than 0!")
        if minTime > maxTime:
            error.setdefault("minTime", []).append("minTime " + str(minTime) + " is greater than maxTime " + str(maxTime))
        if runNumber < 0:
            error.setdefault("runNumber", []).append(str(runNumber) + "is less than 0 and not a valid run number!")
        if subsystem not in serverParameters.subsystemList:
            error.setdefault("qaFunction:", []).append("Subsystem " + subsystem + " not available in qa function list!")
    # Handle an unexpected exception
    except Exception as e:
        error.setdefault("generalError", []).append("Unknown exception! " + str(e))

    return (error, minTime, maxTime, runNumber, subsystem)

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

