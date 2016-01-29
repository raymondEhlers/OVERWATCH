""" HLT subsystem specific functions

This currently serves as a catch all for unsorted histograms. No additional QA functions are applied.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University

"""

from processRunsModules import generateHtml

######################################################################################################
######################################################################################################
# Sorting
######################################################################################################
######################################################################################################

###################################################
def sortAndGenerateHtmlForHLTHists(outputHistNames, outputFormatting, subsystem = "HLT"):
    """ Sorts and displays HLT histograms.

    Heavily relies on :func:`~processRunsModules.generateHtml.generateHtmlForHistLinkOnRunPage`
    and :func:`~processRunsModules.generateHtml.generateHtmlForHistOnRunPage`.
    Check out code for specifics on how the pages are formatted and the images are sorted.

    Args:
        outputHistNames (list): List of histograms to add to the page. Typically, these have
            been printed from ROOT files.
        outputFormatting (str): Specially formatted string which contains a generic path to the printed histograms.
            The string contains "%s" to print the filename contained in listOfHists. It also includes the file
            extension. Ex: "img/%s.png"
        subsystem (str): The current subsystem by three letter, all capital name .Here it should always be ``HLT``.
            Default: "HLT"

    Returns:
        str: HTML containing all of the HLT histograms, with proper formatting and links from the top of the page
            to the named images.

    """
    # Generate links to histograms below
    htmlText = ""
    htmlText += "<div class=\"contentDivider\">"
    htmlText += "<h3>" + "HLT Histograms" + "</h3>\n"
    htmlText += generateHtml.generateHtmlForHistLinkOnRunPage(outputHistNames, 0)
    htmlText += "</div>"

    # Plot histograms in same order as anchors
    htmlText += generateHtml.generateHtmlForHistOnRunPage(outputHistNames, outputFormatting, 0)

    return htmlText


######################################################################################################
######################################################################################################
# QA Functions
######################################################################################################
######################################################################################################

# None currently implemented
