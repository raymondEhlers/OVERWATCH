"""
.. code-author: Mateusz Piwowarczyk <>, AGH University of Science and Technology
"""
import BTrees
import persistent


class Map(dict):
    """ Dictionary wrapper class. This class allows to acess dictionary with dot notation.
        For more information see https://stackoverflow.com/questions/2352181/how-to-use-a-dot-to-access-members-of-dictionary
    """

    def __init__(self, *args, **kwargs):
        super(Map, self).__init__(*args, **kwargs)
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.items():
                    self[k] = v

        if kwargs:
            for k, v in kwargs.items():
                self[k] = v

    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    def __setitem__(self, key, value):
        super(Map, self).__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delattr__(self, item):
        self.__delitem__(item)

    def __delitem__(self, key):
        super(Map, self).__delitem__(key)
        del self.__dict__[key]


def todict(obj, classkey=None):
    """ Converts object to dictionary.
        For more information see https://stackoverflow.com/questions/1036409/recursively-convert-python-object-graph-to-dictionary
    """
    if isinstance(obj, dict) or isinstance(obj, BTrees.OOBTree.BTree) \
            or isinstance(obj, persistent.mapping.PersistentMapping):
        data = Map()
        for (k, v) in obj.items():
            data[str(k)] = todict(v, classkey)
        return data
    elif hasattr(obj, "_ast"):
        return todict(obj._ast())
    elif hasattr(obj, "__iter__") and not isinstance(obj, str):
        return [todict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = Map([(key, todict(value, classkey))
                    for key, value in obj.__dict__.items()
                    if not callable(value) and not key.startswith('_')])
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    else:
        return obj
