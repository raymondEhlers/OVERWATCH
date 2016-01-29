# Holds all of the server parameters

# General
import socket
import os

# Bcrypt
from flask.ext.bcrypt import generate_password_hash

# Config
from sharedParams import sharedParameters

class serverParameters:
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
    #: Sets the ip address
    ipAddress = "127.0.0.1"

    #: Sets the port
    port = 8850

    #: Setup Bcrypt
    bcryptLogRounds = 12

    dynamicContent = True
    """ Determine whether to use dynamic content (ie templates for the Run pages).
    
    If this is disabled, then static pages will be served for viewing the data.
    The "/login", "/logout", "/testingData" and "/contant" pages will continue
    to be rendered via templates. Time dependent merging will also continue to operate.
    """

    _users = {"username": generate_password_hash("password", bcryptLogRounds)}
    """ Contains the users for authenticating on the server
    This could be more complex, but there isn't any point for such a simple project
    For more security in this file, one could also generate the hash and then just
    copy that here so that the password is not visible in plain text in this file.

    Defined with an underscore since it is a private value.
    
    Other usernames can be added here if desired. Users are defined as:
    
    >>> _users = {"username": generate_password_hash("password", bcryptLogRounds)}
    """

    _secretKey = ''
    """ Secret key for signing cookies

    Defined with an underscore since it is a private value.
    
    Generated using urandom(50), as suggested by the flask developers.
    """

    #: basePath is just a useful value.
    #: It defines a base directory to reference if the static, template, etc folders are
    #: all in the same dir.
    basePath = ""

    #: staticFolder is the disk location of the static folder
    #: It is a flask defined variable.
    #: To check if the static files are from the front-end webserver, use:
    #: https://stackoverflow.com/questions/16595691/static-files-with-flask-in-production
    #:
    #: (ie. add + "CHANGE" to the staticFolder location specified here)
    staticFolder = os.path.join(basePath, sharedParameters.staticFolderName) 

    #: staticURLPath is the URL of the static folder.
    #: If you want to access "foo", it would be at $BASE_URL/staticURLPath/foo. "" is just the root.
    #: It is a flask defined variable.
    staticURLPath = "/static"

    #: protectedFolder is the disk location of the protected folder
    #: This folder holds the experimental data
    protectedFolder = os.path.join(basePath, sharedParameters.dataFolderName)

    #: templateFolder is the disk location of the template folder
    templateFolder = os.path.join(basePath, sharedParameters.templateFolderName)

    # Can set alternative values here if necessary, but it does not seem very likely that this will be needed.
    #if "pdsf" in socket.gethostname():
    #    staticURLPath = "/../site_media/aliemcalmonitor"

    #: Enable debugging information
    debug = sharedParameters.debug

    #: List of subsystems.
    #: Each subsystem listed here will have an individual page for their respective histograms.
    subsystemList = sharedParameters.subsystemList

    qaFunctionsList = sharedParameters.qaFunctionsList
    """ Define which functions are accessible from the QA page

    See Also: 
        :attr:`config.sharedParams.sharedParameters.qaFunctionsList`
    """

print "\nServer Parameters:"
print "ipAddress:", serverParameters.ipAddress
print "port:", serverParameters.port
print "bcryptLogRounds:", serverParameters.bcryptLogRounds
print "basePath:", serverParameters.basePath
print "staticFolder:", serverParameters.staticFolder
print "staticURLPath:", serverParameters.staticURLPath
print "protectedFolder:", serverParameters.protectedFolder
print "templateFolder:", serverParameters.templateFolder
print "debug:", serverParameters.debug
print "subsystemList:", serverParameters.subsystemList
print "qaFunctionsList:", serverParameters.qaFunctionsList
