#!/usr/bin/env python

""" ZMQ receiver monitor

Checks timestamps of heartbeat files to ensure that the ZMQ receivers are still alive.
Note that this doesn't apply to the DQM receiver.

``__main__`` is implemented to allow for this function to be executed directly,
while ``run*()`` is defined to allow for execution via ``entry_points`` defined
in the python package setup.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

import os
import pendulum
import pprint
import logging
# We want to log everything, so we give it empty quotes.
logger = logging.getLogger("")

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

# Config
from overwatch.base import config
from overwatch.base import utilities
(parameters, filesRead) = config.readConfig(config.configurationType.base)
print("Configuration files read: {filesRead}".format(filesRead = filesRead))
print("parameters: {parameters}".format(
    parameters = pprint.pformat(parameters)))

# Setup logging
utilities.setupLogging(logger = logger,
                       logLevel = parameters["loggingLevel"],
                       debug = parameters["debug"])
# Log settings
logger.info(parameters)

# Setup sentry to create alerts for warning level messages.
sentry_logging = LoggingIntegration(level = logging.WARNING, event_level = None)
# Usually, we want the module specific DSN, but we will take the general one if it's the only one available.
sentry_sdk.init(dsn = os.getenv("SENTRY_DSN_RECEIVER_MONITOR") or os.getenv("SENTRY_DSN"), integrations = [sentry_logging])

def getHeartbeat(subsystem):
    """ Get the heartbeat of a ZMQ receiver for a given subsystem.

    Note:
        The timestamp returned is not converted from time zones - it is just the stored value.

    Args:
        subsystem (str): Three letter subsystem name. For example, ``EMC``.
    Returns:
        int: The unix timestamp stored in the heartbeat file or -1 if the file can't be found.
    """
    heartbeatFilename = os.path.join(parameters["receiverData"], "heartbeat.{subsystem}Receiver".format(subsystem = subsystem))
    try:
        with open(heartbeatFilename, "r") as f:
            heartbeatTimestamp = int(f.read())
    except (IOError, ValueError) as e:
        logger.info("e: {e}".format(e = type(e)))
        # If the file doesn't exist, return -1 to indicate that the receiver heartbeat wasn't found.
        heartbeatTimestamp = -1

    return heartbeatTimestamp

def checkHeartbeat(deadReceivers):
    """ Check the heartbeat of all ZMQ receivers.

    If the receiver doesn't have a heartbeat for 5 minutes, then it is considered dead.

    Note:
        This assumes that the heartbeat was recorded in the same timezone as the current timestamp,
        which should be a reasonable assumption given that local file access is required to monitor
        these heartbeats.

    Args:
        deadReceivers (set): Receivers where are currently dead.
    Returns:
        set: Receivers which are dead (or continue to be) after checking the heartbeats.
    """
    for subsystem in parameters["subsystemList"]:
        heartbeatTimestamp = getHeartbeat(subsystem)
        # The receivers are run in Geneva
        # This heartbeat is converted to UTC.
        heartbeat = pendulum.from_timestamp(heartbeatTimestamp, tz = "Europe/Zurich")
        now = pendulum.now(tz = "UTC")
        # If the receiver doesn't have a heartbeat for 5 minutes, then it is considered dead.
        subsystemDead = False
        logger.debug("now: {}, heartbeat: {}".format(now.timestamp(), heartbeat.timestamp()))
        logger.debug("Diff: {}".format(now.diff(heartbeat).in_minutes()))
        if now.diff(heartbeat).in_minutes() >= 5:
            subsystemDead = True

        logger.info("subsystemDead: {}".format(subsystemDead))
        if subsystem in deadReceivers:
            if subsystemDead is True:
                # Reduced notification frequency so we don't overwhelm ourselves with errors.
                # Just notify once per hour.
                if now.minute == 0:
                    logger.critical("{subsystem} receiver appears to have been dead since {heartbeat}!".format(subsystem = subsystem,
                                                                                                               heartbeat = heartbeat))
            else:
                deadReceivers.remove(subsystem)
                logger.warning("{subsystem} receiver has been revived.".format(subsystem = subsystem))
        else:
            if subsystemDead is True:
                deadReceivers.add(subsystem)
                logger.critical("{subsystem} receiver has had no heart beat for 5 minutes!".format(subsystem = subsystem))
            else:
                logger.info("{subsystem} receiver appears to be fine".format(subsystem = subsystem))

    return deadReceivers

def run():
    """ Entry point for monitoring ZMQ receivers. """
    handler = utilities.handleSignals()
    # Keep track of the subsystem receivers so we can reduce the rate of warnings if they are already dead.
    # We can also keep track of when it has been restored.
    deadReceivers = set()
    logger.info("Starting ZMQ receiver monitoring.")
    while not handler.exit.is_set():
        deadReceivers = checkHeartbeat(deadReceivers)
        # Repeat every minute. We shouldn't need to configure this vgalue.
        handler.exit.wait(60)

if __name__ == "__main__":  # pragma: nocover
    run()
