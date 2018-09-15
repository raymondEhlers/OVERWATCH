# Testing Overwatch

Tests are implemented using `pytest`. As of July 2018, they don't have extensive coverage, but should be
expanded upon when making code improvements. For running tests, you should run them from the `tests` folder!
Otherwise, if you run from, for example, the base folder, your `config.yaml` could interfere with testing
against reference values!

To execute the testing, I tend to use something like:

```bash
$ pytest -l --cov=overwatch --cov-report html --cov-branch . --durations=5
```

This assumes you are running from the `tests` folder (as suggested above) and will be report on which tests
are the slowest as well as provide a coverage report for (in this case) the entire `overwatch` module. The
branch coverage is particularly useful to help avoid missing coverage over control flow.

You can skip slow tests (those related to intentionally failing copy tests) with the additional argument `-m
"not slow"`.

## Configuration system reference YAML files

These configuration reference files depend on the default configuration values. Thus, if you add, remove, or
modify any default configuration values in any of the modules, it will cause these tests to fail. To resolve
this issue, delete `overwatch/tests/base/configTestFiles/*.yaml` and run `test_config.py` **twice**. If it
still fails, then the tests have actually failed. Check that you haven't introduced a bug or that you didn't
pick up your local `config.yaml` when creating the reference files.
