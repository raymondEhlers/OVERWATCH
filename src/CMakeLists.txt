cmake_minimum_required(VERSION 2.8.11)

set(MODULE ZMQ_TEST)

include_directories(
  ${ROOT_INCLUDE_DIR}
  ${ZEROMQ_INCLUDE_DIR}
  )

link_directories(
  ${ROOT_LIBRARY_DIR}
  )

set(ALICE_LIBRARIES AliHLTGlobal AliHLTHOMER HLTbase)

add_executable(zmqReceive zmqReceiver.cxx zmqReceive.cxx)
target_link_libraries(zmqReceive ${ROOT_LIBRARIES} ${ZEROMQ_LIBRARIES} ${ALICE_LIBRARIES})

install(TARGETS zmqReceive DESTINATION bin)
