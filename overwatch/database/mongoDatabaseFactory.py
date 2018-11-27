import pymongo

from overwatch.database.databaseFactory import DatabaseFactory
from overwatch.database.mongoDatabase import MongoDatabase

class DatabaseFactory:
    def __init__(self, databaseName):
        self.databaseName = databaseName

    def getDB(self):
        raise NotImplemented

class MongoDatabaseFactory(DatabaseFactory):
    def __init__(self, databaseName, host, port):
        DatabaseFactory.__init__(self, databaseName)
        self.host = host
        self.port = port

    def getDB(self):
        client = pymongo.MongoClient(
            host=self.host,
            port=self.port)
        db = client[self.databaseName]
        return MongoDatabase(db), client
