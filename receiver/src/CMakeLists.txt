cmake_minimum_required(VERSION 2.8.11)

set(MODULE ZMQ_TEST)

include_directories(
  # Variable should be plural to support both ROOT build methods...
  ${ROOT_INCLUDE_DIRS}
  ${ZEROMQ_INCLUDE_DIR}
  )

link_directories(
  ${ROOT_LIBRARY_DIR}
  )

set(ALICE_LIBRARIES AliHLTGlobal HLTbase AliHLTUtil)

add_executable(zmqReceive zmqReceiver.cxx zmqReceive.cxx)
target_link_libraries(zmqReceive ${ROOT_LIBRARIES} ${ZEROMQ_LIBRARIES} ${ALICE_LIBRARIES})

install(TARGETS zmqReceive DESTINATION bin)
