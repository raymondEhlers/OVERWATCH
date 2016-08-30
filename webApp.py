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
import jinja2
import json
import collections 

try:
    import cPickle as pickle
    #import pickle
except ImportError:
    import pickle

# Flask
from flask import Flask, url_for, request, render_template, redirect, flash, send_from_directory, Markup, jsonify
from flask.ext.login import LoginManager, login_user, logout_user, login_required, current_user
from flask.ext.bcrypt import Bcrypt
from flup.server.fcgi import WSGIServer

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

# Load data
# TODO: Improve mechanism!
runs = pickle.load( open(os.path.join(serverParameters.protectedFolder, "runs.p"), "rb") )

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
    print("request: {0}".format(request.args))
    ajaxRequest = routing.convertRequestToPythonBool("ajaxRequest")

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
        print("Redirecting...")
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

    Redirects back to :func:`.index`, which leads back to the login page.
    """
    logout_user()

    flash("User logged out!")
    return redirect(url_for("index"))

###################################################
@app.route("/contact")
def contact():
    """ Simple contact page so we can provide support in the future."""
    ajaxRequest = routing.convertRequestToPythonBool("ajaxRequest")

    if ajaxRequest == False:
        return render_template("contact.html")
    else:
        drawerContent = ""
        mainContent = render_template("contactMainContent.html")
        return jsonify(drawerContent = drawerContent, mainContent = mainContent)

# TEMP
###################################################
@app.route("/favicon.ico")
def favicon():
    """ Browsers always try to load the Favicon, so this suppresses the errors about not finding one. """
    return ""
# END TEMP

######################################################################################################
# Authenticated Routes
######################################################################################################

###################################################
@app.route("/monitoring", methods=["GET"])
@login_required
def index():
    """ This is the main page for logged in users. It always redirects to the run list.
    
    """
    print("request: {0}".format(request.args))
    ajaxRequest = routing.convertRequestToPythonBool("ajaxRequest")

    try:
        mostRecentRun = runs[runs.keys()[-1]]
        #if mostRecentRun:
        subsystemsInLastRun = mostRecentRun.subsystems
        # We just take the last subsystem in a given run. Any will do
        lastSubsystem = subsystemsInLastRun[subsystemsInLastRun.keys()[-1]]
        runOngoing = lastSubsystem.newFile
        runOngoingNumber = mostRecentRun.runNumber
    except KeyError as e:
        runOngoing = False
        runOngoingNumber = ""

    if ajaxRequest == False:
        return render_template("runList.html", runs=reversed(runs.values()), subsystemsWithRootFilesToShow = serverParameters.subsystemsWithRootFilesToShow, runOngoing = runOngoing, runOngoingNumber = runOngoingNumber)
    else:
        drawerContent = render_template("runListDrawer.html", runOngoing = runOngoing, runOngoingNumber = runOngoingNumber)
        mainContent = render_template("runListMainContent.html", runs=reversed(runs.values()), subsystemsWithRootFilesToShow = serverParameters.subsystemsWithRootFilesToShow, runOngoing = runOngoing, runOngoingNumber = runOngoingNumber)

        return jsonify(drawerContent = drawerContent, mainContent = mainContent)

###################################################
@app.route("/Run<int:runNumber>/<string:subsystem>/<string:requestedFileType>", methods=["GET"])
@login_required
def runPage(runNumber, subsystem, requestedFileType):
    """ Serves the run pages and root files for a request run
    
    """
    runDir = "Run{0}".format(runNumber)
    jsRoot = routing.convertRequestToPythonBool("jsRoot")
    ajaxRequest = routing.convertRequestToPythonBool("ajaxRequest")
    print("request: {0}".format(request.args))
    print("runDir: {0}, subsytsem: {1}, requestedFileType: {2}, ajaxRequest: {3}, jsRoot: {4}".format(runDir, subsystem, requestedFileType, ajaxRequest, jsRoot))
    # TODO: Validate these values
    requestedHistGroup = request.args.get("histGroup", None, type=str)
    requestedHist = request.args.get("histName", None, type=str)

    # Empty strings should be treated as None
    if requestedHistGroup == "":
        requestedHistGroup = None
    if requestedHist == "":
        requestedHist = None

    print("ajaxRequest: {0}, jsRoot: {1}".format(ajaxRequest,jsRoot))

    if ajaxRequest == False:
        if requestedFileType == "runPage":
            runPageName = subsystem + "runPage.html"
            if runPageName not in serverParameters.availableRunPageTemplates:
                runPageName = runPageName.replace(subsystem, "")

            try:
                returnValue = render_template(runPageName, run=runs[runDir], subsystemName=subsystem, selectedHistGroup=requestedHistGroup, selectedHist = requestedHist, jsRoot = jsRoot, useGrid=False)
            except jinja2.exceptions.TemplateNotFound as e:
                returnValue = render_template("error.html", errors={"Template Error": ["Request template: \"{0}\", but it was not found!".format(e.name)]})
        elif requestedFileType == "rootFiles":
            returnValue = render_template("rootfiles.html", run=runs[runDir], subsystem=subsystem)
        else:
            returnValue = render_template("error.html", errors={"Request Error": ["Requested: {0}. Must request either runPage or rootFiles!".format(requestedFileType)]})

        return returnValue
    else:
        print("requestedHistGroup: {0}".format(requestedHistGroup))
        if requestedFileType == "runPage":
            drawerContent = render_template("runPageDrawer.html", run=runs[runDir], subsystem=runs[runDir].subsystems[subsystem], selectedHistGroup = requestedHistGroup, selectedHist = requestedHist, jsRoot = jsRoot, useGrid=False)
            mainContent = render_template("runPageMainContent.html", run=runs[runDir], subsystem=runs[runDir].subsystems[subsystem], selectedHistGroup = requestedHistGroup, selectedHist = requestedHist, jsRoot = jsRoot, useGrid=False)
        elif requestedFileType == "rootFiles":
            drawerContent = ""
            mainContent = render_template("rootfilesMainContent.html", run=runs[runDir], subsystem=subsystem)
        else:
            drawerContent = ""
            mainContent =  render_template("errorMainContent.html", errors={"Request Error": ["Requested: {0}. Must request either runPage or rootFiles!".format(requestedFileType)]})

        return jsonify(drawerContent = drawerContent, mainContent = mainContent)

###################################################
@app.route("/<path:runPath>")
@login_required
def showRuns(runPath):
    """ This handles the routing for serving most files, especially for partial merging and for serving ROOT files.

    In such cases, the path is requested and must be handled (ie ``localhost:port/Run123/HLT/HLTRootFiles.html``).
    In the case of templates, the template is rendered.
    If the path is to a ROOT file or we are using static html files then the request is forwarded to
    :func:`.protected()`. This also covers any other files, such as images, although most of those directly
    call url_for("protected").

    Note:
        This function ensures that the user is logged in before it serves the file.
    """
    # Hnaldes partial merges and rendering templates that are accessed by path.
    print("runPath: {0}".format(runPath))
    if serverParameters.dynamicContent and ".root" not in runPath:
        print("runPath:", runPath)
        return render_template(os.path.join("data",runPath))
    else:
        # This handles ROOT files. It also handles static html files if dynamicContent is false.
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
    print("filename", filename)
    print("request.args: ", request.args)
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
@app.route("/partialMerge", methods=["GET", "POST"])
@login_required
def partialMerge():
    """ Handles partial merges (time slices).

    In the case of a GET request, it will throw an error, since the interface is built into the header of each
    individual run page. In the case of a POST request, it handles, validates, and processes the timing request,
    rendering the result template and returning the user to the same spot as in the previous page.

    """
    print("request: {0}".format(request.args))
    ajaxRequest = routing.convertRequestToPythonBool("ajaxRequest")
    print("request: {0}".format(request.form))

    if request.method == "POST":
        # TEMP
        return jsonify(testData = "testData")

        # Validates the request
        (error, minTime, maxTime, runNumber, subsystem, histGroup, histName) = validation.validatePartialMergePostRequest(request)

        if error == {}:
            # Print input values
            print("minTime: {0}".format(minTime))
            print("maxTime: {0}".format(maxTime))
            print("runNumber: {0}".format(runNumber))
            print("subsystem: {0}".format(subsystem))
            print("histGroup: {0}".format(histGroup))
            print("histName: {0}".format(histName))

            # Process the partial merge
            # TODO: Handle if we return an error
            returnPath = processRuns.processPartialRun(runNumber, minTime, maxTime, subsystem, histGroup, histName)

            print("returnPath", returnPath)

            return redirect(url_for("showRuns", runPath=returnPath))
        else:
            print("Error:", error)
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
    print("request: {0}".format(request.args))
    ajaxRequest = routing.convertRequestToPythonBool("ajaxRequest")
    # Variable is shared, so it is defined here
    # This assumes that any folder that exists should have proper files.
    # However, this seems to be a fairly reasonable assumption and can be handled safely.
    #runList = utilities.findCurrentRunDirs(serverParameters.protectedFolder)
    runList = runs.keys()
    print("runList: {0}".format(runList))

    if request.method == "POST":
        # Validate post request
        (error, firstRun, lastRun, subsystem, qaFunction) = validation.validateQAPostRequest(request, runList)

        # Process
        if error == {}:
            # Print input values
            print("firstRun:", firstRun)
            print("lastRun:", lastRun)
            print("subsystem:", subsystem)
            print("qaFunction:", qaFunction)

            # Process the QA
            returnValues = processRuns.processQA(firstRun, lastRun, subsystem, qaFunction)

            # Ensures that the image is not cached by adding a meaningless but unique argument.
            histPaths = {}
            for name, histPath in returnValues.items():
                # Can add an argument with "&arg=value" if desired
                histPaths[name] = histPath + "?time=" + str(time.time())
                print("histPaths[", name, "]: ", histPaths[name])

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
    print("Creating zipFile at %s" % os.path.join(serverParameters.protectedFolder, zipFilename))

    # Add files to the zip file
    for i in range(0, numberOfFilesToDownload):
        for subsystem in serverParameters.subsystemList:
            # Get the combined file
            if os.path.exists(os.path.join(serverParameters.protectedFolder, runList[i], subsystem)):
                combinedFile = next(name for name in os.listdir(os.path.join(serverParameters.protectedFolder, runList[i], subsystem)) if "combined" in name)
                print(os.path.join(serverParameters.protectedFolder, runList[i], subsystem, combinedFile))

                # Find the file that the combined file is derived from. This is needed because processRuns expects at least the combined file and one other file
                # This will work in cumulative mode just fine. This will also be fine in REQ mode too, since the number of files in the dir is less than the
                # number of combined files, so it will not remerge
                numberOfCombinedFiles = combinedFile.split(".")[2]
                # - is included to remove leading 0's in the time string.
                # It apparently only works on Mac OS X and Linux
                # See: https://stackoverflow.com/a/2073189
                fileTime = time.strftime("%Y_%-m_%-d_%-H_%-M_%-S", time.gmtime(int(combinedFile.split(".")[3])))
                uncombinedFile = subsystem + "hists." + fileTime + ".root"
                print(os.path.join(serverParameters.protectedFolder, runList[i], subsystem, uncombinedFile))

                # Write files to the zip file
                zipFile.write(os.path.join(serverParameters.protectedFolder, runList[i], subsystem, combinedFile))
                zipFile.write(os.path.join(serverParameters.protectedFolder, runList[i], subsystem, uncombinedFile))

    # Finish with the zip file
    zipFile.close()

    # Return with a download link
    return redirect(url_for("protected", filename=zipFilename))

###################################################
@app.route("/status")
@login_required
def status():
    """ Returns the status of the OVERWATCH sites """
    if request.method == "POST":
        # Responds to requests from other overwatch servers to display the status of the site
        # TODO: Implement the responses
        pass
    else:
        # Display the status page from the other sites
        ajaxRequest = routing.convertRequestToPythonBool("ajaxRequest")

        statuses = collections.OrderedDict()
        # TODO: Actually query for these values
        statuses["Yale"] = True
        statuses["PDSF"] = False
        statuses["CERN"] = True
        statuses["Last received data"] = "%i minutes ago" % 15

        if ajaxRequest == False:
            return render_template("status.html", statuses = statuses)
        else:
            drawerContent = ""
            mainContent = render_template("statusMainContent.html", statuses = statuses)

            return jsonify(drawerContent = drawerContent, mainContent = mainContent)

if __name__ == "__main__":
    # Support both the WSGI server mode, as well as standalone
    #app.run(host="0.0.0.0")
    if "pdsf" in socket.gethostname():
        print("Starting flup WSGI app")
        WSGIServer(app, bindAddress=("127.0.0.1",8851)).run()
    elif "sgn" in socket.gethostname():
        print("Starting flup WSGI app on sciece gateway")
        WSGIServer(app, bindAddress=("127.0.0.1",8851)).run()
    else:
        print("Starting flask app")
        app.run(host=serverParameters.ipAddress, port=serverParameters.port)
