```
# To compile, use
mkdir build && cd build
# Adapt the zmq location
cmake ../ -DCMAKE_INSTALL_PREFIX="../" -DZEROMQ=/usr/local -DALIROOT="$ALICE_ROOT"
# Creates the executables in bin
make
make install
cd ../bin
```
