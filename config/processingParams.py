## Holds all of the processing parameters

# General
import os

# Config
from sharedParams import sharedParameters

class processingParameters:
    """ Contains the parameters used to configure the server.

    Draws a number of settings from :class:`~config.sharedParams.sharedParameters`.
    """

    #: The file extension to use when printing ROOT files.
    fileExtension = ".png"

    #: Print additional messages while processing
    beVerbose = True

    #: Enable debugging information
    debug = sharedParameters.debug

    #: Force each run to be reprinted and regenerate the pages
    forceReprocessing = False

    #: Force each run to be remerged.
    #: Note that this can change the merging if new information has arrived since the last merge.
    forceNewMerge = False

    #: Transfer data to PDSF
    sendData = True

    #: Set the type of merging based on the data we are receiving. If set to true, that means we are receiving
    #: cumulative files (ie. the hists are not reset after they are sent by the HLT). In that case,
    #: to do a partial merge we take the last run file and subtract it from the first. 
    cumulativeMode = True

    #: The name of the template folder.
    templateFolderName = sharedParameters.templateFolderName

    #: The name of the folder inside the template folder that contains the run dir structure to hold templates.
    #: To turn off templates, set it to None
    templateDataDirName = os.path.join(sharedParameters.templateFolderName, sharedParameters.dataFolderName)

    #: Specifies the prefix necessary to get to all of the folders
    #: Don't include a trailing slash! (This may be mitigated by os.path calls, but not worth the
    #: risk in changing it).
    dirPrefix = sharedParameters.dataFolderName

    #: The name of the folder containing the modules for processRuns.
    modulesPath  = "processRunsModules"

    #: The name of the folder inside the modules folder containing the detector files.
    detectorsPath = "detectors"

    #: List of subsystems.
    #: Each subsystem listed here will have an individual page for their respective histograms.
    subsystemList = sharedParameters.subsystemList

    #: Each of these subsystems will also get an individual page for access to their respective ROOT files.
    subsystemsWithRootFilesToShow = sharedParameters.subsystemsWithRootFilesToShow

    #: Define which functions are accessible from the QA page
    qaFunctionsList = sharedParameters.qaFunctionsList

    qaFunctionsToAlwaysApply = sharedParameters.qaFunctionsToAlwaysApply
    """ Automated QA functions that are always applied when processing

    See Also: 
        :attr:`config.sharedParams.sharedParameters.qaFunctionsToAlwaysApply`

    """

    #: Username at PDSF for sending data
    pdsfUsername = ""

    # Determine proper pdsf username
    _localUser = os.getenv("USER")
    if _localUser == "re239" or _localUser == "rehlers":
        pdsfUsername = "rehlers"
    else:
        pdsfUsername = "jdmull"

    # Set variables for testing
    if True:
        forceReprocessing = True
        sendData = False
        
    ###################################################
    @classmethod
    def defineRunProperties(cls):
        """ Useful function to return all of the parameters in a compact way """
        return (cls.fileExtension, cls.beVerbose, cls.forceReprocessing, cls.forceNewMerge, cls.sendData, cls.pdsfUsername, cls.cumulativeMode, cls.templateDataDirName, cls.dirPrefix, cls.subsystemList, cls.subsystemsWithRootFilesToShow)

# Print settings
print "\nProcessing Parameters:"
print "fileExtension:", processingParameters.fileExtension
print "beVerbose:", processingParameters.beVerbose
print "debug:", processingParameters.debug
print "forceReprocessing:", processingParameters.forceReprocessing
print "forceNewMerge:", processingParameters.forceNewMerge
print "sendData:", processingParameters.sendData
print "pdsfUsername:", processingParameters.pdsfUsername
print "cumulativeMode:", processingParameters.cumulativeMode
print "templateDataDirName:", processingParameters.templateDataDirName
print "dirPrefix:", processingParameters.dirPrefix
print "modulesPath:", processingParameters.modulesPath
print "detectorsPath:", processingParameters.detectorsPath
print "subsystemList:", processingParameters.subsystemList
print "subsystemsWithRootFilesToShow:", processingParameters.subsystemsWithRootFilesToShow
print "qaFunctionsToAlwaysApply:", processingParameters.qaFunctionsToAlwaysApply
