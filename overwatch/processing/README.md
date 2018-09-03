# Processing package details

Note: The code is _not_ entirely object oriented due to the evolution of the package. It is predominately data
structures with functions. In an ideal world, this would be refactored further into a fully object oriented
design.

Below is a collection of information relevant to the processing package, presented in no particular order.

## File information

### File types

We refer to a few different types of ROOT files used in Overwatch:

- "Standard file" or "Receiver file": A file from the subsystems' receiver which was received from the HLT and
  stored. This is the main Overwatch data source.
- "Combined file": The file which stores the most recent data for a particular run and subsystem. This is
  derived from standard files.
- "Time slice": A combined file which is composed of data from a particular time range in the run. It may also
  be reprocessed with a non-default set of parameters.

### Received file modes

The HLT receiver can operate in two possible file modes: "cumulative mode" or "reset mode". Since this is
already explain in detail in `mergeFiles.merge(...)`, we will just quote the description (with minor edits for
clarity):

> The merge is only performed if we have received new files in the specified run. The details of the merge are
> determined by the `cumuluativeMode` setting. This setting, which is determined by the options sent in the data
> request sent to the HLT by the ZMQ receiver, denotes whether the data that we received are reset each time the
> data is sent. If the data is being reset, then the files are not cumulative, and therefore `cumulativeMode`
> should be set to `False`.
>
> Note that although Overwatch supports both modes, we tend to operate in cumulative mode because resetting
> the objects would interfere with other subscribes to the HLT data. For example, if both Overwatch and
> another subscriber were set to request data with resets every minute and were offset by 30 seconds, they
> would both only receive approximately half the data! Thus, it's preferred to operate in cumulative mode.

### File and directory layout

Overwatch relies the files of each run and subsystem being laid out in a particular structure. Using run
123456 as an illustrative example, the file layout is as follows:

```none
Run123456/
    runInfo.yaml
    EMC/
        EMChists.2015_11_24_18_05_03.root
        ...
        EMChists.2015_11_24_18_07_23.root
        hists.combined.1.1448388323.root
        img/
            EMCTRQA_histDCalMedianVsDCalMaxEMCREBKGOffline.png
            EMCTRQA_histDCalMedianVsDCalMaxEMCREGAOffline.png
            EMCTRQA_histDCalMedianVsDCalMaxEMCREJEOffline.png
            ...
        json/
            EMCTRQA_histDCalMedianVsDCalMaxEMCREBKGOffline.json
            EMCTRQA_histDCalMedianVsDCalMaxEMCREGAOffline.json
            EMCTRQA_histDCalMedianVsDCalMaxEMCREJEOffline.json
            ...
    HLT/
        HLThists.2015_11_24_18_05_04.root
        ...
        HLThists.2015_11_24_18_07_26.root
        hists.combined.1.1471503723.root
        img/
            fHistClusterChargeMax.png
            fHistClusterChargeTot.png
            fHistHLTInSize_HLTOutSize.png
            ...
        json/
            fHistClusterChargeMax.json
            fHistClusterChargeTot.json
            fHistHLTInSize_HLTOutSize.json
            ...
    ...
```

With this file structure, it is possible to recreate an entire run just from the information stored in this
directory structure and the files within.

### Subsystem and file location subsystem

There are two possible sources of data for a subsystems within a particular run. In the standard approach, the
subsystem has a dedicated receiver which stores data receiver from the HLT component corresponding to that
subsystem.

However, if a subsystem doesn't have a dedicated receiver (either in general, or just during a particular
run), it can still perform processing if it also produces information through the main HLT component. For
example, there are histograms relevant to both the TPC and V0 which are produced by the main HLT component. In
this case, the subsystem can use the main HLT component data as an alternative data source. In particular, the
`fileLocationSubsystem` is specified to by the HLT. When we go to process the histograms for this particular
subsystem, we process files from the main HLT component and store our output within that subsystems image and
`json` folders. The subsystem can be though of as a thin wrapper around a different data source. The benefit
to such an approach is that it allows subsystems to customize processing of their own subsystem specific
files, even if they haven't built up enough infrastructure to justify a dedicated HLT component (and
consequently, a receiver).

## Zope Object Database (ZODB) and their object types

All information in Overwatch is stored in the ZODB object database. This database enables extremely simple
storage of complicated dictionary structure and objects with little configuration or other boilerplate.
However, this comes at the cost of somewhat unclear documentation. Therefore, we provide a few notes here.

