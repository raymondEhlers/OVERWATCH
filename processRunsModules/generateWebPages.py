""" Main driver functions to generate web pages.

Contains functions to create the main run list page, each individual run page,
and each individual run direct ROOT files access page.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University
"""

# Python 2/3 support
from __future__ import print_function

# General includes
import os
import sys
import time

# Used to load functions from other modules
import inspect
import importlib

# Module includes
from . import utilities
from . import generateHtml

# Configuration
from config.processingParams import processingParameters

# Get the current module
# Used to load functions from other moudles and then look them up.
currentModule = sys.modules[__name__]

###################################################
def writeToWebPage(dirPrefix, runDir, subsystem, outputHistNames, outputFormatting, runStartTime, maxTime, minTimeRequested = -1, maxTimeRequested = -1, actualTimeBetween = -1, generateTemplate = False):
    """ Writes the web page for a given run.

    The file is written out as ${subsystem}output.html (ex: EMCoutput.html) at dirPrefix/subsystem
    (or at the proper template dir structure).

    Args:
        dirPrefix (str): The directory prefix for a given run. It should always contain the value of root path for data for the function.
            For a run, this should be roughly of the form "path"/Run#/subsytem (ex "path"/Run123/EMC)
            where "path" is the path of get to where the data will actually be stored
        runDir (str): String of the form "Run#". Ex: "Run123"
        subsystem (str): The current subsystem by three letter, all capital name (ex. ``EMC``).
        outputHistNames (list): List of histograms to add to the page. Typically, these have
            been printed from ROOT files.
        outputFormatting (str): Specially formatted string which contains a generic path to the printed histograms.
            The string contains "%s" to print the filename contained in listOfHists. It also includes the file
            extension. Ex: "img/%s.png"
        runStartTime (int): Start time of the run in unix time.
        maxTime (int): The length of the run in minutes from the start of the run. This is the maximum
            possible merge time. It is set as the limit and an initial value in the form.
        minTimeRequested (Optional[int]): The requested start time of the merge in minutes. Default: -1.
        maxTimeRequested (Optional[int]): The requested end time of the merge in minutes. Default: -1.
        actualTimeBetween (Optional[int]): The length of time that was merged together (ie. earliest time - latest time).
            This value must always be less than or equal to maxTimeRequested - minTimeRequested. Default: -1.
        generateTemplate (Optional[bool]): Whether to generate a link for a templated page instead
            of a static page. Default: False.

    Returns:
        None

    """
    # Open the particular file
    f = open(os.path.join(dirPrefix, subsystem + "output.html"), "wb")
    print("Writing page:", os.path.join(dirPrefix, subsystem + "output.html"))

    # Contains just the number as an int
    runNumber = int(runDir.replace("Run",""))

    # Create the header of the html page
    if generateTemplate == False:
        # This is fragile, but static files are only a backup, so this should be acceptable.
        relativePath = "../../../.."
        # Change the path if we are doing timeSlices. We must got two directories further
        if actualTimeBetween != -1:
            relativePath = "../../../../../.."

        partialMergeActionUrl = "%s/partialMerge" % relativePath

        # This leaves us with an open content container div!
        htmlText = generateHtml.generateHtmlForStaticHeader("Run " + str(runNumber), relativePath, generateHtml.interactiveFormText(partialMergeActionUrl, runNumber, subsystem, maxTime, minTimeRequested, maxTimeRequested, actualTimeBetween))
    else:
        # Set the url that should be request for a partial merge.
        partialMergeActionUrl = "{{ url_for(\"partialMerge\") }}"

        # Setting up the scrollIfHashExists value here ensures that we scroll to the right part of the page on load.
        htmlText = """{% extends "layout.html" %}
        {% block onLoad %}scrollIfHashExists({{ scrollAmount }});setScrollValueInForm();{% endblock %}
        {% block secondLineInHeader %}"""
        htmlText += generateHtml.interactiveFormText(partialMergeActionUrl, runNumber, subsystem, maxTime, minTimeRequested, maxTimeRequested, actualTimeBetween)
        htmlText +="""{% endblock %}
        {% block body %}\n"""

        # Setup outputFormatting to set the image path correctly
        # Hardcoded "Run" here. However, it should almost certainly be constant. In fact, many other things will break before
        # this line if it's changed.
        # Cannot just blindly use something like dirPrefix because the images are not located in the same dir as the templates.
        # We need to remove since actual images are at Run.../SUBSYSTEM/... , not dirPrefix/templates/data/Run..
        #print "outputFormatting", outputFormatting
        #print "dirPrefix", dirPrefix
        outputFormatting = """{{ url_for("protected", filename="%s") }}""" % os.path.join(dirPrefix[dirPrefix.find("Run"):], outputFormatting)
        print("outputFormatting", outputFormatting)

    # Setup at top of page.
    htmlText += "<a class=\"anchor\" name=\"topOfPage\"></a>\n"
    htmlText += "<h1>Run " + str(runNumber) + "</h1>\n"

    # Fill in logbook and run start time.
    runStartTimeStruct = time.gmtime(runStartTime)
    runStartTimeString = time.strftime("%A, %d %b %Y %H:%M:%S", runStartTimeStruct)
    logbookLink = "https://alice-logbook.cern.ch/logbook/date_online.php?p_cont=rund&p_run=%s" % str(runNumber)
    htmlText += "<p>Run %s started at %s (CERN time zone).</br>\n<a target=\"_blank\" href=\"%s\">Logbook entry</a></p>\n" % (str(runNumber), runStartTimeString, logbookLink)

    # Call the sort and generate function for the proper subsystem. See the docs in that submodules for details on the function.
    htmlText += getattr(currentModule, "sortAndGenerateHtmlFor%sHists" % subsystem)(outputHistNames, outputFormatting, subsystem)
       
    # Close up html page
    if generateTemplate == False:
        htmlText += """<div class="contactLinkContainer"><p class="contactLinkParagraph"><a href="%s/contact">Information, documentation, contact, and suggestions</a></p></div></div></body></html>""" % relativePath
    else:
        htmlText += "{% endblock %}"

    f.write(htmlText)
    f.close()

