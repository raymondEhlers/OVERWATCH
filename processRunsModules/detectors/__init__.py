""" Documentation for adding new detectors

Each ALICE detector can add a file named the respective three letter detector name.

Addding a New Detector
======================

Adding a new detector is a fairly straightforward process. There are several available
options:

1.  Adding histograms to the HLT, which will then be accessible through the *Web App*.
    For more information on this approach, contact the HLT. Work in progress.

2.  Creating a subpage that splits out a detectors histograms. The histograms avialable to be
    split out are the ones that are shown on the web site.

3.  Creating a QA or automated QA (ie one that always runs) function to process the some or all of
    the available histograms. The histograms availabe to be processed are the ones shown on
    the web site.

Getting Started
---------------

1.  Create a new file in the :mod:`processRunsModules.detectors` package. This should be the
    "processRunsModules/detectors" folder. The file should be named by the three letter detector
    name, in all caps (ex: "EMC.py"). If it has already been created, then simply edit the
    existing file.

    The next steps depend on the desired used case. One can `Create a Detector Page`_, which
    will handle sorting histograms to be shown on a dedicated page for the detector. Alternatively,
    one can `Create a QA function`_, which will allow the creation of a QA function for a particular
    detector.

Create a Detector Page
----------------------

1.  Be sure to follow the directions in `Getting Started`_ if they have not already been performed.

2.  Create a new sorting function for viewing the histograms in this file. It must be named

    >>> sortAndGenerateHtmlFor(SUBSYSTEM)Hists(outputHistNames, outputFormatting, subsystem = "SUBSYSTEM")

    where ``SUBSYSTEM`` is replaced by the three letter detector name. For example, the EMC function is

    >>> sortAndGenerateHtmlForEMCHists(outputHistNames, outputFormatting, subsystem = "EMC")

    See :func:`~processRunsModules.detectors.EMC.sortAndGenerateHtmlForEMCHists()` for full argument
    documentation, but in short,
    ``outputHistNames`` is the names of all of the histograms,
    ``outputFormatting`` is the generic (ie contains a %s, which should be filled with the histogram name)
    path to the images to allow them to be printed, and
    ``subsystem`` is the three letter detector name.

    ..  seealso::
        For an example function, see: :func:`~processRunsModules.detectors.EMC.sortAndGenerateHtmlForEMCHists()`

3.  Add the three letter detector name to 
    :attr:`config.sharedParams.sharedParameters.subsystemList` in the config file "config/sharedParams.py".

4.  Optional: If the detector has a dedicated merger in the HLT, direct access to the ROOT files
    is possible. To create this page per run, add the three letter detector name to 
    :attr:`config.sharedParams.sharedParameters.subsystemsWithRootFilesToShow`. If the detector does
    not have a dedicated merger, then the histograms are stored in the HLT ROOT files, and can be
    accessed on that page.

5. Continue on to `Test the Function Locally`_.

Create a QA function
--------------------

1.  Be sure to follow the directions in `Getting Started`_ if they have not already been performed.

2.  Create the new QA or automated QA function in the detector file created in `Getting Started`_. It will be
    called for every histogram processed with two arguments:

    >>> functionName(hist, qaContainer)

    where ``hist`` is a TH1 that contains the histogram to be processed and ``qaContainer`` is a 
    :class:`~processRunsModules.qa.qaFunctionContainer` which contains information
    about the QA function and stored histograms, as well as the run being processed.

    This function can be anything the user desires, and histograms to show derived quantities can be stored in the
    ``qaContainer`` class.

    Warning:
        Be sure to document your class fully using docstrings and that the last two items ars "Args"
        and "Returns". This documentation will be the information shown to the user on the QA page,
        so it is important that it is clear!

    ..  seealso::
        For an example of a QA function that should be run on request from the web app, see,
        see :func:`~processRunsModules.detectors.EMC.determineMedianSlope()`.
        
        For an example of an automated QA function that runs for every single histogram,
        see :func:`~processRunsModules.detectors.EMC.checkForOutliers()`.

    Note:
        The functions will be listed by subsystem. They will only work on the defined subsystem.
        If it is desired to use the same function on two subsystems, it is possible, but the function must
        be imported into each module. See the :mod:`~processRunsModules.generateWebPages` and
        :mod:`~processRunsModules.qa` modules for examples on how to import the function. It would then
        need to be added according to step 3.

3.  If it is a QA function that should be run on request, add the three letter detector name and the name
    of the function to :attr:`config.sharedParams.sharedParameters.qaFunctionsList` in the config file
    "config/sharedParams.py".

    If it is an automated QA function that runs for every single histogram, add the three letter detector name
    and the name of the function to :attr:`config.sharedParams.sharedParameters.qaFunctionsToAlwaysApply` in
    the config file "config/sharedParams.py".

    See the documentation for the attributes for the precise format of how it should be added.

4. Continue on to `Test the Function Locally`_.

Test the Function Locally
-------------------------

Now that a new function is created, it is important to test it before making a pull request. Data is needed
to test the function. Fortunately, it is straightfoward to download (and does not require downloading many individual
files by hand!).

1.  To download test data to use, go to the contact page (``/contact``), and click on the link to the test data. It will
    provide a zip file to download. If the link is not there, please login first, and then return to the contact page.
    This archive has data from (at most) the 5 most recent runs. It contains the proper directory structure, starting at the "data"
    directory. It contains the combined files for all subsystems, meaning it should contain the most recent merged data.

2.  Extract the zip archive in the root of this package's directory (ie. where ``processRuns.py`` and ``webApp.py`` are located).
    
    Warning:
        This archive contains the "data" directory and all of the structure below it. Therefore, when it is extracted, it could
        potentially overwrite your current "data" directory (if it exists), depending on the settings of your system.
        Please be careful whe you extract it, as you would with any archive, to prevent data loss!

3.  Run ``python processRuns.py`` to process your new files and generate the required web pages.

4.  Run ``python webApp.py`` to start the web server. Go to the ip address and port specified in the serverParameters
    config file and go check to see if your function works. If something does not work, look at the debug messages
    (see the note), and fix your function. Note that when debug is enabled, auto reload is also enabled in the web app
    so any change made to your function should cause the web app to reload automatically. After the web app is reloaded,
    refresh the web page and check your function again.

    Note:
        It is highly recommended to enable debugging! Change the setting at
        :attr:`config.sharedParams.sharedParameters.debug` to ``True``. This should never be done in production, it the debug
        information is extremely useful when testing, and it provides comprehensive debugging in the browser!

5.  When done testing, close the web app using ``ctrl-c``.

Addding the Code
----------------

Once the code has been tested, please create a pull request for the project on github at `raymondEhlers/OVERWATCH`_ . Note that the code will only be accepted if it is properly documented! For it to show up when the documentation is rebuilt, the entry must be added in ``doc/source/processRunsModules.detectors.rst``.

.. _raymondEhlers/OVERWATCH: https://github.com/raymondEhlers/OVERWATCH

Getting Help
------------

If you run into trouble, please contact the authors.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University
"""
