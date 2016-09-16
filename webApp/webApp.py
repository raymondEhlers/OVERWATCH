#!/usr/bin/env python
""" WSGI server for hists and interactive features with HLT histograms.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""
# For python 3 support
from __future__ import print_function
from builtins import range

# General includes
import os
import socket
import time
import zipfile
import subprocess
import signal
import jinja2
import json
import collections 
# For server status
import requests
# Python logging system
import logging
# Setup logger
if __name__ == "__main__":
    # By not setting a name, we get everything!
    #logger = logging.getLogger("")
    # Alternatively, we could set "webApp" to get everything derived from that
    #logger = logging.getLogger("webApp")
    pass
else:
    # When imported, we just want it to take on it normal name
    logger = logging.getLogger(__name__)
    # Alternatively, we could set "webApp" to get everything derived from that
    #logger = logging.getLogger("webApp")

# Flask
from flask import Flask, url_for, request, render_template, redirect, flash, send_from_directory, Markup, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
# Unfortunately, flask_zodb does not work...
from flask.ext.zodb import ZODB
from flup.server.fcgi import WSGIServer

# Server configuration
from config.serverParams import serverParameters

# WebApp Module includes
from . import routing
from . import auth
from . import validation

# Main processing file
from processRuns import processRuns

# Processing module includes
from processRuns import utilities
from processRuns import qa

# Flask setup
app = Flask(__name__, static_url_path=serverParameters.staticURLPath, static_folder=serverParameters.staticFolder, template_folder=serverParameters.templateFolder)

# Setup database
app.config["ZODB_STORAGE"] = serverParameters.databaseLocation
db = ZODB(app)

# Set serverParameters secret key and add user from database if they exist
if serverParameters.appendSettings and db.has_key("config"):
    #if db["config"].has_key("users"):
    #    for user, pw in db["config"]["users"]:
    #        # Add each user, overriding an existing settings
    #        serverParameters._users[user] = pw
    if db["config"].has_key("secretKey"):
        # Set the secret key to be the same as where the db is hosted
        serverParameters._secretKey = db["config"]["secretKey"]

# Set secret key for flask
app.secret_key = serverParameters._secretKey

# Enable debugging if set in configuration
if serverParameters.debug == True:
    app.debug = True

# Setup Bcrypt
app.config["BCRYPT_LOG_ROUNDS"] = serverParameters.bcryptLogRounds
bcrypt = Bcrypt(app)

# Setup login manager
loginManager = LoginManager()
loginManager.init_app(app)

# Tells the manager where to redirect when login is required.
loginManager.login_view = "login"

###################################################
@loginManager.user_loader
def load_user(user):
    """ Used to remember the user so that they don't need to login again each time they visit the site. """
    return auth.User.getUser(user, db)

######################################################################################################
# Unauthenticated Routes
######################################################################################################

