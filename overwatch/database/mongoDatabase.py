
from overwatch.database.abstractDatabase import Database


class MongoDatabase(Database):
    def fetch(self, item):
        if item not in self.db.collection_names():
            return {}
        collection = list(self.db[item].find())[0]
        collection.pop("_id", None)
        return collection

    def commit(self):
        for key, value in self.collection.items():
            self.db[key].insert_one(todict(value))

    def clear(self, item):
        self.db[item].delete_many({})

    def contains(self, item):
        return item in self.db.collection_names() or item in self.collection

def todict(obj, classkey=None):
    if isinstance(obj, dict):
        data = {}
        for (k, v) in obj.items():
            data[str(k)] = todict(v, classkey)
        return data
    elif hasattr(obj, "_ast"):
        return todict(obj._ast())
    elif hasattr(obj, "__iter__") and not isinstance(obj, str):
        return [todict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = dict([(key, todict(value, classkey))
                     for key, value in obj.__dict__.items()
                     if not callable(value) and not key.startswith('_')])
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    else:
        return obj