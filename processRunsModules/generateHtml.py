""" Generators of HTML for various pages.

Contains all of the functions to generate html for various web pages. Pages include
the main runList, each run page, and the root hists page.

This likely would have been easier to develop using templates, but is this way for
historical reasons. In addition, this allows the creation of entirely static pages,
which would be impossible with templates.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University

"""

###################################################
def generateHtmlForRootWebPage(firstSubsystem, path, label):
    """ Generates HTML for links on the main runList page.

    Used for links to individual runs on the run list page. 

    Args:
        firstSubsystem (bool): True if this is the first subsystem being printed in the table.
            The run number is the first data element in that row, so we should only add one element here.
        path (str): Path (ie URL) of the page to link
        label (str): Label for the link

    Returns:
        str: HTML for the link

    """

    # The spans are for alignment
    htmlText = ""
    if firstSubsystem == False:
        # Need to start a new row
        # The first column should be empty
        htmlText += "<tr><td></td>"

    htmlText += "<td><a href=\"" + path + "\">" + label + "</a></td></tr>\n"
    return htmlText

###################################################
def generateHtmlForRootFileAccessPage(rootFilename, label, generateTemplate = False):
    """ Generates HTML for links on the direct file access page.

    Used for links to ROOT files on the direct file access page. Most commonly used for direct file
    access by the HLT.

    Args:
        rootFilename (str): Path to root file to link
        label (str): Label for the link
        generateTemplate (Optional[bool]): Whether to generate a link for a templated page instead
            of a static page. Default: False.

    Returns:
        str: HTML for the link

    """

    # the "download" tag causes it to download the file instead of trying to view it
    htmlText = "<li><a href=\"%s\" download>%s</a></li>\n" 

    if generateTemplate == True:
        returnFilename = "{{ url_for(\"protected\", filename=%) }}" % rootFileName
    else:
        returnFilename = rootFilename

    #print returnFilename

    return htmlText % (rootFilename, label)

###################################################
def generateHtmlForHistLinkOnRunPage(listOfHists, startOfName):
    """ Generates HTML links for all histograms in a list.

    Used for creating the links at the top of an individual run page. This function is quite similar to
    :func:`~generateHtmlForHistOnRunPage()`.

    Args:
        listOfHists (list): List of histogram filenames. Does not contain the path to the file. That is contained
            in outputFormatting.
        startOfName (int): Position in each filename where the histogram name actually starts. This name will be
            used to set the link anchor and to label the link. Ex: If the hist name is "EMChistName",
            use startOfName = 3 to get "histName".
    
    Returns:
        str: HTML containing links to **all** of the histograms in the list. All of the links go to anchors labeled by the histogram name.

    """

    returnText = ""
    for filename in listOfHists:
        histName = filename[startOfName:]
        returnText += '<a href="#' + histName + '">' + histName + '</a><br>\n'

    return returnText

###################################################
def generateHtmlForHistOnRunPage(listOfHists, outputFormatting, startOfName):
    """ Generates HTML img tags and names for histograms in a list.

    Used for adding images and names to an individual run page. This function is quite similar to
    :func:`~generateHtmlForHistLinkOnRunPage()`.

    Args:
        listOfHists (list): List of histogram filenames. Does not contain the path to the file. That is contained
            in outputFormatting.
        outputFormatting (str): Specially formatted string which contains a generic path to the printed histograms.
            The string contains "%s" to print the filename contained in listOfHists. It also includes the file
            extension. Ex: "img/%s.png"
        startOfName (int): Position in each filename where the histogram name actually starts. This name will be
            used to set the link anchor and to label the link. Ex: If the hist name is "EMChistName",
            use startOfName = 3 to get "histName".
    
    Returns:
        str: HTML containing names and image tags of **all** of the histograms in the list. Anchors are also included so that each image can be linked to individually.

    """

    returnText = ""
    for filename in listOfHists:
        outputFilename = outputFormatting % filename
        histName = filename[startOfName:]
        returnText += "<a class=\"anchor\" name=\"" + histName + "\"></a>\n"
        returnText += "<h2>" + histName + "</h2>\n"
        returnText += "<img src=\"" + outputFilename + "\" alt=\"" + outputFilename + "\">\n"

    return returnText