###################################################
@app.route("/", methods=["GET", "POST"])
def login():
    """ Login function. This is is the first page the user sees.
    Unauthenticated users are also redirected here if they try to access something restricted.
    After logging in, it should then forward them to resource they requested.
    """
    logger.debug("request.args: {0}".format(request.args))
    logger.debug("request.form: {0}".format(request.form))
    ajaxRequest = validation.convertRequestToPythonBool("ajaxRequest", request.args)
    previousUsername = validation.extractValueFromNextOrRequest("previousUsername")

    errorValue = None
    nextValue = routing.getRedirectTarget()

    # A post request Attempt to login the user in
    if request.method == "POST":
        # Validate the request.
        (errorValue, username, password) = validation.validateLoginPostRequest(request)

        # If there is an error, just drop through to return an error on the login page
        if errorValue == None:
            # Validate user
            validUser = auth.authenticateUser(username, password, db)

            # Return user if successful
            if validUser is not None:
                # Login the user into flask
                login_user(validUser, remember=True)

                flash("Login Success for {0}.".format(validUser.id))
                logger.info("Login Success for {0}.".format(validUser.id))

                return routing.redirectBack("index")
            else:
                errorValue = "Login failed with invalid credentials"

    if previousUsername == serverParameters.defaultUsername:
        logger.debug("Equal!")
    logger.debug("serverParameters.defaultUsername: {0}".format(serverParameters.defaultUsername))
    # If we are not authenticated and we have a default username set and the previous username is 
    if not current_user.is_authenticated and serverParameters.defaultUsername and previousUsername != serverParameters.defaultUsername:
        # Clear previous flashes which will be confusing to the user
        # See: https://stackoverflow.com/a/19525521
        session.pop('_flashes', None)
        # Get the default user
        defaultUser = auth.User.getUser(serverParameters.defaultUsername, db)
        # Login the user into flask
        login_user(defaultUser, remember=True)
        # Note for the user
        logger.info("Logged into user \"{0}\" automatically!".format(current_user.id))
        flash("Logged into user \"{0}\" automatically!".format(current_user.id))

    # If we visit the login page, but we are already authenticated, then send to the index page.
    if current_user.is_authenticated:
        logger.info("Redirecting logged in user \"{0}\" to index...".format(current_user.id))
        return redirect(url_for("index", ajaxRequest = json.dumps(ajaxRequest)))

    if ajaxRequest == False:
        return render_template("login.html", error=errorValue, nextValue=nextValue)
    else:
        drawerContent = ""
        mainContent = render_template("loginMainContent.html", error=errorValue, nextValue=nextValue)
        return jsonify(drawerContent = drawerContent, mainContent = mainContent)

###################################################
@app.route("/logout")
@login_required
def logout():
    """ Logout function.

    NOTE:
        Careful in changing the routing, as this is hard coded in :func:`~webApp.routing.redirectBack()`!

    Redirects back to :func:`.login`, which willl redirect back to index if the user is logged in.
    """
    previousUsername = current_user.id
    logout_user()

    flash("User logged out!")
    return redirect(url_for("login", previousUsername = previousUsername))

###################################################
@app.route("/contact")
def contact():
    """ Simple contact page so we can provide support in the future."""
    ajaxRequest = validation.convertRequestToPythonBool("ajaxRequest", request.args)

    if ajaxRequest == False:
        return render_template("contact.html")
    else:
        drawerContent = ""
        mainContent = render_template("contactMainContent.html")
        return jsonify(drawerContent = drawerContent, mainContent = mainContent)

###################################################
@app.route("/favicon.ico")
def favicon():
    """ Browsers always try to load the Favicon, so this suppresses the errors about not finding one.

    However, the real way that this is generally loaded is via code in layout template!
    """
    return redirect(url_for("static", filename="icons/favicon.ico"))

###################################################
@app.route("/statusQuery", methods=["POST"])
def statusQuery():
    """ Respond to a status query (separated so that it doesn't require a login!) """

    # Responds to requests from other OVERWATCH servers to display the status of the site
    return "Alive"

######################################################################################################
# Authenticated Routes
######################################################################################################

###################################################
@app.route("/monitoring", methods=["GET"])
@login_required
def index():
    """ This is the main page for logged in users. It always redirects to the run list.
    
    """
    logger.debug("request.args: {0}".format(request.args))
    ajaxRequest = validation.convertRequestToPythonBool("ajaxRequest", request.args)

    runs = db["runs"]

    # Determine if a run is ongoing
    # To do so, we need the most recent run
    mostRecentRun = runs[runs.keys()[-1]]
    runOngoing = mostRecentRun.isRunOngoing()
    if runOngoing:
        runOngoingNumber = mostRecentRun.runNumber
    else:
        runOngoingNumber = ""

    # Number of runs
    numberOfRuns = len(runs.keys())
    # We want 15 anchors
    # NOTE: We need to round it to an int to ensure that mod works.
    anchorFrequency = int(round(numberOfRuns/15.0))

    if ajaxRequest != True:
        return render_template("runList.html", drawerRuns = reversed(runs.values()),
                                mainContentRuns = reversed(runs.values()),
                                runOngoing = runOngoing,
                                runOngoingNumber = runOngoingNumber,
                                subsystemsWithRootFilesToShow = serverParameters.subsystemsWithRootFilesToShow,
                                anchorFrequency = anchorFrequency)
    else:
        drawerContent = render_template("runListDrawer.html", runs = reversed(runs.values()), runOngoing = runOngoing,
                                         runOngoingNumber = runOngoingNumber, anchorFrequency = anchorFrequency)
        mainContent = render_template("runListMainContent.html", runs = reversed(runs.values()), runOngoing = runOngoing,
                                       runOngoingNumber = runOngoingNumber,
                                       subsystemsWithRootFilesToShow = serverParameters.subsystemsWithRootFilesToShow,
                                       anchorFrequency = anchorFrequency)

        return jsonify(drawerContent = drawerContent, mainContent = mainContent)

