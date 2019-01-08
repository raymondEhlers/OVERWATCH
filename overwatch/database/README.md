
# Database

Database is responsible for storing histogram metadata. 
This data is used by web application to localize histograms in filesystem.

You can specify which database to use by setting value of `databaseType` in config.yaml.
Available databases are MongoDB (`databaseType: mongodb`) and ZODB (`databaseType: zodb`).

# MongoDB
To use MongoDB you should set `databaseType` value in `congig.yaml` to `mongodb`.

When working with C++ code it will be impossible to access ZODB, as a result you should use MongoDB instead.

First of all you should have installed MongoDB on your system and have started database service.
## parameters in config.yaml
    -mongoPort: database service port. For more information see [documentation](https://api.mongodb.com/python/current/api/pymongo/mongo_client.html?highlight=client#pymongo.mongo_client.MongoClient).
    -mongoHost: database service host. For more information see [documentation](https://api.mongodb.com/python/current/api/pymongo/mongo_client.html?highlight=client#pymongo.mongo_client.MongoClient).
    -databaseName: name of database



# ZODB

To use ZODB you should set `databaseType` value in `congig.yaml` to `zodb`.

## parameters in config.yaml
    - databaseLocation: location of your database in a filesystem




