import zodburi
import ZODB

from overwatch.database.databaseFactory import DatabaseFactory
from overwatch.database.zodbDatabase import ZodbDatabase


class ZodbDatabaseFactory(DatabaseFactory):
    def __init__(self, databaseLocation):
        DatabaseFactory.__init__(self)
        self.databaseLocation = databaseLocation
        self.instance = None

    def initializeDB(self):
        # Get the database
        # See: http://docs.pylonsproject.org/projects/zodburi/en/latest/
        # storage = ZODB.FileStorage.FileStorage(os.path.join(dirPrefix,"overwatch.fs"))
        storage_factory, dbArgs = zodburi.resolve_uri(self.databaseLocation)
        storage = storage_factory()
        db = ZODB.DB(storage, **dbArgs)
        connection = db.open()
        dbRoot = connection.root()
        return ZodbDatabase(dbRoot, connection)