###################################################
@app.route("/Run<int:runNumber>/<string:subsystemName>/<string:requestedFileType>", methods=["GET"])
@login_required
def runPage(runNumber, subsystemName, requestedFileType):
    """ Serves the run pages and root files for a request run
    
    """
    # Setup runDir
    runDir = "Run{0}".format(runNumber)

    # Setup db information
    runs = db["runs"]

    (error, run, subsystem, requestedFileType, jsRoot, ajaxRequest, requestedHistGroup, requestedHist, timeSliceKey, timeSlice) = validation.validateRunPage(runDir, subsystemName, requestedFileType, runs)

    # This will only work if all of the values are properly defined.
    # Otherwise, we just skip to the end to return the error to the user.
    if error == {}:
        # Sets the filenames for the json and img files
        # Create these templates here so we don't have inside of the template
        jsonFilenameTemplate = os.path.join(subsystem.jsonDir, "{0}.json")
        if timeSlice:
            jsonFilenameTemplate = jsonFilenameTemplate.format(timeSlice.filenamePrefix + ".{0}")
        imgFilenameTemplate = os.path.join(subsystem.imgDir, "{0}." + serverParameters.fileExtension)

        # Print request status
        logger.debug("request: {0}".format(request.args))
        logger.debug("runDir: {0}, subsytsem: {1}, requestedFileType: {2}, "
              "ajaxRequest: {3}, jsRoot: {4}, requestedHistGroup: {5}, requestedHist: {6}, "
              "timeSliceKey: {7}, timeSlice: {8}".format(runDir, subsystemName, requestedFileType,
               ajaxRequest, jsRoot, requestedHistGroup, requestedHist, timeSliceKey, timeSlice))

        # TEMP
        logger.debug("subsystem.timeSlices: {0}".format(subsystem.timeSlices))
        # END TEMP
    else:
        logger.warning("Error: {0}".format(error))

    if ajaxRequest != True:
        if error == {}:
            if requestedFileType == "runPage":
                # Attempt to use a subsystem specific run page if available
                runPageName = subsystemName + "runPage.html"
                if runPageName not in serverParameters.availableRunPageTemplates:
                    runPageName = runPageName.replace(subsystemName, "")

                try:
                    returnValue = render_template(runPageName, run = run, subsystem = subsystem,
                                                  selectedHistGroup = requestedHistGroup, selectedHist = requestedHist,
                                                  jsonFilenameTemplate = jsonFilenameTemplate,
                                                  imgFilenameTemplate = imgFilenameTemplate,
                                                  jsRoot = jsRoot, timeSlice = timeSlice)
                except jinja2.exceptions.TemplateNotFound as e:
                    error.setdefault("Template Error", []).append("Request template: \"{0}\", but it was not found!".format(e.name))
            elif requestedFileType == "rootFiles":
                # Subsystem specific run pages are not available since they don't seem to be necessary
                returnValue = render_template("rootfiles.html", run = run, subsystem = subsystemName)
            else:
                # Redundant, but good to be careful
                error.setdefault("Template Error", []).append("Request template: \"{0}\", but it was not found!".format(e.name))

        if error != {}:
            logger.warning("error: {0}".format(error))
            returnValue = render_template("error.html", errors = error)

        return returnValue
    else:
        if error == {}:
            if requestedFileType == "runPage":
               # Drawer
                runPageDrawerName = subsystemName + "runPageDrawer.html"
                if runPageDrawerName not in serverParameters.availableRunPageTemplates:
                    runPageDrawerName = runPageDrawerName.replace(subsystemName, "")
                # Main content
                runPageMainContentName = subsystemName + "runPageMainContent.html"
                if runPageMainContentName not in serverParameters.availableRunPageTemplates:
                    runPageMainContentName = runPageMainContentName.replace(subsystemName, "")

                try:
                    drawerContent = render_template(runPageDrawerName, run = run, subsystem = subsystem,
                                                    selectedHistGroup = requestedHistGroup, selectedHist = requestedHist,
                                                    jsonFilenameTemplate = jsonFilenameTemplate,
                                                    imgFilenameTemplate = imgFilenameTemplate,
                                                    jsRoot = jsRoot, timeSlice = timeSlice)
                    mainContent = render_template(runPageMainContentName, run = run, subsystem = subsystem,
                                                  selectedHistGroup = requestedHistGroup, selectedHist = requestedHist,
                                                  jsonFilenameTemplate = jsonFilenameTemplate,
                                                  imgFilenameTemplate = imgFilenameTemplate,
                                                  jsRoot = jsRoot, timeSlice = timeSlice)
                except jinja2.exceptions.TemplateNotFound as e:
                    error.setdefault("Template Error", []).append("Request template: \"{0}\", but it was not found!".format(e.name))
            elif requestedFileType == "rootFiles":
                drawerContent = ""
                mainContent = render_template("rootfilesMainContent.html", run = run, subsystem = subsystemName)
            else:
                # Redundant, but good to be careful
                error.setdefault("Template Error", []).append("Request template: \"{0}\", but it was not found!".format(e.name))

        if error != {}:
            logger.warning("error: {0}".format(error))
            drawerContent = ""
            mainContent =  render_template("errorMainContent.html", errors = error)

        # Includes hist group and hist name for time slices since it is easier to pass it here than parse the get requests. Otherwise, they are ignored.
        return jsonify(drawerContent = drawerContent,
                       mainContent = mainContent,
                       timeSliceKey = json.dumps(timeSliceKey),
                       histName = requestedHist,
                       histGroup = requestedHistGroup)

