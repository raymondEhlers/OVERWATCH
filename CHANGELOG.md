# Overwatch Changelog

Changelog based on the [format here](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- Fully document all classes.
- Update documentation scheme.

### Changed

- Moved `overwatch.processing.qa` -> `overwatch.processing.pluginManager` to better represent how it's purpose
  how evolved.
- Moved update users script to the base package, allowing for it to be installed via `setup.py`. It is
  available via `overwatchUpdateUsers`.

### Fixed

- Add missing `__init__.py` in the `overwatch.processing.detectors` module.

### Removed

- Removed `bcryptLogRounds` alias from the YAML config. The default is now drawn for `overwatch.base.config`.
  The value can still by set via YAML, but one should not depend on the alias.

## [v1.0] - 11 July 2018

- Initial full release.
