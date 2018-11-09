# Base package details

## Configuration system

The Overwatch configuration system is based around hierarchical overridden values stored in YAML configuration
files. Each package within Overwatch has its own YAML file. For each property, the system looks for possible
values in each configuration file. If the multiple configuration files define the property, the further down
the hierarchy overrides the base value. By doing so, the loaded configuration provides just one value per
property (as opposed to combine every value which was defined for the property).

As a concrete example, consider two modules, where module `A` depends on module `B`, and they both define a
property named `x`. For module `A`, `x=5`, while for module `B`, `x=3`. In this case, after all of the
configurations were loaded, the configuration system would provide `5` when property `x` is retrieved.

As of August 2018, the configuration override order is as follows:

1) Current working directory
2) User home directory
3) `overwatch.webApp`
4) `overwatch.processing`
5) `overwatch.receiver`
6) `overwatch.api`
7) `overwatch.base`

where 1 has the highest priority and 7 has the lowest priority. In each folder, the system looks for a file
named `config.yaml`. In addition to the base configuration system, a number of YAML constructor plugins are
also provided to improve the user configuration experience. For example, there is a constructor to facilitate
the joining of paths, in a similar way to `os.path.join`.

For additional technical details regarding the configuration system as well as an exhaustive list of
constructor plug-ins, see the documentation for functions within the `overwatch.base.config` module.

## Additional files

`storageWrapper.py` is an idea for how files could be accessed through `XRootD` instead of needing to preside
on the local disk. This would be particularly useful because we would then be able to take advantage of EOS
directly. However, as of August 2018, this is still very much a work in progress and isn't fully operation.

## Deployment system

To facilitate configuring and launching tasks (particularly in docker containers), Overwatch includes a
configuration and launching module. It is available as `overwatchDeploy`. To operate, it requires a YAML based
config file. All executables inherit from the `executable` class. As of September 2018, it can execute:

- Environment setup
- `autossh` for SSH tunnels.
- `ZODB` for the Overwatch Database
- Overwatch ZMQ receiver
- Overwatch receiver data transfer
- Overwatch DQM receiver
    - Via `uswgi`, `uwsgi` behind `nginx` or directly.
- Overwatch processing
- Overwatch web app
    - Via `uswgi`, `uwsgi` behind `nginx` or directly.

For a comprehensive set of options, see the docstrings of the module, as well as the reference
configuration, `overwatch/base/deployReference.yaml`. Note that all executable are disabled by default,
so one may leave the configuration for all objects in a deployment configuration, and then just enable the
parts that you want for a particular execution. However, it is also important to note that the deploy system
doesn't support default values or overriding parts of the configuration like the Overwatch configuration
system - every option of interest **must** be in the config passed to `overwatchDeploy`.

## Monitoring for errors

It is important to monitor Overwatch for errors and other issues. For the data transfer module, this
monitoring is provided by `sentry`, which hooks into exceptions, logging, and other parts of the app to
automatically provide alerts and information when issues occur.

For successful monitoring, the environment must export the `DSN` as `export SENTRY_DSN_DATA_TRANSFER=<value>`.
The value will be some sort of unique URL. Note that this endpoint is just for Overwatch data transfer (called
`overwatch-datatransfer` on `sentry`). If it is not available, it will look for the general environment
variable `SENTRY_DSN`.

## Data transfer

Data must be moved from the ZMQ and DQM receivers to other Overwatch sites, as well as exported to EOS. All of
these transfers are handled by the data transfer module. It will transfer the data in a robust manner, retry
on failures, and then notifying the admin if the issues continue. For further information on configuration,
see the `dataTransfer` module.

## Data replay

In order to fully test the entire Overwatch processing and visualization chain, as well as test trending
values as they evolve, data must be replayed over some time as if it was actually being received from the
receivers. In order to fully simulate data this arrival, Overwatch provides a `dataReplay` module. This module
will take an existing run directory, and replay all of the files within one by one.

This module can be configured via a number of parameters:

- `dataReplayTimeToSleep`: Time to sleep between each replay execution.
- `dataReplaySourceDirectory`: Select which Run directory will be replayed. This must be the path to the full
  run directory. For example, it may be "data/Run123456". "Run" must be in the directory name. It is null be
  default because we don't want to unexpected begin replaying, which could lead to data loss.
- `dataReplayDestinationDirectory`: Where the data should be replayed to. Usually, this is just the data
  folder, because Overwatch will then process the files from there.
- `dataReplayTempStorageDirectory`: Location where directories and files are temporarily stored when replaying
  a run.
- `dataReplayMaxFilesPerReplay`:  Maximum number of files to move per replay. `nMaxFiles` defaults to one,
  which will ensure that files are transferred one by one, which is the desired behavior if one wants to test
  the evolution of dataset. Such an approach is the best possible simulation of actually receiving data.

This module can also be utilized to generically transform processed Overwatch data to appear as if it hasn't
been processed yet by moving and renaming the underlying `ROOT` files. This is particularly useful if one
wants to transfer processed data via the `dataTransfer` module. Simply set the replay destination directory as
the data transfer input directory, and the data will be transferred as if it was just received from the HLT.

### Common Issues

When replaying data, if you receive an error similar to:

```
  File "/overwatch/overwatch/base/replay.py", line 86, in availableFiles
    name = convertProcessedOverwatchNameToUnprocessed(dirPrefix = root, name = name)
  File "/overwatch/overwatch/base/replay.py", line 45, in convertProcessedOverwatchNameToUnprocessed
    runNumber = int(prefixAndRunDir[runDirLocation:])
ValueError: invalid literal for int() with base 10: 'ta/tempReplayData/testDirectory/input'
```

you should closely check your directory structure. This is likely caused by a root file being located outside
of the standard Overwatch directory structure. For example, a root file in `Run123/.` will cause this issue.
Moving the root files to the proper location should resolve the issue.
