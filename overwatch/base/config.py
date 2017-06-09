#!/usr/bin/env python

import enum
import logging
#import yaml
import ruamel.yaml as yaml
import sys
import os

import warnings

# TEMP
import pprint
# ENDTEMP

logger = logging.getLogger(__name__)

class configurationType(enum.Enum):
    processing = 0
    webApp = 1

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
    print("retVal: {0}".format(retVal))
    return retVal
# Register the function
yaml.SafeLoader.add_constructor('!findRunPageTemplates', determineRunPageTemplates)

def readConfigFiles(fileList):
    configs = []
    filesRead = []
    for filename in fileList:
        try:
            f = open(filename, "r")
        except IOError:
            logger.debug("Cannot open configuration file {0}".format(filename))
            continue
        else:
            with f:
                filesRead.append(filename)
                configs.append(f.read())

    return (configs, filesRead)

def readConfig(configType):
    if configType == configurationType.processing or configType == configurationType.webApp:
        fileList = [
                    # Ensures that we have "WebApp" here.
                    os.path.expandvars("~/.overwatch{0}").format(configType.name[0].upper() + configType.name[1:]),
                    os.path.join(sys.prefix, "overwatch", "{0}".format(configType.name), "config.yaml"),
                    os.path.join(sys.prefix, "overwatch", "{0}".format(configType.name), "shared.yaml")
                    ]
    else:
        logger.critical("Unrecognized configuration type {0}!".format(configType.name))
        sys.exit(1)

    logger.debug("Config filenames: {0}".format(fileList))
    # TEMP
    #fileList = [
    #            "b.yaml",
    #            "a.yaml"
    #            ]
    fileList = [
                "../../config/processingParams.yaml",
                "../../config/serverParams.yaml",
                "../config/shared.yaml"
               ]
    # ENDTEMP

    (configs, filesRead) = readConfigFiles(fileList)
    logger.debug("Read config files: {0}".format(filesRead))

    # Merge the configurations together
    # List is reversed so the earlier listed config will always override settings from lower listed files
    configs = "\n".join(reversed(configs))
    #print("configs: {0}".format(configs))
    # Handle warnings
    # See: https://stackoverflow.com/a/40376576
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        globalConfig = yaml.load(configs, Loader=yaml.SafeLoader)

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