###################################################
@app.route("/monitoring/protected/<path:filename>")
@login_required
def protected(filename):
    """ Serves the actual files.

    Based on the suggestion described here: https://stackoverflow.com/a/27611882

    Note:
        This ignores GET parameters. However, they can be useful to pass here to prevent something
        from being cached, such as a QA image which has the same name, but has changed since last
        being served.

    """
    logger.debug("filename: {0}".format(filename))
    logger.debug("request.args: {0}".format(request.args))
    # Ignore the time GET parameter that is sometimes passed- just to avoid the cache when required
    #if request.args.get("time"):
    #    print "timeParameter:", request.args.get("time")
    return send_from_directory(os.path.realpath(serverParameters.protectedFolder), filename)

###################################################
@app.route("/docs/<path:filename>")
@login_required
def docs(filename):
    """ Serve the documentation.

    """
    if os.path.isfile(os.path.join(serverParameters.docsBuildFolder, filename)):
        # Serve the docs
        return send_from_directory(os.path.realpath(serverParameters.docsBuildFolder), filename)
    else:
        # If it isn't built for some reason, tell the user what happened
        flash(filename + " not available! Docs are probably not built. Contact the admins!")
        return redirect(url_for("contact"))

###################################################
@app.route("/doc/rebuild")
@login_required
def rebuildDocs():
    """ Rebuild the docs based on the most recent source files.

    The link is only available to the admin user.
    """
    if current_user.id == "emcalAdmin":
        # Cannot get the actual output, as it seems to often crash the process
        # I think this is related to the auto-reload in debug mode
        #buildResult = subprocess.check_output(["make", "-C", serverParameters.docsFolder, "html"])
        #print buildResult
        #flash("Doc build output: " + buildResult)

        # Run the build command 
        subprocess.call(["make", "-C", serverParameters.docsFolder, "html"])

        # Flash the result
        flash("Docs rebuilt")

    else:
        # Flash to inform the user
        flash("Regular users are not allowed to rebuild the docs.")

    # Return to where the build command was called
    return redirect(url_for("contact"))

