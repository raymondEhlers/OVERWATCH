# Overwatch Changelog

Changelog based on the [format here](https://keepachangelog.com/en/1.0.0/).

## [1.3.1] - 2 January 2019

### Fixed

- Tagging issue in Travis with multiple python 3 versions. We only wanted to deploy to PyPI for one python
  version, which we arbitrarily select as the python 3.7 version. See: `460aab69`.

## [1.3] - 2 January 2019

### Added

- Python 3.7 docker image. See: `aa97cecf`.
- Alarms subsystem to automatically detect unexpected trending values using user defined criteria. Thanks to
  Artur, Jacek, Pawel! See PR #50.

### Changed

- Updated python 3.6.6 -> 3.6.7. See: `358fed11`.
- Reduced the cloned size of the ROOT repo when building the docker image. See: `5d9a63a7`.
- Bumped ROOT version in the docker images to 6.14/06. See: `627381b2`.

### Fixed

- Fixed typos in the ROOT build script. See: `d967dda3`.
- Blank pkgconfig directory created in the ROOT install. See: `627381b2` and the related [ROOT JIRA
  ticket](https://sft.its.cern.ch/jira/browse/ROOT-9864).
- Allow passing in of database information to the `processAllRuns()` to avoid database locking issue
  when running repeated processing locally (ie without a ZEO/ZODB server). Thanks to Raquel for reporting! See: `7422451a`.

## [1.2.3] - 3 December 2018

### Added

- Additional processing debug information. See: `b35ac4bc`.
- Additional documentation. See: `97d4b884` and `20adf1b1`.

### Fixed

- Fixed Travis not successfully upload docker images during tags. See: `ff4c6f9b`.
- Fix undefined variable in the web app validation. See: `2aed8646`.

## [1.2.2] - 24 November 2018

### Added

- Updated ZMQ receiver to take advantage of improved error checking in `AliZMQhelpers`.
- Minor documentation updates.

### Changed

- Modernized ZMQ receiver to use better coding practices (`Printf` -> `std::cout`, etc).
- Increase certificate proxy validity time to a week. See: `ee64bd29`.

### Fixed

- Attempted fix at memory leak that appears to be associated with `TCanvas` in the processing not being
  garaged collected very quickly. See: `de5945a4`.
- Fully implemented polling timeout in the ZMQ receivers. It was possibly to specify an option, but it wasn't
  actually applied. Now it is. See: `8a3fd937`

## [1.2.1] - 24 November 2018

### Fixed

- Tagging synchronization went wrong with 1.2 between the GitHub release and PyPI. This release fixes it (with
  the rest of the changes of 1.2).

## [1.2] - 12 November 2018

### Added

- Travis CI to run tests, `flake8`, and coverage. Also added `coveralls` to expand of tests coverage
  information. Note that the `flake8` tests run in the Travis CI python 2.7 and 3.6, while the tests run
  inside the docker images.
- Travis CI will build new docker images on each commit, which are known as `rehlers/overwatch:latest-py*`.
  Tagged releases will be available as `rehlers/overwatch:tag-py*`.
- Releases are automatically made on PyPI through Travis CI.
- Added `overwatch.base.dataTransfer` module, which is responsible for transferring data provided by the
  receiver to various Overwatch and EOS sites. This modules is fairly well covered by tests.
- Added webApp, processing, and data transfer monitoring via `sentry`. It hooks into everything (exceptions,
  logs, etc) to help identify and debug issues.
- Added a module for replaying data in `overwatch.base.replay`. Can be used to generically replay processed
  data, moving from one directory to another. For further information, see the README in `overwatch.base`.
- Units tests for timestamp extraction in `overwatch.base.utilities`. See: `62737f10`.
- Added some integration tests for creating runs and subsystems in `overwatch.processing.processRuns`. See:
  `b09e7388`.
- Added rudimentary ZMQ receiver monitoring via the `dataTransfer` module. If no files have been transferred
  in 12 hours, a warning will be emitted. See: `4ea80cf2`.
- Added dedicated direct ZMQ receiver monitor via the `overwatch.receiver.monitor` module. It monitors
  heartbeat information directly from the ZMQ receivers. It is a supplement to the monitoring via the
  `dataTransfer` module. See: `c081a8bf`.
- `repr` and `str` methods to most of the processing classes to aid in debugging. See: `3a544d67` and
  `43657bcf`

### Changed

- Updated `overwatchDeploy` to be class based, and generally far more stable and extensible. It is also
  broadly covered by unit tests.
- Improved webApp status information (and removed obsolete code). See: `c41e5599`.
- Changed all time related functionality to utilize the `pendulum` package. It makes live so much easier! See:
  `8fe66ba3`.

### Fixed

- Creation of run and subsystem containers as new data arrives. Issues were caused by received files arriving
  at different times, which split up the processing. See: `b9230b98`, with fixes in
  `1cfb18c3`, `5e3630a0`, `f7863a64`, and `364543f3`.
- Fixed data transfer to only select on files which end in ".root". ROOT appears to create temporary files
  when writing which are sometimes picked up during data transfer. See: `83412bb7`.
- Execution data is now stored in the `exec` directory. Information includes logs, configurations (except for
  the Overwatch config, which must be in the executing directory), and more sensitive files (SSL, etc). They
  will be used automatically in the docker images and by `supervisor` This was changed to better reflect what
  information was stored. See: `ec64fbd8`.
- Removed the `deploy` directory, along with much of its obsolete contents, which have been replaced by the
  `deploy` module. See: `97357488`.
- Timestamp handling was inconsistent, which caused problems when trying to improve the `isRunOngoing(...)`
  logic. Switch to explicitly handling the time zones with the `pendulum` package, which makes things much
  easier. See: `819fa6a9` for the start, and `8fe66ba3` for the last commit, which resolved all known issues.
- The docker images now run in a less privileged user.
- Ensure that the data replay copies to the proper folder when there is already an existing folder. See:
  `f71afab0`.
- A wide variety of typos.

## [1.1] - 2 September 2018

### Added

- Fully document all classes.
- Update documentation scheme and system (update sphinx, etc)
- Deploy documentation to Read The Docs.
- `CSRF` protection for the web app in preparation for deployment.
- Tests for `overwatch.base.config` and `overwatch.receiver.dqmReceiver`.

### Changed

- Moved `overwatch.processing.qa` -> `overwatch.processing.pluginManager` to better represent how it's purpose
  how evolved.
- Moved update users script to the base package, allowing for it to be installed via `setup.py`. It is
  available via `overwatchUpdateUsers`.
- Modified plugin future arguments to only use `**kwargs`. Using `*args` seems like a dangerous standard.
  Anything that will be added should be added explicitly as a keyword argument.
- Renamed `retrieveHist` -> `retrieveHistogram` in the `trendingObject` for consistency with the histogram
  container. Updated the corresponding classes and documentation.
- Drop `v` prefix in tags. The actual version we use in python doesn't include the `v`, so including it in the
  tag makes versioning a bit more difficult for no benefit.

### Fixed

- Add missing `__init__.py` in the `overwatch.processing.detectors` module.
- Handling of newly received files had a number of small bugs and other mistakes in the relevant data
  structures. All of these were corrected and tested.

### Removed

- Removed `bcryptLogRounds` alias from the YAML config. The default is now drawn for `overwatch.base.config`.
  The value can still by set via YAML, but one should not depend on the alias.
- Removed obsolete code in the webApp related to the former QA system. Mainly removed obsolete `js` and `css`.

## [v1.0] - 11 July 2018

- Initial full release.
