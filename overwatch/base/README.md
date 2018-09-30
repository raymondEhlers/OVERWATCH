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
configuration, `overwatch/base/deployReferenceConfig.yaml`. Note that all executable are disabled by default,
so one may leave the configuration for all objects in a deployment configuration, and then just enable the
parts that you want for a particular execution.

## Monitoring for errors

It is important to monitor Overwatch for errors and other issues. For the data transfer module, this
monitoring is provided by `sentry`, which hooks into exceptions, logging, and other parts of the app to
automatically provide alerts and information when issues occur.

For successful monitoring, the environment must export the `DSN` as `export SENTRY_DSN=<value>`. The value
will be some sort of unique URL. Note that this endpoint is for _all_ Overwatch monitoring, so be certain to
check the traceback to determine the originating source of the issue.
