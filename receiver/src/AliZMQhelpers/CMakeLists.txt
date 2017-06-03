cmake_minimum_required(VERSION 2.8.11)

set(MODULE AliZMQhelpers)

# Download the files from the HLT
foreach(f ZMQ/AliZMQhelpers
          BASE/util/AliOptionParser)
    foreach(extension .h
                      .cxx)
        get_filename_component(filename ${f}${extension} NAME)
        message(STATUS "Downloading file: ${filename}")
        # Download the file from the HLT dev AliRoot repository
        # so that the files are always up to date
        file(DOWNLOAD https://raw.githubusercontent.com/ALICEHLT/AliRoot/dev/HLT/${f}${extension} ${CMAKE_CURRENT_SOURCE_DIR}/${filename} SHOW_PROGRESS)
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
