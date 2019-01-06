class DatabaseFactory:
    def __init__(self):
        self.instance = None

    def getDB(self):
        if not self.instance:
            self.instance = self.initializeDB()
        return self.instance

    def initializeDB(self):
        raise NotImplementedError
