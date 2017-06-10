#!/usr/bin/env python

# For unrandom
import os
# Bcrypt
from flask_bcrypt import generate_password_hash
# Config
from overwatch.base import config
(serverParameters, filesRead) = config.readConfig(config.configurationType.webApp)

# Define additional needed variables
defaultUsername = serverParameters["defaultUsername"]
bcryptLogRounds = serverParameters["bcryptLogRounds"]

# Contains sensitive parameters
# Defined here since it is fewer values to maintain
_users = {"username": generate_password_hash("password", bcryptLogRounds)}
# Add the default username if it makes sense
if defaultUsername != "":
    pass
""" Contains the users for authenticating on the server
This could be more complex, but there isn't any point for such a simple project
For more security in this file, one could also generate the hash and then just
copy that here so that the password is not visible in plain text in this file.

Defined with an underscore since it is a private value.

Other usernames can be added here if desired. Users are defined as:

>>> _users = {"username": generate_password_hash("password", bcryptLogRounds)}
"""

_secretKey = str(os.urandom(50))
""" Secret key for signing cookies

Defined with an underscore since it is a private value.

Generated using urandom(50), as suggested by the flask developers.
"""
