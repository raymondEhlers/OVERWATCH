"""
.. code-author: Mateusz Piwowarczyk <>, AGH University of Science and Technology
"""


class DatabaseFactory:
    """ Allows to create and manage instances of database objects.

    Args:
        None.

    Attributes:
        instance (Database): instance of database.
    """

    def __init__(self):
        self.instance = None

    def getDB(self):
        """ Returns cached database object.

         Args:
             None

         Returns:
             Database object.
         """
        if not self.instance:
            self.instance = self.initializeDB()
        return self.instance

    def initializeDB(self):
        """ Initializes database connection.
         Args:
             None

         Returns:
             Database object.
         """
        raise NotImplementedError
