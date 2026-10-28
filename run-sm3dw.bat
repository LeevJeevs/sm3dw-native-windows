@echo off
rem Launches the work-in-progress native SM3DW build in a window. NOT a playable game yet.
rem Needs: work\title\0000000000000000_v0 (extracted game, see PROGRESS.md) and build\sm3dw-native\sm3dw-native.exe
rem Console output (stub/fault logs) goes to work\run-window.log. Close the window or press Ctrl+C to stop.
cd /d "%~dp0"
set NWIIU_OFFLINE_STUBS=1
rem Game clock: ~20 guest instructions per console tick (real hardware speed); without it timers fire ~20x too early.
set NWIIU_INSTR_PER_TICK=20
set NWIIU_FAULT_DUMP=1
set NWIIU_IMPORT_STATS=1
build\sm3dw-native\sm3dw-native.exe work\title\0000000000000000_v0\code\RedCarpet.rpx --window --max-instructions 100000000000 --save-root out\save 2> work\run-window.log
echo.
echo Exited with code %ERRORLEVEL%. Log: work\run-window.log
pause
