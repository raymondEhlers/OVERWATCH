cmake_minimum_required(VERSION 2.8.11)
project(zmqReceiver)
set(CMAKE_MODULE_PATH "${zmqReceiver_SOURCE_DIR}/cmake")

# Set policies
# CMP0042 - MACOSX_RPATH is enabled by default (v3.0)
if(POLICY CMP0042)
  cmake_policy(SET CMP0042 NEW)
endif()

# RPATH settings
# Enable MACOS_RPATH
set(CMAKE_MACOSX_RPATH TRUE)

# Additional settings from: https://cmake.org/Wiki/CMake_RPATH_handling#Always_full_RPATH
# use, i.e. don't skip the full RPATH for the build tree
set(CMAKE_SKIP_BUILD_RPATH  FALSE)

# when building, don't use the install RPATH already
# (but later on when installing)
set(CMAKE_BUILD_WITH_INSTALL_RPATH FALSE)

# Set install RPATH
set(CMAKE_INSTALL_RPATH "${CMAKE_INSTALL_PREFIX}/lib")

# add the automatically determined parts of the RPATH
# which point to directories outside the build tree to the install RPATH
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)

# the RPATH to be used when installing, but only if it's not a system directory
list(FIND CMAKE_PLATFORM_IMPLICIT_LINK_DIRECTORIES "${CMAKE_INSTALL_PREFIX}/lib" isSystemDir)
if("${isSystemDir}" STREQUAL "-1")
    set(CMAKE_INSTALL_RPATH "${CMAKE_INSTALL_PREFIX}/lib")
endif("${isSystemDir}" STREQUAL "-1")
     
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
# If ALIROOT is passed, then use it.
# Otherwise, it will automatically download the requisite files.
if(ALIROOT)
    find_package(AliRoot REQUIRED)
else()
    message(STATUS "AliRoot was not passed, so the necessary AliZMQ files will be downloaded automatically!")
endif()

add_subdirectory(src)
