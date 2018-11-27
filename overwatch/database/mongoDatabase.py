from overwatch.database.abstractDatabase import Database

class MongoDatabase(Database):
    def fetch(self, item):
        if item not in self.db.collection_names():
            return {}
        collection = list(self.db[item].find())[0]
        collection.pop("_id", None)
        return collection

    def commit(self):
        for key, value in self.collection.iteritems():
            self.db[key].insert_one(value)

    def clear(self, item):
        self.db[item].delete_many({})
