## Holds all of the processing parameters

# Python 2/3 support
from __future__ import print_function

# General
import os
import logging
# Setup logger
logger = logging.getLogger(__name__)

# Config
from .sharedParams import sharedParameters

class processingParameters(object):
    """ Contains the parameters used to configure the server.

    Draws a number of settings from :class:`~config.sharedParams.sharedParameters`.
    """

    #: The file extension to use when printing ROOT files.
    fileExtension = sharedParameters.fileExtension

    #: Enable debugging information.
    debug = sharedParameters.debug

    #: Print additional messages while processing.
    beVerbose = True

    #: Set the logging level
    loggingLevel = logging.INFO

    #: Force each run to be reprinted and regenerate the pages.
    forceReprocessing = False

    #: Force each run to be remerged.
    #: Note that this can change the merging if new information has arrived since the last merge.
    forceNewMerge = False

    #: Transfer data to the remote system.
    sendData = True

    #: Set the type of merging based on the data we are receiving. If set to true, that means we are receiving
    #: cumulative files (i.e. the hists are not reset after they are sent by the HLT). In that case,
    #: to do a partial merge we take the last run file and subtract it from the first. 
    cumulativeMode = True

    #: The name of the template folder.
    templateFolderName = sharedParameters.templateFolderName

    #: The name of the folder inside the template folder that contains the run dir structure to hold templates.
    #: To turn off templates, set it to None.
    templateDataDirName = os.path.join(sharedParameters.templateFolderName, sharedParameters.dataFolderName)

    #: The path to the database.
    databaseLocation = sharedParameters.databaseLocation

    #: Specifies the prefix necessary to get to all of the folders.
    #: Don't include a trailing slash! (This may be mitigated by os.path calls, but not worth the
    #: risk in changing it).
    dirPrefix = sharedParameters.dataFolderName

    #: The name of the folder containing the modules for processRuns.
    modulesPath  = "processRuns"

    #: The name of the folder inside the modules folder containing the detector files.
    detectorsPath = "detectors"

    #: List of subsystems.
    #: Each subsystem listed here will have an individual page for their respective histograms.
    subsystemList = sharedParameters.subsystemList

    #: Each of these subsystems will also get an individual page for access to their respective ROOT files.
    subsystemsWithRootFilesToShow = sharedParameters.subsystemsWithRootFilesToShow

    #: Define which functions are accessible from the QA page.
    qaFunctionsList = sharedParameters.qaFunctionsList

    qaFunctionsToAlwaysApply = sharedParameters.qaFunctionsToAlwaysApply
    """ Automated QA functions that are always applied when processing.

    See Also: 
        :attr:`config.sharedParams.sharedParameters.qaFunctionsToAlwaysApply`

    """

    #: Username at remote system for sending data.
    remoteUsername = ""

    # Determine proper remote username.
    _localUser = os.getenv("USER")
    if _localUser == "re239" or _localUser == "rehlers" or _localUser == "emcal":
        remoteUsername = "rehlers"
    else:
        remoteUsername = "jdmull"

    #: Remote system hostnames.
    #: The number of entries in remoteSystems must match remoteFileLocations!
    remoteSystems = ["aliceoverwatch.physics.yale.edu", "pdsf.nersc.gov"]

    #: Remote locations where to store the data files.
    #: The number of entries in each dict label must match remoteSystems!
    remoteFileLocations = {"data" : ["/opt/www/aliceoverwatch/data/", "/project/projectdirs/alice/www/emcalMonitoring/data/2015/"], "templates" : ["/opt/www/aliceoverwatch/templates/data/", "/project/projectdirs/alice/aliprodweb/overwatch/templates/data/"]}

    # Set variables for testing
    if True:
        forceReprocessing = True
        sendData = False

    # Lower the min logging level if we want to be verbose
    if beVerbose:
        loggingLevel = logging.DEBUG

    # Print methods
    @classmethod
    def __repr__(cls):
        return cls.__str__()

    @classmethod
    def printSettings(cls):
        return cls.__str__()

    @classmethod
    def __str__(cls):
        returnValue = "Processing Parameters configuration:\n"
        members = [var for var in vars(cls)]
        for member in members:
            # Filter out elements with "_" in name and the printSettings function
            if "_" not in member and "printSettings" not in member:
                returnValue += "{0}: {1}\n".format(member, getattr(cls, member))

        return returnValue



