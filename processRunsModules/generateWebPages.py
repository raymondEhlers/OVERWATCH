""" Main driver functions to genreate web pages.

Contains functions to create the main run list page, each individual run page,
and each individual run direct ROOT files access page.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University
"""

# General includes
import os
import sys
import time

# Used to load functions from other modules
import inspect
import importlib

# Module includes
import utilities
import generateHtml

# Configuration
from config.processingParams import processingParameters

# Get the current module
# Used to load functions from other moudles and then look them up.
currentModule = sys.modules[__name__]

###################################################
def writeToWebPage(dirPrefix, runDir, subsystem, outputHistNames, outputFormatting, runStartTime, maxTime, minTimeRequested = -1, maxTimeRequested = -1, actualTimeBetween = -1, generateTemplate = False):
    """ Writes the web page for a given run.

    The file is written out as ${subsystem}output.html (ex: EMCoutput.html) at dirPrefix/subsystem.
    (or at the proper template dir structure)

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
            possible merge time. It is set as the limits and a initial value in the form.
        minTimeRequested (Optional[int]): The requested start time of the merge in minutes. Default: -1.
        maxTimeRequested (Optional[int]): The requested end time of the merge in minutes. Default: -1.
        actualTimeBetween (Optional[int]): The lenght of time that was merged together (ie. earliest time - latest time).
            This value must always be less than or equal to maxTimeRequested - minTimeRequested. Default: -1.
        generateTemplate (Optional[bool]): Whether to generate a link for a templated page instead
            of a static page. Default: False.

    Returns:
        None

    """
    # Open the particular file
    f = open(os.path.join(dirPrefix, subsystem + "output.html"), "wb")
    print "Writing page:", os.path.join(dirPrefix, subsystem + "output.html")

    # Contains just the number as an int
    runNumber = int(runDir.replace("Run",""))

    # Create the header of the html page
    if generateTemplate == False:
        # This is fragile, but static files are only a backup, so this should be acceptable.
        relativePath = "../../../.."
        # Change the path if we are doing timeSlices. We must got two directories further
        if actualTimeBetween != -1:
            relativePath = "../../../../../.."

        # This leaves us with an open content container div!
        htmlText = generateHtml.generateHtmlForStaticHeader("Run " + str(runNumber), relativePath, generateHtml.interactiveFormText(runNumber, subsystem, maxTime, minTimeRequested, maxTimeRequested, actualTimeBetween))
    else:
        # Setting up the scrollIfHashExists value here ensures that we scroll to the right part of the page on load.
        htmlText = """{% extends "layout.html" %}
        {% block onLoad %}scrollIfHashExists({{ scrollAmount }});setScrollValueInForm();{% endblock %}
        {% block secondLineInHeader %}"""
        htmlText += generateHtml.interactiveFormText(runNumber, subsystem, maxTime, minTimeRequested, maxTimeRequested, actualTimeBetween)
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
        print "outputFormatting", outputFormatting

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
        htmlText += """<p id="contactLink"><a href="%s/contact">Information, contact, and suggestions</a></p></div></body></html>""" % relativePath
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
        subsystem (str): The current subsystem by three letter, all capital name (ex. ``EMC``).
        generateTemplate (Optional[bool]): Whether to generate a link for a templated page instead
            of a static page. Default: False.

    Returns:
        None

    """
    f = open(os.path.join(dirPrefix, subsystem + "ROOTFiles.html"), "wb")
    #print "Writing page:", os.path.join(dirPrefix, subsystem + "ROOTFiles.html")

    # Well formatted text containing the run
    runText = "Run " + dirName.replace("Run", "")

    # Create the header of the html page
    if generateTemplate == False:
        relativePath = "../../../.."
        htmlText = generateHtml.generateHtmlForStaticHeader(runText, relativePath, None)
    else:
        htmlText = """{% extends "layout.html" %}
        {% block body %}\n"""

    # Setup the page
    htmlText += "<a class=\"anchor\" name=\"topOfPage\"></a>\n"
    htmlText += "<h1>" + runText + " " + subsystem + " ROOT Files</h1>\n"
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
    #print "subsystem:", subsystem
    #print "generateTemplate:", generateTemplate

    # Add all of the files to the web page
    for unixTime in sortedKeys:
        # Show the time in a more readable manner
        timeStruct = time.gmtime(unixTime)
        timeString = time.strftime("%A, %d %b %Y %H:%M:%S", timeStruct)
        
        htmlText += generateHtml.generateHtmlForRootFileAccessPage(filenameTimes[unixTime], timeString)
        #print "filename:", filename
        #print "path:", os.path.join(dirName, subsystem, filename)

    # Close listColumns ul and contentContainer div opened above
    htmlText += "</ul>"
    htmlText += "</div>"

    # Close up html page
    if generateTemplate == False:
        htmlText += """<p id="contactLink"><a href="%s/contact">Information, contact, and suggestions</a></p></div></body></html>""" % relativePath
    else:
        htmlText += "{% endblock %}"

    f.write(htmlText)
    f.close()

###################################################
def writeRootWebPage(writeDirs, subsystemRunDirDict, dirPrefix, subsystemsWithRootFilesToShow, generateTemplate = False):
    """ Write the root web page given a list of the valid directories (ie dirs with images).

    The file is written out as runList.html in dirPrefix
    (or at the proper template dir structure, usually dirPrefix/templates/)

    Args:
        writeDirs (list): List of all runs, with entries in the form of "Run#" (str). 
        subsystemRunDirDict (dict): Contains the name of each valid run for each subsystem. The keys are the three letter subsystem names,
            and there is a list at each key which contains all of the valid runs, with entries of the form "Run#" (str).
        dirPrefix (str): The directory prefix for a given run. It should always contain the value of root path for data for the function.
            For a run, this should be roughly of the form "path"/Run#/subsytem (ex "path"/Run123/EMC)
            where "path" is the path of get to where the data will actually be stored
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
    <a class="anchor" name="topOfPage"></a>
    <h1> OVERWATCH Run List <span style="float:right"><a class="basicQALink" href="/processQA">Basic QA</a></span></h1>\n"""

    htmlText += """<div class="contentDivider">\n"""

    # Write runList with newest runs at top
    writeDirs.sort(reverse=True)
    for dirName in writeDirs:
        # Get the run number for better presentation
        runText = "Run " + dirName.replace("Run", "")
        htmlText += "<p>" + runText

        # We need different padding for the first line and the later lines.
        firstSubsystem = True
        paddingLength = 1

        # Write out the various subsystems
        for subsystem in processingParameters.subsystemList:
            subsystemLabel = subsystem + " Histograms"
            if dirName in subsystemRunDirDict[subsystem]:
                subsystemPath = os.path.join(dirName, subsystem, subsystem + "output.html")

                # Generate the link
                htmlText += generateHtml.generateHtmlForRootWebPage(paddingLength, subsystemPath, subsystemLabel)

                # Change the padding size if we have written out the first subsystem
                if firstSubsystem:
                    # Need wider pading for all further subsysytems
                    paddingLength = 6
                    firstSubsystem = False

                # Write out the ROOT file access page and link to it if selected
                if subsystem in subsystemsWithRootFilesToShow:
                    createPageForRootFileAccess(os.path.join(dirPrefix, dirName, subsystem), dirName, subsystem, generateTemplate)
                    htmlText += generateHtml.generateHtmlForRootWebPage(paddingLength, os.path.join(dirName, subsystem, "%sROOTFiles.html" % subsystem), "%s ROOT Files" % subsystem)

        # Finish the paragraph started with the run number
        htmlText += "</p>\n"

    # Close link container div
    htmlText += "</div>"

    # Close up html page
    if generateTemplate == False:
        htmlText += """<p id="contactLink"><a href="/contact">Information, contact, and suggestions</a></p></div></body></html>"""
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


