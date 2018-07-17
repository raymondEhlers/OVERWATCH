#!/usr/bin/env python

# Tests for the configuration module.
#
# Note: These tests are not quite ideal, as they rely on the default implementation
#       for the configuration and modules (which can change), but the implementation
#       takes much less time than mocking objects.
#
# author: Raymond Ehlers <raymond.ehlers@yale.edu>, Yale University
# date: 16 July 2018

from future.utils import iteritems

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
bcrypt: !bcrypt
    bcryptLogRounds: 12
    user: "pass"
bcryptNoUser: !bcrypt
    bcryptLogRounds: 12
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
    # Use pkg_resources to make sure we don't end up with the wrong resources (and to ensure that the tests
    # are cwd independent).
    expected = [name for name in pkg_resources.resource_listdir("overwatch.webApp", "templates") if "runPage" in name]
    assert parameters["runPageTemplates"] == expected

def testBcrypt(loggingMixin, yamlConfigForParsingPlugins):
    """ Tests for using bcrypt to setup users. """
    parameters = yamlConfigForParsingPlugins
    expected = {"user" : "pass"}
    assert parameters["bcrypt"].keys() == expected.keys()
    # The hash isn't repeatable, so we just want to be certain that it's hashed.
    assert parameters["bcrypt"]["user"] != expected["user"]
    # We do know that the hash should begin with the following string
    beginningStr = b"$2b$12$"
    assert parameters["bcrypt"]["user"][:len(beginningStr)] == beginningStr
    # We don't expect any users here.
    assert parameters["bcryptNoUser"] == {}

def testSecretKey(loggingMixin, yamlConfigForParsingPlugins):
    """ Tests for determining the secret key. """
    parameters = yamlConfigForParsingPlugins
    # It will always return a string, so we must compare to a string.
    assert parameters["secretKey"] == "12345"
    # We can't predict what it will produce, so we just check to make sure that it's not null
    assert parameters["secretKeyGen"] != "null"
    assert parameters["secretKeyGen"] is not None

@pytest.mark.parametrize("configTypeString", [
        False,
        True
    ], ids = ["Using config type value", "Using config type string"])
@pytest.mark.parametrize("configType", [
        config.configurationType.base,
        config.configurationType.processing,
        config.configurationType.webApp
    ], ids = ["base module", "processing module", "webApp module"])
def testReadConfig(loggingMixin, configType, configTypeString):
    """ Integration tests for reading a configuration for a particular module. """
    # This could be different than configType if we want to use a string.
    # We use a different object because we still want to use the standard config type later in the test.
    configTypeForReadingConfig = configType
    if configTypeString:
        configTypeForReadingConfig = configType.name
    (parameters, filesRead) = config.readConfig(configTypeForReadingConfig)

    filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), "testFiles", "{}ConfigRef.txt".format(configType.name))

    # We need to treat whether the file exists with a bit of care.
    # NOTE: Since the parametization causes this to run mulitple times, some will pass and
    #       and some will fail, even when creating the configuration files. This is fine.
    if os.path.exists(filename):
        # Access the expected values
        with open(filename, "r") as f:
            expected = yaml.load(f.read(), Loader = yaml.SafeLoader)
    else:
        # For making the reference
        with open(filename, "w") as f:
            yaml.dump(parameters, f)
        logger.warning("Creating configuration reference for {} module".format(configType.name))
        # We don't want to go further - we're just creating the reference.
        assert False

    # Don't compare the full "_users" values because they will always be different due to differences in hashing
    paramUsers = parameters.pop("_users", None)
    expectedUsers = expected.pop("_users", None)
    # However, the beginning should match (same idea as in `testBcrypt`)
    lengthToCheck = 7
    # It won't always exist, so we need to check for it first.
    if paramUsers:
        for k, v in iteritems(paramUsers):
            assert v[:lengthToCheck] == expectedUsers[k][:lengthToCheck]

    # Everything else should be identical.
    assert parameters == expected
