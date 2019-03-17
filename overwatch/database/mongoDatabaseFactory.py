"""
.. code-author: Mateusz Piwowarczyk <>, AGH University of Science and Technology
"""
import pymongo

from overwatch.database.databaseFactory import DatabaseFactory
from overwatch.database.mongoDatabase import MongoDatabase


class MongoDatabaseFactory(DatabaseFactory):
    def __init__(self, databaseName, host, port):
        DatabaseFactory.__init__(self)
        self.databaseName = databaseName
        self.host = host
        self.port = port

    def initializeDB(self):
        """ Deletes item from database.

        Args:
            key (String): name of item to delete
        Returns:
            None
        """
        client = pymongo.MongoClient(
            host=self.host,
            port=self.port)
        db = client[self.databaseName]
        return MongoDatabase(db, client)
