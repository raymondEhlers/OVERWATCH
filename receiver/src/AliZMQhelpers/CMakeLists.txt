cmake_minimum_required(VERSION 2.8.11)

set(MODULE AliZMQhelpers)

# Download the files from the HLT
foreach(f ZMQ/AliZMQhelpers
          BASE/util/AliOptionParser)
    foreach(extension .h
                      .cxx)
        get_filename_component(filename ${f}${extension} NAME)
        message(STATUS "Downloading file: ${filename}")
        # Download the file from the main AliRoot GitHub repository since it appears to be in sync with the
        # HLT dev repository. Note that if a newer version is necessary and updates are provided, it may be
        # made available in the dev branch of the ALICEHLT/AliRoot fork.
        # TEMP: 18 November 2018 - Need a particular tag because the AliZMQhelpers module isn't easily standalone.
        #       Should be updated in the coming days/weeks, and then we can return to master
        # TEMP: 19 November 2018 - Trying a fix developed by Mikolaj.
        file(DOWNLOAD https://raw.githubusercontent.com/mkrzewic/AliRoot/AliZMQhelpers_fix/HLT/${f}${extension} ${CMAKE_CURRENT_SOURCE_DIR}/${filename} SHOW_PROGRESS)
    endforeach()
endforeach()

include_directories(
  # Variable should be plural to support both ROOT build methods...
  ${ROOT_INCLUDE_DIRS}
  ${ZEROMQ_INCLUDE_DIR}
  )

link_directories(
  ${ROOT_LIBRARY_DIR}
  )

set(SRCS
  AliZMQhelpers.cxx
  AliOptionParser.cxx
  )

set(LIBDEPS ${ROOT_LIBRARIES} ${ZEROMQ_LIBRARIES})

add_library(${MODULE} SHARED ${SRCS})
target_link_libraries(${MODULE} ${LIBDEPS})

# Installation
install(TARGETS ${MODULE}
        ARCHIVE DESTINATION lib
        LIBRARY DESTINATION lib)
