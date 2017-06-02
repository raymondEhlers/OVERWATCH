cmake_minimum_required(VERSION 2.8.11)

set(MODULE zmqReceive)

if(NOT AliRoot_FOUND)
  # Use local copy
  # Must be enabled to properly format the buffer for HLT messages.
  # For historical reasons, HLT and ROOT buffers are formatted differently.
  add_definitions(-DAliZMQhelpers_AliHLTMessageFormat)
  # Add ZMQ Helpers extracted from AliRoot
  add_subdirectory(AliZMQhelpers)
endif()

include_directories(
  # Variable should be plural to support both ROOT build methods...
  ${ROOT_INCLUDE_DIRS}
  ${ZEROMQ_INCLUDE_DIR}
  )

set(SRCS
  zmqReceiver.cxx
  zmqReceive.cxx
  )

link_directories(
  ${ROOT_LIBRARY_DIR}
  )

set(ALICE_LIBRARIES AliZMQhelpers)

# Also include AliRoot includes if needed
if(AliRoot_FOUND)
  # Add AliRoot include directory explicitly (it is added implicitly by FindAliRoot.cmake)
  include_directories(
    ${ALIROOT}/include
  )

  # Link against the util library to get AliOptionParser
  set(ALICE_LIBRARIES ${ALICE_LIBRARIES} AliHLTUtil)
else()
  # Include our local copy
  include_directories(
    AliZMQhelpers
  )
endif()

add_executable(${MODULE} ${SRCS})
target_link_libraries(${MODULE} ${ROOT_LIBRARIES} ${ZEROMQ_LIBRARIES} ${ALICE_LIBRARIES})

install(TARGETS ${MODULE}  DESTINATION bin)
