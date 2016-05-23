## Containers parameters shared between processingParameters and serverParameters

class sharedParameters(object):
    """ Containers parameters shared between processingParameters and serverParameters.

    They often just take the value and reuse the variable name so that variables are available
    from one consistent class.
    """

    #: Enable debugging information.
    debug = True

    #: List of subsystems.
    #: Each subsystem listed here will have an individual page for their respective histograms.
    #: The HLT _MUST_ be included here!
    subsystemList = ["EMC", "HLT"]

    #: Each of these subsystems will also get an individual page for access to their respective ROOT files.
    subsystemsWithRootFilesToShow = ["EMC", "HLT"]

    qaFunctionsList = {"EMC": ["determineMedianSlope", "checkForOutliers"]}
    #qaFunctionsList = {"EMC": ["determineMedianSlope", "checkForOutliers"], "HLT" : ["determineValue"], "TPC" : ["checkForOutliers"]}
    """ These are the QA functions that should be displayed as options on the QA page.
    
    The functions should be sorted by subsystem. They will only work on the defined subsystem.
    If it is desired to use the same function on two subsystems, it is possible, but the function must
    be imported into each module. See the :mod:`~processRunsModules.generateWebPages` and
    :mod:`~processRunsModules.qa` modules for examples on how to import the function. It would then
    need to be added to the dict for each subsystem.
    
    The dictionary should be formatted as

    >>> qaFunctionsList = { "det": [ "functions" ], "det": [ "functions" ] }
    """

    qaFunctionsToAlwaysApply = ["setEMCDrawOptions"]
    """ These are functions that should always be applied when processing ROOT files.

    These functions are often only automated QA functions, in that they can improve or help check the data quality,
    but they do it on a histogram by histogram level, without extracting representative values. Examples
    include checking particular histograms for outliers, or improving the quality of presenation of a
    histogram by adding an axis or a grid.
    """

    # Folders
    #: The name of the static folder on the disk.
    staticFolderName = "static"

    #: The name of the data folder on the disk.
    dataFolderName = "data"

    #: The name of the templates folder on the disk.
    templateFolderName = "templates"
