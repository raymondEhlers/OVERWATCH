# Docker

## Building the images

Assuming python 2.7.15

```bash
$ docker build --build-arg PYTHON_VERSION=2.7.15 -t overwatch-base:py2.7.15 -f Dockerfile.build .
# Can also set `--build-arg OVERWATCH_BRANCH="name"` to have it build a particlar branch in the container.
$ docker build --build-arg PYTHON_VERSION=2.7.15 -t overwatch:latest-py2.7.15 -f Dockerfile .
```

For other python versions (such as python 3), simply put in the desired python 3 version. As long as there is
a python base image with that version, it should build (subject to python versions which are supported by
Overwatch).

## Tagged versions

### Base images

The base image contains software which is heavy and/or unlikely to change, such as ROOT, XRootD, etc. It is
build via the `Dockerfile.build` file. Each new version of the build tag will be of the form
`overwatch-base:py3.6.7` (for python 3.6.7). Note that the base image is far too heavy to be built on Travis
(for example, ROOT will often take hours to compile), so the base image must be built on another system (such
as a developer's laptop), and then pushed to docker hub. Once updated, the standard image will use this new
base image.

### Standard images

For actually using Overwatch, one must be use the standard images, which build off the base image and sets up
Overwatch itself. Each release of Overwatch will generate a tag of the form `overwatch:X.Y-py2.7.15`.
Additionally, each commit to master will recreate the latest build, with a tag of the form
`overwatch:latest-py2.7.15`. Equivalent images are also created for python 3.

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

- We use docker logging for the `nginx-proxy` because it is configured for such operation. Supervisor is
  configured to output its logs (and its children's logs) to stdout, so it can also be handled by docker
  logging.
- To access EOS in a docker container, provide the proper grid cert and key, ensure that
  `OVERWATCH_EXECUTABLES` is not set, then run (for example):

    ```bash
    $ docker run --rm -it -v ${PWD}/data:/opt/overwatch/data -v ${PWD}/overwatch:/opt/overwatch/overwatch -v ${PWD}/exec:/opt/overwatch/exec -e config -e gridCert -e gridKey rehlers/overwatch:latest-py3.6.7 /bin/bash
    # In the container (note that a python socket exception is expected)
    $ overwatchDeploy -e config
    # Now everything should be all set!
    # Note that ls on the directory above overwatch my or may not work...
    $ xrdfs eospublic.cern.ch ls /eos/experiment/alice/overwatch
    ```

- To update the nginx template to be used with the nginx container, run in the docker directory:

    ```bash
    $ curl https://raw.githubusercontent.com/jwilder/nginx-proxy/master/nginx.tmpl > nginxProxyGen.tmpl
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

### `docker-gen` fails on startup

For no clear reason, docker-gen sometimes fails at startup with the error `nginx-gen exited with code 2`.
According to this [issue](https://github.com/jwilder/docker-gen/issues/201#issuecomment-227990877), this seems
to occur sometimes and can be solved by replacing the entry point. The cause is not clear, but the fix has
been implemented, and there have been no issues so far.
