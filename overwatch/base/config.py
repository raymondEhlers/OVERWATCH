#!/usr/bin/env python

import enum
import logging
#import yaml
import ruamel.yaml as yaml
import sys
import os
import pkg_resources
from flask_bcrypt import generate_password_hash

import warnings

# TEMP
import pprint
# ENDTEMP

logger = logging.getLogger(__name__)

class configurationType(enum.Enum):
    processing = 0
    webApp = 1
    dqmReceiver = 2
    apiConfig = 3

# Join passed paths
# Inspired by: https://stackoverflow.com/a/23212524
# Could similarly use "!!python/object/apply:os.path.join", with the downside of allowing lots of
# arbitrary code execution since you cannot use safe_load. Instead, we write this simple function
# and then explicitly allow it.
def joinPaths(loader, node):
    seq = loader.construct_sequence(node)
    return os.path.join(*seq)
# Register the function
yaml.SafeLoader.add_constructor('!joinPaths', joinPaths)

#: Subsystems which have templates available (determined on startup).
#: Since this is run from the root directory, we need to go into the "webApp" directory to find the templates!
def determineRunPageTemplates(loader, node):
    seq = loader.construct_sequence(node)
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), *seq)
    retVal = [name for name in os.listdir(path) if "runPage" in name]
    #print("retVal: {0}".format(retVal))
    return retVal
# Register the function
yaml.SafeLoader.add_constructor('!findRunPageTemplates', determineRunPageTemplates)

#: Handle bcrypt
def bcrypt(loader, node):
    n = loader.construct_mapping(node)
    # Get number of rounds!
    bcryptLogRounds = n.pop("bcryptLogRounds")
    returnDict = dict()
    for k, v in n.items():
        # Check if the key and value exists since they could be None
        if k and v:
            returnDict[k] = generate_password_hash(v, rounds = bcryptLogRounds)
    return returnDict
# Register the function
yaml.SafeLoader.add_constructor('!bcrypt', bcrypt)

#: Generate secret key if necessary
def secretKey(loader, node):
    val = loader.construct_scalar(node)
    if val:
        return str(val)

    """ Secret key for signing cookies. Regenerated if a value is not passed.

    Generated using urandom(50), as suggested by the flask developers.
    """
    return str(os.urandom(50))
# Register the function
yaml.SafeLoader.add_constructor('!secretKey', secretKey)

def readConfigFiles(fileList):
    configs = []
    filesRead = []
    for filename in fileList:
        try:
            f = open(filename, "r")
        except IOError:
            # Suppressed for cleaning up start up messages
            #logger.debug("Cannot open configuration file \"{0}\"".format(filename))
            continue
        else:
            with f:
                filesRead.append(filename)
                configs.append(f.read())

    return (configs, filesRead)

def readConfig(configType):
    if configType in configurationType:
        # The earliest config files are given the _most_ precedence.
        # ie. A value in the config in the local directory will override the same variable
        #     defined in the config in the package base directory.
        # For more on pkg_resources, see: https://stackoverflow.com/a/5601839
        fileList = [
                    # Config file in the local directory where it is run
                    "config.yaml",
                    # Config in the home directory
                    # Ensures that we have "WebApp" here.
                    os.path.expanduser("~/.overwatch{0}.yaml").format(configType.name[0].upper() + configType.name[1:]),
                    # Config type specific directory in the package (ex: "processing")
                    # TODO: There is a problem when loading the shared configuration with the processing configuration
                    #       because the shared configuration can have options which are defined in the web app config
                    #       and therefore undefined when the web app config is not loaded!
                    #       To resolve it temporarily, both configuration files will be included
                    pkg_resources.resource_filename("overwatch.webApp", "config.yaml"),
                    pkg_resources.resource_filename("overwatch.processing", "config.yaml"),
                    pkg_resources.resource_filename("overwatch.receiver", "config.yaml"),
                    pkg_resources.resource_filename("overwatch.api", "config.yaml"),
                    #       Below is the line that should be used when the above issue is resolved
                    #pkg_resources.resource_filename("overwatch.{0}".format(configType.name), "config.yaml"),
                    # Shared config in the package base
                    pkg_resources.resource_filename("overwatch.base", "config.yaml")
                    ]
    else:
        # Cannot just be the logger because the logger many not yet be initialized
        print("CRITICAL: Unrecognized configuration type {0}!".format(configType.name))
        logger.critical("Unrecognized configuration type {0}!".format(configType.name))
        sys.exit(1)

    # Suppressed for cleaning up start up messages
    #logger.debug("Config filenames: {0}".format(fileList))

    (configs, filesRead) = readConfigFiles(fileList)
    # Suppressed for cleaning up start up messages
    #logger.debug("Read config files: {0}".format(filesRead))

    # Merge the configurations together
    # List is reversed so the earlier listed config will always override settings from lower listed files
    configs = "\n".join(reversed(configs))
    #print("configs: {0}".format(configs))
    # Handle warnings
    # See: https://stackoverflow.com/a/40376576
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        globalConfig = yaml.load(configs, Loader=yaml.SafeLoader)

    dbLoc = globalConfig["databaseLocation"]
    dbLoc = dbLoc if dbLoc.startswith("file://") else "file://" + dbLoc
    globalConfig["databaseLocation"] = dbLoc

    return (globalConfig, filesRead)

if __name__ == "__main__":
    # Setup logging
    # Provides a warning if there are no handlers
    logging.raiseExceptions = True
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    streamHandler = logging.StreamHandler(sys.stdout)
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)
    logger.setLevel("DEBUG")

    # Load configuration
    config,_ = readConfig(configurationType.processing)
    logger.info("Final config: {0}".format(pprint.pformat(config)))
