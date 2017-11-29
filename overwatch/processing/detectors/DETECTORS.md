# Detector Plug-ins

NOTE: Please ignore the information in `__init__.py` until it is updated further.

The processing provides a number of opportunities to plug-in detector specific options. These functions will
automatically be called if the subsystem is enabled. Note that it is fine if a function does not exist -
execution will proceed without that part of the functionality.

## Available Plug in Functions

The example functions below are ordered by the order that they are called. Replace the subsystem `EMC` by the desired subsystem.

- Create groups of histograms: `createEMCHistogramGroups(subsystemContainer)`.
- Create stack of histograms: `createEMCHistogramStacks(subsystemContainer)`.
- Set processing options or apply settings that apply to the entire subsystem: `setEMCHistogramOptions(subsystemContainer)`.
- Find functions that apply to particular histograms for a given subsystem: `findFunctionsForEMCHistogram(subsystemContainer, histogramContainer)`
    - This function is most important. It is how you map particular histograms to particular processing functions.
