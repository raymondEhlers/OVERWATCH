
# Trending Manager

TrendingManager is responsible for keeping all Trending Objects in one place.
In constructor, the manager takes database and all parameters.

Before processing, function 'createTrendingObjects' must be called.
It imports 'qa' module and for each subsystem tries to get information
about trending object (by invoking 'getSYSTrendingObjectInfo' function from SYS.py).
Then creates TrendingObject indicated in info.

When root hist is available, the manger is noticed about new histogram.
It invokes all TrendingObjects that wanted this specific histogram.

# Trending Info
TrendingInfo is a simple object containing:
- name of trending
- description
- histograms that are used while trend processing
- TrendingObject class responsible for computing trends

# Trending Object
TrendingObject is an abstract class responsible for adding measurements.

It contains methods to implement by subclass:
- initStartValue() -> \[T] ---> Returns container that stores trended values
- getMeasurement(hist: histogramContainer) -> T ---> Computes trend value from histogramContainer
- retrieveHist() -> TObject ---> Creates root object from trended values

# General Diagram
![Diagram](./doc/Trending.png)

# Sequence Diagram
![Sequence](./doc/Seq.png)