###################################################
@app.route("/timeSlice", methods=["GET", "POST"])
@login_required
def timeSlice():
    """ Handles time slice requests.

    In the case of a GET request, it will throw an error, since the interface is built into the header of each
    individual run page. In the case of a POST request, it handles, validates, and processes the timing request,
    rendering the result template and returning the user to the same spot as in the previous page.

    """
    #logger.debug("request.args: {0}".format(request.args))
    logger.debug("request.form: {0}".format(request.form))
    # We don't get ajaxRequest because this request should always be made via ajax
    jsRoot = validation.convertRequestToPythonBool("jsRoot", request.form)

    if request.method == "POST":
        # Get the runs
        runs = db["runs"]

        # Validates the request
        (error, minTime, maxTime, runDir, subsystem, histGroup, histName, inputProcessingOptions) = validation.validateTimeSlicePostRequest(request, runs)

        if error == {}:
            # Print input values
            logger.debug("minTime: {0}".format(minTime))
            logger.debug("maxTime: {0}".format(maxTime))
            logger.debug("runDir: {0}".format(runDir))
            logger.debug("subsystem: {0}".format(subsystem))
            logger.debug("histGroup: {0}".format(histGroup))
            logger.debug("histName: {0}".format(histName))

            # Process the time slice
            returnValue = processRuns.processTimeSlices(runs, runDir, minTime, maxTime, subsystem, inputProcessingOptions)

            logger.info("returnValue: {0}".format(returnValue))
            logger.debug("runs[runDir].subsystems[subsystem].timeSlices: {0}".format(runs[runDir].subsystems[subsystem].timeSlices))

            if not isinstance(returnValue, collections.Mapping):
                timeSliceKey = returnValue
                #if timeSliceKey == "fullProcessing":
                #    timeSliceKey = None
                # We always want to use ajax here
                return redirect(url_for("runPage",
                                        runNumber = runs[runDir].runNumber,
                                        subsystemName = subsystem,
                                        requestedFileType = "runPage",
                                        ajaxRequest = json.dumps(True),
                                        jsRoot = json.dumps(jsRoot),
                                        histGroup = histGroup,
                                        histName = histName,
                                        timeSliceKey = json.dumps(timeSliceKey)))
            else:
                # Fall through to return an error
                error = returnValue

        logger.info("Time slices error:", error)
        drawerContent = ""
        mainContent = render_template("errorMainContent.html", errors=error)

        # We always want to use ajax here
        return jsonify(mainContent = mainContent, drawerContent = "")

    else:
        return render_template("error.html", errors={"error": ["Need to access through a run page!"]})

