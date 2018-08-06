# Testing

Tests are implemented using `pytest`. As of July 2018, they don't have extensive coverage, but should be
expanded upon when making code improvements. For running tests, you should run them from the `tests` folder!
Otherwise, if you run from, for example, the base folder, your `config.yaml` could interfere with testing
against reference values!

To execute the testing, I tend to use something like:

```bash
$ pytest -l --cov=overwatch.base --cov-report html . --durations=5
```

This assumes you are running from the `tests` folder (as suggested above) and will be report on which tests
are the slowest as well as provide a coverage report for (in this case) the `overwatch.base` module. This can
be adapted as desired.
