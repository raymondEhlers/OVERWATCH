
# Database

Database is responsible for storing histogram metadata. This data is used by web application to  

TrendingManager is responsible for keeping all Trending Objects in one place.
In constructor, the manager takes database and all parameters.

Before processing, function 'createTrendingObjects' must be called.
It imports 'pluginManager' module and for each subsystem tries to get information
about trending object (by invoking 'getTrendingObjectInfo' function from SYS.py).
Then creates TrendingObject indicated in info.

When the ROOT hist is processed, the manger is notified about new histogram.
It invokes all TrendingObjects that wanted this specific histogram.

# MongoDB
When working with C++ code it will be impossible to access ZODB, as a result you should use MongoDB instead.

First of all you should have installed MongoDB on your system and have started database service.
## parameters in config.yaml
    
    
    - 
    mongoPort: 27017
    - mongoHost: "0.0.0.0"



# ZODB

To use ZODB you should set `databaseType` value in `congig.yaml` to `zodb`.

## parameters in config.yaml
    - databaseLocation: location of your database in filesystem
You must also specify database location




