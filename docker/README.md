# Docker

## Build for python 2.7

Assuming python 2.7.15

```bash
$ docker build --build-arg PYTHON_VERSION=2.7.15 -f Dockerfile.build .
$ docker tag <firstImageID> overwatch-base:py2.7.15
$ docker build --build-arg PYTHON_VERSION=2.7.15 -f Dockerfile .
$ docker tag <secondImageID> overwatch:master-py2.7.15
```

For python 3, simply put in the desired python 3 version.

## Tagged versions

Each release of Overwatch will generate a tag of the form `overwatch:X.Y-py2.7.15`. Additionally, each commit
to master will recreate the latest build, with a tag of the form `overwatch:latest-py2.7.15`. Equivalent
images are also created for python 3.

Docker images will automatically be created by Travis CI for both python 2 and python 3. In detail, any commit
to master or to any branch with a name that contains `-docker` will create an image. These images will be
tagged as `latest-pyX.Y.Z` (as described above). Git tags will also automatically trigger the building of
images.

## Notes on logging

Since we use supervisor, we use that to handle the logs. Then, we need to select a location for those logs.
Although it appears that it would be convenient to put them in the `dataFolder` directory, this is problematic
because they will be accessible through the `webApp`. Instead, we put them in the `exec` directory, which is a
directory dedicated to files generated during execution. It may also contain configuration files, etc.

Note that we explicitly keep empty `logs`, `config` and `sockets` directories inside of the `exec` directory
in the git repository to ensure that supervisor doesn't fail to execute due missing those directories. It is
not required to use the directories in the repository, but it certainly is convenient.

## Common errors

If you see:

```bash
error: <class 'ConnectionRefusedError'>, [Errno 111] Connection refused: file: /usr/local/lib/python3.6/socket.py line: 713
```

without any further context at the end of executing `overwatchDeploy`, you should check the value of
`supervisor` in the config. If it is enabled, this error corresponds to `supervisor` being asked to update
when it is not running. If you didn't intend to use `supervisor` (for example, if you executed
`overwatchDeploy` manually), then this error is harmless.
