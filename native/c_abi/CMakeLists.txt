cmake_minimum_required(VERSION 3.16)
project(cosmos_synaptic_cabi LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(cosmos_synaptic SHARED
  src/cosmos_synaptic.cpp
  ../cpp/src/cosmos_media.cpp
)

target_include_directories(cosmos_synaptic PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/../cpp/include
)

set_target_properties(cosmos_synaptic PROPERTIES
  OUTPUT_NAME cosmos_synaptic
  WINDOWS_EXPORT_ALL_SYMBOLS ON
)
