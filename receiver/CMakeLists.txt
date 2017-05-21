cmake_minimum_required(VERSION 2.8.11)
project(zmqReceiver)
set (CMAKE_MODULE_PATH "${zmqReceiver_SOURCE_DIR}/cmake")
     
# Old style root build process
execute_process ( COMMAND root-config --etcdir WORKING_DIRECTORY /tmp OUTPUT_VARIABLE ROOT_ETCDIR OUTPUT_STRIP_TRAILING_WHITESPACE )
set( CMAKE_MODULE_PATH "${CMAKE_MODULE_PATH};${ROOT_ETCDIR}/cmake" )
# New style root build process (with CMake)
# From: https://root.cern.ch/how/integrate-root-my-project-cmake
# (May not be entirely required...)
list(APPEND CMAKE_PREFIX_PATH $ENV{ROOTSYS})

# Ensure compilation with c++11
SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
if(CMAKE_CXX_COMPILER_ID EQUAL Clang)
  SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -stdlib=libc++")
endif(CMAKE_CXX_COMPILER_ID EQUAL Clang)

find_package(ROOT REQUIRED)

if (ROOT_FOUND)
    message (STATUS "ROOT found via root-config --etcdir and etc/FindROOT.cmake : CMAKE_MODULE_PATH: ${CMAKE_MODULE_PATH}")
  # Check for ROOT Version for C++11 support
  execute_process(COMMAND root-config --version OUTPUT_VARIABLE ROOT_VERSION ERROR_VARIABLE error OUTPUT_STRIP_TRAILING_WHITESPACE )
  if(error)
    message(FATAL_ERROR "Error retrieving ROOT version : ${error}")
  endif(error)
  string(STRIP "${ROOT_VERSION}" ROOT_VERSION)
  string(REGEX REPLACE "^([0-9]+)\\.[0-9][0-9]+\\/[0-9][0-9]+.*" "\\1" ROOT_VERSION_MAJOR "${ROOT_VERSION}")
  string(REGEX REPLACE "^[0-9]+\\.([0-9][0-9])+\\/[0-9][0-9]+.*" "\\1" ROOT_VERSION_MINOR "${ROOT_VERSION}")
  string(REGEX REPLACE "^[0-9]+\\.[0-9][0-9]+\\/([0-9][0-9]+).*" "\\1" ROOT_VERSION_PATCH "${ROOT_VERSION}")
  if(${ROOT_VERSION_MAJOR} GREATER 5)
    SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
    if(CMAKE_CXX_COMPILER_ID EQUAL Clang)
      SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -stdlib=libc++")
    endif(CMAKE_CXX_COMPILER_ID EQUAL Clang)
  endif()
endif (ROOT_FOUND)

if (ROOT-NOTFOUND)
    message (STATUS "ROOT not found - checking with the provided FindROOT.cmake")
    set(CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake" ${CMAKE_MODULE_PATH})
    message (STATUS "+ROOT CMAKE_MODULE_PATH: ${CMAKE_MODULE_PATH}")
    find_package(ROOT REQUIRED)
endif(ROOT-NOTFOUND)

find_package(ZeroMQ REQUIRED)
find_package(AliRoot REQUIRED)

add_subdirectory(src)
