from overwatch.database.abstractDatabase import Database

from utilities import todict


class MongoDatabase(Database):
    def fetch(self, item):
        if item not in self.db.collection_names():
            return {}
        collection = dict(self.db[item].find_one({"_id": item}))
        collection.pop("_id", None)
        return collection

    def commit(self):
        for key, value in todict(self.collection).items():
            self.db[key].update_one(
                {"_id": key},
                {"$set": dict(todict(value), **{"_id": key})},
                upsert=True)

    def clear(self, key):
        self.db[key].remove()

    def contains(self, key):
        return key in self.db.collection_names() or key in self.collection

    def get(self, key):
        if key not in self.collection:
            self.collection[key] = todict(self.fetch(key))
        return self.collection[key]

    def set(self, key, value):
        self.collection[key] = value
