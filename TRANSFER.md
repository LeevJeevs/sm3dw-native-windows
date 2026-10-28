# Moving the project to the laptop (Arch Linux, MSI Katana GF66)

Everything here is local to the owner's own game copy. Do not upload the game data or the built exe anywhere public.

## Option A (recommended first): run the existing Windows exe in Bottles / Wine — untested
Why it might work: the exe is plain C++ + SDL3 + SDL3's Vulkan GPU backend; Wine forwards Vulkan. The work is CPU-bound,
so Wine's overhead should be small. Not tested: nobody has run it under Wine yet.

Copy these (keep the relative layout):
- `build/sm3dw-native/sm3dw-native.exe` (~190 MB) and, next to it, `SDL3.dll`, `libcrypto-3-x64.dll`, `z.dll`
- `work/title/0000000000000000_v0/` (~1.7 GB: `code/`, `content/`, `meta/`)
- `run-sm3dw-wine.sh` (Linux launcher) or `run-sm3dw.bat` (read it for the exact arguments/env vars)
- an empty folder `out/save/` is created on first run (saves go there)

Bottles: create a Gaming bottle, add `sm3dw-native.exe` as a program, set the launch options
`work/title/0000000000000000_v0/code/RedCarpet.rpx --window --max-instructions 100000000000 --save-root out/save`
and the environment variables `NWIIU_OFFLINE_STUBS=1`, `NWIIU_INSTR_PER_TICK=20`. Set the working directory to the project root.
Prefer Vulkan-capable runner (any recent Wine/Proton-GE). On Arch install the vulkan driver for the GPU
(`nvidia-utils` + `vulkan-icd-loader` for the RTX, or `vulkan-intel` for the iGPU). `NWIIU_INSTR_PER_TICK=20` is mandatory.
Expected today: controller guide -> title -> character-select menu, ~10 fps, stuttering audio. That matches the Windows build.

## Option B: native Linux build — not done yet
The generated code in `out/recomp/sm3dw/` is portable C++20; the runtime uses SDL3, shaderc, zlib/zstd/OpenSSL. A Linux build
needs a CMake invocation like `tools/build-sm3dw-native.bat` does (read it), with `sdl3`, `shaderc`, `zlib`, `zstd`, `openssl`
installed from the Arch repos/AUR, plus `-DCMAKE_BUILD_TYPE=Release` and clang or gcc 13+. Likely trouble spots: MSVC-specific
code in the third-party runtime, case-sensitive file paths in the game content, and `NWIIU_MEM2_HEAP_BASE` (set via CXXFLAGS,
see `tools/env.bat`). I can prepare/verify this on the laptop once there is a shell with the toolchain; I did not attempt it here
because I cannot test Linux from this machine. Native Linux is the better long-term target (no Wine layer, easier profiling).

## To continue development on the laptop
Also copy: `CLAUDE.md`, `PROGRESS.md`, `configs/`, `tools/`, `third_party/nWiiURecomp/` (~7 MB), and (to rebuild without
re-running the recompiler) `out/recomp/` (~570 MB). The extracted `work/rpx/` is only needed by `tools/disasm.py`.
Do NOT copy `build/` for Linux (Windows objects), nor `work/extracted-wua`-style leftovers.

## Recreating `third_party/nWiiURecomp` from this repo
The modified runtime is not committed (it is a nested clone); only the patch is:
```
mkdir -p third_party && cd third_party
git clone https://github.com/BlackLineInteractive/nWiiURecomp.git
cd nWiiURecomp && git checkout d9118564dcedc45facf5adea06729799bfbc6774
git apply --whitespace=nowarn ../../tools/patches/combined-local-changes.patch
```
`out/recomp/sm3dw/` is regenerated from your own `RedCarpet.rpx` with the recompiler and `configs/sm3dw-eu-rev1.toml`
(see PROGRESS.md "reproduce steps"); it is never committed because it is derived from the game binary.
