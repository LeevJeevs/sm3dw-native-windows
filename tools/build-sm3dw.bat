@echo off
rem SM3DW variant of the upstream build: MEM2 heap base moved past this game's .bss (approximation).
set "BUILD_DIR=%~dp0..\build\nwiiurecomp-sm3dw"
set "CXXFLAGS=-DNWIIU_MEM2_HEAP_BASE=0x10E40000u"
call "%~dp0build-nwiiurecomp.bat"
