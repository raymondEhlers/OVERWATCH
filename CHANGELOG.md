# Overwatch Changelog

Changelog based on the [format here](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

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

### Changed

- Updated `overwatchDeploy` to be class based, and generally far more stable and extensible. It is also
  broadly covered by unit tests.

### Fixed

- Creation of run and subsystem containers as new data arrives. Issues were caused by received files arriving
  at different times, which split up the processing. See: `b9230b98`.
- Fixed data transfer to only select on files which end in ".root". ROOT appears to create temporary files
  when writing which are sometimes picked up during data transfer. See: `83412bb7`.
- Execution data is now stored in the `exec` directory. Information includes logs, configurations (except for
  the Overwatch config, which must be in the executing directory), and more sensitive files (SSL, etc). They
  will be used automatically in the docker images and by `supervisor` This was changed to better reflect what
  information was stored. See: `ec64fbd8`.
- Removed the `deploy` directory, along with much of its obsolete contents, which have been replaced by the
  `deploy` module. See: `97357488`.
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