###################################################
def createPageForRootFileAccess(dirPrefix, dirName, subsystem, generateTemplate = False):
    """ Generates the web page to access the raw ROOT files for a given subsystem.

    Lists links to all of the ROOT files ordered by time. The links are presented in two columns.
    The file is written out as ${subsystem}ROOTFiles.html (ex: EMCoutput.html) in dirPrefix/subsystem
    (or at the proper template dir structure, usually dirPrefix/templates/subsystem)

    Args:
        dirPrefix (str): The directory prefix for a given run. It should always contain the value of root path for data for the function.
            For a run, this should be roughly of the form "path"/Run#/subsytem (ex "path"/Run123/EMC)
            where "path" is the path of get to where the data will actually be stored
        dirName (str): String of the form "Run#". Ex: "Run123"
        subsystem (:class:`~subsystemProperties`): Contains information about the current subsystem.
        generateTemplate (Optional[bool]): Whether to generate a link for a templated page instead
            of a static page. Default: False.

    Returns:
        None

    """
    # Make sure that the dir exists before trying to create the file
    if not os.path.exists(os.path.join(dirPrefix, subsystem.fileLocationSubsystem)):
        os.makedirs(os.path.join(dirPrefix, subsystem.fileLocationSubsystem))

    # Create file
    f = open(os.path.join(dirPrefix, subsystem.subsystem + "ROOTFiles.html"), "wb")
    #print "Writing page:", os.path.join(dirPrefix, subsystem.subsystem + "ROOTFiles.html")

    # Well formatted text containing the run
    runText = "Run " + dirName.replace("Run", "")

    # Create the header of the html page
    if generateTemplate == False:
        relativePath = "../../../.."
        htmlText = generateHtml.generateHtmlForStaticHeader(runText, relativePath, None)
    else:
        htmlText = """{% extends "layout.html" %}
        {% block body %}\n"""

    # Make a note if the subsystem does not have it's own data
    additionalFileLocationInformation = ""
    if subsystem.subsystem != subsystem.fileLocationSubsystem:
        additionalFileLocationInformation = " (stored in %s files)" % subsystem.fileLocationSubsystem

    # Setup the page
    htmlText += "<a class=\"anchor\" name=\"topOfPage\"></a>\n"
    htmlText += "<h1>" + runText + " " + subsystem.subsystem + " ROOT Files%s</h1>\n" % additionalFileLocationInformation
    htmlText += "<p>All times recorded in the CERN time zone.</p>"
    htmlText += """<div class="contentDivider">\n"""
    htmlText += "<ul class=\"listColumns\">\n"

    # Need to remove "templates" from the path, since the data is not stored with the templates
    if not processingParameters.templateFolderName.endswith("/"):
        replaceValue = processingParameters.templateFolderName + "/"
    else:
        replaceValue = processingParameters.templateFolderName

    runDir = dirPrefix.replace(replaceValue, "")

    # Find all of the files that we want to display
    uncombinedFiles = [name for name in os.listdir(runDir) if "combined" not in name and ".root" in name ]

    # Sort by unix time
    filenameTimes = {}
    for filename in uncombinedFiles:
        filenameTimes[utilities.extractTimeStampFromFilename(filename)] = filename

    # Sort the unixtime keys so that they are ordered
    sortedKeys = sorted(filenameTimes.keys())

    #print "dirPrefix:", dirPrefix
    #print "dirName:", dirName
    #print "subsystem.subsystem:", subsystem.subsystem
    #print "generateTemplate:", generateTemplate

    # Add all of the files to the web page
    for unixTime in sortedKeys:
        # Show the time in a more readable manner
        timeStruct = time.gmtime(unixTime)
        timeString = time.strftime("%A, %d %b %Y %H:%M:%S", timeStruct)
        
        htmlText += generateHtml.generateHtmlForRootFileAccessPage(filenameTimes[unixTime], timeString)
        #print "filename:", filename
        #print "path:", os.path.join(dirName, subsystem.fileLocationSubsystem, filename)

    # Add the combined file
    combinedFile = next((name for name in os.listdir(runDir) if "combined" in name and ".root" in name), None)
    if combinedFile:
        # TODO: Make this more robust!
        # Get number of files
        numberOfFiles = int(combinedFile.split(".")[2])
        # Get time
        combinedFileTime = int(combinedFile.split(".")[3])
        timeStruct = time.gmtime(combinedFileTime)
        timeString = time.strftime("%A, %d %b %Y %H:%M:%S", timeStruct)
        linkLabel = "Combined File created from {0} file(s) at {1}".format(numberOfFiles, timeString)

        htmlText += generateHtml.generateHtmlForRootFileAccessPage(combinedFile, linkLabel)

    # Close listColumns ul and contentContainer div opened above
    htmlText += "</ul>"
    htmlText += "</div>"

    # Close up html page
    if generateTemplate == False:
        htmlText += """<div id="contactLink"><p><a href="%s/contact">Information, documentation, contact, and suggestions</a></p></div></div></body></html>""" % relativePath
    else:
        htmlText += "{% endblock %}"

    f.write(htmlText)
    f.close()