###################################################
@app.route("/processQA", methods=["GET", "POST"])
@login_required
def processQA():
    """ Handles QA functions.

    In the case of a GET request, it serves a page showing the possible QA options. In the case of a
    POST request, it handles, validates and executes the QA task, rendering the result template.

    It also supports the ability to add GET parameters to the returned values for the result template
    to ensure that the browser doesn't cache things that have actually changed. Such parameters will
    be ignored without any other intervention.

    """
    logger.debug("request: {0}".format(request.args))
    ajaxRequest = validation.convertRequestToPythonBool("ajaxRequest", request.args)

    runs = db["runs"]
    runList = runs.keys()
    logger.debug("runList: {0}".format(list(runList)))

    if request.method == "POST":
        # Validate post request
        (error, firstRun, lastRun, subsystem, qaFunction) = validation.validateQAPostRequest(request, runList)

        # Process
        if error == {}:
            # Print input values
            logger.debug("firstRun:", firstRun)
            logger.debug("lastRun:", lastRun)
            logger.debug("subsystem:", subsystem)
            logger.debug("qaFunction:", qaFunction)

            # Process the QA
            returnValues = processRuns.processQA(firstRun, lastRun, subsystem, qaFunction)

            # Ensures that the image is not cached by adding a meaningless but unique argument.
            histPaths = {}
            for name, histPath in returnValues.items():
                # Can add an argument with "&arg=value" if desired
                histPaths[name] = histPath + "?time=" + str(time.time())
                logger.debug("histPaths[{0}]: {1}".format(name, histPaths[name]))

            # Ensures that the root file is not cached by adding a meaningless but unique argument.
            rootFilePath = os.path.join(qaFunction, qaFunction + ".root")
            rootFilePath += "?time=" + str(time.time())

            return render_template("qaResult.html", firstRun=firstRun, lastRun=lastRun, qaFunctionName=qaFunction, subsystem=subsystem, hists=histPaths, rootFilePath=rootFilePath)
        else:
            return render_template("error.html", errors=error)

    else:
        # We need to combine the available subsystems. subsystemList is not sufficient because we may want QA functions
        # but now to split out the hists on the web page.
        # Need to call list so that subsystemList is not modified.
        # See: https://stackoverflow.com/a/2612815
        subsystems = list(serverParameters.subsystemList)
        for subsystem in serverParameters.qaFunctionsList:
            subsystems.append(subsystem)

        # Make sure that we have a unique list of subsystems.
        subsystems = sorted(set(subsystems))

        if ajaxRequest == False:
            return render_template("qa.html", runList=runList, qaFunctionsList=serverParameters.qaFunctionsList, subsystemList=subsystems, docStrings=qa.qaFunctionDocstrings)
        else:
            drawerContent = render_template("qaDrawer.html", subsystemList=subsystems, qaFunctionsList=serverParameters.qaFunctionsList)
            mainContent = render_template("qaMainContent.html", runList=runList, qaFunctionsList=serverParameters.qaFunctionsList, subsystemList=subsystems, docStrings=qa.qaFunctionDocstrings)
            return jsonify(drawerContent = drawerContent, mainContent = mainContent)

###################################################
@app.route("/testingDataArchive")
@login_required
def testingDataArchive():
    """ Creates a zip archive to download data for QA function testing.

    It will return at most the 5 most recent runs. The archive contains the combined file for all subsystems.

    NOTE:
        Careful in changing the routing, as this is hard coded in :func:`~webApp.routing.redirectBack()`!

    Args:
        None

    Returns:
        redirect: Redirects to the newly created file.
    """
    # Get db
    runs = db["runs"]
    runList = runs.keys()

    # Retreive at most 5 files
    if len(runList) < 5:
        numberOfFilesToDownload = len(runList)
    else:
        numberOfFilesToDownload = 5

    # Create zip file. It is stored in the root of the data directory
    zipFilename = "testingDataArchive.zip"
    zipFile = zipfile.ZipFile(os.path.join(serverParameters.protectedFolder, zipFilename), "w")
    logger.info("Creating zipFile at %s" % os.path.join(serverParameters.protectedFolder, zipFilename))

    # Add files to the zip file
    runKeys = runs.keys()
    for i in range(1, numberOfFilesToDownload+1):
        run = runs[runKeys[-1*i]]
        for subsystem in run.subsystems.values():
            # Write files to the zip file
            # Combined file
            zipFile.write(os.path.join(serverParameters.protectedFolder, subsystem.combinedFile.filename))
            # Uncombined file
            zipFile.write(os.path.join(serverParameters.protectedFolder, subsystem.files[subsystem.files.keys()[-1]].filename))

    # Finish with the zip file
    zipFile.close()

    # Return with a download link
    return redirect(url_for("protected", filename=zipFilename))

