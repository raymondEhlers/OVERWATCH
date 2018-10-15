
# Trending Manager

TrendingManager is responsible for keeping all Trending Objects in one place.
In constructor, the manager takes database and all parameters.

Before processing, function 'createTrendingObjects' must be called.
It imports 'pluginManager' module and for each subsystem tries to get information
about trending object (by invoking 'getTrendingObjectInfo' function from SYS.py).
Then creates TrendingObject indicated in info.

When the ROOT hist is processed, the manger is notified about new histogram.
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
- initializeTrendingArray() -> \[T] ---> Returns container that stores trended values
- extractTrendValue(hist: histogramContainer) -> None --->
Computes trend value from histogramContainer and place in appropriate place
- retrieveHist() -> TObject ---> Creates root object from trended values

# General Diagram
![Diagram](./doc/Trending.png)

# Sequence Diagram
![Sequence](./doc/Seq.png)
