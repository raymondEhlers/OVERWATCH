#!/usr/bin/env python

""" Contains auth functions.

For user authentication, https://exploreflask.com/users.html was extensively used as a guide.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

# Flask
from flask_login import UserMixin
from flask_bcrypt import check_password_hash

# Logging
import logging
logger = logging.getLogger(__name__)

class User(UserMixin):
    """ A basic user class to manage authentication.

    Inherits from ``UserMixin``, which implements a basic class for use with ``login_manger()``.

    New users should be added into the external config file. This class provides no ability to store new users dynamically
    and assumes that passwords passed to it are already hashed by ``bcrypt.generate_password_hash(password, BCRYPT_LOG_ROUNDS)``.

    The ``login_manager`` stores this class to manage users.

    Note:
        There are also a few attributes inherited from UserMixin

    Args:
        username (str): Username of new user
        password (str): Hashed password of new user. Password should be hashed with
            ``bcrypt.generate_password_hash(desiredPassword, BCRYPT_LOG_ROUNDS)``

    Attributes:
        users (dict): Contains all valid users with hashed passwords. Loaded from an extra config file.
        id (str): The username of the instance of the object
        password (str): The password of the instance of the object. Note: This must be hashed by the user before
            passing to this object!
    """

    def __init__(self, username, password):
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

    @staticmethod
    def getUser(username, db):
        """ Retrieve the username and password of a user.

        Used by ``load_user()`` to maintain a logged in user session.

        Args:
            username (str): Username to retrieve
        Returns:
            ``User``: Returns an instance of the ``User`` class if the user exists. Otherwise, it
                returns ``None``.
        """
        try:
            userPasswordHash = db["config"]["users"][username]
        except KeyError:
            # Catch if one of the keys doesn't exist.
            userPasswordHash = None
        # If we can retrieve the hash, then it means that we have a valid user
        if userPasswordHash:
            return User(username, userPasswordHash)
        else:
            return None

def authenticateUser(username, password, db):
    """ Checks whether the user credentials are correct.

    Args:
        username (str): username of the attempted user.
        password (str): plain text password of the attempted user.
    Returns:
        ``User``: If the credentials were valid, an instance of the ``User`` class is returned so that the login_manager
            can store that object and track which user is logged in. Otherwise, it returns ``None``.
    """
    attemptedUser = User.getUser(username, db)
    if attemptedUser:
        # If the password is valid, then return the user so that it can be logged in.
        if attemptedUser.checkPassword(password):
            return attemptedUser

    return None

