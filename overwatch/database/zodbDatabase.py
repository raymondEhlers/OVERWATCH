from overwatch.database.abstractDatabase import Database
import transaction


class ZodbDatabase(Database):
    def fetch(self, item):
        if item not in self.db:
            return {}
        return self.db[item]

    def commit(self):
        for key, value in self.collection.items():
            self.db[key] = value
        transaction.commit()

    def clear(self, item):
        self.db[item] = {}
        transaction.commit()

    def contains(self, item):
        return item in self.db or item in self.collection
