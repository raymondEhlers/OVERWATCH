
class DatabaseFactory:
    def __init__(self, databaseName):
        self.databaseName = databaseName

    def getDB(self):
        raise NotImplemented