###################################################
class sortingGroup(object):
    """ Class to handle sorting of objects.

    This class can select a group of histograms and store their names in a list. It also stores a more
    readable version of the group name, as well as whether the histograms should be plotted in a grid.

    Args:
        groupName (str): Readable name of the group.
        groupSelectionPattern (str): Pattern of the histogram names that will be selected. For example, if
            wanted to select histograms related to EMCal patch amplitude, we would make the pattern something
            like "PatchAmp". The name depends on the name of the histogram sent from the HLT.
        plotInGridSelectionPattern (str): Pattern which denotes whether the histograms should be plotted in
            a grid. ``plotInGrid`` is set based on whether this value is in ``groupSelectionPattern``. For
            example, in the EMCal, the ``plotInGridSelectionPattern`` is "_SM". 

    Available attributes include:

    Attributes:
        name (str): Readable name of the group. Set via the ``groupName`` in the constructor.
        selectionPattern (str): Pattern of the histogram names that will be selected.
        plotInGridSelectionPattern (str): Pattern which denotes whether the histograms should be plotted in
            a grid.
        plotInGrid (bool): True when the histograms should be plotted in a grid.
        histList (list): List of the histograms that should be filled when the ``selectionPattern`` is matched.
    
    """

    def __init__(self, groupName, groupSelectionPattern, plotInGridSelectionPattern = "DO NOT PLOT IN GRID"):
        """ Initializes the sorting group """
        self.name = groupName
        self.selectionPattern = groupSelectionPattern
        self.plotInGridSelectionPattern = plotInGridSelectionPattern
        self.histList = []

        # So that it is not necessary to check the list every time
        if self.plotInGridSelectionPattern in self.selectionPattern:
            self.plotInGrid = True
        else:
            self.plotInGrid = False

###################################################
def generateHtmlForPlotInGridLinks(groupName):
    """ Generate a link to the grid for a given group name.

    Args:
        groupName (str): Name of the group that will be plotted in the grid.

    Returns:
        str: HTML containing a link the group.

    """
    returnText = '<a href="#' + groupName.replace(" ","") + '">' + groupName + '</a><br>\n'

    return returnText

###################################################
def generateHtmlForPlotInGrid(listOfHists, groupName, outputFormatting, nColumns):
    """ Generates a html table for a group of histograms

    Args:
        listOfHists (list): List of histogram filenames. Does not contain the path to the file. That is contained
            in outputFormatting.
        groupName (str): Name of the group of hists that are being plotted in the grid.
        outputFormatting (str): Specially formatted string which contains a generic path to the printed histograms.
            The string contains "%s" to print the filename contained in listOfHists. It also includes the file
            extension. Ex: "img/%s.png"

    Returns:
        str: HTML containing names and image tags of **all** of the histograms in the list. An anchor is also included so that the grid can be linked.
    
    """

    # Needed to count our position in the table
    maxImageWidth = 100/nColumns
    # Give a 4% margin (1% on left and right -> 2% between the images)
    maxImageWidth = maxImageWidth - maxImageWidth*.04

    # Label
    returnText = "<a class=\"anchor\" name=\"" + groupName.replace(" ","") + "\"></a>\n"
    returnText += "<h2>%s</h2>\n" % groupName

    # Start container div
    returnText += "<div class=\"gridContainer\">\n"
    # Loop over hists
    for filename in listOfHists:
        # Add image
        outputFilename = outputFormatting % filename
        # Setting the image width is important so that it fills all available space!
        returnText += """<div style="width: %f%%" class="gridImageContainer">
            <img src="%s" alt="%s">
        </div>
        """ % (maxImageWidth, outputFilename, outputFilename)

    # Close container div
    returnText += "</div>\n"

    return returnText

