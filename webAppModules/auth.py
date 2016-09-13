""" Contains auth functions.

For user authentication, https://exploreflask.com/users.html was extensively used as a guide.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University 
"""

# Flask
from flask_login import UserMixin
from flask_bcrypt import check_password_hash

# Config
from config.serverParams import serverParameters

###################################################
class User(UserMixin):
    """ A basic user class to manage authentication.

    Inherits from UserMixin, which implements a basic class for use with login_manger().

    New users should be added into the external config file. This class provides no ability to store new users dynamically
    and assumes that passwords passed to it are already hashed by ``bcrypt.generate_password_hash(password, BCRYPT_LOG_ROUNDS)``.

    The login_manager stores this class to manage users.

    Args:
        username (str): Username of new user
        password (str): Hashed password of new user. Password should be hashed with
            ``bcrypt.generate_password_hash(desiredPassword, BCRYPT_LOG_ROUNDS)``

    Attributes:
        users (dict): Contains all valid users with hashed passwords. Loaded from an extra config file.
        id (str): The username of the instance of the object
        password (str): The password of the instance of the object. Note: This must be hashed by the user before
            passing to this object!

    Note:
        There are also a few attributes inherited from UserMixin

    """

    def __init__(self, username, password):
        """ Initialize a new user, assuming that their password is hashed.
        
        Does not store the new user in a central database! It will disappear when the object goes out of scope."""
        self.id = username
        self.password = password

    def checkPassword(self, plainTextPassword):
        """ Check a plain text password against a hashed password.
        
        Args:
            plainTextPassword (str): The plain text password to test.

        Returns:
            bool: True if the password matches the instance of the user.
            
        """
        return check_password_hash(self.password, plainTextPassword)

    # Static objects and methods
    #: List of valid users, loaded from an external file.
    users = serverParameters._users

    @classmethod
    def getUser(cls, username):
        """ Retrieve the username and password of a user.

        Used by ``load_user()`` to maintain a logged in user session.

        Args:
            username (str): Username to retrieve

        Returns:
            :class:`.User`: Returns an instance of the :class:`.User` class if the user exists. Otherwise, it
            returns None.
        """
        userPasswordHash = cls.users.get(username)
        # If we can retrieve the hash, then it means that we have a valid user
        if userPasswordHash:
            return User(username, userPasswordHash)
        else:
            return None

###################################################
def authenticateUser(username, password):
    """ Checks whether the user credentials are correct.

    Args:
        username (str): username of the attempted user.
        password (str): plain text password of the attempted user.

    Returns:
        :class:`.User`: If the credentials were valid, an instance of the :class:`.User` class is returned so that the login_manager can store that object and track which user is logged in.
            Otherwise, it returns None.

    """
    attemptedUser = User.getUser(username)
    if attemptedUser:
        # If the password is valid, then return the user so that it can be logged in.
        if attemptedUser.checkPassword(password):
            return attemptedUser

    return None

