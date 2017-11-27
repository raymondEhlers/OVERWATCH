#!/usr/bin/env python

"""
Wrapper to handle file access via EOS
"""

## Loyout of file access

import XRootD
from XRootD.client.flags import OpenFlags

## Relevant operations
# Read (get)
# Write (put)
# Delete (del)

# Global list of storage elements
gStorageElemenets = set()

def StorageElement(object):
    def __init__(self, storageLocation):
        self.storageLocation = storageLocation

    def FullFilename(self, filename):
        return os.path.join(storageLocation, filename)

    def CheckForFile(self):
        """ Check for file """
        raise NotImplementedError("Need to derived a storage element to check for a particular file")

def LocalStorageElement(StorageElement):
    def __init__(self, storageLocation):
        super(LocalStorageElement, self).__init__(storageLocation)

    def CheckForFile(self, filename):
        fullFilename = FullFilename(filename)

        if os.path.exists(fullFilename):
            return (fullFilename, True)

        # Return False if unsuccessful
        return (fullFilename, False)

def LocalFile(object):
    def __init__(self):
        pass

    def OpenFile(self, filename, mode, **kwargs):
        # TODO: Careful here: This is a specific file, but the class is for general storage!
        self.openFile = open(FullFilename(filename), mode)
        return self.openFile

def XRDStorageElement(StorageElement):
    # Translation of modes from rootpy
    # Defined in rootpy.io.root_open.mode_map
    __modes__ = {"a": OpenFlags.UPDATE,
                 "a+": OpenFlags.UPDATE,
                 "r": OpenFlags.READ,
                 "r+": OpenFlags.UPDATE,
                 "w": OpenFlags.RECREATE,
                 "w+": OpenFlags.RECREATE}

    def __init__(self, storageLocation):
        super(LocalStorageElement, self).__init__(storageLocation)
        self.client = XRootD.client.FileSystem(storageLocation)

    def CheckForFile(self, filename):
        fullFilename = FullFilename(filename)

        # Use stat as a proxy for if the file exists.
        (status, info) = self.client.stat(fullFilename)

        # Check if status returned properly and the file size is non-zero
        # TODO: How better can this be verified?
        if status.ok and status.errno == None and info.size != 0:
            return (fullFilename, True)

        # Return False if unsuccessful
        return (fullFilename, False)

@contextlib.contextmanager
def localFile(filename, mode):
    __basePath__ = ""
    path = os.path.join(__basePath__, filename)
    with open(path, mode) as f:
        try:
            yield f
            print("Finished local file")
        finally:
            print("Finally finished local file")

@contextlib.contextmanager
def XRDFile(filename, mode):
    __baseUrl__ = ""
    # Translation of modes from rootpy
    # Defined in rootpy.io.root_open.mode_map
    __modes__ = {"a": OpenFlags.UPDATE,
                 "a+": OpenFlags.UPDATE,
                 "r": OpenFlags.READ,
                 "r+": OpenFlags.UPDATE,
                 "w": OpenFlags.RECREATE,
                 "w+": OpenFlags.RECREATE}

    with XRootD.client.File() as f:
        try:
            if mode in __modes__:
                mode = __modes__[mode]
            # Should work despite note being the obivous option
            path = os.path.join(__baseUrl__, filename)
            f.open(path)

            status, _ = f.Open(self.FullFilename(filename), mode)
            if status.ok:
                yield f
            else:
                yield IOError("Failed to open XRD file. Message: {}".format(status.message))
        finally:
            print("Exiting XRD file")

def DefineStorageElementsFromConfig(storageLocations):
    for storageLocation in storageLocations:
        if storageLocation.startswith("file://"):
            # "file://" Should not be included in the path!
            gStorageElements.update(LocalStorageElement(storageLocation.replace("file://")))
        elif storageLocation.startswith("xrd://") or storageLocation.startswith("eos://"):
            gStorageElements.update(XRDStorageElement(storageLocation))
        else:
            raise NameError("Storage location {} not recognized!".format(storageLocation))

