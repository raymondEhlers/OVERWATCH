# ZMQ Receiver

The ZMQ Receiver handles receiving data from the HLT. Since it is receiving ROOT objects from the HLT, it
depends on ROOT. There is also a minimal dependence on `AliRoot`, but this can be downloaded and compiled
automatically if `AliRoot` is not available.

## Compilation

To compile, from the receiver directory, run

```bash
mkdir build && cd build
# Configure cmake and provide the software locations
# With the options below, it will install to receiver/bin
# Adapt the zmq location. Specifying DAlIROOT is optional.
cmake ../ -DCMAKE_INSTALL_PREFIX="../" -DZEROMQ=/usr/local -DALIROOT="$ALICE_ROOT"
# Compile the executable
make
# Install it
make install
```

## Heartbeat

The ZMQ receivers each emit a heartbeat before request. The file is named `heartbeat.${SYS}Receiver` and
containers the unix time stamp when the heartbeat was created. This can then be monitored via
`overwatchZMQReceiverMonitor`, which will check those time stamps and compare them to the current time, and
send an alert if the heartbeats are too old.
