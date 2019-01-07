#!/usr/bin/env python

""" Web App for serving Overwatch results, as well as access to user defined reprocessing
and times slices.

This is the main web app executable, so it contains quite some functionality, especially
that which is not so obvious how to refactor when using flask. Routing is divided up
into authenticated and unauthenticated views.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

# For python 3 support
from __future__ import print_function
from future.utils import iteritems

# General includes
import os
import zipfile
import subprocess
import signal
import jinja2
import json
import collections
import pendulum
import pkg_resources
# For server status
import requests
import logging

from overwatch.database.factoryMethod import getDatabaseFactory
from overwatch.processing.processingClasses import runContainer

logger = logging.getLogger(__name__)

# Flask
from flask import Flask, url_for, request, render_template, redirect, flash, send_from_directory, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_zodb import ZODB
from flask_assets import Environment
from flask_wtf.csrf import CSRFProtect, CSRFError

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.flask import FlaskIntegration

# Server configuration
from ..base import config
(serverParameters, filesRead) = config.readConfig(config.configurationType.webApp)
# Utilities
from ..base import utilities as baseUtilities

# WebApp module includes
from . import routing
from . import auth
from . import validation
from . import utilities  # NOQA

# Processing module includes
from ..processing import processRuns

# Flask setup
app = Flask(__name__, static_url_path=serverParameters["staticURLPath"], static_folder=serverParameters["staticFolder"], template_folder=serverParameters["templateFolder"])

# Setup database
# app.config["ZODB_STORAGE"] = serverParameters["databaseLocation"]
# db = ZODB(app)
databaseFactory = getDatabaseFactory()
from .trending import trendingPage
app.register_blueprint(trendingPage)

# Set secret key for flask
if serverParameters["debug"]:
    # Cannot use the db value here since the reloader will cause it to fail.
    app.secret_key = serverParameters["_secretKey"]
else:
    # Set a temporary secret key. It can be set from the database later
    # The production key is set in ``overwatch.webApp.run``
    app.secret_key = str(os.urandom(50))

# Enable debugging if set in configuration
if serverParameters["debug"] is True:
    app.debug = True

# Setup Bcrypt
app.config["BCRYPT_LOG_ROUNDS"] = config.bcryptLogRounds
bcrypt = Bcrypt(app)

# Setup flask assets
assets = Environment(app)
# Set the Flask Assets debug mode
# Note that the bundling is _only_ performed when flask assets is _not_ in debug mode.
# Thus, we want it to follow the global debug setting unless we explicit set it otherwise.
# For more information, particularly on debugging, see the web app `README.md`. Further details
# are included in the web app utilities module where the filter is defined.
app.config["ASSETS_DEBUG"] = serverParameters["flaskAssetsDebug"] if not serverParameters["flaskAssetsDebug"] is None else serverParameters["debug"]
# Load bundles from configuration file
assets.from_yaml(pkg_resources.resource_filename("overwatch.webApp", "flaskAssets.yaml"))

# Setup CSRF protection via flask-wtf
csrf = CSRFProtect(app)
# Setup custom error handling to use the error template.
@app.errorhandler(CSRFError)
def handleCSRFError(error):
    """ Handle CSRF error.

    Takes advantage of the property of the ``CSRFError`` class which will return a string
    description when called with ``str()``.

    Note:
        The only requests that could fail due to a CSRF token issue are those made with AJAX,
        so it is reasonable to return an AJAX formatted response.

    Note:
        For the error format in ``errors``, see the :doc:`web app README </webAppReadme>`.

    Args:
        error (CSRFError): Error object raised during as CSRF validation failure.
    Returns:
        str: ``json`` encoded response containing the error.
    """
    # Define the error in the proper format.
    # Also provide some additional error information.
    errors = {"CSRF Error": [
        error,
        "Your page was manipulated. Please contact the admin."
    ]}
    # We don't have any drawer content
    drawerContent = ""
    mainContent = render_template("errorMainContent.html", errors = errors)
    return jsonify(drawerContent = drawerContent, mainContent = mainContent)

# Setup login manager
loginManager = LoginManager()
loginManager.init_app(app)

# Tells the manager where to redirect when login is required.
loginManager.login_view = "login"

@loginManager.user_loader
def load_user(user):
    """ Used to retrieve a remembered user so that they don't need to login again each time they visit the site.

    Args:
        user (str): Username to retrieve.
    Returns:
        auth.User: The user stored in the database which corresponds to the given username, or
            ``None`` if it doesn't exist.
    """
    db = databaseFactory.getDB()
    return auth.User.getUser(user, db)

# Sentry for monitoring errors and other issues.
# Setup sentry to create alerts for warning level messages. Those will include info level breadcrumbs.
sentry_logging = LoggingIntegration(level = logging.INFO, event_level = logging.WARNING)
# Usually, we want the module specific DSN, but we will take a generic one if it's the only one available.
sentryDSN = os.getenv("SENTRY_DSN_WEBAPP") or os.getenv("SENTRY_DSN")
if sentryDSN:
    # It's helpful to know that sentry is setup, but we also don't want to put the DSN itself in the logs,
    # so we simply note that it is enabled.
    logger.info("Sentry DSN set and integrations enabled.")
# Note that if SENTRY_DSN is not set, it simply won't activated.
sentry_sdk.init(dsn = sentryDSN, integrations = [FlaskIntegration(), sentry_logging])

######################################################################################################
# Unauthenticated Routes
######################################################################################################

@app.route("/", methods=["GET", "POST"])
def login():
    """ Login function. This is is the first page the user sees.

    Unauthenticated users are also redirected here if they try to access something restricted.
    After logging in, it should then forward them to resource they requested.

    Note:
        Function args are provided through the flask request object.

    Args:
        ajaxRequest (bool): True if the response should be via AJAX.
        previousUsername (str): The username that was previously used to login. Used to check when
            automatic login should be performed (if it's enabled).
    Returns:
        response: Response based on the provided request. Possible responses included validating
            and logging in the user, rejecting invalid user credentials, or redirecting unauthenticated
            users from a page which requires authentication (it will redirect back after login).
    """
    # Retrieve args
    logger.debug("request.args: {args}".format(args = request.args))
    ajaxRequest = validation.convertRequestToPythonBool("ajaxRequest", request.args)
    previousUsername = validation.extractValueFromNextOrRequest("previousUsername", request.args)

    errorValue = None
    nextValue = routing.getRedirectTarget()

    db = databaseFactory.getDB()
    # Check for users and notify if there are none!
    if "users" not in db.get("config") or not db.get("config")["users"]:
        logger.fatal("No users found in database!")
        # This is just for developer convenience.
        if serverParameters["debug"]:
            # It should be extremely unlikely for this condition to be met!
            logger.warning("Since we are debugging, adding users to the database automatically!")
            # Transactions saved in the function
            baseUtilities.updateDBSensitiveParameters(db)

    # A post request Attempt to login the user in
    if request.method == "POST":
        # Validate the request.
        (errorValue, username, password) = validation.validateLoginPostRequest(request)

        # If there is an error, just drop through to return an error on the login page
        if errorValue is None:
            # Validate user
            validUser = auth.authenticateUser(username, password, db)

            # Return user if successful
            if validUser is not None:
                # Login the user into flask
                login_user(validUser, remember=True)

                message = "Login Success for {id}.".format(id = validUser.id)
                flash(message)
                logger.info(message)

                return routing.redirectBack("index")
            else:
                errorValue = "Login failed with invalid credentials"

    if previousUsername == serverParameters["defaultUsername"]:
        logger.debug("Previous username is the same as the default username!")
    logger.debug("serverParameters[defaultUsername]: {defaultUsername}".format(defaultUsername = serverParameters["defaultUsername"]))
    # If we are not authenticated and we have a default username set and the previous username is not the default.
    if not current_user.is_authenticated and serverParameters["defaultUsername"] and previousUsername != serverParameters["defaultUsername"]:
        # In this case, we want to perform an automatic login.
        # Clear previous flashes which will be confusing to the user
        # See: https://stackoverflow.com/a/19525521
        session.pop('_flashes', None)
        # Get the default user
        defaultUser = auth.User.getUser(serverParameters["defaultUsername"], db)
        # Login the user into flask
        login_user(defaultUser, remember=True)
        # Note for the user
        logger.info("Logged into user \"{id}\" automatically!".format(id = current_user.id))
        flash("Logged into user \"{id}\" automatically!".format(id = current_user.id))

    # If we visit the login page, but we are already authenticated, then send to the index page.
    if current_user.is_authenticated:
        logger.info("Redirecting logged in user \"{id}\" to the index page.".format(id = current_user.id))
        return redirect(url_for("index", ajaxRequest = json.dumps(ajaxRequest)))

    if ajaxRequest is False:
        return render_template("login.html", error=errorValue, nextValue=nextValue)
    else:
        drawerContent = ""
        mainContent = render_template("loginMainContent.html", error=errorValue, nextValue=nextValue)
        return jsonify(drawerContent = drawerContent, mainContent = mainContent)

@app.route("/logout")
@login_required
def logout():
    """ Logs out an authenticated user.

    Once completed, it will always redirect to back to ``login()``. If the user then logs in,
    they will be redirected back to index. Some care is required to handle all of the edge cases
    - these are handled via careful redirection in ``login()`` and the ``routing`` module.

    Warning:
        Careful in making changes to the routing related to function, as it is hard coded
        in ```routing.redirectBack()``!

    Note:
        ``previousUsername`` is provided to the next request so we can do the right thing on
        automatic login. In that case, we want to provide automatic login, but also allow the opportunity
        to logout and then explicitly login with different credentials.

    Args:
        None
    Returns:
        Response: Redirect back to the login page.
    """
    previousUsername = current_user.id
    logout_user()

    flash("User logged out!")
    return redirect(url_for("login", previousUsername = previousUsername))

@app.route("/contact")
def contact():
    """ Simple contact page so we can provide general information and support to users.

    Also exposes useful links for development (for test data), and system status information
    to administrators (which must authenticate as such).

    Note:
        Function args are provided through the flask request object.

    Args:
        ajaxRequest (bool): True if the response should be via AJAX.
    Returns:
        Response: Contact page populated via template.
    """
    ajaxRequest = validation.convertRequestToPythonBool("ajaxRequest", request.args)

    # Provide current year for copyright information
    currentYear = pendulum.now(tz = "UTC").year
    if ajaxRequest is False:
        return render_template("contact.html", currentYear = currentYear)
    else:
        drawerContent = ""
        mainContent = render_template("contactMainContent.html", currentYear = currentYear)
        return jsonify(drawerContent = drawerContent, mainContent = mainContent)

@app.route("/status", methods=["GET"])
def statusQuery():
    """ Returns the status of the Overwatch server instance.

    This can be accessed by a GET request. If the request is successful, it will response with "Alive"
    and the response code 200. If it didn't work properly, then the response won't come through properly,
    indicating that an action must be taken to restart the web app.

    Note:
        It doesn't require authentication to simply the process of querying it. This should be fine
        because the information that the web app is up isn't sensitive.

    Args:
        None
    Returns:
        Response: Contains a string, "Alive", and a 200 response code to indicate that the web app is still up.
            If the database is somehow not available, it will return "DB failed" and a 500 response code.
            A response timeout indicates that the web app is somehow down.
    """
    # Responds to requests from other OVERWATCH servers to display the status of the site
    response = "DB failed", 500
    db = databaseFactory.getDB()
    if db:
        response = "Alive", 200
    return response

######################################################################################################
# Authenticated Routes
######################################################################################################

@app.route("/monitoring", methods=["GET"])
@login_required
def index():
    """ This is run list, which is the main page for logged in users.

    The run list shows all available runs, which links to available subsystem histograms, as well
    as the underlying root files. The current status of data taking, as extracted from when the
    last file was received, is displayed in the drawer, as well as some links down the page to
    allow runs to be moved through quickly. The main content is paginated in a fairly rudimentary
    manner (it should be sufficient for our purposes). We have selected to show 50 runs per page,
    which seems to be a reasonable balance between showing too much or too little information. This
    can be tuned further if necessary.

    Note:
        Function args are provided through the flask request object.

    Args:
        ajaxRequest (bool): True if the response should be via AJAX.
        runOffset (int): Number of runs to offset into the run list. Default: 0.
    Returns:
        Response: The main index page populated via template.
    """
    logger.debug("request.args: {args}".format(args = request.args))
    ajaxRequest = validation.convertRequestToPythonBool("ajaxRequest", request.args)
    # We only use this once and there isn't much complicated, so we just perform the validation here.
    runOffset = validation.convertRequestToPositiveInteger(paramName = "runOffset", source = request.args)

    db = databaseFactory.getDB()
    runs = db.get("runs")

    # Determine if a run is ongoing
    # To do so, we need the most recent run (regardless of which runs we selected to display)
    mostRecentRun = runs[runs.keys()[-1]]
    runOngoing = runContainer.isRunOngoing(mostRecentRun)
    if runOngoing:
        runOngoingNumber = mostRecentRun.runNumber
    else:
        runOngoingNumber = ""

    # Determine number of runs to display
    # We select a default of 50 runs per page. Too many might be unreasonable.
    numberOfRunsToDisplay = 50
    # Restrict the runs that we are going to display to those that are included in our requested range.
    # It is reversed because we process the earliest runs first. However, the reversed object isn't scriptable,
    # so it must be converted to a list to slice it.
    # +1 on the upper limit so that the 50 is inclusive
    runsToUse = list(reversed(runs.values()))[runOffset:runOffset + numberOfRunsToDisplay + 1]
    logger.debug("runOffset: {}, numberOfRunsToDisplay: {}".format(runOffset, numberOfRunsToDisplay))
    # Total number of runs, which should be displayed at the bottom.
    numberOfRuns = len(runs.keys())

    # We want 10 anchors
    # NOTE: We need to convert it to an int to ensure that the mod call in the template works.
    anchorFrequency = int(numberOfRunsToDisplay / 10.0)

    if ajaxRequest is not True:
        return render_template("runList.html", drawerRuns = runsToUse,
                               mainContentRuns = runsToUse,
                               runOngoing = runOngoing,
                               runOngoingNumber = runOngoingNumber,
                               subsystemsWithRootFilesToShow = serverParameters["subsystemsWithRootFilesToShow"],
                               anchorFrequency = anchorFrequency,
                               runOffset = runOffset, numberOfRunsToDisplay = numberOfRunsToDisplay,
                               totalNumberOfRuns = numberOfRuns)
    else:
        drawerContent = render_template("runListDrawer.html", runs = runsToUse, runOngoing = runOngoing,
                                        runOngoingNumber = runOngoingNumber, anchorFrequency = anchorFrequency,
                                        startOfRunTimeStamp=runContainer.startOfRunTimeStamp)
        mainContent = render_template("runListMainContent.html", runs = runsToUse, runOngoing = runOngoing,
                                      runOngoingNumber = runOngoingNumber,
                                      subsystemsWithRootFilesToShow = serverParameters["subsystemsWithRootFilesToShow"],
                                      anchorFrequency = anchorFrequency,
                                      runOffset = runOffset, numberOfRunsToDisplay = numberOfRunsToDisplay,
                                      totalNumberOfRuns = numberOfRuns)

        return jsonify(drawerContent = drawerContent, mainContent = mainContent)

@app.route("/Run<int:runNumber>/<string:subsystemName>/<string:requestedFileType>", methods=["GET"])
@login_required
def runPage(runNumber, subsystemName, requestedFileType):
    """ Serves the run pages and root files for a request run.

    This is really the main function for serving information in Overwatch. The run page provides subsystem
    specific histograms and information to the user. Time slices and user directed reprocessing is also
    made available through this page. If a subsystem has made a customized run page, this will automatically
    be served. If they haven't, then a default page will be provided.

    This function serves both run pages, which display histograms, as well as root files pages, which provide
    direct access to the underlying root files. Since they require similar information, it is convenient to
    provide access to both of them from one function.

    Note:
        Some function args (after the first 3) are provided through the flask request object.

    Warning:
        Careful if changing the routing for this function, as the display swtich for the time slices button
        in the web app depends on "runPage" being in this route. If this is changed, then the ``js`` also needs
        to be changed.

    Args:
        runNumber (int): Run number of interest.
        subsystemName (str): Name of the subsystem of interest.
        requestedFileType (str): Type of file in which we are interested. Can be either ``runPage`` (corresponding to a
            run page) or ``rootFiles`` (corresponding to access to the underlying root files).
        jsRoot (bool): True if the response should use jsRoot instead of images.
        ajaxRequest (bool): True if the response should be via AJAX.
        requestedHistGroup (str): Name of the requested hist group. It is fine for it to be an empty string.
        requestedHist (str): Name of the requested histogram. It is fine for it to be an empty string.
    Returns:
        Response: A run page or root files page populated via template.
    """
    # Setup runDir and db information
    runDir = "Run{runNumber}".format(runNumber = runNumber)
    db = databaseFactory.getDB()
    runs = db.get("runs")

    # Validation for all passed values
    (error, run, subsystem, requestedFileType, jsRoot, ajaxRequest, requestedHistGroup, requestedHist, timeSliceKey, timeSlice) = validation.validateRunPage(runDir, subsystemName, requestedFileType, runs)

    # This will only work if all of the values are properly defined.
    # Otherwise, we just skip to the end to return the error to the user.
    if error == {}:
        # Sets the filenames for the json and image files
        # Create these templates here so we don't have inside of the template
        jsonFilenameTemplate = os.path.join(subsystem.jsonDir, "{}.json")
        if timeSlice:
            jsonFilenameTemplate = jsonFilenameTemplate.format(timeSlice.filenamePrefix + ".{}")
        imgFilenameTemplate = os.path.join(subsystem.imgDir, "{}." + serverParameters["fileExtension"])

        # Print request status
        logger.debug("request: {}".format(request.args))
        logger.debug("runDir: {}, subsystem: {}, requestedFileType: {}, "
                     "ajaxRequest: {}, jsRoot: {}, requestedHistGroup: {}, requestedHist: {}, "
                     "timeSliceKey: {}, timeSlice: {}".format(runDir, subsystemName, requestedFileType,
                                                              ajaxRequest, jsRoot,
                                                              requestedHistGroup, requestedHist,
                                                              timeSliceKey, timeSlice))
    else:
        logger.warning("Error on run page: {error}".format(error = error))

    if ajaxRequest is not True:
        if error == {}:
            if requestedFileType == "runPage":
                # Attempt to use a subsystem specific run page if available
                runPageName = subsystemName + "runPage.html"
                if runPageName not in serverParameters["availableRunPageTemplates"]:
                    runPageName = runPageName.replace(subsystemName, "")

                # We use try here because it's possible for this page not to exist if ``availableRunPageTemplates``
                # is not determined properly due to other files interfering..
                try:
                    returnValue = render_template(runPageName, run = run, subsystem = subsystem,
                                                  selectedHistGroup = requestedHistGroup, selectedHist = requestedHist,
                                                  jsonFilenameTemplate = jsonFilenameTemplate,
                                                  imgFilenameTemplate = imgFilenameTemplate,
                                                  jsRoot = jsRoot, timeSlice = timeSlice)
                except jinja2.exceptions.TemplateNotFound as e:
                    error.setdefault("Template Error", []).append("Request template: \"{}\", but it was not found!".format(e.name))
            elif requestedFileType == "rootFiles":
                try:
                    # Subsystem specific run pages are not available since they don't seem to be necessary
                    # Note that even though this file should always be found, we check for exceptions just in case.
                    returnValue = render_template("rootFiles.html", run = run, subsystem = subsystemName)
                except jinja2.exceptions.TemplateNotFound as e:
                    error.setdefault("Template Error", []).append("Request template: \"{}\", but it was not found!".format(e.name))
            else:
                # Redundant, but good to be careful
                error.setdefault("Template Error", []).append("Request page: \"{}\", but it was not found!".format(requestedFileType))

        if error != {}:
            logger.warning("error: {error}".format(error = error))
            returnValue = render_template("error.html", errors = error)

        return returnValue
    else:
        if error == {}:
            if requestedFileType == "runPage":
                # Drawer
                runPageDrawerName = subsystemName + "runPageDrawer.html"
                if runPageDrawerName not in serverParameters["availableRunPageTemplates"]:
                    runPageDrawerName = runPageDrawerName.replace(subsystemName, "")
                # Main content
                runPageMainContentName = subsystemName + "runPageMainContent.html"
                if runPageMainContentName not in serverParameters["availableRunPageTemplates"]:
                    runPageMainContentName = runPageMainContentName.replace(subsystemName, "")

                # We use try here because it's possible for this page not to exist if ``availableRunPageTemplates``
                # is not determined properly due to other files interfering..
                # If either one fails, we want to jump right to the template error.
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
                                                  jsRoot = jsRoot, timeSlice = timeSlice,
                                                  prettyPrintUnixTime=utilities.prettyPrintUnixTime)
                except jinja2.exceptions.TemplateNotFound as e:
                    error.setdefault("Template Error", []).append("Request template: \"{}\", but it was not found!".format(e.name))
            elif requestedFileType == "rootFiles":
                try:
                    # Subsystem specific run pages are not available since they don't seem to be necessary
                    # Note that even though this file should always be found, we check for exceptions just in case.
                    drawerContent = ""
                    mainContent = render_template("rootFilesMainContent.html",
                                                  run = run,
                                                  subsystem = subsystemName,
                                                  prettyPrintUnixTime=utilities.prettyPrintUnixTime)
                except jinja2.exceptions.TemplateNotFound as e:
                    error.setdefault("Template Error", []).append("Request template: \"{}\", but it was not found!".format(e.name))
            else:
                # Redundant, but good to be careful
                error.setdefault("Template Error", []).append("Request page: \"{}\", but it was not found!".format(requestedFileType))

        if error != {}:
            logger.warning("error: {error}".format(error = error))
            drawerContent = ""
            mainContent = render_template("errorMainContent.html", errors = error)

        # Includes hist group and hist name for time slices since it is easier to pass it here than parse the GET requests. Otherwise, they are ignored.
        return jsonify(drawerContent = drawerContent,
                       mainContent = mainContent,
                       timeSliceKey = json.dumps(timeSliceKey),
                       histName = requestedHist,
                       histGroup = requestedHistGroup)

@app.route("/monitoring/protected/<path:filename>")
@login_required
def protected(filename):
    """ Serves the underlying files.

    This function is response for actually making files available. Ideally, these would be served via
    the production web server, but since access to the data requires authentication, we instead have
    to provide access via this function. To provide this function, we utilized the approach
    `described here <https://stackoverflow.com/a/27611882>`_.

    Note:
        This function ignores GET parameters. This is done intentionally to allow for avoiding problematic
        caching by a browser. To avoid this caching, simply pass an additional get parameter after the
        filename which varies when we need to avoid the cache. This is particularly useful for time slices,
        where the name could be the same, but the information has changed since last being served.

    Args:
        filename (str): Path to the file to be served.
    Returns:
        Response: File with the proper headers.
    """
    logger.debug("filename: {filename}".format(filename = filename))
    # Ignore the time GET parameter that is sometimes passed- just to avoid the cache when required
    #if request.args.get("time"):
    #    print "timeParameter:", request.args.get("time")
    return send_from_directory(os.path.realpath(serverParameters["protectedFolder"]), filename)

@app.route("/timeSlice", methods=["GET", "POST"])
@login_required
def timeSlice():
    """ Handles time slice and user reprocessing requests.

    This is the main function for serving user requests. This function calls out directly to the processing module
    to perform the actual time slice or reprocessing request. It provides access to this functionality through
    the interface built into the header of the run page. In the case of a POST request, it handles, validates,
    and processes the timing request, rendering the result template and returning the user to the same spot as
    in the previous page. A GET request is invalid and will return an error (but the route itself is allowed
    to check that it is handled correctly).

    This request should always be submitted via AJAX.

    Note:
        Function args are provided through the flask request object.

    Args:
        jsRoot (bool): True if the response should use jsRoot instead of images.
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
        Response: A run page template populated with information from a newly processed time slice (via a redirect
            to ``runPage()``). In case of error(s), returns the error message(s).
    """
    logger.debug("request.form: {}".format(request.form))
    # We don't get ``ajaxRequest`` because this request should always be made via AJAX.
    jsRoot = validation.convertRequestToPythonBool("jsRoot", request.form)

    if request.method == "POST":
        # Get the runs
        db = databaseFactory.getDB()
        runs = db.get("runs")

        # Validates the request.
        (error, minTime, maxTime, runDir, subsystem, histGroup, histName, inputProcessingOptions) = validation.validateTimeSlicePostRequest(request, runs)

        if error == {}:
            # Print input values for help in debugging.
            logger.debug("minTime: {minTime}".format(minTime = minTime))
            logger.debug("maxTime: {maxTime}".format(maxTime = maxTime))
            logger.debug("runDir: {runDir}".format(runDir = runDir))
            logger.debug("subsystem: {subsystem}".format(subsystem = subsystem))
            logger.debug("histGroup: {histGroup}".format(histGroup = histGroup))
            logger.debug("histName: {histName}".format(histName = histName))

            # Process the time slice
            returnValue = processRuns.processTimeSlices(runs, runDir, minTime, maxTime, subsystem, inputProcessingOptions)
            logger.info("returnValue: {}".format(returnValue))
            logger.debug("runs[runDir].subsystems[subsystem].timeSlices: {}".format(runs[runDir].subsystems[subsystem].timeSlices))

            # A normal return value should be a time slice key as a string. We can continue as expected.
            # However, if we received an error, we expect some sort of dictionary (mapping). We handle that below.
            if not isinstance(returnValue, collections.Mapping):
                timeSliceKey = returnValue

                # Passed off the result to render via the run page since we a time slice just modifies
                # the content which is displayed there.
                # We always want to use AJAX here
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

        logger.info("Time slices error: {error}".format(error = error))
        drawerContent = ""
        mainContent = render_template("errorMainContent.html", errors = error)

        # We always want to use AJAX here
        return jsonify(drawerContent = drawerContent, mainContent = mainContent)
    else:
        return render_template("error.html", errors={"error": ["Need to access through a run page!"]})

@app.route("/testingDataArchive")
@login_required
def testingDataArchive():
    """ Provides a zip archive of test data for Overwatch development.

    This function will look through at most the 5 most recent runs, looking for the minimum number of files
    necessary for running Overwatch successfully. These files will be zipped up and provided to the user.
    The minimum files are the combined file, and the most recent file received for the subsystem (they are
    usually the same, but it is easier to include both). If possible, an additional file is included for testing
    the time slice and trending functionality. It may not always be available if runs are extremely short. The
    zip archive will include all subsystems which are available. It will skip runs where any subsystem is unavailable
    to ensure that the data provided is of more utility.

    Warning:
        Careful in changing the routing for this function, as the name of it is hard coded in
        ``webApp.routing.redirectBack()``. This hard coding is to avoid a loop where the user is stuck accessing
        this file after logging in.

    Args:
        None
    Returns:
        redirect: Redirect to the newly created file.
    """
    # Get db
    db = databaseFactory.getDB()
    runs = db.get("runs")
    runList = runs.keys()

    # Retrieve at most 5 files
    numberOfFilesToDownload = 5
    if len(runList) < 5:
        numberOfFilesToDownload = len(runList)

    # Create zip file. It will be stored in the root of the data directory.
    # It is fine to be overwritten because it can always be recreated.
    zipFilename = "testingDataArchive.zip"
    with zipfile.ZipFile(os.path.join(serverParameters["protectedFolder"], zipFilename), "w") as zipFile:
        logger.info("Creating zipFile at %s" % os.path.join(serverParameters["protectedFolder"], zipFilename))

        # Starting from the end, we look for runs which have the full set of subsystems. For each one, we write
        # each subsystem of that run to the zip file. Note that the files are written in reverse order. However,
        # this is fine because the order doesn't make a difference in the final archive.
        numberOfFilesWritten = 0
        # We need to explicitly call keys here because ``BTree`` doesn't support being reversed directly.
        for runDir in reversed(runs.keys()):
            if numberOfFilesWritten == numberOfFilesToDownload:
                break
            # It's easier to operate with the runContainer object.
            run = runs[runDir]
            # Ensure that we get a full set of subsystems. If the run doesn't have data for all subsystems, we skip
            # it because otherwise the test data is much less useful.
            if set(serverParameters["subsystemList"]) != set(run.subsystems):
                continue
            else:
                for subsystem in run.subsystems.values():
                    # Write files to the zip file
                    # Combined file
                    zipFile.write(os.path.join(serverParameters["protectedFolder"], subsystem.combinedFile.filename))
                    # Uncombined file. This is the last file that was received from the subsystem.
                    zipFile.write(os.path.join(serverParameters["protectedFolder"], subsystem.files[subsystem.files.keys()[-1]].filename))
                    # We select 4 as an arbitrary point to ensure that there is some different between the data stored
                    # in it and the combined file.
                    if len(subsystem.files) > 4:
                        # Write an additional file for testing time slices.
                        zipFile.write(os.path.join(serverParameters["protectedFolder"], subsystem.files[subsystem.files.keys()[-5]].filename))
                numberOfFilesWritten += 1

    # Return with a download link
    return redirect(url_for("protected", filename=zipFilename))

@app.route("/overwatchStatus")
@login_required
def overwatchStatus():
    """ Query and determine the status of some parts of Overwatch.

    This function takes advantage of the status functionality of the web app to determine the state of any
    deployed web apps that are specified in the web app config. This is achieved by sending requests to all
    other sites and then aggregating the results. Each request is allowed a 0.5 second timeout.

    It will also provide information on when the last files were received from other sites.

    This functionality will only work if the web app is accessible from the site where this is run. This may
    not always be the case.

    Note:
        Since the GET requests are blocking, it can appear that the web app is hanging. However, this is
        just due to the time that the requests take.

    Warning:
        This can behave somewhat strangely using the flask development server, especially if there is reloading.
        If possible, it is best to run with ``uwsgi`` for testing of this function.

    Note:
        Function args are provided through the flask request object.

    Args:
        ajaxRequest (bool): True if the response should be via AJAX.
    Returns:
        Response: Status template populated with the status of Overwatch sites specified in the configuration.
    """
    # Setup
    db = databaseFactory.getDB()
    runs = db.get("runs")
    ajaxRequest = validation.convertRequestToPythonBool("ajaxRequest", request.args)

    # Where the statuses will be collected
    statuses = collections.OrderedDict()

    # Determine if a run is ongoing
    # To do so, we need the most recent run
    mostRecentRun = runs[runs.keys()[-1]]
    runOngoing = runContainer.isRunOngoing(mostRecentRun)
    if runOngoing:
        runOngoingNumber = "- " + mostRecentRun.prettyName
    else:
        runOngoingNumber = ""
    # Add to status
    statuses["Ongoing run?"] = "{runOngoing} {runOngoingNumber}".format(runOngoing = runOngoing, runOngoingNumber = runOngoingNumber)

    # Determine the time of the most recent modification
    # Add to status
    statuses["Time since last timestamp file"] = "{minutes} minutes".format(minutes = int(mostRecentRun.minutesSinceLastTimestamp()))

    # Determine server statuses
    exceptionErrorMessage = "Request to \"{site}\" at \"{url}\" {errorType} with error message {e}!"
    sites = serverParameters["statusRequestSites"]
    for site, url in iteritems(sites):
        serverError = {}
        statusResult = ""
        try:
            serverRequest = requests.get(url + "/status", timeout = 0.5)
            if serverRequest.status_code != 200:
                serverError.setdefault("Request error", []).append("Request to \"{}\" at \"{}\" returned error response {}!".format(site, url, serverRequest.status_code))
            else:
                statusResult = "Site is up!"
        except requests.exceptions.Timeout as e:
            serverError.setdefault("Timeout error", []).append(exceptionErrorMessage.format(site = site, url = url, errorType = "timed out", e = e))
        except requests.exceptions.ConnectionError as e:
            serverError.setdefault("Connection error", []).append(exceptionErrorMessage.format(site = site, url = url, errorType = "had a connection error", e = e))
        except requests.exceptions.RequestException as e:
            serverError.setdefault("General Requests error", []).append(exceptionErrorMessage.format(site = site, url = url, errorType = "had a general requests error", e = e))

        # Store the error if one occurred
        if serverError != {}:
            statusResult = serverError
        # Add to status
        statuses[site] = statusResult

    if ajaxRequest is False:
        return render_template("status.html", statuses = statuses)
    else:
        drawerContent = ""
        mainContent = render_template("statusMainContent.html", statuses = statuses)

        return jsonify(drawerContent = drawerContent, mainContent = mainContent)

@app.route("/upgradeDocker")
@login_required
def upgradeDocker():
    """ Kill ``supervisord`` in the docker image so the docker image will stop.

    On the ALICE offline infrastructure, a stopped docker image will cause the image to be upgraded and restarted.
    Thus, we can intentionally stop the image indirectly by killing the supervisor process to force an upgrade.

    Note:
        This operation requires administrative rights (as the ``emcalAdmin`` user).

    Warning:
        This is untested and is unsupported in any other infrastructure! It is experimental as of August 2018.

    Note:
        Function args are provided through the flask request object.

    Args:
        ajaxRequest (bool): True if the response should be via AJAX.
    Returns:
        Response or None: Likely a timeout if the function was successful, or a response with an error message
            if the function was unsuccessful.
    """
    # Display the status page from the other sites
    ajaxRequest = validation.convertRequestToPythonBool("ajaxRequest", request.args)

    error = {}
    if current_user.id != "emcalAdmin":
        error.setdefault("User error", []).append("You are not authorized to view this page!")

    try:
        if os.environ["deploymentOption"]:
            logger.info("Running docker in deployment mode {}".format(os.environ["deploymentOption"]))
    except KeyError:
        error.setdefault("User error", []).append("Must be in a docker container to run this!")

    if error == {}:
        # Attempt to kill `supervisord`
        # Following: https://stackoverflow.com/a/2940878
        p = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
        out, err = p.communicate()

        # Kill the process
        for line in out.splitlines():
            if "supervisord" in line:
                pid = int(line.split(None, 1)[0])
                # Send TERM
                os.kill(pid, signal.SIGTERM)
                # NOTE: If this succeeds, then nothing will be sent because the process will be dead.
                error.setdefault("Signal Sent", []).append("Sent TERM signal to process with \"{line}\"".format(line = line))

        # Give a note if nothing happened.
        if error == {}:
            error.setdefault("No response", []).append("Should have some response by now, but there is none. It seems that the `supervisord` process cannot be found!")

    # Co-opt error output here since it is not worth a new template.
    if ajaxRequest is True:
        logger.warning("error: {error}".format(error = error))
        drawerContent = ""
        mainContent = render_template("errorMainContent.html", errors = error)

        # We always want to use AJAX here
        return jsonify(drawerContent = drawerContent, mainContent = mainContent)
    else:
        return render_template("error.html", errors = error)

