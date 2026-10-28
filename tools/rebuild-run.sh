#!/bin/bash
# Rebuild the SM3DW native exe (incremental) and run it. Usage: tools/rebuild-run.sh [max-instructions]
cd "$(dirname "$0")/.." || exit 1
cmd //c "tools\build-sm3dw-native.bat" > work/build-sm3dw-native-inc.log 2>&1 || { echo BUILD FAILED; grep -E "error C|LNK[0-9]|CMake Error" work/build-sm3dw-native-inc.log | head -8 | cut -c1-240; exit 1; }
T=work/title/0000000000000000_v0/code/RedCarpet.rpx
s=$(date +%s)
NWIIU_FAULT_DUMP=1 NWIIU_IMPORT_STATS=1 NWIIU_OFFLINE_STUBS=1 NWIIU_FS_TRACE=1 timeout 900 ./build/sm3dw-native/sm3dw-native.exe $T --max-instructions ${1:-3000000000} --save-root out/save > work/native-run.log 2>&1
echo "run: $(( $(date +%s)-s ))s rc=$?  fs-opens=$(grep -c FSOPEN work/native-run.log)"
grep -E "^(OFFLINE-STUB|SYSCONFIG-STUB|ALLOC-FAIL|FAULT-DUMP|IMPORT-TIME)" work/native-run.log | head -40
grep -E "^STOP|^PC|^LR|^Instructions|^Import|^Address|^Instruction:|^Arguments|INPUT|^Native" work/native-run.log | cut -c1-200
