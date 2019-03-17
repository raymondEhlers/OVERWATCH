"""
.. code-author: Mateusz Piwowarczyk <>, AGH University of Science and Technology
"""
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

    def clear(self, key):
        self.db[key] = {}
        transaction.commit()

    def contains(self, key):
        return key in self.db or key in self.collection
