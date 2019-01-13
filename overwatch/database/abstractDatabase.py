"""
.. code-author: Mateusz Piwowarczyk <>, AGH University of Science and Technology
"""

from overwatch.database.utilities import Map


class Database:
    """ Database wrapper which allows to use different databases in the project.

    Args:
        db: Object which allows to access underlying database. Type depends on underlying database.
        connection: Database connection. Type depends on underlying database.

    Attributes:
        db: Object which allows to access underlying database. Type depends on underlying database.
        connection: Database connection object. Type depends on underlying database.
        collection: Collection of items stored in the database. Type depends on underlying database.
    """

    def __init__(self, db, connection):
        self.db = db
        self.connection = connection
        self.collection = Map()

    def get(self, key):
        """  Returns reference to item stored in the database.

        Args:
            key (String): name of the item to return
        Returns:
            Item identified by given key. Type of returned value depends on underlying database used to store it.
        """
        if key not in self.collection:
            self.collection[key] = self.fetch(key)
        return self.collection[key]

    def set(self, key, value):
        """  Sets item in the database identified by given key.

        Args:
            key (String): name of item to be stored in the database
            item: item to be stored under given key
        Returns:
            Item identified by given key. Type of returned value depends on underlying database used to store it.
        """
        self.collection[key] = value

    def contains(self, key):
        """  Checks if item exists in the database.

        Args:
            key (String): name of item to check if exists
        Returns:
            True if item exists in the database, False otherwise.
        """
        raise NotImplementedError

    def fetch(self, key):
        """  Returns collection stored in underlying database .

        Args:
             key (String): name of the item to return
        Returns:
            Item identified by given key. Type of returned value depends on underlying database used to store it.
        """
        raise NotImplementedError

    def commit(self):
        """ Commits all local data changes in the database.

        Args:
            None:
        Returns:
            None
        """
        raise NotImplementedError

    def clear(self, key):
        """ Deletes item from the database.

        Args:
            key (String): name of item to delete
        Returns:
            None
        """
        raise NotImplementedError

    def close_connection(self):
        """ Closes connection to the database.

        Args:
            None
        Returns:
            None
        """
        if self.connection:
            self.connection.close()