def DetermineFilenameForAccess(filename):
    """ Oriented towards reading an existing file. """

    for storageElemenet in gStorageElements:
        (fullFilename, existsInStorage) = storageElements.CheckForFile(filename)

        if existsInStorage:
            return (fullFilename, storageElement)

    # If we get here, then nothing exists!
    raise IOError("File doesn't exist!")

def OpenFile(filename, mode):
    (filename, storageElement) = DetermineFilenameForAccess(filename, mode)

    return storageElement.OpenFile(filename)

# Define storage elements.
# NOTE: Stored in global variable!
# TODO: Implement using configuration
DefineStorageElementsFromConfig(["file://.", "xrd://"])

####

class StorageElement(object):
    """ Base storage element
    
    Defined as possible to use with a context manager."""
    def __init__(self, filename, mode):
        self.location = location

    def __enter__(self):
        """ Returns file handler """
        pass

    def __exit__(self, *args):
        pass

    def Open(self, filename, mode):
        """ Opens the file """
        pass

    def Filename(self, filename):
        """ Returns the filename corresponding to the source"""
        pass

class LocalStorageElement(StorageElement):
    def __init__(self, location):
        super(LocalStorageElement, self).__init__(location)

    def __eneter__(self, filename):
        pass

    def __exit__(self, *args):
        pass

    def Open(self, filename, mode = "rb"):
        fullFilename = self.Filename(filename)

        # TODO: Can we use with here?
        return open(fullFilename, mode)
    
    def Filename(self, filename):
        return self.location + filename

class XRDStorageElement(StorageElement):
    def __init__(self, location):
        super(XRDStorageElement, self).__init__(location)

    def __eneter__(self, filename):
        pass
    
    def __exit__(self, *args):
        pass

    def Open(self, filename, mode):
        """ Use the XRD python wrapper """
        pass

    def Filename(self, filename):
        """ Combine with location. Here probably eos:// """
        pass

class Storage(object):
    def __init__(self, storageLocations):
        self.storageLocations = s

lcaolStorage = Storage(config["dirPrefix"])
xrdStorage = Storage("xrd://")

storageMap = dict()
# Put this in config??
storageMap["eos://"] = XRDStorageElement
storageMap["alien://"] = XRDStorageElement
storageMap["file://"] = LocalStorageElement

class XRDStorage(object):
    def __init__(self, storageLocation):
        self.storageLocation = storageLocation

# TODO: Driver function to handle the above!
class StorageAccessType(Enum.enum):
    filename = 0
    openFile = 1

# TODO: Maybe use rootpy to map file modes. But perhaps it is best to avoid root dependencies if possible!

#####
# OLD
#####

#from rootpy import ROOT

# TODO: Can this be a deocrator??
class StorageWrapper(object):
    def __init__(self, storageLocations = None, localStorage = None, remoteStorage = None):
        if storageLocations == None:
            storageLocations = []
        self.storageLocations = storageLocations

    def OpenFile(self, *args, **kwargs):
        if "mode" not in kwargs:
            kwargs["mode"] = "rb"
        self._AccessFile(args, kwargs)

    def WriteFile(self, *args, **kwargs):
        if "mode" not in kwargs:
            kwargs["mode"] = "wb"
        self._AccessFile(args, kwargs)

    # Normal mode should be to return the file,
    # with the option to only return the filename
    def _AccessFile(filePath, mode, rootFile = None):
        if rootFile is None
            # Only check if the user doesn't specify
            if ".root" in filePath:
                rootFile = True
            else:
                rootFile = False

        for storage in storageLocations:
            # Determine if remote
            remoteLocation = False
            if "://" in filePath:
                remoteLocation = True

            # Open file
            try
                f = Open(filePath, mode)
                return f
            except IOError:
                # File doesn't exist - look at remote

        if remoteCache:
            # Write to EOS
            if EOS:
                ROOT.TFile.Cp(os.path.join(eosPath, filePath), localPath)

                try
                    f = Open(filePath, mode)
                    return f
                except IOError:
                    # File doesn't exist. Fatal
            else:

    def writeFile(localCache = False):
        pass
