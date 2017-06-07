cmake_minimum_required(VERSION 2.8.11)

set(MODULE zmqReceive)

if(NOT AliRoot_FOUND)
  # Download and use local copy
  # NOTE: We don't need to use the MessageFormat switch!
  #       It is only needed when sending with the new library and receiving with the old. Which we don't do,
  #       so we don't need to worry about it!

  # Add ZMQ Helpers extracted from AliRoot
  add_subdirectory(AliZMQhelpers)
endif()

# Add wanning options (not included for AliZMQhelpers since that code isn't under our control)
SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Werror")

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

install(TARGETS ${MODULE} DESTINATION bin)
