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

## uwsgi and ZODB

Since uwsgi runs a large number of python interpreters, it will only work with ZODB when the database is
served externally!

## Modifying the hosts file on mac OS

To test the `nginx` proxy, the only good way I've found is to add the address to the local hosts file. This
can be accomplished by:

```bash
# Make necessary edits
$ sudo vim /etc/hosts
# Clear the DNS cache
$ sudo dscacheutil -flushcache
```

Note that `dnsmasq` didn't seem to work (although it certainly should have, so I must have missing
something...).

One can also add a request header `Host: <address>`. Via curl, this would look like `curl -H "Host:
dev.aliceoverwatch.physics.yale.edu" localhost`, while for the browser, the custom header must be set with an
extension. Regardless of how the request is made, this headers approach will fail on redirects in the web app.

## Variables to configure for Docker

`config` should be the set to the Overwatch deploy config via `export config="$(cat deployConfig.yaml)"`.
Similar variables should be configured for the grid certificate, grid key, and ssh key.

### IP address and external access

[This stack overflow answer](https://stackoverflow.com/a/24326540) is particularly useful for understanding
how and when to make containers accessible to the outside world.

`externalIP` should be set to the IP address where we want the Overwatch services to be externally accessible.
Usually, we don't want this to happen (I'm not sure of when we would), but it is left as an option for
completeness. It defaults to `127.0.0.1` (ie not externally accessible).

`nginxIP` should be set to the IP address where we want the `nginx` reverse proxy to be available. Generally,
this is our external facing server, so this defaults to `0.0.0.0`.

## Additional docker notes

- We use docker logging for the `nginx-proxy` because it is configured for such operation. However, since we
  use supervisor in the Overwatch containers, we have supervisor handle the logs for us.
- To access EOS in a docker container, provide the proper grid cert and key, ensure that
  `OVERWATCH_EXECUTABLES` is not set, then run (for example):

    ```bash
    $ docker run --rm -it -v ${PWD}/data:/opt/overwatch/data -v ${PWD}/overwatch:/opt/overwatch/overwatch -v ${PWD}/exec:/opt/overwatch/exec -e config -e gridCert -e gridKey rehlers/overwatch:latest-py3.6.6 /bin/bash
    # In the container
    $ overwatchDeploy -e config
    # Now everything should be all set!
    $ xrdfs eospublic.cern.ch ls /eos/experiment/alice
    ```

## Common errors

### Socket error

If you see:

```bash
error: <class 'ConnectionRefusedError'>, [Errno 111] Connection refused: file: /usr/local/lib/python3.6/socket.py line: 713
```

without any further context at the end of executing `overwatchDeploy`, you should check the value of
`supervisor` in the config. If it is enabled, this error corresponds to `supervisor` being asked to update
when it is not running. If you didn't intend to use `supervisor` (for example, if you executed
`overwatchDeploy` manually), then this error is harmless.

### `rsync` errors

If you see something like:

```bash
Permission denied (publickey).
rsync: connection unexpectedly closed (0 bytes received so far) [sender]
rsync error: unexplained error (code 255) at io.c(235) [sender=3.1.2]
```

this is often caused by `rsync` being unable to use the ssh private key. In particular, if the key has a
passphrase, rsync will not be able to use it in this mode. To resolve it, provide a key without a passphrase
(of course taking appropriate care to ensure that such a key is kept well protected).
