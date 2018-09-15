#!/usr/bin/env python

""" Handles configuration of overwatch via yaml.

Configurations are built in a hierarchy, with the base configuration providing
the first layer, and building up further until the specified module.

YAML parsing plugins are also specified here. This breaks the abstraction
a little bit, but it makes things much simpler, so it's worth the trade-off.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

import aenum
import ruamel.yaml as yaml
import sys
import os
import pprint
import pkg_resources
from flask_bcrypt import generate_password_hash
import warnings
import logging
logger = logging.getLogger(__name__)

class configurationType(aenum.OrderedEnum):
    """ Specifies the module ordering for loading of configurations.

    It is also used to specify the maximum level for which a config should be loaded.
    For example, if ``webApp`` is specified, it should load all configurations, while
    for processing, everything but processing should be loaded.

    The numerical values of this enum basically specify the dependencies of the package.

    Note:
        The names of these values must match the names of their corresponding modules!
    """
    base = 0
    receiver = 1
    api = 2
    processing = 3
    webApp = 4

def joinPaths(loader, node):
    """ Join elements of a list into a path using ``os.path.join``.
    Specified by ``!joinPaths`` (defined on registration below).

    Inspired by `here <https://stackoverflow.com/a/23212524>`__.

    Could similarly use ``!!python/object/apply:os.path.join``, with the downside of allowing lots of
    arbitrary code execution since you cannot use safe_load. Instead, we write this simple function
    and then explicitly make only this function available via the SafeLoader.

    Args:
        loader (yaml.Loader): YAML loader which is parsing the configuration.
        node (SequenceNode): Node containing the list of the paths to join together.
    Returns:
        str: The list elements joined together into a valid path.
    """
    seq = loader.construct_sequence(node)
    return os.path.join(*seq)
# Register the defined function
yaml.SafeLoader.add_constructor('!joinPaths', joinPaths)

def determineRunPageTemplates(loader, node):
    """ Determine which subsystems have run page templates on startup by determining the filenames of
    each run pages templates. We will later check for a subsystem specific filename is this list.
    Specified by ``!findRunPageTemplates`` (defined on registration below) and should be defined with the
    path to the templates directory.

    Since this is run from the root directory, we need to go into the "webApp" directory to find the templates!

    Args:
        loader (yaml.SafeLoader): YAML loader which is parsing the configuration.
        node (SequenceNode): Node containing the list of the paths to join together.
    Returns:
        list: Subsystems which have a run page template.
    """
    seq = loader.construct_sequence(node)

    # Construct the path. It should always be inside of the `webApp` module.
    path = ["overwatch", "webApp"]
    path.extend(seq)

    # We need the last part of the path to be separate for calling resource_listdir, so we join everything
    # up to that last value, and then pass the last value separately.
    returnList = [name for name in pkg_resources.resource_listdir(".".join(path[:-1]), path[-1]) if "runPage" in name]
    # Apparently the order can vary from system to system. This order doesn't matter, but for consistency,
    # we'll sort it. This will ensure that stored test configurations will match on any system.
    returnList = sorted(returnList)
    #logger.debug("returnList: {0}".format(returnList))
    return returnList
# Register the defined function
yaml.SafeLoader.add_constructor('!findRunPageTemplates', determineRunPageTemplates)

#: Number of rounds of hashing when using bcrypt.
#: Define the default value here so it can be accessed outside of the module.
#: This is a hack, but I think it is worth the simplification in everything else.
bcryptLogRounds = 12

def bcrypt(loader, node):
    """ Hash any given passwords according to the provided number of rounds.
    Specified by ``!bcrypt`` (defined on registration below).

    Block should look like:

    .. code-block:: yaml

        bcryptExampleBlock: !bcrypt
            # Could be defined elsewhere and referenced using an anchor here
            bcryptLogRounds: 12
            user1: "password1"
            user2: "password2"

    The block will result in two users, ``user1`` and ``user2`` being added to the database.
    Their passwords will be the hash of the given strings using 12 bcrypt log rounds.

    Note:
        bcryptLogRounds can also be omitted. In that case, it will default to 12.

    Args:
        loader (yaml.SafeLoader): YAML loader which is parsing the configuration.
        node (MappingNode): Node containing something like the block above.
    Returns:
        dict: Keys are usernames, while values are the corresponding hashed passwords.
    """
    n = loader.construct_mapping(node)
    # Get number of rounds to hash the password! Note that we default here to 12.
    logRounds = n.pop("bcryptLogRounds", bcryptLogRounds)
    returnDict = {}
    # Now setup each username with a hashed password.
    for k, v in n.items():
        # Check if the key and value exists since they could be `None`.
        # Only proceed if they are valid - otherwise they are skipped.
        if k and v:
            returnDict[k] = generate_password_hash(v, rounds = logRounds)
    return returnDict
# Register the defined function
yaml.SafeLoader.add_constructor('!bcrypt', bcrypt)

def secretKey(loader, node):
    """ Determine the secret key for signing cookies in the webApp.
    Specified by ``!secretKey`` (defined on registration below).

    If a value is already specified, that value is simply used. However, if an invalid value is passed
    (for example, ``None``), a value is generated according to the best practices recommendation of the
    flask developers.

    Args:
        loader (yaml.SafeLoader): YAML loader which is parsing the configuration.
        node (ScalarNode): Node containing the secret key.
    Returns:
        str: The secret key for signing cookies.
    """
    val = loader.construct_scalar(node)
    if val != "null":
        return str(val)
    # Generate a new value using `unrandom(50)` (as suggested by the flask developers) if one is not passed.
    return str(os.urandom(50))
# Register the defined function
yaml.SafeLoader.add_constructor('!secretKey', secretKey)

def readConfigFiles(fileList):
    """ Read the configurations from the given list of files.

    Args:
        fileList (list): List of paths to configuration files.
    Returns:
        tuple: (list of configurations read from the files, list of configuration filenames which were read)
    """
    configs = []
    filesRead = []
    for filename in fileList:
        try:
            f = open(filename, "r")
        except IOError:
            # If we can't open the file, that's fine - we just skip it
            # Commented out to reduce number of startup messages
            #logger.debug("Cannot open configuration file \"{0}\"".format(filename))
            continue
        else:
            with f:
                # Store each configuration separately so we can decide how to combine them later.
                filesRead.append(filename)
                configs.append(f.read())

    return (configs, filesRead)

def readConfig(configType):
    """ Main function to read the Overwatch configuration.

    It looks for values in a set of configuration files according to the module that is specified.

    The configuration file must be named ``config.yaml``. The files are read in such an order that values
    specified in later packages will override earlier ones. For example, ``webApp`` depends on ``processing``,
    so if we specify different values for the same key in both module configurations, the value in the
    ``webApp`` config will be used.

    In additional to looking in Overwatch modules, it also looks for a configuration in the current working
    directory, as well as in the user home directory.

    The current (as of August 2018) order of override priority from highest to lowest is:

    .. code-block:: none

        Current working directory
        User home directory
        overwatch.webApp
        overwatch.processing
        overwatch.receiver
        overwatch.api
        overwatch.base

    (this basically follows the dependency tree).

    Args:
        configType (configurationType or str): Type of the module for which we are loading the configuration.
    Returns:
        tuple: (Fully merged configuration, list of configuration filenames which were read)
    """
    # Validate arguments
    if not isinstance(configType, configurationType):
        # Perhaps we got a string, so let's try to construct it based on that.
        # It's fine if this raises an exception, because it will tell us where we've gone wrong
        configType = configurationType[configType]

    # The earliest config files are given the _most_ precedence.
    # ie. A value in the config in the local directory will override the same variable
    #     defined in the config in the package base directory.
    # For more on pkg_resources, see: https://stackoverflow.com/a/5601839
    fileList = [
        # Config file in the local directory where it is run
        "config.yaml",
        # Config in the home directory
        # Ensures that we have "WebApp" here.
        os.path.expandvars("~/.overwatch{0}").format(configType.name[0].upper() + configType.name[1:]),
    ]
    # Reversed so the modules are added in the proper order (ie. following the dependencies)
    for val in reversed(configurationType):
        # Retrieve and store the configuration of the requested object depends on that configuration
        # (as determined by the order of the configurationType values)
        if val <= configType:
            fileList.append(pkg_resources.resource_filename("overwatch.{}".format(val.name), "config.yaml"))

    # Commented out to reduce number of startup messages
    #logger.debug("Config filenames: {0}".format(fileList))

    (configs, filesRead) = readConfigFiles(fileList)
    # Commented out to reduce number of startup messages
    #logger.debug("Configuration type: {}, Read config files: {}".format(configType, filesRead))

    # Merge the configurations together
    # List is reversed so the earlier listed config will always override settings from lower listed files
    configs = "\n".join(reversed(configs))
    # Commented out to reduce number of startup messages
    #logger.debug("configs: {0}".format(pprint.pformat(configs)))

    # Handle warnings related to redefined anchors.
    # This is perhaps overly broad, but for our purposes, it should be fine.
    # See: https://stackoverflow.com/a/40376576
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        globalConfig = yaml.load(configs, Loader = yaml.SafeLoader)

    return (globalConfig, filesRead)

if __name__ == "__main__":  # pragma: no cover
    """ Load basic configuration for testing (although unit tests would be preferred in the future). """
    # Setup logging
    # Provides a warning if there are no handlers
    logging.raiseExceptions = True
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    streamHandler = logging.StreamHandler(sys.stdout)
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)
    logger.setLevel("DEBUG")

    # Load configuration
    config, _ = readConfig(configurationType.processing)
    logger.info("Final config: {0}".format(pprint.pformat(config)))
