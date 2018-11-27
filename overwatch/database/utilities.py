import aenum

from overwatch.base import config
from overwatch.database.mongoDatabaseFactory import MongoDatabaseFactory
from overwatch.database.zodbDatabaseFactory import ZodbDatabaseFactory

(databaseParameters, _) = config.readConfig(config.configurationType.database)


class databaseTypes(aenum.OrderedEnum):
    mongodb = 0
    zodb = 1

def getDatabaseFactory():
    databaseType = databaseParameters["databaseType"]
    if databaseTypes[databaseType] == databaseTypes.mongodb:
        return MongoDatabaseFactory(
            databaseName=databaseParameters["databaseName"],
            host=databaseParameters["mongoHost"],
            port=databaseParameters["mongoPort"])
    if databaseTypes[databaseType] == databaseTypes.zodb:
        return ZodbDatabaseFactory(
            databaseName=databaseParameters["databaseName"],
            databaseLocation=databaseParameters["trendingDatabaseLocation"])

def todict(obj, classkey=None):
    if isinstance(obj, dict):
        data = {}
        for (k, v) in obj.items():
            data[str(k)] = todict(v, classkey)
        return data
    elif hasattr(obj, "_ast"):
        return todict(obj._ast())
    elif hasattr(obj, "__iter__") and not isinstance(obj, str):
        return [todict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = dict([(key, todict(value, classkey))
            for key, value in obj.__dict__.items()
            if not callable(value) and not key.startswith('_')])
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    else:
        return obj