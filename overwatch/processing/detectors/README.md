# Subsystem (Detector) Plug-ins

The Overwatch processing module provides a number of opportunities to plug-in subsystem (detector) specific
functionality. These functions will automatically be called if the subsystem is enabled. Note that it is fine
if a function does not exist - execution will proceed without that part of the functionality.

As a general convention throughout this documentation, `SYS` should be replaced by the three letter name of
your desired subsystem (ie a detector). As an example, if you are working with the EMCal and are attempting to
create groups of histograms, `create(SYS)HistogramGroups(...)` would be `createEMCHistogramGroups(...)`.

## Table of Contents

- [Subsystem plugins](#general-philosophy)
- [Trending system](#trending)
- [Available histograms](#available-histograms)

## General Philosophy

Processing is written to be as flexible as possible by allowing detectors to plugin into every step. This way,
every aspect can be customized as desired. Histograms are stored and accessed through a hierarchical
structure. Each run is stored in a `runContainer` object and contains subsystems, which are stored in
`subsystemContainer` objects. Each subsystem container stores groups of histograms in
`histogramGroupContainer` objects. Individual histograms are assigned to and stored by particular
`histogramContainer` objects and each histogram is stored inside of a `histogramContainer` object. A
complicated run would look something like:

```none
# Of the form "class (name)"
runContainer (Run 3) ->
    subsystemContainer (EMC) ->
        # Group args are (name, selector)
        histogramGroupContainer ("group1", "trig") ->
            histogramContainer (trigA)
            histogramContainer (trigB)
        histogramGroupContainer ("group2", "hist") ->
            histogramContainer (histC)
    subsystemContainer (TPC) ->
        histogramGroupContainer ("group3", "V") ->
            histogramContainer (Vz)
            histogramContainer (Vy)
        histogramGroupContainer ("group4", "hist") ->
            histogramContainer (histF)
```

This structure will be generated through the plug-in functionality described below. 

In general, there are two modes of operation:

- Run based processing, which is oriented around a set of histograms which are updated at a particular time
interval during each run. This is the focus on the [plug-in functionality](#available-plug-in-functions).
- Trending, which is oriented around time series data extracted from the set of histograms which are updated at
a particular time interval during each run. This functional is described in the section on
[trending](#trending).

### Note on Database Scheme and Troubleshooting

If the variables or functionality of a class changes too drastically, it can cause problems with the metadata
database schema evolution. To avoid these issues, when adding a field, be certain to give it a default value
in the base definition of the object (not just the constructor!) so that older objects can successfully
constructed.

Sometimes the charges are too large to resolve easily. In the case, it is easier to rebuild the database from
scratch. Fortunately, Overwatch is designed such that it should always be possible to rebuild it from
scratch.To do so, simply delete the database file (usually located at `data/overwatch.fs`) and it should be
recreated automatically.

## Available Plug-in Functions

Plug-ins are available at all steps throughout the processing. The following functions are called for each new
run, as histograms may have changed from run to run depending on various conditions. To make processing more
efficient, the output of these functions is stored in the metadata database, allowing the generated
structures, classes, and results to be used repeatedly for that run. In particular, this avoids repeated
string comparison, which is usually an extremely slow operation. Consequently, once these functions have been
executed for a particular run, they will not be repeated again until the next run.

They plug-in functions are listed below in the order that they are called.

1. Create [new additional histogmras](#additional-histograms): `createAdditional(SYS)Histograms(subsystem, **kwargs)`.
2. Create [stack of histograms](#histogram-stacks): `create(SYS)HistogramStacks(subsystem, **kwargs)`.
3. Set [histogram processing options](#general-histogram-processing-options) or set options that apply to the entire subsystem:
  `set(SYS)HistogramOptions(subsystem, **kwargs)`.
4. Create [groups of histograms](#histogram-groups): `create(SYS)HistogramGroups(subsystem, **kwargs)`.
5. [Find processing functions](#find-processing-functions) that apply to particular histograms for a given
   subsystem: `findFunctionsFor(SYS)Histogram(subsystem, hist, **kwargs)`

Note that the find processing functions plug-in is most important. It is how a detector maps particular
 histograms to particular processing functions. Recall that it is fine if a function does not exist
- execution will proceed without that part of the functionality. Lastly, for each function above, `subsystem`
is a `subsystemContainer` for the current subsystem in the current run. At the end of each section, an example
implementation for the plug-in will be shown, with complete argument documentation. The example subsystem name
is `SYS` (for "Subsystem").

### Additional Histograms

While a specific set of histograms is provided by the HLT, subsystems are not limited to displaying only those
histograms. The available histograms provide a wealth of information, such that different projections can
clarify different aspects of detector performance. Consequently, it is possible to define new histograms which
will depend on projections of existing histograms. Note that if you instead want to extract values (eg. time
series of mean), use the [trending framework](#trending) instead.

To create new histograms, implement the function `createAdditional(SYS)Histograms(subsystem, **kwargs)`
and add a new `histogramContainer` to the `subsystemContainer.histsAvailable` list. When specifying the
histogram container, the histogram it will be projected from must be specified! Then, the projection function
must be appended to the list `histogramContainer.projectionFunctionsToApply`. Note that additional processing
functions should be [added later](#find-processing-functions). Remember that the histogram to project is
cloned, and therefore the user does not need to reset the axes ranges.

For more implementation details, see the example below. Note that for an optimal workflow, the name of the
projected histogram should be selected such that it will be included in a histogram group when they are
defined later on.

#### Example Implementation

```python
def createAdditionalSYSHistograms(subsystem):
    """ Create new histograms by defining new histogram containers and their projection functions.

    New histogram containers for the given subsystem should be created here. The projection function which
    will be used to project from an existing histogram should also be assigned here. The actual histograms
    will be created later when the projection function is executed.

    Here, we will define just one new histogram, which is created via a projection from just one histogram.

    Args:
        subsystem (subsystemContainer): Subsystem for which the additional histograms are to be created.
    Returns:
        None. Newly created histograms are added to ``subsystemContainer.histsAvailable``.
    """
    # Define the additional histogram
    histName = "projectedHist"
    # Select the histogram for which it will be projected.
    # The histogram(s) will be made available inside of the projection function via the histogram container.
    histToProjectFrom = ["histToProjectFrom"]
    histCont = processingClasses.histogramContainer(histName = histName, histList = histToProjectFrom)
    # Add projection function
    histCont.projectionFunctionsToApply(projectionFunction)
    # Store the additional histogram
    subsystem.histsAvailable[histName] = histCont

def projectionFunction(subsystem, hist, processingOptions, **kwargs):
    """ Perform the actual projection to create a new histogram.

    This function should make any necessary axes restrictions or other adjustments relevant
    for the projection. One it is fully prepared, the projected itself should be performed.
    The histogram from which the new hist should be projected is available inside of the
    passed ``histogramContainer`` and thus can be accessed via ``hist.hist``. Note that the
    properties of the passed ``histogramContainer`` correspond to the hist created when defining
    the new histograms, not to the histogram available via ``hist.hist``.

    Args:
        subsystem (subsystemContainer): Subsystem which contains the projected histogram.
        hist (histogramContainer): Histogram container corresponding to the projected histogram.
            When this function is called, it contains the histogram to project from, so the hist
            to project from can be retrieved via ``hist.hist``.
        processingOptions (dict): Dictionary of processing options for the given subsystem.
        kwargs (dict): Additional possible future arguments.
    Returns:
        ROOT.TH1: The projected histogram
    """
    # Example of restricting the range of the histogram projection.
    hist.hist.GetXaxis().SetRangeUser(0, 2)
    # Assigns the project the expected histogram name from the histogram container.
    proj = hist.hist.ProjectionX(hist.histName)
    # Return the projected histogram to ensure that it is saved for later processing.
    return proj
```

### Histogram Stacks

At times, it is desirable to display sets of histograms on top of each other. For example, comparison between
two spectra is easier when they are superimposed. When creating the stacks, we will add a histogram container
that corresponds to the stacked objects, and then we will note that the individual histograms should not be
displayed separately (unless that is also desired).

To achieve this, the `create(SYS)HistogramStacks(subsystem, **kwargs)` function is expected to iterate over
the `subsystemConatiner.histsInFile` dictionary. Histograms which don't need to be stacked should be stored
immediately in the `subsystemContainer.histsAvailable` dictionary use the same key under which it was stored
in the `histsInFile` dictionary. In the most trivial case where all histograms would be kept and none would be
stacked, we could have the following trivial piece of code (note that in such a case, we should just leave out
the function entirely. This function will be performed automatically):

```python
# Don't actually do this!!
for histName in subsystem.histsInFile:
    # Just add if we don't want need to stack
    subsystem.histsAvailable[histName] = subsystem.histsInFile[histName]
```

For a less trivial example where we actually create a histogram stack, we can consider the case of the case
where we would want stack two histograms, `spectraA` and `spectraB`.  To do so, we would first need to add a
new `histogramContainer` for the stacked spectra, inform the histogram container to stack the spectra via the
`histList` argument, and then we would want to skip `spectraA` and `spectraB`. For a full example of how this
would be performed, see the example implementation below.

#### Example Implementation

```python
def createSYSHistogramStacks(subsystem):
    """ Create histogram stacks from the existing histograms in the SYS subsystem.

    Here we will stack two spectra histograms onto a single canvas so we can display them together.
    This can be particularly useful for comparing similar spectra. Note that although this doesn't
    necessarily have to be the case, we decided for this function to assume that histograms will
    only be assigned to one stack.

    Note:
        This function is responsible for moving histogram containers from ``subsystem.histsInFile``
        to ``subsystem.histsAvailable``.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
    Returns:
        None. However, see the note above for the side effects.
    """
    # Define and store the stacked spectra.
    # Name of the stacked spectra histogram stack
    histName = "stackedSpectra"
    # The stacked histogram container must be aware of the names of the histograms which will be stacked
    histsToStack = ["spectraA", "spectraB"]
    stackedSpectraCont = processingClasses.histogramContainer(histName = histName, histList = histsToStack)
    # Store out stacked `histogramContainer`.
    subsystem.histsAvailable[histName] = stackedSpectraCont

    # Now move all of the rest of the histograms from `histsInFile` to `histsAvailable`,
    # except for the individual spectra, which we will only display in the stack.
    for histName in subsystem.histsInFile:
        # Skip the spectra that will be stacked
        if histName in histsToStack:
            continue

        # Add all other histograms
        subsystem.histsAvailable[histName] = subsystem.histsInFile[histName]
```

For a full example, see `overwatch.processing.detectors.EMC.createEMCHistogramStacks`.

### General Histogram Processing Options

There are a number of general options that could apply to all or a large subset of histograms in a subsystem.
Perhaps they all contain a prefix that should be hidden. Perhaps all `TH2` histograms should have `colz`
applied. Perhaps you want to set arbitrary properties that can be influence processing later. All such
functionality can be achieved through setting the general subsystem properties, which are set in
`set(SYS)HistogramOptions(subsystem, **kwargs)`.

To modify all (or a subset of) histogram properties, iterate over all histograms in
`subsystemContainer.histsAvailable`. Although the histogram containers that are returned will not yet contain
the actual histograms or canvases to draw, options such as `histogramContainer.prettyName` (the display name
in the webApp), or `histogramContainer.drawOptions` (which will be passed to the draw function) can still be
set.

The `subsystemContainer.processingOptions` dictionary allows arbitrary options and values related to a
subsystem to be stored. These options can then be later retrieved when processing individual histogram. For
example, the desired to scale (or not scale) every histogram in the subsystem by the number of events could be
noted. Later, your processing function could retrieve that value and perform the proper scaling.

#### Example Implementation

```python
def setSYSHistogramOptions(subsystem):
    """ Set general SYS histogram options.

    In particular, these options should apply to all histograms, or at least a broad selection
    of them. The list of histograms are accessed through the ``histsAvailable`` field of the
    ``subsystemContainer``. Canvas options and additional histogram specific options must be
    set later because the canvas and underlying histograms are not yet available.

    Note:
        The underlying hists and canvases are not yet available for this function. Only fields
        available in the ``histogramContainer`` should be used!

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
    Returns:
        None. Histogram groups are stored in appropriate field of the ``subsystemContainer``.
    """
    # Set histogram specific options
    for hist in subsystem.histsAvailable.values():
        # Set the histogram pretty names
        hist.prettyName = hist.histName.title()

        # Set `colz` for any TH2 hists
        if hist.histType.InheritsFrom(TH2.Class()):
            hist.drawOptions += " colz"

    # Set general processing options
    # Set the subsystem wide preference that we would like for hists to be scaled by the number of events.
    # This option can then be used in the processing functions to decide whether to scale the histogram
    # which is being processed. This is _not_ performed automatically.
    # NOTE: This assumes that the number of events is available in the SYS subsystem.
    subsystem.processingOptions["scaleHists"] = True
```

For a full example, see `overwatch.processing.detectors.EMC.setEMCHistogramOptions`.

### Histogram Groups

Histogram groups are related histograms which should be displayed together. For example, this may be
histograms all related to one class of triggers. A histogram group, which is created via
`processingClasses.histogramGroupContainer(title, selector)`, is defined by a title, which will be a displayed
to the user, and a selector, which is a string that matches some subset (or full) histogram name(s).

These groups should be defined in `create(SYS)HistogramGroups(subsystem, **kwargs)`. The groups are stored as
a list in a `subsystemContainer`, which is accessible through `subsystemContainer.histGroups`. The order in
which these groups are appended determines the priority of the selector. If a histogram could match into two
groups, it will be stored in the group which is nearest to the front of the list.

When defining histogram groups for a subsystem, it is recommended to have a catch all group at the end of the
list to ensure that all histograms will be displayed. This also gives additional future proofing in the case
that new classes of histograms are added to a particular subsystem. It is generally recommended to aim for
less than 6 histograms in a group to ensure reasonable performance when loading an entire group over a slower
internet connection through the webApp.

To determine the available histograms for a particular subsystem, it is best to simply retrieve a file for
that subsystem and look at the histograms available with your favorite method, such as a `TBrowser`. All
histograms available in that file will be available for processing.

Note that an empty histogram group will not be displayed in the webApp. This can be beneficial if different
histograms are available at different times - for example, if a histogram that was previously available is
not being sent anymore, it is not necessary to modify the histogram group configuration.

#### Example Implementation

```python
def createSYSHistogramGroups(subsystem):
    """ Create histogram groups for the SYS subsystem.

    This functions sorts the histograms into categories for better presentation based
    on their names. The names are determined by those specified for each hist in the
    subsystem component on the HLT. Assignments are made by the looking for substrings
    specified in the hist groups in the hist names. Note that each histogram will be
    categorized once, so the first entry will take all histograms which match. Thus,
    histograms should be ordered in such that the most inclusive are specified last.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
    Returns:
        None. Histogram groups are stored in ``histGroups`` list of the ``subsystemContainer``.
    """
    # Trigger related hists
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("Triggers in SYS", "trigger"))
    # Background related hists
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("Background in SYS", "BKG"))
    # Other Example hists
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("Other SYS", "SYS"))

    # Catch all of the other hists if we have a dedicated receiver.
    # NOTE: We only want to do this if we are using a subsystem that actually has a file from a
    #       dedicated receiver. Otherwise, you end up with lots of irrelevant histograms.
    if subsystem.subsystem == subsystem.fileLocationSubsystem:
        subsystem.histGroups.append(processingClasses.histogramGroupContainer("Non EMC", ""))
```

### Find Processing Functions

To customize how each histogram is processed and displayed, subsystem defined functions can be applied to each
histogram each time it is processed. The content of these functions is entirely up to the subsystem developer.
To apply these functions, a reference to each function that is to be executed is stored in the corresponding
histogram container. That function will automatically be called when the histogram is processed.

The relationship between which functions belong to which histogram should be defined in
`findFunctionsFor(SYS)Histogram(subsystem, hist, **kwargs)`. In this function, the histogram name
should be checked to determine which subsystem specific functions should be applied. Each function is stored
by appending it to the `histogramContainer.functionsToApply` list. Note that these functions will be executed
in the order which they are added.

Each function will all be called with the signature `(subsystemContainer, histogramContainer,
processingOptions, **kwargs)`, where the `subsystemContainer` corresponds to the current subsystem, the
`histogramContainer` corresponds to the current histogram being processed, and the `processingOptions`
correspond to the processing options you set in the [general options](#general-histogram-processing-options),
or in the special case of reprocessing, a set of customized options. Note that including `**kwargs` in
the function signature is important for forward compatibility.

#### Adding new histograms

If new histograms are to be created during these functions, they must be stored to be displayed. Here there
are two options: the original histogram does not need to be kept, or the original histogram needs to be kept.

In the case of the original histogram not being needed, the approach is straightforward: simply replace the
existing histogram in the current `histogramContainer` with the new histogram. This new histogram will be then
be printed in the place of the existing histogram. Please note that if this could cause problems if additional
functions rely on the histogram.

#### Example Implementation

```python
# Plug-in function
def findFunctionsForSYSHistogram(subsystem, hist, **kwargs):
    """ Find processing functions for EMC histograms based on their names.

    This plug-in function steers the histograms to the right set of processing functions. These functions
    will then be executed later when the histograms are actually processed. This function only executes
    when the subsystem is created at the start of each new run. By doing so, we can minimize inefficient
    string comparison each time we process a file in the same run.

    Note:
        The histogram underlying the ``histogramContainer`` which is passed in is not yet available
        for this function. Only information which is stored directly in ``histogramContainer`` fields
        should be used when classifying them and assigning functions.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The hist is modified.
    """
    # General SYS Options
    hist.functionsToApply.append(generalOptions)

    if "trigger" in hist.histName:
        hist.functionsToApply.append(triggerThreshold)

# Two example processing functions are below for illustrative purposes
def generalOptions(subsystem, hist, processingOptions, **kwargs):
    """ General SYS histogram options.

    The underlying histogram and canvas are available, so this function can configure both of those objects.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The current canvas is modified.
    """
    # For example, set the z-axis to display as a log.
    hist.canvas.SetLogz(True)

def triggerThreshold(subsystem, hist, processingOptions, **kwargs)
    """ Histogram processing options for trigger histograms.

    Check for bins above a threshold. The threshold could be set in the processing options.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The current canvas is modified.
    """
    # Check for bins over some threshold.
    # The threshold could be set in the processing options instead of hard coding it here.
    threshold = 1
    binsOverThreshold = []
    for iBin in range(1, hist.hist.GetXaxis().GetNbins()+1):
        if hist.hist.GetBinContent(iBin) > threshold:
            binsOverThreshold.append(iBin)
    # Store the output for display in the web app
    hist.information["Bins over threshold"] = binsOverThreshold
```

For a full example of how to determine the functions to apply to particular histograms, see
`overwatch.processing.detectors.EMC.findFunctionsForEMCHistogram`. For a full example of a processing
function, see `overwatch.processing.detectors.EMC.generalOptionsRequiringUnderlyingObjects`.

## Trending 

The trending framework is based on a thin wrapper around the framework being implemented for the ALICE O2
project. This allows the development and investigation of the trending framework while still in Run 2.
Additionally, all functionality should be implemented in such a manner so as to facilitate easy porting from
Overwatch to O2.

### Trending objects

Trending is implemented through custom objects which perform the trending action and store the result. These
objects should be implemented in each subsystem file and should inherit from `processingClasses.trendingObject`.
In particular, they should implement a `fill(hist)` method which takes the histogram, extract the value and error,
and then calls the base class `fill(value, error)` method to fill the trending histogram at the time stamp of
the current file. The `fill()` function in the base class will store the value in a `numpy` array, which can
later be used to construct a `ROOT.TGraph` or `ROOT.TH1` to display the trended values.

For an example, see `proccessing.detectors.TPC.TPCTrendingObjectMean`.

### Implement Trending in a Subsystem

#### Define trending objects

Trending objects are defined via the function `defineSYSTrendingObjects(trending, **kwargs)`, where the
argument `trending` can be treated as a dictionary. The purpose of this function is to name and define
[trending objects](#trending-objects), as well as specify the objects (histograms) that the trending object is
supposed to be used with. For example, a trending object could extract the mean from a histogram, and then
that extracted value would be trended. The trended object should be added to the dictionary with a descriptive
key, such as the object name.

Once defined, the `fill(...)` function will be called automatically any time the histogram is being processed,
similar to processing functions.

For the trended values to be displayed, a `ROOT.TGraph` or `ROOT.TH1` must be defined, and the trended values
copied in. As a default option, `trendingObject.retrieveHistogram()` will automatically define a `TGraph`
based on the number of entries specified during object construction. It can be overridden by defining an
object to be stored in `histContainer.hist` before calling the base class `retrieveHistogram()`.

For an example, see `processing.detectors.TPC.defineTPCTrendingObjects`.

#### Displaying Trending Objects

Trending objects are available under the "trending" section of the webApp. They are sorted by detector
subsystem.

During processing, trending objects are treated the same as histograms in terms of processing. Consequently,
there are similar opportunities for processing functions, options, etc. The exposure of such settings in a
framework is under construction.

# Available histograms

This list can by looking at the histograms that are available in the test data. As of 9 July 2018 in Run
289210, these include:

- EMC:

    ```none
    # 2D histograms with respect to row, column of EMCal
    # Integrated trigger amplitues
    KEY: TH2F     EMCTRQA_histAmpEdgePosEMCGAHOffline;1   Integrated amplitude EMCGAH patch Offline
    KEY: TH2F     EMCTRQA_histAmpEdgePosEMCGAHOnline;1    Integrated amplitude EMCGAH patch Online
    KEY: TH2F     EMCTRQA_histAmpEdgePosEMCGAHRecalc;1    Integrated amplitude EMCGAH patch Recalc
    KEY: TH2F     EMCTRQA_histAmpEdgePosEMCGALOnline;1    Integrated amplitude EMCGAL patch Online
    KEY: TH2F     EMCTRQA_histAmpEdgePosEMCJEHOffline;1   Integrated amplitude EMCJEH patch Offline
    KEY: TH2F     EMCTRQA_histAmpEdgePosEMCJEHOnline;1    Integrated amplitude EMCJEH patch Online
    KEY: TH2F     EMCTRQA_histAmpEdgePosEMCJEHRecalc;1    Integrated amplitude EMCJEH patch Recalc
    KEY: TH2F     EMCTRQA_histAmpEdgePosEMCJELOnline;1    Integrated amplitude EMCJEL patch Online
    KEY: TH2F     EMCTRQA_histAmpEdgePosEMCL0Offline;1    Integrated amplitude EMCL0 patch Offline
    KEY: TH2F     EMCTRQA_histAmpEdgePosEMCL0Online;1     Integrated amplitude EMCL0 patch Online
    KEY: TH2F     EMCTRQA_histAmpEdgePosEMCL0Recalc;1     Integrated amplitude EMCL0 patch Recalc
    KEY: TH1F     EMCTRQA_histEvents;1    				  Number of events
    # Trigger patch max edge value 
    KEY: TH2F     EMCTRQA_histMaxEdgePosEMCGAHOffline;1   Edge Position Max EMCGAH patch Offline
    KEY: TH2F     EMCTRQA_histMaxEdgePosEMCGAHOnline;1    Edge Position Max EMCGAH patch Online
    KEY: TH2F     EMCTRQA_histMaxEdgePosEMCGAHRecalc;1    Edge Position Max EMCGAH patch Recalc
    KEY: TH2F     EMCTRQA_histMaxEdgePosEMCGALOnline;1    Edge Position Max EMCGAL patch Online
    KEY: TH2F     EMCTRQA_histMaxEdgePosEMCJEHOffline;1   Edge Position Max EMCJEH patch Offline
    KEY: TH2F     EMCTRQA_histMaxEdgePosEMCJEHOnline;1    Edge Position Max EMCJEH patch Online
    KEY: TH2F     EMCTRQA_histMaxEdgePosEMCJEHRecalc;1    Edge Position Max EMCJEH patch Recalc
    KEY: TH2F     EMCTRQA_histMaxEdgePosEMCJELOnline;1    Edge Position Max EMCJEL patch Online
    KEY: TH2F     EMCTRQA_histMaxEdgePosEMCL0Offline;1    Edge Position Max EMCL0 patch Offline
    KEY: TH2F     EMCTRQA_histMaxEdgePosEMCL0Online;1     Edge Position Max EMCL0 patch Online
    KEY: TH2F     EMCTRQA_histMaxEdgePosEMCL0Recalc;1     Edge Position Max EMCL0 patch Recalc
    # L0 and L1 trigger information
    KEY: TH1F     EMCTRQA_histFastORL0;1  				  L0 entires vs FastOR number
    KEY: TH2F     EMCTRQA_histFastORL0Amp;1       		  L0 amplitudes vs position
    KEY: TH1F     EMCTRQA_histFastORL0LargeAmp;1  		  L0 (amp>400) vs FastOR number
    KEY: TH2F     EMCTRQA_histFastORL0Time;1      		  L0 trigger time vs FastOR number
    KEY: TH1F     EMCTRQA_histFastORL1;1  				  L1 entries vs FastOR number
    KEY: TH2F     EMCTRQA_histFastORL1Amp;1       		  L1 amplitudes
    KEY: TH1F     EMCTRQA_histFastORL1LargeAmp;1  		  L1 (amp>400)
    ```

- HLT:

    ```none
    KEY: TH1D     fHistClusterChargeMax;1         TPC Cluster ChargeMax
    KEY: TH1D     fHistClusterChargeTot;1         TPC Cluster ChargeTotal
    KEY: TH2F     fHistHLTInSize_HLTOutSize;1     HLT Out Size vs HLT In Size
    KEY: TH2F     fHistHLTSize_HLTInOutRatio;1    HLT Out/In Size Ratio vs HLT Input Size
    KEY: TH2F     fHistSDDclusters_SDDrawSize;1   SDD clusters vs SDD raw size
    KEY: TH2F     fHistSPDclusters_SDDclusters;1  SDD clusters vs SPD clusters
    KEY: TH2F     fHistSPDclusters_SPDrawSize;1   SPD clusters vs SPD raw size
    KEY: TH2F     fHistSPDclusters_SSDclusters;1  SSD clusters vs SPD clusters
    KEY: TH2F     fHistSSDclusters_SDDclusters;1  SDD clusters vs SSD clusters
    KEY: TH2F     fHistSSDclusters_SSDrawSize;1   SSD clusters vs SSD raw size
    KEY: TH2F     fHistTPCAallClustersRowPhi;1    TPCA clusters all, raw cluster coordinates
    KEY: TH2F     fHistTPCAattachedClustersRowPhi;1       TPCA clusters attached to tracks, raw cluster coordinates
    KEY: TH2F     fHistTPCCallClustersRowPhi;1    TPCC clusters all, raw cluster coordinates
    KEY: TH2F     fHistTPCCattachedClustersRowPhi;1       TPCC clusters attached to tracks, raw cluster coordinates
    KEY: TH1D     fHistTPCClusterFlags;1        TPC Cluster Flags
    KEY: TH2F     fHistTPCClusterSize_TPCCompressedSize;1 TPC compressed size vs TPC HWCF Size
    KEY: TH2F     fHistTPCHLTclusters_TPCCompressionRatio;1       Huffman compression ratio vs TPC HLT clusters
    KEY: TH2F     fHistTPCHLTclusters_TPCFullCompressionRatio;1   Full compression ratio vs TPC HLT clusters
    KEY: TH2F     fHistTPCHLTclusters_TPCSplitClusterRatioPad;1   TPC Split Cluster ratio pad vs TPC HLT clusters
    KEY: TH2F     fHistTPCHLTclusters_TPCSplitClusterRatioTime;1  TPC Split Cluster ratio time vs TPC HLT clusters
    KEY: TH2F     fHistTPCRawSize_TPCCompressedSize;1     TPC compressed size vs TPC Raw Size
    KEY: TH1D     fHistTPCTrackPt;1             TPC Track Pt
    KEY: TH2F     fHistTPCdEdxMaxIROC;1         TPC dE/dx v.s. P (qMax, IROC)
    KEY: TH2F     fHistTPCdEdxMaxOROC1;1        TPC dE/dx v.s. P (qMax, OROC1)
    KEY: TH2F     fHistTPCdEdxMaxOROC2;1        TPC dE/dx v.s. P (qMax, OROC2)
    KEY: TH2F     fHistTPCdEdxMaxOROCAll;1      TPC dE/dx v.s. P (qMax, OROC all)
    KEY: TH2F     fHistTPCdEdxMaxTPCAll;1       TPC dE/dx v.s. P (qMax, full TPC)
    KEY: TH2F     fHistTPCdEdxTotIROC;1         TPC dE/dx v.s. P (qTot, IROC)
    KEY: TH2F     fHistTPCdEdxTotOROC1;1        TPC dE/dx v.s. P (qTot, OROC1)
    KEY: TH2F     fHistTPCdEdxTotOROC2;1        TPC dE/dx v.s. P (qTot, OROC2)
    KEY: TH2F     fHistTPCdEdxTotOROCAll;1      TPC dE/dx v.s. P (qTot, OROC all)
    KEY: TH2F     fHistTPCdEdxTotTPCAll;1       TPC dE/dx v.s. P (qTot, full TPC)
    KEY: TH2F     fHistTPCtracks_TPCtracklets;1   TPC Tracks vs TPC Tracklets
    KEY: TH2F     fHistTZERO_ITSSPDVertexZ;1      TZERO interaction time vs ITS vertex z
    KEY: TH2F     fHistVZERO_SPDClusters;1        SPD Clusters vs VZERO Trigger Charge (A+C)
    KEY: TH2F     fHistZNA_VZEROTrigChargeA;1     ZNA vs. VZERO Trigger Charge A
    KEY: TH2F     fHistZNC_VZEROTrigChargeC;1     ZNC vs. VZERO Trigger Charge C
    KEY: TH2F     fHistZNT_VZEROTrigChargeT;1     ZN (A+C) vs. VZERO Trigger Charge (A+C)
    ```

- TPC (less straightforward to extract):

    ```none
    KEY: TH3D     TPCQA/h_tpc_track_all_recvertex_0_5_7;1   Number of clusters
    KEY: TH3D     TPCQA/h_tpc_track_all_recvertex_2_5_7;1   Number of found/findable clusters
    KEY: TH3D     TPCQA/h_tpc_track_all_recvertex_3_5_7;1   DCA vs r inclusive
    KEY: TH3D     TPCQA/h_tpc_track_all_recvertex_4_5_7;1   DCA vs z inclusive
    KEY: TH3D     TPCQA/h_tpc_track_pos_recvertex_3_5_6;1   DCA vs r for positive tracks
    KEY: TH3D     TPCQA/h_tpc_track_neg_recvertex_3_5_6;1   DCA vs r for negative tracks
    KEY: TH3D     TPCQA/h_tpc_track_neg_recvertex_4_5_6;1   DCA vs z for positive tracks
    KEY: TH3D     TPCQA/h_tpc_track_neg_recvertex_4_5_6;1   DCA vs z for negative tracks
    KEY: TH1D     TPCQA/h_tpc_event_recvertex_4;1           Postive track mutliplicity
    KEY: TH1D     TPCQA/h_tpc_event_recvertex_5;1           Negative track multiplicity
    KEY: TH1D     TPCQA/h_tpc_event_recvertex_0;1           vertex x position
    KEY: TH1D     TPCQA/h_tpc_event_recvertex_1;1           vertex y position
    KEY: TH1D     TPCQA/h_tpc_event_recvertex_2;1           vertex z position
    ```

