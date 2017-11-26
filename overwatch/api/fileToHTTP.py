#!/usr/bin/env python

import requests
import json
import StringIO # Should I use the io module instead?
import os
import contextlib
import tempfile

host = "http://127.0.0.1:5000/rest/api/v1/files"

def getFile(filename, fileObject):
    fileInMemory = StringIO.StringIO()
    r = requests.get("{host}/{filename}".format(host = host, filename = filename), stream=True)
    print("response: {}".format(r))
    if r.ok:
        for chunk in r:
            fileObject.write(chunk)
        # Return to start of file so the read is seamless
        fileObject.seek(0)
        return (r.ok, r.status_code, fileObject)
    
    return (r.ok, r.status_code, fileObject)

@contextlib.contextmanager
def FileInMemory(filename, writeFile = False):
    try:
        fileInMemory = StringIO.StringIO()
        yield getFile(filename = filename, fileObject = fileInMemory)
    finally:
        fileInMemory.close()

# See: https://stackoverflow.com/a/28401296
@contextlib.contextmanager
def FileWithLocalFilename(filename, writeFile = False):
    with tempfile.NamedTemporaryFile() as f:
        try:
            with FileInMemory(filename) as (success, status, fileInMemory):
                if success:
                    print("Writing to temporary file")
                    print("success: {}, status: {}".format(success, status))
                    f.write(fileInMemory.read())
                    #f.write("Hello")
                    # Return to start of file so the read is seamless
                    f.seek(0)
                    f.flush()
                    # May be required to fully flush, although flush() seems sufficient for now
                    # See: https://docs.python.org/2/library/os.html#os.fsync
                    #os.fsync(f.fileno())
                    #print("f.read(): {}".format(f.read()))

                    yield f.name

                    #print("Post yield")
                    #f.seek(0, os.SEEK_END)
                    #print("f length in with def: {}".format(f.tell()))

                    fileInMemory.close()
                else:
                    #yield (False, status, fileInMemory)
                    yield False
                print("Successfully completed FileWithLocalFilename")
        except IOError as e:
            # Just need an exception so that else is valid.
            print("IOError: {}".format(e))
        else:
            # Only do this if there are no exceptions above
            print("Potentially writing file")
            if writeFile:
                (success, status, returnValue) = putFile(filename = filename, file = f)
                print("Successfully wrote file")
        finally:
            print("Finally exiting from FileWithLocalFilename")

def GetFileWithLocalFilename(object):
    def __init__(self, filename):
        self._filename = filename

    def __enter__(self):
        (success, status, fileInMemory) = getFile(self._filename)

        if success:
            f.write(fileInMemory.read())
            return f.name

    def __exit__(self, *args, **kwargs):
        self._temporaryFile.close()


def putFile(filename, file = None, localFilename = None):
    """ Use StringIO to write from memory. """
    if not file and not filename:
        print("Please pass a valid file or filename")

    if filename and not file:
        file = open(filename, "rb")

    r = requests.put("{host}/{filename}".format(host = host, filename = filename), files = { "file": file })
    return (r.ok, r.status_code, r.text)

if __name__ == "__main__":
    # Get the file
    #(success, status, strIO) = getFile(filename = "246980/EMC/combined")
    with FileInMemory(filename = "246980/EMC/combined") as (success, status, fileInMemory):
        # Just to find the length
        fileInMemory.seek(0, os.SEEK_END)
        print("success: {}, status: {}, file length: {}".format(success, status, fileInMemory.tell()))

    with FileWithLocalFilename(filename = "246980/EMC/combined") as filename:
        # Stricktly speaking, this only works on unix! But this should be fine for our purposes,
        # as Overwatch is not designed to work on Windows anyway.
        with open(filename, "rb") as f:
            print("looking inside if statement")
            print("Temporary filename: {}".format(filename))
            f.seek(0, os.SEEK_END)
            print("f length with localfile: {}".format(f.tell()))
            #f.seek(0)
            #print("f.read(): {}".format(f.read()))

    # Put the file
    (success, status, returnText) = putFile("246980/EMC/helloworld.root", file = open("test.txt", "rb"))
    print("success: {}, status: {}, returnText: {}".format(success, status, returnText))

    ### Additional testing
    with tempfile.NamedTemporaryFile() as f:
        f.write("Hello")
        f.seek(0)
        print("temp named file: {}".format(f.read()))
        f.seek(0)

        with open(f.name, "rb") as f2:
            print("read f2: {}".format(f2.read()))