###################################################
@app.route("/status")
@login_required
def status():
    """ Returns the status of the OVERWATCH sites """

    # Get db
    runs = db["runs"]

    # Display the status page from the other sites
    ajaxRequest = validation.convertRequestToPythonBool("ajaxRequest", request.args)

    # Where the statuses will be collected
    statuses = collections.OrderedDict()

    # Determine if a run is ongoing
    # To do so, we need the most recent run
    mostRecentRun = runs[runs.keys()[-1]]
    runOngoing = mostRecentRun.isRunOngoing()
    if runOngoing:
        runOngoingNumber = "- " + mostRecentRun.prettyName
    else:
        runOngoingNumber = ""
    # Add to status
    statuses["Ongoing run?"] = "{0} {1}".format(runOngoing, runOngoingNumber)

    if db.has_key("config") and db["config"].has_key("receiverLogLastModified"):
        receiverLogLastModified = db["receiverLogLastModified"]
        lastModified = time.time() - receiverLogLastModified
        # Display in minutes
        lastModified = int(lastModified//60)
        lastModifiedMessage = "{0} minutes ago".format(lastModified)
    else:
        lastModified = -1
        lastModifiedMessage = "Error! Could not retrieve receiver log information!"
    # Add to status
    statuses["Last requested data"] = lastModifiedMessage

    # Determine server statuses
    sites = serverParameters.statusRequestSites
    for site, url in sites.iteritems():
        serverError = {}
        statusResult = ""
        try:
            serverRequest = requests.post(url + "/status", timeout = 0.5)
            if serverRequest.status_code != 200:
                serverError.setdefault("Request error", []).append("Request to \"{0}\" at \"{1}\" returned error response {2}!".format(site, url, serverRequest.status_code))
            else:
                statusResult = "Site is up!"
        except requests.exceptions.Timeout as e:
            serverError.setdefault("Timeout error", []).append("Request to \"{0}\" at \"{1}\" timed out with error {2}!".format(site, url, e))

        # Return error if one occurred
        if serverError != {}:
            statusResult = serverError

        # Add to status
        statuses[site] = statusResult

    if ajaxRequest == False:
        return render_template("status.html", statuses = statuses)
    else:
        drawerContent = ""
        mainContent = render_template("statusMainContent.html", statuses = statuses)

        return jsonify(drawerContent = drawerContent, mainContent = mainContent)

###################################################
@app.route("/upgradeDocker")
@login_required
def upgradeDocker():
    """ Kill supervisord in the docker image (so that it will be upgrade with the new version by offline). """
    # Display the status page from the other sites
    ajaxRequest = validation.convertRequestToPythonBool("ajaxRequest", request.args)

    error = {}
    if current_user.id != "emcalAdmin":
        error.setdefault("User error", []).append("You are not authorized to view this page!")

    try:
        if os.environ["deploymentOption"]:
            logger.info("Running docker in deployment mode {0}".format(os.environ["deploymentOption"]))
    except KeyError:
        error.setdefault("User error", []).append("Must be in a docker container to run this!")

    if error == {}:
        # Attempt to kill supervisord
        # Following: https://stackoverflow.com/a/2940878
        p = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
        out, err = p.communicate()

        # Kill the process
        for line in out.splitlines():
            if "supervisord" in line:
                pid = int(line.split(None, 1)[0])
                # Send TERM
                os.kill(pid, signal.SIGTERM)
                # NOTE: If this succeeds, then nothing will be sent because the process will be dead...
                error.setdefault("Signal Sent", []).append("Sent TERM signal to line with \"{0}\"".format(line))

        # Give a note if nothing happened....
        if error == {}:
            error.setdefault("No response", []).append("Should have some response by now, but there is none. It seems that the supervisord process cannot be found!")

    # Co-opt error output here since it is probably not worth a new page yet...
    if ajaxRequest == True:
        logger.warning("error: {0}".format(error))
        drawerContent = ""
        mainContent =  render_template("errorMainContent.html", errors = error)

        # We always want to use ajax here
        return jsonify(mainContent = mainContent, drawerContent = "")
    else:
        return render_template("error.html", errors = error)

if __name__ == "__main__":
    pass
