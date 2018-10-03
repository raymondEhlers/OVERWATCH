#!/usr/bin/env python

import XRootD
from XRootD.client.flags import OpenFlags
import contextlib

import os

def defineFileAccess(basePath):
    if "eos://" in basePath or "xrd://" in basePath:
        def xrdFileWrapper(filename, mode):
            # TODO: May need to select the path more carefully!
            return XRDFile(os.path.join(basePath, filename), mode)
        func = xrdFileWrapper
    else:
        def localFileWrapper(filename, mode):
            return open(os.path.join(basePath, filename), mode)
        func = localFileWrapper
    return func

def defineLocalFile(basePath):
    def localFileWrapper(filename, mode):
        return open(os.path.join(basePath, filename), mode)
    return localFileWrapper

#def defineLocalFile(basePath):
#    def localFileWrapper(filename, mode):
#        return localFile(os.path.join(basePath, filename), mode)
#    return localFileWrapper

@contextlib.contextmanager
def localFile(filename, mode):
    #__basePath__ = ""
    #path = os.path.join(__basePath__, filename)

    print("Filename: {}, mode: {}".format(filename, mode))
    with open(filename, mode) as f:
        try:
            yield f
            print("Finished local file")
        finally:
            print("Finally finished local file")

@contextlib.contextmanager
def XRDFile(filename, mode):
    #__baseUrl__ = ""
    # Translation of modes from rootpy
    # Defined in rootpy.io.root_open.mode_map
    __xrdModes__ = {
        "a": OpenFlags.UPDATE,
        "a+": OpenFlags.UPDATE,
        "r": OpenFlags.READ,
        "r+": OpenFlags.UPDATE,
        "w": OpenFlags.RECREATE,
        "w+": OpenFlags.RECREATE
    }

    print("Filename: {}, mode: {}".format(filename, mode))
    with XRootD.client.File() as f:
        try:
            if mode in __xrdModes__:
                mode = __xrdModes__[mode]
            # Should work despite note being the obivous option
            #path = os.path.join(__baseUrl__, filename)
            status, _ = f.Open(filename, mode)
            if status.ok:
                yield f
            else:
                yield IOError("Failed to open XRD file. Message: {}".format(status.message))
        finally:
            print("Exiting XRD file")

if __name__ == "__main__":
    # Local file example
    func1 = defineFileAccess("data")
    # XRD file example
    func2 = defineFileAccess("xrd://")
