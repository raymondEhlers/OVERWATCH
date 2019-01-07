from utilities import Map


class Database:
    def __init__(self, db, connection):
        self.db = db
        self.connection = connection
        self.collection = Map()

    def get(self, item):
        if item not in self.collection:
            self.collection[item] = self.fetch(item)
        return self.collection[item]

    def set(self, key, value):
        self.collection[key] = value

    def contains(self, item):
        raise NotImplementedError

    def fetch(self, key):
        raise NotImplementedError

    def commit(self):
        raise NotImplementedError

    def clear(self, item):
        raise NotImplementedError

    def close_connection(self):
        if self.connection:
            self.connection.close()
