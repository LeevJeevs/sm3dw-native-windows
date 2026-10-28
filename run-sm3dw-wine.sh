#!/bin/bash
# Launcher for running the Windows build under Wine (e.g. outside Bottles, or as the command Bottles runs).
# UNTESTED: written on Windows without access to Wine. Needs a Vulkan-capable driver (SDL3 GPU backend).
cd "$(dirname "$0")" || exit 1
export NWIIU_OFFLINE_STUBS=1
export NWIIU_INSTR_PER_TICK=20
export NWIIU_FAULT_DUMP=1
export WINEDEBUG=${WINEDEBUG:--all}
exec wine build/sm3dw-native/sm3dw-native.exe \
  work/title/0000000000000000_v0/code/RedCarpet.rpx \
  --window --max-instructions 100000000000 --save-root out/save 2> work/run-window.log