###################################################
def writeRootWebPage(dirPrefix, subsystems, generateTemplate = False):
    """ Write the root web page given a list of the valid directories (ie dirs with images).

    The file is written out as runList.html in dirPrefix
    (or at the proper template dir structure, usually dirPrefix/templates/)

    Args:
        dirPrefix (str): The directory prefix for a given run. It should always contain the value of root path
            for data for the function.
            For a run, this should be roughly of the form "path"/Run#/subsytem (ex "path"/Run123/EMC)
            where "path" is the path of get to where the data will actually be stored
        subsystems (list): List of subsystemProperties that conatining all of the subsystems to write to the page.
        generateTemplate (Optional[bool]): Whether to generate a link for a templated page instead
            of a static page. Default: False.

    Returns:
        None

    """
    # Open file
    f = open(os.path.join(dirPrefix, "runList.html"), "wb")

    # Create header
    if generateTemplate == False:
        relativePath = "../.."
        htmlText = generateHtml.generateHtmlForStaticHeader("Run List", relativePath, None)
    else:
        htmlText = """{% extends "layout.html" %}
        {% block body %}\n"""

    # Text at the top of the page. Includes a link to the QA.
    htmlText += """
    <a class="anchor" name="topOfPage"></a>"""

    # Handle the processQA link in the title
    titleLine = """<h1><div style="float: left;">OVERWATCH Run List</div><div style="float: right;"><a class="basicQALink" href="%s">Basic QA</a></div></h1>\n"""
    if generateTemplate == False:
        additionalText = "%s/processQA"
        additionalText = additionalText % relativePath
        htmlText += titleLine % additionalText
    else:
        htmlText += titleLine % "{{ url_for(\"processQA\") }}"

    # Start the container div
    htmlText += """<div class="contentDivider">\n"""

    # Determine all possible write dirs so that we can loop through them below
    # By looping through all writeDirs, we are able to write all of the subsystems links for a given run
    # inside of one paragraph
    writeDirs = []
    for subsystem in subsystems:
        for runDir in subsystem.runDirs:
            if runDir not in writeDirs:
                writeDirs.append(runDir)

    # Write runList with newest runs at top
    writeDirs.sort(reverse=True)
    for dirName in writeDirs:
        # Get the run number for better presentation
        runText = "Run " + dirName.replace("Run", "")
        htmlText += "<table class=\"rootPageRunListTable\">\n<tr><td>" + runText + "</td>"

        # We need different table entries for the first line and the later lines.
        firstSubsystem = True

        # Write out the various subsystems
        for subsystem in subsystems:
            subsystemLabel = subsystem.subsystem + " Histograms"
            if dirName in subsystem.runDirs:
                subsystemPath = os.path.join(dirName, subsystem.fileLocationSubsystem, subsystem.subsystem + "output.html")

                # Generate the link
                htmlText += generateHtml.generateHtmlForRootWebPage(firstSubsystem, subsystemPath, subsystemLabel)

                # The first column should be empty if we have written out the first subsystem
                if firstSubsystem:
                    firstSubsystem = False

                # Write out the ROOT file access page and link to it if selected
                if subsystem.showRootFiles == True:
                    createPageForRootFileAccess(os.path.join(dirPrefix, dirName, subsystem.fileLocationSubsystem), dirName, subsystem, generateTemplate)
                    htmlText += generateHtml.generateHtmlForRootWebPage(firstSubsystem, os.path.join(dirName, subsystem.fileLocationSubsystem, "%sROOTFiles.html" % subsystem.subsystem), "%s ROOT Files" % subsystem.subsystem)

        # Finish the table for this run number
        htmlText += "</table>\n"

    # Close link container div
    htmlText += "</div>"

    # Close up html page
    if generateTemplate == False:
        htmlText += """<div id="contactLink"><p><a href="%s/contact">Information, documentation, contact, and suggestions</a></p></div></div></body></html>""" % relativePath
    else:
        htmlText += "{% endblock %}"

    f.write(htmlText)
    f.close()

###################################################
# Load detector sorting functions from detector specific modules
###################################################
# functions are of the form:
# sortAndGenerateHtmlFor$(subsystem)Hists
#
# For more details on how this is possible, see: https://stackoverflow.com/a/3664396

#print dir(currentModule)
detectorsPath = processingParameters.detectorsPath
modulesPath = processingParameters.modulesPath
for subsystem in processingParameters.subsystemList:
    #print "subsystem", subsystem
    funcName = "sortAndGenerateHtmlFor%sHists" % subsystem

    # Ensure that the module exists before trying to load it
    if os.path.exists(os.path.join(modulesPath, detectorsPath, "%s.py" % subsystem)):
        # Import module dynamically
        subsystemModule = importlib.import_module("%s.%s.%s" % (modulesPath, detectorsPath, subsystem))

        # Get functions from other module
        func = getattr(subsystemModule, funcName)

        # Add the function to the current module
        setattr(currentModule, funcName, func)


