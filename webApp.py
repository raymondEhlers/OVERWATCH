#!/usr/bin/env python
""" WSGI server for hists and interactive features with HLT histograms.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University 
"""

# General includes
import os
import socket
import time
import zipfile

# Flask
from flask import Flask, url_for, request, render_template, redirect, flash, send_from_directory, Markup
from flask.ext.login import LoginManager, login_user, logout_user, login_required, current_user
from flask.ext.bcrypt import Bcrypt

# Server configuration
from config.serverParams import serverParameters

# WebApp Module includes
from webAppModules import routing
from webAppModules import auth
from webAppModules import validation

# Main processing file
import processRuns

# Processing module includes
from processRunsModules import utilities
from processRunsModules import qa

# Flask setup
app = Flask(__name__, static_url_path=serverParameters.staticURLPath, static_folder=serverParameters.staticFolder, template_folder=serverParameters.templateFolder)

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
    return auth.User.getUser(user)

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

    errorValue = None
    nextValue = routing.getRedirectTarget()
    if request.method == "POST":
        # Validate the request.
        (errorValue, username, password) = validation.validateLoginPostRequest(request)

        # If there is an error, just drop through to return an error on the login page
        if errorValue == None:
            # Validate user
            validUser = auth.authenticateUser(username, password)

            # Return user if successful
            if validUser is not None:
                # Login the user into flask
                login_user(validUser, remember=True)

                flash("Login Success for %s." % validUser.id)

                return routing.redirectBack("index")
            else:
                errorValue = "Login failed with invalid credentials"

    # If we visit the login page, but we are already authenticated, then send to the index page.
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    return render_template("login.html", error=errorValue, nextValue=nextValue)

###################################################
@app.route("/logout")
@login_required
def logout():
    """ Logout function.

    Redirects back to :func:`.index`, which leads back to the login page.
    """
    logout_user()

    flash("User logged out!")
    return redirect(url_for("index"))

###################################################
@app.route("/contact")
def contact():
    """ Simple contact page so we can provide support in the future."""
    return render_template("contact.html")

###################################################
@app.route("/favicon.ico")
def favicon():
    """ Browsers always try to load the Favicon, so this suppresses the errors about not finding one. """
    return ""

######################################################################################################
# Unauthenticated Routes
######################################################################################################

###################################################
@app.route("/monitoring")
@login_required
def index():
    """ This is the main page for logged in users. It always redirect to the run list. 
    
    In the case of dynamicContent being enabled, it renders the runList template. Otherwise, it will
    redirect to the static page.
    """
    if serverParameters.dynamicContent:
        return render_template(os.path.join("data", "runList.html"))
    else:
        return redirect(url_for("protected", filename="runList.html"))

###################################################
@app.route("/<path:runPath>")
@login_required
def showRuns(runPath):
    """ This handles the routing for serving most files, especially for partial merging and for serving ROOT files.

    In such cases, the path is requested and must be handled (ie ``localhost:port/Run123/HLT/HLTRootFiles.html``).
    In the case of templates, the template is rendered. Anchors (which are from partial merges) are handled specially.
    If the path is to a ROOT file or we are using static html files then the request is forwarded to
    :func:`.protected()`. This also covers any other files, such as images, although most of those directly
    call url_for("protected").

    Note:
        This function ensures that the user is logged in before it serves the file. 
    """
    # Hnaldes partial merges and rendering templates that are accessed by path.
    if serverParameters.dynamicContent and ".root" not in runPath:
        # Handle anchor. Should only occur for timeSlices
        if "#" in runPath:
            anchor = runPath[runPath.find("#"):]
            print "anchor:", anchor
            return render_template(os.path.join("data",runPath), scrollAmount=anchor)

        print "runPath:", runPath
        return render_template(os.path.join("data",runPath))
    else:
        # This handles ROOT files. It also hanldes static html files if dynamicContent is false. 
        return redirect(url_for("protected", filename=runPath))

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
    print "filename", filename
    # Ignore the time GET parameter that is sometimes passed- just to avoid the cache when required
    #if request.args.get("time"):
    #    print "timeParameter:", request.args.get("time")
    return send_from_directory(os.path.realpath(serverParameters.protectedFolder), filename)