###################################################
def interactiveFormText(partialMergeActionUrl, runNumber, subsystem, maxTime, minTimeRequested = -1, maxTimeRequested = -1, actualTimeBetween = -1):
    """ Generates the form that provides time dependent merge capabilities.

    Used to create the time dependent merge header. The function generates a complicated HTML form,
    with the initial values set properly based on the arguments passed to the function. 

    Note:
        This form will generate a POST request. Consequently, this form requires at least a WSGI web server
        to function properly. Thus, this form is fairly useless on totally static pages, but this form will
        be shown because we cannot know at the time of this function whether the page will be dynamic or static.
        If the pages are dynamic, but backed with a low load WSGI server (i.e. no templates available), this form
        will still operate properly.
    
    Notes:
        ``actualTimeBetween`` can be less than ``maxTimeRequested - minTimeRequested`` if there is not enough
        data to satisfy the precise times requested.

        ``minTimeRequested``, ``maxTimeRequested``, and ``actualTimeBetween`` will only be displayed on the
        web page if all values are set. They should always be set in pairs. If they are all set, an additional
        line with timing information will be written to the header.

    Args:
        partialMergeActionUrl (str): The URL to put into the action field in the HTML form. In the case of static
            pages, this is just the direct URL with the proper relative path. In the case of dynamic pages, it is
            simply the ``url_for()`` for the partial merge.
        runNumber (int): The current run number.
        subsystem (str): The current subsystem by three letter, all capital name (ex. ``EMC``).
        maxTime (int): The length of the run in minutes from the start of the run. This is the maximum
            possible merge time. It is set as the limits and a initial value in the form.
        minTimeRequested (Optional[int]): The requested start time of the merge in minutes. Default: -1.
        maxTimeRequested (Optional[int]): The requested end time of the merge in minutes. Default: -1.
        actualTimeBetween (Optional[int]): The length of time that was merged together (i.e. earliest time - latest time).
            This value must always be less than or equal to maxTimeRequested - minTimeRequested. Default: -1.

    Returns:
        str: HTML containing the form, with proper values already set.

    """

    interactiveForm = """<form class="timeDependentMergeControls" id="timeDependentMergeControls" action="%s" method="post">
    <input type="hidden" name="runNumber" value="%i"/>
    <input type="hidden" name="subsystem" value="%s"/>
    <input type="hidden" name="scrollAmount" id="scrollAmount" value=0 />
    <div class="mergeControlsContainer">Min Time: <input name="minTime" id="minTimeID" type="range" min="0" max="%f" value="0" oninput="minTimeOutputId.value= minTimeID.value"/>
    <output name="minTimeOutput" id="minTimeOutputId">0</output></div>
    <div class="mergeControlsContainer">Max Time: <input name="maxTime" id="maxTimeID" type="range" min="0" max="%f" value="%f" oninput="maxTimeOutputId.value= maxTimeID.value"/>
    <output name="maxTimeOutput" id="maxTimeOutputId">%.0f</output></div>
    <div class="mergeControlsContainer">(minutes)
    <input value="Time Dependent Merge" class="submitButton" type="submit" /></div>
    </form>\n"""
    #print "minTimeRequested", minTimeRequested, "maxTimeRequested", maxTimeRequested, "actualTimeBetween", actualTimeBetween

    # Only include this if the request actually restricted the time. If all of these values are greater than -1
    # then it means we have a time slice request, and this line should be included
    if minTimeRequested > -1 and maxTimeRequested > -1 and actualTimeBetween > -1:
        interactiveForm += "<p class=\"responsiveHeaderParagraph timeSliceResults\">Requested data between %i and %i minutes. Actual time due to data constraints is <strong>%i minutes</strong></p>\n" % (minTimeRequested, maxTimeRequested, actualTimeBetween)

    return interactiveForm % (partialMergeActionUrl, runNumber, subsystem, maxTime, maxTime, maxTime, maxTime)

###################################################
def generateHtmlForStaticHeader(runNumberString, relativePath, secondDivText):
    """ Generates the HTML header and beginning of body for a static page.

    Such a header is already in the layout template, and thus is not necessary for a templated page.

    Warning:
        The return text includes an open div tag, ``<div class="contentContainer"``.
        It is the users responsbility to close it!

    Args:
        runNumberString (str): The run number as a well formatted string. Ex: "Run 123456"
        relativePath (str): The relative path to the static directory. This will depend on the setup of
            the server or directory stucture. The static directory should contain the ``shared.js`` javascript
            file, as well as the ``style.css`` css style file.
        secondDivText (str): String containing HTML to go into the second line of the header.
            This is often used in conjunction with :func:`interactiveFormText()`.
        
    Returns:
        str: HTML for the header tag and the beginning of the body. The returned string covers all setup of a page, such that content can be added directly after this string.

    """

    # The staticBody css class is in case extra selectors are needed. See the commented css

    # The "Return to Run List" link intentionally goes back to pages served by /monitoring.
    #  If on totally static pages, then the back and forward buttons work just fine.
    #  Otherwise, if the user unintentionally ends on up static pages served by a server,
    #  but outside the normal routing structure, then we want them redirected back to the normal
    #  routing stucture to ensure normal and proper operation.

    # In summary, this choice only affects totally static users, but ensures better operation for
    #  any users with a server, so we find it to be a worthwhile tradeoff.
    htmlText = """<html>
    <head>
        <title>%s</title>
        <script src="%s/static/shared.js" type="text/javascript"></script>
        <link rel="stylesheet" type="text/css" href="%s/static/style.css">
    </head>
    <body onload="scrollIfHashExists();setScrollValueInForm()" class="staticBody">
        <div class="header">
            <div id="firstLineOfHeader">
                <p class="responsiveHeaderParagraph">
                    <span style="padding-left:5px;"></span>
                    <a href="%s/monitoring">Return to Run List</a>
                    <span style="padding-left:1em;padding-right:1em;">-</span>
                    <a href="#topOfPage">Top of Page</a>
                    <span style="float:right;padding-right:5px;">
                        <a href="%s/logout">Logout</a>
                    </span>
                </p>
            </div>
            <div id="timeDependentMergeContainer">
                <div id="timeDependentMergeDiv">
                    %s
                </div>
            </div>
        </div>
        <div id="contentContainer">\n"""

    # If we have not passed a div, this just set it to empty. It will collapse and not be shown
    # on the web page.
    if secondDivText == None:
        secondDivText = ""
    return htmlText % (runNumberString, relativePath, relativePath, relativePath, relativePath, secondDivText)

