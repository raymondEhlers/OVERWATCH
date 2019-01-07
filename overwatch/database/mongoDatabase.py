from overwatch.database.abstractDatabase import Database

from utilities import todict


class MongoDatabase(Database):
    def fetch(self, item):
        if item not in self.db.collection_names():
            return {}
        collection = list(self.db[item].find())[0]
        collection.pop("_id", None)
        return collection

    def commit(self):
        for key, value in todict(self.collection).items():
            self.db[key].insert_one(value)

    def clear(self, item):
        self.db[item].remove()

    def contains(self, item):
        return item in self.db.collection_names() or item in self.collection

    def get(self, item):
        if item not in self.collection:
            self.collection[item] = todict(self.fetch(item))
        return self.collection[item]

    def set(self, key, value):
        self.collection[key] = todict(value)
