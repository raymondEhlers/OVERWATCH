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
- Added webApp monitoring via `sentry`. It hooks into everything (exceptions, logs, etc) to help identify and
  debug issues.

### Changed

- Updated `overwatchDeploy` to be class based, and generally far more stable and extensible. It is also
  broadly covered by unit tests.

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