- For list-like objects, use `PersistentList()`
- For dict-like objects, use either `PersistentMapping` or `BTree`. `PersistentMapping` is fine for small
  dictionaries, `BTree` is preferred for anything complicated or if it will contain a large number of values,
  since `BTree` can scale to hold millions of objects.
    - `BTree` can be optimized for limited types of keys or values. In particular, it can optimize for
    integers or objects. However, we usually have strings as keys, so these optimizations are not applicable
    for our use case. We just use `BTree.OOBTree` (although it is encouraged to use one of the optimized types
    if possible!).
- For classes, objects should inherit from `persistent.Persistent`.

Note that although the types above are strongly recommended, it is also possible to store objects persistently
without using such objects. It just takes more effort and care. In addition, schema evolution is possible by
setting default parameters for new class fields, but again, some care must be taken. Further information on ZODB types and persistence is available [here](http://www.zodb.org/en/latest/guide/writing-persistent-objects.html).

### Schema for Overwatch

Overwatch stores information in a few different branches of the top level database object. In general, the
ZODB docs encourage minimizing the number of keys stored in the database root for performance reasons.
Consequently, we store only a few objects at that level.

- Runs information is stored under the "runs" key. The value stored under this key is a `BTree` which stores
  the actual run objects.
- Trending objects are stored under the "trending" key. The value stored under this key is a `BTree` which
  stores the actual trending objects.
- Some configuration which we want to share between various locations is stored under the "config" key. The
  value stored under this key is a `BTree` which stores the actual config values. Note that most of the config
  values are store in the Overwatch config system and those values are not stored in this `BTree`.

## Object creation

Run and subsystem objects are created in two different ways when performing the processing. If there is no
existing runs database, it will be reconstructed at the beginning of processing in `processAllRuns()` based on
the all available information which has been stored on disk. However, more frequently, new object creation is
triggered by receiving new files. When these new files are received, they are moved into the Overwatch file
structure, and then new objects are created in `processMovedFilesIntoRuns()`. Although the general procedure
for creating the objects is approximately the same, there are a number of subtle details that vary between the
two procedures. For further information, look at the `processRuns` package documentation, particular for the
functions listed above.

### Rebuilding is always possible

As a key principle of Overwatch, it should always be possible to rebuild the entire database from scratch.
This means that allow information must be stored on disk, and that all processing must be reproducible.
Although this approach takes a bit of care, it is also quite powerful, as it allows straightforward recovery
from even the most catastrophic crash, as long as at least one backup of the data is available.

## How histograms are distributed in processing

The plug-in architecture is described in great detail in the detector plug-in and trending system README
stored in the `overwatch.processing.detectors` folder. However, one detail worth describing here is regarding
the flow of histograms within members of the `subsystemContainer` during the processing. It proceeds as
follows (each named dictionary is a member of `subsystemContainer`):

- When histograms are first loaded from a file, they are stored in the `histsInFile` dictionary.
- When new histograms are created, they are stored in the `histsAvailable` dictionary. 
- When creating histogram stacks, all histograms of interest need to be moved from `histsInFile` to
  `histsAvailable`. At that point, `histsAvailable` should contain all histograms which we wish to process,
  whether they are from the input file or were created afterwards.
- Lastly, we attempt to classify the available histograms into histogram groups. If a histogram is
  successfully classified, it is stored in the `hists` dictionary. The histograms available in that dictionary
  are the final set of histograms that will actually be processed for that subsystem. This dictionary may not
  be the same as `histsAvailable` because some files contain histograms unrelated to the subsystem. For
  example, the HLT files sometimes contain a few V0 histograms. We may or may want to include such files; for
  a normal subsystem, we probably wouldn't, but in the particular case of the HLT subsystem, we do include
  them because the HLT subsystem is fully inclusive.

In general, this flow of histogram can get rather complicated, so when developing new subsystem specific
processing, it is extremely important to keep close track of which histograms are making it from one step to
the next.

## HLT Modes

There are a number of valid HLT modes. Their meaning is as follows:

| HLT Mode | Explanation         | Action    |
| -------- | ------------------- | --------- |
| A        | HLT wasn't included in data taking | We recieved no data, so nothing to be done (we won't see this data ever). |
| B        | HLT with no compression | Process data as normal (we don't see the difference between compression included or not). |
| C        | HLT with compression | Process data as normal (we don't see the difference between compression included or not). |
| E        | HLT data replay      | Replay of an old run for testing. This data is saved by the receiver, moved to the "ReplayData" directory, and not processed. |
| U        | HLT mode unknown     | The HLT mode was lost somewhere. Process data as normal. The mode is available in the logbook if needed. |


