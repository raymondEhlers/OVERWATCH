#!/usr/bin/env python

""" Handle and move files from the receiver(s).

We take a simple approach of determine which files to transfer, and then moving them to the
appropriate locations. We could try to use something like ``watchdog`` to do something more
clever when a file changes. However, we want to batch transfer files to take advantage of
``rsync``, so such an approach would require much more complicated bookkeeping (for example,
what happens if a file shows up when transferring data, etc). The much simpler approach that
we use solves our problem just as well, but is also much easier to write and maintain.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

# Python 2/3 support
from __future__ import print_function
from future.utils import iteritems

# General
import os
import math
import time
import shutil
import subprocess
import tempfile
import functools

import ROOT

# Logging
import logging
logger = logging.getLogger(__name__)

# TODO: Fully setup logging using utils.

# Config
from . import config
(parameters, filesRead) = config.readConfig(config.configurationType.processing)

def retry(tries, delay = 3, backoff = 2):
    """ Retries a function or method until it returns ``True`` or runs out of retries.

    Retries are performed at a specific delay with an additional back off term. The retries go
    as

    .. math::

        t = delay * backoff^(nTry)

    where :math:`nTry` is the trial that we are on.

    Original decorator from the `Python wiki <https://wiki.python.org/moin/PythonDecoratorLibrary#Retry>`__,
    and using some additional improvements `here <https://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/>`__,
    and some ideas `here <https://www.calazan.com/retry-decorator-for-python-3/>`__.

    Args:
        tries (int): Number of times to retry.
        delay (int): Delay in seconds for the initial retry. Default: 3.
        backoff (int): Amount to multiply the delay by between each retry. See the formula above.
    Returns:
        bool: True if the function succeeded.
    """
    # Argument validation
    if backoff <= 1:
        raise ValueError("Backoff must be greater than 1.")
    tries = math.floor(tries)
    if tries < 0:
        raise ValueError("Tries must be 0 or greater.")
    if delay <= 0:
        raise ValueError("Delay must be greater than 0.")

    def deco_retry(f):
        @functools.wraps(f)
        def f_retry(*args, **kwargs):
            # Make mutable
            mtries, mdelay = tries, delay

            # First attempt at calling the function
            rv = f(*args, **kwargs)
            while mtries > 0:
                # If we ever get a return value of `True`, we are done.
                if rv is True:
                    return True

                # Setup for the next attempt and wait before the next attempt
                mtries -= 1
                time.sleep(mdelay)
                mdelay *= backoff

                # Try again
                rv = f(*args, **kwargs)

            # Ran out of tries. Return failure.
            return False

        # true decorator -> decorated function
        return f_retry
    # @retry(arg[, ...]) -> true decorator
    return deco_retry

def determineFilesToMove(directory):
    """ Determine the files which are available to be moved or otherwise transferred.

    Since there could be additional directories which we want to ignore, we want to use avoid
    using ``os.walk()``, which will include subdirectories. Instead, we use a simpler solution
    with ``os.listdir()`` and verify that we include only files.

    Note:
        These files are required to be ROOT files by looking for the ``.root`` extension.

    Args:
        directory (str): Path to the directory where the files are stored.
    Returns:
        list: List of the files available to be moved. Note that just the filenames are stored,
            so it's the callers responsibility to include the directory when using the filename.
    """
    return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f)) and ".root" in f]

@retry(tries = 3)
def rsyncFilesFromFilelist(directory, destination, filelistFilename, transferredFilenames):
    """ Transfer files via rsync based on a list of filenames in a given file.

    Note:
        This must be a separate function which returns a bool to work properly with the retry wrapper.
        Consequently, we return any transferred filenames by reference via ``transferredFilenames``.

    Args:
        directory (str): Path to the directory where the files are stored locally.
        destination (str): Path to the remote directory where the files are stored. Since the
            files are being transferred with rsync via ssh, this path should be of the form
            ``user@host:/dir/path``.
        filelistFilename (str): Filename of the file which contains the list of files to transfer.
        transferredFilenames (list): List of filenames which were transfer. Used to return this information
            because we have to return ``True`` or ``False`` with the retry wrapper.
    Returns:
        bool: True if the files were transferred successfully.
    """
    # Check destination value. If we are testing, it doesn't need to have the ":", but for normal operation,
    # it usually will.
    if ":" not in destination:
        logger.warning("Expected, but did not find, \":\" in the remote path.")

    # Needed so that rsync will transfer to that directory!
    if not destination.endswith("/"):
        destination = destination + "/"

    # Define the rsync command itself.
    rsync = [
        "rsync",
        # -l preserves symlinks.
        # -t preserves timestamps.
        # -h presents human readable information.
        # -v is verbose. (Not currently included).
        "-lth",
        # This outputs just the name of the file that is transferred.
        r"--out-format=%n",
        # Files from is relative to the remote path.
        "--files-from={name}".format(name = filelistFilename),
        # Source
        directory,
        # Destination
        destination,
    ]

    logger.debug("Args: {rsync}".format(rsync = rsync))
    try:
        result = subprocess.check_output(args = rsync, universal_newlines = True)
    except subprocess.CalledProcessError as e:
        # The call failed for some reason. We want to handle it.
        logger.debug("rsync call failed!")
        return False

    # NOTE: Getting to this point is equivalent to having a return code of 0.
    # Change: "hello\nworld\n" -> ["hello", "world"]
    parsedResult = result.strip("\n").split("\n")
    # Extend so we don't entirely reassign the reference.
    transferredFilenames.extend(parsedResult)

    logger.debug("Result: {}".format(result))
    logger.debug("Result parsed: {}".format(parsedResult))

    return True

def copyFilesToOverwatchSites(directory, destination, filenames):
    """ Copy the given files to the Overwatch deployment sites.

    The Overwatch sites and where the files should be stored at those sites is determined
    in the configuration. Retries should usually not be necessary here, but are included
    as an additional assurance.

    Args:
        directory (str): Path to the directory where the files are stored locally.
        destination (str): Path to the remote directory where the files are stored. Since the
            files are being transferred with rsync via ssh, this path should be of the form
            ``user@host:/dir/path``.
        filenames (list): Paths to files to copy to each Overwatch site.
    Returns:
        list: Filenames for all of the files which **failed**.
    """
    # TODO: Determine receiver last modified times.

    # First write the filenames out to a temp file so we can pass them to rsync.
    with tempfile.NamedTemporaryFile() as f:
        # Need encode because the file is written as bytes.
        f.write("\n".join(filenames).encode())
        # Move back to the front so it can be read.
        f.seek(0)

        # Perform the actual files transfer.
        transferredFilenames = []
        success = rsyncFilesFromFilelist(directory = directory,
                                         destination = destination,
                                         filelistFilename = f.name,
                                         transferredFilenames = transferredFilenames)

        logger.debug("transferredFilenames: {}".format(transferredFilenames))

        # We want to return the files that _failed_, so if the files were transferred,
        # we return an empty list. Otherwise, we return the files that were not transferred.
        failedFilenames = list(set(filenames) - set(transferredFilenames))
        return [] if success else failedFilenames

@retry(tries = 3)
def copyFileToEOSWithRoot(directory, destination, filename):
    """ Copy a given file to EOS using ROOT capabilities.

    We include the possibility to show the ROOT cp progress bar if we are in debug mode.

    Args:
        directory (str): Path to the directory where the files are stored locally.
        destination (str): Directory on EOS to which the file should be copied.
        filename (str): Local filename of the string to be copied. This will be used for setting
            the path where it will be copied.
    Returns:
        bool: True if the file was copied successfully
    """
    source = os.path.join(directory, filename)
    destination = os.path.join(destination, filename)
    # We only want to see such information if we are debugging. Otherwise, it will just clog up the logs.
    showProgressBar = parameters["debug"]
    return ROOT.TFile.Cp(source, destination, showProgressBar)

def copyFilesToEOS(directory, destination, filenames):
    """ Copy the given filenames to EOS.

    Files which failed are returned so that these files can be saved and the admin can be alerted to take
    additional actions.

    Args:
        directory (str): Path to the directory where the files are stored locally.
        destination (str): Directory on EOS to which the file should be copied.
        filenames (list): Files to copy to EOS.
    Returns:
        list: Filenames for all of the files which **failed**.
    """
    failedFilenames = []
    for f in filenames:
        # This function will automatically retry.
        res = copyFileToEOSWithRoot(directory = directory, destination = destination, filename = f)
        # Store the failed files so we can notify the admin that something went wrong.
        if res is False:
            failedFilenames.append(f)

    return failedFilenames

# Steps:
# - Enumerate the available files.
# - rsync the files to other sites.
#   - Somehow signal that we have new files. Touch a file? Write what was transferred?
# - Copy those files to EOS.
# - If both of the above were successful, then delete the local files
# - Otherwise, move the unsuccessful files to another directory to keep them around. Still delete any successful files

def processReceivedFiles():
    """ Main driver function for receiver file processing and moving.

    Note:
        Configuration is controlled via the Overwatch YAML configuration system. In particular,
        the options relevant here are defined in the base module.

    Args:
        None.
    Returns:
        None.
    """
    # These are just raw filenames.
    filenames = determineFilesToMove(directory = parameters["receiverData"])

    if not filenames:
        logger.info("No new files found. Returning.")
        return

    # Copy files via rsync
    # TODO: Fill in parameters
    rsyncFailedFilenames = copyFilesToOverwatchSites(directory = directory,
                                                     destination = parameters[""],
                                                     filenames = filenames)

    # TODO: Notify the Overwatch sites about the new files

    # Copy files to EOS
    eosFailedFilenames = copyFilesToEOS(directory = parameters["receiverData"],
                                        destination = parameters["eosDirPrefix"],
                                        filenames = filenames)

    # Determine the definitive set of failed files
    # NOTE: We shouldn't have any duplicate filenames, so set shouldn't do anything
    #       beyond making it possible to call union.
    failedFilenames = set(rsyncFailedFilenames) | set(eosFailedFilenames)

    # Only delete files if none have failed.
    if failedFilenames:
        # Move to a safer location
        for f in failedFilenames:
            # TODO: Define this directory in parameters
            shutil.move(f, os.path.join(parameters["tempStorageData"], f))

        # Keep track of which ones failed in which case.
        # rsync
        with open(os.path.join(parameters["tempStroageData"], "rsyncFailedFilenames.txt"), "a") as f:
            f.write("\n".join(rsyncFailedFilenames))

        # EOS
        with open(os.path.join(parameters["tempStroageData"], "eosFailedFilenames.txt"), "a") as f:
            f.write("\n".join(eosFailedFilenames))

        # By logging, it will be sent to the admins when appropriate.
        logger.warning("Files failed to copy!\nrsyncFailedFilenames: {rsyncFailedFilenames}\neosFailedFilenames: {eosFailedFilenames}".format(rsyncFailedFilenames = rsyncFailedFilenames, eosFailedFilenames = eosFailedFilenames))

    # Determine which files we can safely remove
    successfullyTransferred = set(filenames) - set(failedFilenames)

    # Store the successful files transferred.
    logger.info("Successfully transferred: {successfullyTransferred}".format(successfullyTransferred = successfullyTransferred))

    if failedFilenames:
        # Sanity check
        assert len(filenames) == len(successfullyTransferred) + len(failedFilenames)

    # Protect from data loss when testing
    if parameters["debug"] is False:
        for f in filenames:
            os.remove(f)
    else:
        for f in filenames:
            shutil.move(f, os.path.join[parameters["debugStorage"], f])

# TODO: Add some monitoring information and send summary emails each day. This way, I'll know that
#       Overwatch is still operating properly.
