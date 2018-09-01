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
