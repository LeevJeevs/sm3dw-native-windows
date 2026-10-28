@echo off
rem Builds the generated SM3DW program (out\recomp\sm3dw) against the local nWiiURecomp runtime.
rem Prereq: nwiiu-recompile has produced out\recomp\sm3dw. Output: build\sm3dw-native\...\sm3dw-native.exe
set "ROOT=%~dp0.."
set "BUILD_DIR=%ROOT%\build\sm3dw-native"
set "CXXFLAGS=-DNWIIU_MEM2_HEAP_BASE=0x10E40000u"
set "BUILD_TARGET=sm3dw-native"
set EXTRA_CMAKE_ARGS=-D"NWIIU_GENERATED_PROGRAM=%ROOT%\out\recomp\sm3dw" -DNWIIU_GENERATED_PREFIX=sm3dw
call "%~dp0build-nwiiurecomp.bat"
