#!/usr/bin/env python

# Tests for the configuration module.
#
# Note: These tests are not quite ideal, as they rely on the default implementation
#       for the configuration and modules (which can change), but the implementation
#       takes much less time than mocking objects.
#
# author: Raymond Ehlers <raymond.ehlers@yale.edu>, Yale University
# date: 16 July 2018

import pytest
import ruamel.yaml as yaml
import pkg_resources
import os
import logging
logger = logging.getLogger(__name__)

import overwatch.base.config as config

@pytest.fixture
def yamlConfigForParsingPlugins():
    """ YAML config in for testing config parsing plugin. """
    parameters = """
joinPaths: !joinPaths
    - a
    - b
    - "c"
runPageTemplates: !findRunPageTemplates
    - "templates"
bcryptBlock: !bcrypt
    bcryptLogRounds: 10
    user: "pass"
bcryptBlockNoUser: !bcrypt
    bcryptLogRounds: 10
    null: null
secretKey: !secretKey 12345
secretKeyGen: !secretKey null
    """
    # Load parameters
    parameters = yaml.load(parameters, Loader = yaml.SafeLoader)
    return parameters

def testJoinPaths(loggingMixin, yamlConfigForParsingPlugins):
    """ Test joining paths in the yaml config. """
    parameters = yamlConfigForParsingPlugins
    assert parameters["joinPaths"] == os.path.join("a", "b", "c")

def testFindAvailableRunPages(loggingMixin, yamlConfigForParsingPlugins):
    """ Test finding available run pages via the yaml config. """
    parameters = yamlConfigForParsingPlugins
    expected = [name for name in pkg_resources.resource_listdir("overwatch.webApp", "templates") if "runPage" in name]
    assert parameters["runPageTemplates"] == expected

def testBcrypt(loggingMixin, yamlConfigForParsingPlugins):
    """ Tests for using bcrypt to setup users. """
    parameters = yamlConfigForParsingPlugins
    expected = {"user" : "pass"}
    assert parameters["bcryptBlock"].keys() == expected.keys()
    # The hash isn't repeatable, so we just want to be certain that it's hashed.
    assert parameters["bcryptBlock"]["user"] != expected["user"]
    # We do know that the hash should begin with the following string
    beginningStr = b"$2b$10$"
    assert parameters["bcryptBlock"]["user"][:len(beginningStr)] == beginningStr
    assert parameters["bcryptBlockNoUser"] == {}

def testSecretKey(loggingMixin, yamlConfigForParsingPlugins):
    """ Tests for determining the secret key. """
    parameters = yamlConfigForParsingPlugins
    # It will always return a string, so we must compare to a string.
    assert parameters["secretKey"] == "12345"
    # We can't predict what it will produce, so we just check to make sure that it's not null
    assert parameters["secretKeyGen"] is not None

def testReadConfig(loggingMixin):
    """ Integration tests for reading a configuration for a particular module. """

    assert False
