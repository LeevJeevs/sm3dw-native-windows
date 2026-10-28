# Builds only nWiiURecomp's analyzer (needs OpenSSL + zlib), skipping its runtime
# (which needs shaderc/pkg-config and GCC/Clang). Local scaffolding, not upstream.
cmake_minimum_required(VERSION 3.20)
project(analyzer_only LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(OpenSSL 3.0 REQUIRED COMPONENTS Crypto)
find_package(ZLIB REQUIRED)
enable_testing()
add_subdirectory("${CMAKE_CURRENT_LIST_DIR}/../../third_party/nWiiURecomp/nWiiUAnalyzer" analyzer)
