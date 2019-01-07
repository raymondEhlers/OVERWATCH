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
            databaseLocation=databaseParameters["databaseLocation"])
