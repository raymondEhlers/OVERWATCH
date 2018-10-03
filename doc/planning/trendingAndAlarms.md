# Trending and Alarms API Planning

These notes are drawn from discussions with Barth during July 2018.

## Trending

- Stateless approach is preferred, at least for the beginning, since it makes reconfiguration and spinning up
  new objects quite easy.
    - External configuration that can be passed to the trending object.
- This same configuration can also configure a manager, which directs the objects which need to be trended.

The general flow would look something like (please excuse the ascii art):

```none
                      |----> trender #1 -|
Data store ---> Manager ---> trender #2 ---> Checkers (alarms) ---> Data store
                      |----> trender #3 -|
                  ^             ^
external config - | - - - - - - |
```

In Overwatch, the manager would be the `trendingContainer`. We would need to move some of the trending
configuration from the detector specific files into some properties of the `trendingContainer`. As it stands
in July 2018, the trending objects are somewhat involved with the routing of the object that it trends, so
this would need to be refactored.

For trending objects, we could then have a trending base object, with inherited classes implementing specific
functionality. Since we are considering a stateless design, all of these objects would serve as interfaces,
with the actual data and configuration passed into each object.

```python
class baseTrendingObject(object):
    """ Basic trending object which defines the trending interface.

    Since it is stateless, we need to find some way to identify it. Perhaps add a single static
    attribute such as a name?

    Although we need to pass around the config, being stateless also means that we can spin up these trending
    objects quite easily.

    Args:
        None
    Attributes:
        None
    """
    def __init__(self):
        pass

    def initialize(self, config):
        """ Initialize any objects needed for trending.

        Is this really necessary if the object is stateless? Perhaps we just return the value
        to the data store.

        Args:
            config (dict): Configuration for the trending object.
        Returns:
            any: Object initialized for the trending.
        """
        # As an example
        return ROOT.TGraph(config["nPoints"])

    def process(self, config, hist):
        """ Process the given object and extract a trended value.

        Args:
            config (dict): Configuration for the trending object.
            hist (ROOT.TObject or histogramContainer or MonitorObject): Object to be trended.
        Return:
            int or float: Trended value. Or perhaps this can be additional types? Str?
                tuple? Perhaps it should also include the time stamp?
        """
        return hist.GetMean()

    def present(self):
        """ Modify the presentation of the trended object.

        For example, we could set the canvas to be displayed as linear-log.

        Instead of configuring the ROOT canvas, it may be better to treat the presentation in
        the web interface.

        Args:
            config (dict): Configuration for the trending object.
            hist (ROOT.TObject or histogramContainer or MonitorObject): Object to be trended.
            canvas (ROOT.TCanvas): Canvas where the object has been drawn.
        Returns:
            ROOT.TCanvaS: Modified canvas.
        """
        pass

    def cleanup(self):
        """ Cleanup any objects that were created.

        Not necessary if we remove the initialize step.

        Args:
            None.
        Returns:
            None.
        """
        pass
```

## Alarms

- We can have a serious of alarms that are checked per object (or per subsystem, etc).
- Stateless approach is preferred, at least for the beginning.
    - This may be less advantageous here, as the alarm may need the previous trended values as well as the
      configuration.

```python
def exampleAlarm(hist, canvas, config, previousValues):
    """ Suggested arguments and returns for a stateless alarm function.

    Arguments below are only suggestions. Does not address how the alarm should register
    for checking a particular histogram.

    Args:
        hist (ROOT.TObject or histogramContainer or MonitorObject): Object to be checked.
        canvas (ROOT.TCanvas): Canvas on which the histogram is drawn. Mostly likely, the
            hist should already be drawn.
        config (dict): Configuration for the alarm function.
        previousValues (numpy.ndarray): Array of the previous values for comparison.
    Returns:
        tuple: (flag, message), where flag (str?) is the quality of the hist, and message (str)
            is the message corresponding to the flag. Or the flag could be omitted?
    """
    pass
```

- Output format and handling:
    - Should contain a quality flag
        - Could also consider the alarm output as `(flag, message)`.
    - Take an OR of the quality flags for the particular object to determine whether an alarm is triggered.
    - This way, the most severe (important) sets the alarm state of the entire object. This avoids missing
      important alarms.
    - Alarms can also draw on the canvas,

NOTE: There are some trending and alarm notes marked by `TODO` in the Overwatch code. They have
suggestion of how to proceed further with these systems.

## Configuration system for trending and alarms

For a smooth transition to O2, we should try to use the O2 configuration system as much as possible. The
system code and documentation is available [here](https://github.com/AliceO2Group/Configuration). Since
Overwatch already uses a YAML based configuration system, perhaps it is easiest to embed the O2 configuration
into the YAML as a string.

For example YAML (using a config taken from the function `test/testExamples.cxx::TreeExample` in the O2
Configuration repo):

```
# Configuration for "testAlarm"
testAlarm:
    # Can store other options here...
    # o2Config is stored as a string by YAML.
    o2Config: |
        {"equipment_1", Branch
          {
            {"enabled", true},
            {"type", "rorc"s},
            {"serial", 33333},
            {"channel", 0},
            {"stuff", Branch
              {
                {"abc", 123},
                {"xyz", 456}
              }
            }
          }
        },
        {"equipment_2", Branch
          {
            {"enabled", true},
            {"type", "dummy"s},
            {"serial", -1},
            {"channel", 0}
          }
        }
```

Then, we load the value with `o2Config = parameters["testAlarm"]["o2Config"]` and figure out how to parse it.
Perhaps we can just write directly around the configuration system.

Alternatively, we can just implement this in YAML and then write a simple utility to be able write out the O2
configuration when we are ready.
