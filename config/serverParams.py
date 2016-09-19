# Holds all of the server parameters

# Python 2/3 support
from __future__ import print_function

# General
import socket
import os
import logging
# Setup logger
logger = logging.getLogger(__name__)

# Bcrypt
from flask_bcrypt import generate_password_hash

# Config
from .sharedParams import sharedParameters

class serverParameters(object):
    """ Contains the parameters used to configure the server.

    Draws a number of settings from :class:`~config.sharedParams.sharedParameters`.

    The stub must be copied, renamed, and filled out with the sensitive information. These sensitive
    attributes include ``_users`` and ``_secretKey``, which are not included in the HTML docs and must
    be viewed in the source file.

    Note: 
        The folder structure for flask can get complicated. See the variables below for their
        purposes. One can generally set staticFolder without staticURLPath, but not the reverse.
        For more information of flask folder structure,
        see (for example): https://stackoverflow.com/a/18746493

    """
    #: Sets the ip address.
    ipAddress = "127.0.0.1"

    #: Sets the port.
    port = 8850

    #: Setup Bcrypt.
    bcryptLogRounds = 12

    #: Default user name. An empty string will disable it. Should only be used when behind CERN SSO!
    defaultUsername = ""
    #defaultUsername = "user"

    #: basePath is just a useful value.
    #: It defines a base directory to reference if the static, template, etc folders are
    #: all in the same dir.
    basePath = ""

    #: staticFolder is the disk location of the static folder.
    #: It is a flask defined variable.
    #: To check if the static files are from the front-end webserver, use:
    #: https://stackoverflow.com/questions/16595691/static-files-with-flask-in-production
    #:
    #: (ie. add + "CHANGE" to the staticFolder location specified here).
    staticFolder = os.path.join(sharedParameters.staticFolderName) 

    #: staticURLPath is the URL of the static folder.
    #: If you want to access "foo", it would be at $BASE_URL/staticURLPath/foo. "" is just the root.
    #: It is a flask defined variable.
    staticURLPath = "/static"

    #: protectedFolder is the disk location of the protected folder.
    #: This folder holds the experimental data.
    protectedFolder = os.path.join(sharedParameters.dataFolderName)

    #: templateFolder is the disk location of the template folder.
    templateFolder = os.path.join(sharedParameters.templateFolderName)

    #: The path to the database.
    databaseLocation = sharedParameters.databaseLocation

    #: The file extension to use when printing ROOT files.
    fileExtension = sharedParameters.fileExtension

    #: docsFolder is the disk location of the docs folder.
    docsFolder = "doc"

    #: docsBuildFolder is the disk location of the docs html folder.
    docsBuildFolder = os.path.join(docsFolder, "build/html")

    # Can set alternative values here if necessary, but it does not seem very likely that this will be needed.
    #if "pdsf" in socket.gethostname():
    #    staticURLPath = "/../site_media/aliemcalmonitor"

    #: Enable debugging information.
    debug = sharedParameters.debug

    #: Set the logging level.
    loggingLevel = logging.INFO

    #: List of subsystems.
    #: Each subsystem listed here will have an individual page for their respective histograms.
    subsystemList = sharedParameters.subsystemList

    #: Subsystems with ROOT files to show.
    subsystemsWithRootFilesToShow = sharedParameters.subsystemsWithRootFilesToShow

    qaFunctionsList = sharedParameters.qaFunctionsList
    """ Define which functions are accessible from the QA page.

    See Also: 
        :attr:`config.sharedParams.sharedParameters.qaFunctionsList`
    """

    #: Subsystems which have templates available (determined on startup).
    #: Since this is run from the root directory, we need to go into the "webApp" directory to find the templates!
    availableRunPageTemplates = [name for name in os.listdir(os.path.join("webApp", templateFolder)) if "runPage" in name]

    #: Sites to check during the status request.
    statusRequestSites = {"CERN": "http://127.0.0.1:8850", "Yale": "https://aliceoverwatch.physics.yale.edu"}

    # Lower the min logging level if we are debugging.
    if debug:
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
        returnValue = "Server Parameters configuration:\n"
        members = [var for var in vars(cls)]
        for member in members:
            # Filter out elements with "_" in name and the printSettings function
            if "_" not in member and "printSettings" not in member:
                returnValue += "{0}: {1}\n".format(member, getattr(cls, member))

        return returnValue

