""" Contains all of the machinery to allow for basic QA.

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

###################################################
def createHistGroups(subsystem):
    """ Properly route histogram group function for each subsystem
    
    """
    functionName = "create" + subsystem.subsystem + "HistogramGroups"
    # Get the function
    sortFunction = getattr(currentModule, functionName, None)
    if sortFunction is not None:
        sortFunction(subsystem)
        return True

    # If it doens't work for any reason, return false so that we can create a default
    logger.info("Could not find histogram group creation function for subsystem {0}".format(subsystem.subsystem))
    return False

###################################################
def createHistogramStacks(subsystem):
    """ Properly routes histogram stack function for each subsystem
    
    """
    functionName = "create" + subsystem.subsystem + "HistogramStacks"
    histogramStackFunction = getattr(currentModule, functionName, None)
    if histogramStackFunction is not None:
        histogramStackFunction(subsystem)
    else:
        logger.info("Could not find histogram stack function for subsystem {0}.".format(subsystem.subsystem))
        # Ensure that the histograms propagate to the next dict if there is not stack function!
        subsystem.histsAvailable = subsystem.histsInFile

###################################################
def setHistogramOptions(subsystem):
    """ Properly routes histogram options function for each subsystem
    
    """
    functionName = "set" + subsystem.subsystem + "HistogramOptions"
    histogramStackFunction = getattr(currentModule, functionName, None)
    if histogramStackFunction is not None:
        histogramStackFunction(subsystem)
    else:
        logger.info("Could not find histogram options function for subsystem {0}.".format(subsystem.subsystem))
        # Ensure that the histograms propagate to the next dict if there is not stack function!
        subsystem.histsAvailable = subsystem.histsInFile

###################################################
def findFunctionsForHist(subsystem, hist):
    """ Determines which functions should be applied to a histogram
    
    """
    functionName = "findFunctionsFor" + subsystem.subsystem + "Histogram"
    findFunction = getattr(currentModule, functionName, None)
    if findFunction is not None:
        findFunction(subsystem, hist)
    else:
        logger.info("Could not find histogram function sorting function for subsystem {0}".format(subsystem.subsystem))

###################################################
def checkHist(hist, qaContainer):
    """ Selects and calls the proper qa function based on the input.

    Args:
        hist (TH1): The histogram to be processed.
        qaContainer (:class:`~processRuns.processingClasses.qaFunctionContainer`): Contains information about the qa
            function and histograms, as well as the run being processed.

    Returns:
        bool: Returns true if the histogram that is being processed should not be printed.
            This is usually true if we are processing all hists to extract a QA value and 
            usually false if we are trying to process all hists to check for outliers or 
            add a legend or check to a particular hist.
    """
    #print "called checkHist()"
    skipPrinting = False

    # Python functions to apply for processing a particular QA function
    # Only a single function is selected on the QA page, so no loop is necessary
    # (ie only one call can be made).
    skipPrinting = getattr(currentModule, qaContainer.qaFunctionName)(hist, qaContainer)

    return skipPrinting

###################################################
# Load detector functions from other modules
###################################################
#print dir(currentModule)
# For more details on how this is possible, see: https://stackoverflow.com/a/3664396
detectorsPath = processingParameters["detectorsPath"]
modulesPath = processingParameters["modulesPath"]
logger.info("\nLoading modules for detectors:")

# For saving and show the docstrings on the QA page.
qaFunctionDocstrings = {}

# We need to combine the available subsystems. subsystemList is not sufficient because we may want QA functions
# but now to split out the hists on the web page.
# Need to call list so that subsystemList is not modified.
# See: https://stackoverflow.com/a/2612815
subsystems = list(processingParameters["subsystemList"])
for subsystem in processingParameters["qaFunctionsList"]:
    subsystems.append(subsystem)

# Make sure that we have a unique list of subsystems.
subsystems = list(set(subsystems))

# Load functions
for subsystem in subsystems:
    logger.info("Subsystem {0} Functions loaded:".format(subsystem))

    # Ensure that the module exists before trying to load it
    if os.path.exists(os.path.join(modulesPath, detectorsPath, "%s.py" % subsystem)):
        #print "file exists"
        # Import module dynamically
        subsystemModule = importlib.import_module("%s.%s.%s" % (modulesPath, detectorsPath, subsystem))
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
            
            # Save the function name so it can be shown on the QA page
            if subsystem in processingParameters["qaFunctionsList"]:
                if funcName in processingParameters["qaFunctionsList"][subsystem]:
                    # Retreive the docstring
                    functionDocstring = inspect.getdoc(func)

                    # Remove anything after and including "Args", since it is not interesting
                    # on the QA page.
                    functionDocstring = functionDocstring[:functionDocstring.find("\nArgs:")]

                    # Save the docstring
                    qaFunctionDocstrings[subsystem + funcName] = [subsystem, functionDocstring]

        # Print out the function names that have been loaded
        if functionNames != []:
            logger.info("\t{0}".format(", ".join(functionNames)))
        else:
            logger.info("")
    else:
        logger.info("")
