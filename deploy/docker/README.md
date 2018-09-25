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
