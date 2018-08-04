""" Contains all of the machinery for the plugin system.

It loads the plugin functions from the detector specific files, allowing
for them to be called by the processing functions.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

# Python 2/3 support
from __future__ import print_function

# General includes
import os
import sys
import logging
# Setup logger
logger = logging.getLogger(__name__)

# Used to load functions from other modules
import importlib
import inspect

# Configuration
#from config.processingParams import processingParameters
from ..base import config
(processingParameters, filesRead) = config.readConfig(config.configurationType.processing)

# Get the current module
# Used to load functions from other moudles and then look them up.
currentModule = sys.modules[__name__]

def createHistGroups(subsystem):
    """ Properly route histogram group function for each subsystem.

    Histogram groups are groups of histograms which should be displayed together for
    visualization. Functions names should be of the form
    ``create(SUBSYSTEM)HistogramGroups(subsystemName, *args, **kwargs)``. where
    subsystemName (str) is the name of the subsystem, and the other args are reserved for
    future use.

    Args:
        subsystem (subsystemContainer): Current subsystem container.
    Returns:
        bool: True if the function was called
    """
    functionName = "create{}HistogramGroups".format(subsystem.subsystem)
    # Get the function
    sortFunction = getattr(currentModule, functionName, None)
    if sortFunction is not None:
        sortFunction(subsystem)
        return True

    # If it doens't work for any reason, return false so that we can create a default
    logger.info("Could not find histogram group creation function for subsystem {0}".format(subsystem.subsystem))
    return False

def createAdditionalHistograms(subsystem):
    """ Properly routes additional histogram creation functions for each subsystem.

    Additional histograms can be created for a particular subsystem via these plugins.
    Functions should be of the
    form ``createAdditional(SUBSYSTEM)Histograms(subsystemName, *args, **kwargs)``, where
    subsystemName (str) is the name of the subsystem, and the other args are reserved for
    future use.

    Args:
        subsystem (subsystemContainer): Current subsystem container
    Returns:
        None.
    """
    functionName = "createAdditional{}Histograms".format(subsystem.subsystem)
    histogramCreationFunction = getattr(currentModule, functionName, None)
    if histogramCreationFunction is not None:
        logger.info("Found additional histogram creation function for subsystem {}".format(subsystem.subsystem))
        histogramCreationFunction(subsystem)
    else:
        logger.info("Could not find additional histogram creation function for subsystem {}.".format(subsystem.subsystem))

def createHistogramStacks(subsystem):
    """ Properly routes histogram stack function for each subsystem.

    Histogram stacks are collections of histograms which should be plotted
    together. For example, one may want to plot similar spectra, such as
    those in the EMCal and DCal, on the same plot. These are treated simiilarly
    to a histogramContainer. Functions should be of the
    form ``create(SUBSYSTEM)HistogramStacks(subsystem, *args, **kwargs)``, where
    subsystem (subsystemContainer) is the current subsystem container, and the
    other args are reserved for future use.

    Args:
        subsystem (subsystemContainer): Current subsystem container
    Returns:
        None.
    """
    functionName = "create{}HistogramStacks".format(subsystem.subsystem)
    histogramStackFunction = getattr(currentModule, functionName, None)
    if histogramStackFunction is not None:
        histogramStackFunction(subsystem)
    else:
        logger.info("Could not find histogram stack function for subsystem {0}.".format(subsystem.subsystem))
        # Ensure that the histograms propagate to the next dict if there is not stack function!
        # Copy by key and value so any existing hists in histsAvailable are preserved
        for k in subsystem.histsInFile.iterkeys():
            subsystem.histsAvailable[k] = subsystem.histsInFile[k]

def setHistogramOptions(subsystem):
    """ Properly routes histogram options function for each subsystem.

    Histogram options include options such as renaming histograms,
    setting draw options, setting histogram scaling, and/or thresholds, etc.
    Canvas options are set elsewhere when actually drawing on the canvas.
    It cannot be set now because the canvas doesn't yet exist and we would
    need to call functions to on that object (we prefer not to use function
    pointers here). Functions should be of the
    form ``set(SUBSYSTEM)HistogramOptions(subsystem, *args, **kwargs)``,
    where subsystem (subsystemContainer) is the current subsystem container, and
    the other args are reserved for future use.
    
    Args:
        subsystem (subsystemContainer): Current subsystem container
    Returns:
        None.
    """
    functionName = "set{}HistogramOptions".format(subsystem.subsystem)
    histogramOptionsFunction = getattr(currentModule, functionName, None)
    if histogramOptionsFunction is not None:
        histogramOptionsFunction(subsystem)
    else:
        logger.info("Could not find histogram options function for subsystem {0}.".format(subsystem.subsystem))

def findFunctionsForHist(subsystem, hist):
    """ Determines which functions should be applied to a histogram.

    Histogram functions apply additional processing, from extracting values
    to change ranges to drawing on top of the histogram. These functions
    are executed when the histogram is processed. The functions should be
    stored as function pointers so the lookup doesn't need to occur every
    time the histogram container is processed. The plugin functions for each
    subsystem should be of the
    form ``findFunctionsFor(SUBSYSTEM)Histogram(subsystem, hist, *args, **kwargs)``,
    where subsystem (subsystemContainer) is the current subsystem and
    hist (histogramContainer) is the current histogram being processed, and
    the other args are reserved for future use.

    Note:
        This function must handle all possible histograms for a subsystem,
        so it is strongly recommended to select them via hist name or another
        property.

    Args:
        subsystem (subsystemContainer): Current subsystem container.
        hist (histogramContainer): Current histogram to be processed.
    Returns:
        None.
    """
    functionName = "findFunctionsFor{}Histogram".format(subsystem.subsystem)
    findFunction = getattr(currentModule, functionName, None)
    if findFunction is not None:
        findFunction(subsystem, hist)
    else:
        logger.info("Could not find histogram function for subsystem {0}".format(subsystem.subsystem))

def defineTrendingObjects(subsystem):
    """ Defines trending objects and the histograms from which they should
    be extracted.

    Defines trending objects related to a subsystem. These objects implement the
    trending function, as well as specifying the histograms that provide the values
    for the trending.  The plugin function for each subsystem should be of the
    form ``define(SUBSYSTEM)TrendingObjects(trending, *args, **kwargs)``, where
    trending is a dict where the new trending objects should be stored, and
    the other args are reserved for future use.

    Args:
        subsystem (str): The current subsystem by three letter, all capital name (ex. ``EMC``).
    Returns:
        dict: Keys are the name of the trending objects, while values are the trending objects themselves.
    """
    functionName = "define{}TrendingObjects".format(subsystem)
    findFunction = getattr(currentModule, functionName, None)
    trending = {}
    if findFunction is not None:
        trending = findFunction(trending)
    else:
        logger.info("Could not find histogram trending function for subsystem {0}".format(subsystem))

    return trending

###################################################
# Load detector functions from other modules
#
# These detector plugin functions are dynamically loaded
# so they don't need to be specified at execution time.
# NOTE: These functions are susceptible to name collisions.
#       This could be resolved by appending subsystem names
#       to the particular functions.
###################################################
#print dir(currentModule)
# For more details on how this is possible, see: https://stackoverflow.com/a/3664396
logger.info("\nLoading modules for detectors:")

# Make sure that we have a unique list of subsystems.
subsystems = list(set(processingParameters["subsystemList"]))

# Load functions
for subsystem in subsystems:
    logger.info("Subsystem {} functions loaded:".format(subsystem))

    # Ensure that the module exists before trying to load it
    if os.path.exists(os.path.join(os.path.dirname(__file__), "detectors", "{}.py".format(subsystem))):
        #print("file exists, qa __name__: {0}".format(__name__))
        # Import module dynamically
        # Using absolute import
        #subsystemModule = importlib.import_module("%s.%s.%s.%s" % ("overwatch", "processing", "detectors", subsystem))
        # Using relative import
        # Relative import is preferred here because it's used elsewhere in the project.
        subsystemModule = importlib.import_module(".detectors.{0}".format(subsystem), package = "overwatch.processing")
        #logger.info(dir(subsystemModule))

        # Loop over all functions from the dynamically loaded module
        # See: https://stackoverflow.com/a/4040709
        functionNames = []
        for funcName in inspect.getmembers(subsystemModule, inspect.isfunction):
            # Contains both the function name and a reference to a pointer. We only want the name,
            # so we take the first element
            funcName = funcName[0]
            func = getattr(subsystemModule, funcName)

            # Add the function to the current module
            setattr(currentModule, funcName, func)

            # Save the function name so that it can be printed
            functionNames.append(funcName)
            
        # Print out the function names that have been loaded
        #print(functionNames)
        if functionNames != []:
            logger.info("\t{0}".format(", ".join(functionNames)))
        else:
            logger.info("")
    else:
        logger.info("")
