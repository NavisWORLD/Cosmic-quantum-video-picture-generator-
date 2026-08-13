cmake_minimum_required(VERSION 3.16)
project(cosmos_quantum_media_core VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(cosmos_media STATIC src/cosmos_media.cpp)
target_include_directories(cosmos_media PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(cosmos_media_demo examples/demo.cpp)
target_link_libraries(cosmos_media_demo PRIVATE cosmos_media)

include(CTest)
if(BUILD_TESTING)
  add_executable(cosmos_media_tests tests/test_core.cpp)
  target_link_libraries(cosmos_media_tests PRIVATE cosmos_media)
  add_test(NAME cosmos_media_core COMMAND cosmos_media_tests)
endif()
