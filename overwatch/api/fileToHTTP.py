#!/usr/bin/env python

import requests
from io import StringIO
import os
import contextlib
import tempfile

import rootpy.io
import rootpy.ROOT as ROOT

host = "http://127.0.0.1:5000/rest/api/v1/files"

class ErrorInGettingFile(Exception):
    def __init__(self, value):
        self.value = value

    def __repr(self):
        return repr("ErrorInGettingFile: {}".format(self.value))

def getFile(filename, fileObject, stream = False):
    print("sending request to {host}/{filename}".format(host = host, filename = filename))
    r = requests.get("{host}/{filename}".format(host = host, filename = filename), stream=True)
    print("response: {}".format(r))
    if r.ok:
        print("Get response is okay! Writing received file")
        # Write in chunks to allow for streaming. See: https://stackoverflow.com/a/13137873
        # To stream a response, we need a generator. See: https://gist.github.com/gear11/8006132#file-main-py-L36
        for chunk in r:
            fileObject.write(chunk.encode())
        # Return to start of file so the read is seamless
        fileObject.seek(0)
        return (r.ok, r.status_code, fileObject)
    else:
        if "error" in r.headers:
            print("ERROR: {}".format(r.headers["error"]))
            raise ErrorInGettingFile(r.headers["error"])

    return (r.ok, r.status_code, fileObject)

def putFile(filename, file = None, localFilename = None):
    """ Use StringIO to write from memory. """
    if not file and not filename:
        print("Please pass a valid file or filename")

    if filename and not file:
        file = open(filename, "rb")

    print("filename: {}, file: {}".format(filename, file))
    r = requests.put("{host}/{filename}".format(host = host, filename = filename), files = {"file": file})
    return (r.ok, r.status_code, r.text)

@contextlib.contextmanager
def FileInMemory(filename, writeFile = False):
    fileInMemory = StringIO()
    try:
        yield getFile(filename = filename, fileObject = fileInMemory)
        print("Successfully completed FileInMemory")
    except IOError as e:
        # Just need an exception so that else is valid.
        print("IOError: {}".format(e))
    else:
        # Only do this if there are no exceptions above
        print("Potentially writing file")
        if writeFile:
            fileInMemory.seek(0)
            (success, status, returnValue) = putFile(filename = filename, file = fileInMemory)
            print("Successfully wrote file")
    finally:
        fileInMemory.close()
        print("Finally exiting from FileInMemory")

# See: https://stackoverflow.com/a/28401296
@contextlib.contextmanager
def FileWithLocalFilename(filename, writeFile = False):
    with tempfile.NamedTemporaryFile() as f:
        try:
            with FileInMemory(filename) as (success, status, fileInMemory):
                if success:
                    print("Writing to temporary file")
                    print("success: {}, status: {}".format(success, status))
                    f.write(fileInMemory.read().encode())
                    f.flush()
                    #f.write("Hello".encode())
                    # Return to start of file so the read is seamless
                    f.seek(0)
                    # May be required to fully flush, although flush() seems sufficient for now
                    # See: https://docs.python.org/2/library/os.html#os.fsync
                    #os.fsync(f.fileno())
                    #print("f.read(): {}".format(f.read()))
                    #f.seek(0)

                    yield f.name
                    #print("Post yield")
                    #f.seek(0, os.SEEK_END)
                    #print("f length in with def: {}".format(f.tell()))
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
                print("Wrote file. success: {}, status: {}, returnValue: {}".format(success, status, returnValue))
        finally:
            print("Finally exiting from FileWithLocalFilename")

if __name__ == "__main__":
    # Get the file
    #(success, status, strIO) = getFile(filename = "246980/EMC/combined")
    writeFile = True
    textFile = True
    textFileTempFile = True
    rootFile = True
    if textFile:
        try:
            #with FileInMemory(filename = "246980/EMC/helloworld.txt", writeFile = True) as (success, status, fileInMemory):
            with FileInMemory(filename = "246980/EMC/EMChists.2015_12_13_5_8_22.root", writeFile = writeFile) as (success, status, fileInMemory):
                if success:
                    # Just to find the length
                    fileInMemory.seek(0)
                    print("fileInMemory.read(): {}".format(fileInMemory.read()))
                    fileInMemory.seek(0, os.SEEK_END)
                    print("success: {}, status: {}, file length: {}".format(success, status, fileInMemory.tell()))
                    fileInMemory.write("Appended information in memory.\n".encode())
                    fileInMemory.seek(0)
                    print("fileInMemory.read(): {}".format(fileInMemory.read()))
                else:
                    print("Failed to retrieve file. status: {}".format(status))
        except ErrorInGettingFile as e:
            print(e)

    if textFileTempFile:
        try:
            with FileWithLocalFilename(filename = "246980/EMC/EMChists.2015_12_13_5_8_22.root", writeFile = writeFile) as filename:
                # Stricktly speaking, this only works on unix! But this should be fine for our purposes,
                # as Overwatch is not designed to work on Windows anyway.
                # "w" does not seem to work properly, even if we page to the end of the file!
                with open(filename, "a+b") as f:
                    print("looking inside if statement")
                    print("Temporary filename: {}".format(filename))
                    f.seek(0, os.SEEK_END)
                    print("f length with localfile: {}".format(f.tell()))
                    f.write("Appended information in temp file.\n".encode())
                    f.seek(0)
                    print("f.read(): {}".format(f.read()))
        except ErrorInGettingFile as e:
            print(e)

    if rootFile:
        try:
            with FileWithLocalFilename(filename = "246980/EMC/EMChists.2015_12_13_5_7_22.root", writeFile = writeFile) as filename:
                print("Temporary filename: {}".format(filename))
                testHist = ROOT.TH1F("testHist", "testHist", 10, 0, 10)
                testHist.Fill(3)
                # Stricktly speaking, this only works on unix! But this should be fine for our purposes,
                # as Overwatch is not designed to work on Windows anyway.
                # "RECREATE" will not work, as the file is being recreated in a way that isn't
                # compatiable with the temp file!
                with rootpy.io.root_open(filename, "UPDATE") as f:
                    print("f.ls()  pre write:")
                    # Needs to be in a separate line. Otherwise, it will print before saying "pre/post write"
                    f.ls()

                    # Write hist
                    testHist.Write()

                    # Needs to be in a separate line. Otherwise, it will print before saying "pre/post write"
                    print("f.ls() post write:")
                    # Needs to be in a separate line. Otherwise, it will print before saying "pre/post write"
                    f.ls()

                # Check that it was written properly
                with rootpy.io.root_open(filename, "READ") as f:
                    print("f.ls() post post write:")
                    # Needs to be in a separate line. Otherwise, it will print before saying "pre/post write"
                    f.ls()
        except ErrorInGettingFile as e:
            print(e)

    # Put the file
    #(success, status, returnText) = putFile("246980/EMC/helloworld.txt", file = open("test.txt", "rb"))
    #print("success: {}, status: {}, returnText: {}".format(success, status, returnText))

    ### Additional testing
    with tempfile.NamedTemporaryFile() as f:
        f.write("Hello".encode())
        f.seek(0)
        print("temp named file: {}".format(f.read()))
        f.seek(0)

        with open(f.name, "rb") as f2:
            print("read f2: {}".format(f2.read()))

