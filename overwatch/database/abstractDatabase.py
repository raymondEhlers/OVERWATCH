
class Database:
    def __init__(self, db):
        self.db = db
        self.collection = {}

    def contains(self, item):
        self.get(item)
        return item in self.collection

    def get(self, item):
        if item not in self.collection:
            self.collection[item] = self.fetch(item)
        return self.collection[item]

    def set(self, key, value):
        self.collection[key] = value

    def fetch(self, key):
        raise NotImplementedError

    def commit(self):
        raise NotImplementedError

    def clear(self, item):
        raise NotImplementedError