###################################################
@app.route("/partialMerge", methods=["GET", "POST"])
@login_required
def partialMerge():
    """ Handles partial merges (time slices)

    In the case of a GET request, it will throw an error, since the interface is built into the header of each
    individual run page. In the case of a POST request, it handles, validates, and processes the timing request,
    rendering the result template and returning the user to the same spot as in the previous page.

    """
    if request.method == "POST":
        # Validates the request
        (error, minTime, maxTime, runNumber, subsystem, scrollAmount) = validation.validatePartialMergePostRequest(request)

        if error == {}:
            # Properly format the scrolling variable to be recognized by javascript
            scrollAmount = "scrollTo" + str(scrollAmount)

            # Print input values
            print "minTime", minTime
            print "maxTime", maxTime
            print "runNumber", runNumber
            print "subsystem", subsystem
            print "scrollAmount", scrollAmount

            # Process the partial merge
            returnPath = processRuns.processPartialRun(runNumber, minTime, maxTime, subsystem)

            print "returnPath", returnPath

            # Passes what usually goes into the anchor as an argument to the template.
            # This is because render_template does not work with an anchor.
            return redirect(url_for("showRuns", runPath=returnPath, _anchor=scrollAmount))
        else:
            print "Error:", error
            return render_template("error.html", errors=error)
    else:
        return render_template("error.html", errors={"error": ["Need to access through other web page"]})

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
    # Variable is shared, so it is defined here
    # This assumes that any folder that exists should have proper files.
    # However, this seems to be a fairly reasonable assumption and can be handled safely.
    runList = utilities.findCurrentRunDirs(serverParameters.protectedFolder)

    if request.method == "POST":
        # Validate post request
        (error, firstRun, lastRun, subsystem, qaFunction) = validation.validateQAPostRequest(request, runList)

        # Process
        if error == {}:
            # Print input values
            print "firstRun:", firstRun
            print "lastRun:", lastRun
            print "subsystem:", subsystem
            print "qaFunction:", qaFunction

            # Process the QA
            returnValues = processRuns.processQA(firstRun, lastRun, subsystem, qaFunction)

            # Ensures that the image is not cached by adding a meaningless but unique argument.
            histPaths = {}
            for name, histPath in returnValues.items():
                # Can add an argument with "&arg=value" if desired
                histPaths[name] = histPath + "?time=" + str(time.time())
                print "histPaths[", name, "]: ", histPaths[name]

            return render_template("qaResult.html", firstRun=firstRun, lastRun=lastRun, qaFunctionName=qaFunction, hists=histPaths)
        else:
            return render_template("error.html", errors=error)

    else:
        return render_template("qa.html", runList=runList, qaFunctionsList=serverParameters.qaFunctionsList, subsystemList=serverParameters.subsystemList, docStrings=qa.qaFunctionDocstrings)

###################################################
@app.route("/testingDataArchive")
@login_required
def testingDataArchive():
    """ Creates a zip archive to download data for QA function testing.

    It will return at most the 5 most recent runs. The archive contains the combined file for all subsystems.

    Args:
        None

    Returns:
        redirect: Redirects to the newly created file.
    """
    # Get the run list
    runList = utilities.findCurrentRunDirs(serverParameters.protectedFolder)

    # Get the most recent runs first
    runList = sorted(runList, reverse=True)

    # Retreive at most 5 files
    if len(runList) < 5:
        numberOfFilesToDownload = len(runList)
    else:
        numberOfFilesToDownload = 5

    # Create zip file. It is stored in the root of the data directory
    zipFilename = "testingDataArchive.zip"
    zipFile = zipfile.ZipFile(os.path.join(serverParameters.protectedFolder, zipFilename), "w")
    print "Creating zipFile at %s" % os.path.join(serverParameters.protectedFolder, zipFilename)

    # Add files to the zip file
    for i in xrange(0, numberOfFilesToDownload):
        for subsystem in serverParameters.subsystemList:
            # Get the combined file
            combinedFile = next(name for name in os.listdir(os.path.join(serverParameters.protectedFolder, runList[i], subsystem)) if "combined" in name)
            print os.path.join(serverParameters.protectedFolder, runList[i], subsystem, combinedFile)

            # Write it to the zip file
            zipFile.write(os.path.join(serverParameters.protectedFolder, runList[i], subsystem, combinedFile))

    # Finish with the zip file
    zipFile.close()

    # Return with a download link
    return redirect(url_for("protected", filename=zipFilename))

if __name__ == "__main__":
    # Support both the WSGI server mode, as well as standalone
    #app.run(host="0.0.0.0")
    print "Starting hist server"

    app.run(host=serverParameters.ipAddress, port=serverParameters.port)
