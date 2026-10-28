# Super Mario 3D World – native Windows port investigation

Status: **Milestone 0 (identification and tooling) done. No port exists yet. Nothing here runs the game.**

## 1. What the local files are (verified by inspection)

| Item in Downloads | Finding |
|---|---|
| `super-mario-3-d-world-bowsers-fury-010028600-ebda-000v-1.1.0\*.xci` (3.17 GB) | Switch title ID `010028600EBDA000` v1.1.0 by name, but **every sampled byte (9 offsets × 64 KiB) is zero** and the `_meta.xml` is blank. It is an empty pre-allocated placeholder (likely an unfinished torrent). **Unusable.** |
| `…_archive.torrent` | Torrent file for the above. Not used. |
| `Super Mario 3D World (Europe) (En,Fr,De,Es,It,Nl,Pt,Ru) (Rev 1).7z` (1.5 GB) | Contains a Cemu `.wua` (ZArchive, valid footer, zstd) + notes. **Extracted and used.** |
| `… (Rev 1) (1).7z` (2.9 GB) | Contains a `.wux`; per its notes it is the same Redump disc. Not extracted (redundant; ~2.9 GB). |

Identified edition (from `code/app.xml`, `meta/meta.xml`, archive notes):
- Platform **Wii U**, region **Europe** (`region=00000004`), disc **Rev 1**
- Title ID `0005000010145D00`, product code `WUP-P-ARDP`, SDK 20922, title version 0
- Notes claim Redump ISO SHA-1 `45268547c6f13d16ef48c78f6f9d80e00d46b9a2` (**not independently re-verified**; I only have the converted NKit/WUA, not the ISO)
- Main executable: `code/RedCarpet.rpx`, 7,227,136 bytes, SHA-1 `09e104248e04bfcc7fa99fdb60456a680e5b1f5a`
- This is the **Wii U game only**. There is no Bowser's Fury / Switch content available locally.

Archive: 3,057 files. Asset dirs: ObjectData (~1.8k), StageData (~690), SoundData, CubeMapTextureData, LayoutData, ShaderData, LocalizedData, etc. (Nintendo SARC/`.szs`, BFRES/GX2-era formats; not yet parsed.)

## 2. Executable facts (from `tools/rpxinfo.py`, output in `work/rpx/rpxinfo.txt`)

- ELF32 big-endian, PowerPC (Espresso), 40 sections, entry `0x026afba0`
- `.text` 7.3 MB @ `0x02000020`; `.rodata` 3.9 MB @ `0x10000000`; `.data` 130 KB; `.bss` ~10.9 MB; large `.rela.*` (relocations present, helpful for code/data separation)
- Imports 25 Cafe OS libraries: coreinit (1039 fn), **gx2** (342), snd_core/snd_user, vpad/vpadbase/padscore (input, GamePad + Pro/Wiimote), nn_save, nn_acp, sysapp, proc_ui, plus online stuff (nn_olv, nn_boss, nn_ac, nn_act, nlibcurl, nsysnet) and camera/mic.
- `.symtab` has 587 entries, **only import stubs; the game's own functions are stripped** (no names, no sizes).

## 3. Research summary (what exists publicly; checked by fetching the pages)

- No public decompilation or native port of the Wii U SM3DW found. A web search returned only a passing mention in a news piece that a Switch port is "in development" (single line, no details). I could not verify it. ([DSOGaming via search](https://www.dsogaming.com/?p=197549))
- [BlackLineInteractive/nWiiURecomp](https://github.com/BlackLineInteractive/nWiiURecomp): PowerPC→C++ recompiler for RPX with HLE of Cafe OS and an interpreter fallback. Its README names **only Wind Waker HD EU as validated**, does not mention SM3DW, and does not state GX2/audio coverage or that it is playable. It also depends on a Cemu-derived host. Treat as a candidate foundation, **unproven for this game**.
- DolRecomp (GameCube/Wii, "experimental" Wii U RPX loading, CPU only, no runtime) was only seen in a search summary. **Not verified.**
- [Exzap/ZArchive](https://github.com/Exzap/ZArchive): the `.wua` container spec (source read directly). `tools/zar.py` is my reimplementation of the reader from that source.

## 4. Feasibility (candid)

Reusable: ZArchive reader (done), RPX loader/parser (basic, done), PowerPC recompiler tech from public projects (unproven for this title), Cemu-style knowledge of GX2/coreinit semantics.

Must be built or validated, in rough order of risk:
1. **Static recompilation of ~7 MB of stripped Espresso code** (paired-singles FP heavy, indirect calls/vtables, jump tables). Needs function discovery without symbols; relocations help.
2. **Cafe OS HLE**: coreinit (threads, memory heaps, FS, alarms, MP-style 3-core scheduling), proc_ui, sysapp, nn_save/acp. The game uses 3 cores; threading semantics must be right for correct game speed.
3. **GX2 → modern GPU API** (D3D12/Vulkan): texture formats/tiling (AMD R6xx), the game's Latte shaders (`ShaderData`) must be translated; render targets, GamePad second screen.
4. **Audio** (snd_core/AX DSP-style mixing), **input** (vpad/padscore → XInput/SDL with remap, dead zones, hot-plug), **saves** (nn_save → local folder).
5. Frame pacing: the game is natively 60 fps on Wii U in most stages; gameplay is tied to its main loop, so a separate render-timing layer is a later task and needs evidence from the recompiled loop.

Unknown: whether any existing recompiler can already boot this RPX to the title screen; how the game uses the GamePad screen/gyro; copy-protection or OS-version checks. These can only be answered by running experiments.

Honest scope: a *complete* playable port is a very large, multi-month effort (comparable to the recompilation projects cited above). Realistic early milestones are listed below; none is "a playable port."

## 5. Milestones

| # | Milestone | State |
|---|---|---|
| 0 | Identify edition; ZArchive reader; RPX inspector | **Done** (this doc) |
| 1 | Toolchain (MSVC/CMake/Ninja from VS 2026) and reproducible build | **Done** |
| 2 | Evaluate nWiiURecomp; analyze + recompile whole `.text` to C++ | **Done for translation** (all 1.83 M instr emitted; full compile/link not yet) |
| 3 | Native exe + platform layer + enough coreinit HLE to reach `main` | **In progress**: interpreter runs ~5.1 M instr, blocked on shared system fonts/HLE |
| 4 | Asset loading (SARC/BFRES/BNTX-era formats via ZArchive virtual FS) | Not started |
| 5 | GX2 renderer, then audio, saves, remappable input | Not started |
| 6 | Timing/60 fps, resolution/aspect options, polish | Not started |

## 5b. Milestone 1 result: toolchain + third-party analyzer run on this RPX

Toolchain: Visual Studio 2026 Community was already installed (MSVC 14.50, bundled CMake 4.1.1 and Ninja). `tools\env.bat` loads it. vcpkg cloned to `third_party\vcpkg` (OpenSSL 3.6.5, zlib 1.3.2 installed).

Third party: `third_party\nWiiURecomp` (shallow clone of BlackLineInteractive/nWiiURecomp, GPLv3, commit `d911856`). Its README says the repo ships `configs/*.toml` profiles, but **`configs/` is not in the clone** (git-ignored upstream), so I used `--any-title`.
- Its **analyzer** compiles unmodified under MSVC (only my wrapper `tools\analyzer-only\CMakeLists.txt` is added, to skip its runtime). Its 5 unit tests pass (`ctest`).
- Ran `nwiiu-analyze --any-title work\rpx\RedCarpet.rpx out\sm3dw-eu-rev1-manifest.json` (2.3 s, 66 MB JSON):
  - 40 sections, 228,127 relocations, **58,749 functions**, 1,833,762 instructions (counted 100% of `.text`; this may include data/padding inside `.text`, not verified)
  - Function discovery sources: relocation 28,579, direct call 21,670, direct branch 7,308, jump-table 2,228
  - **959 unresolved**: all `indirect_branch: jump table base not recovered`. These need work before full static recompilation.
  - Exit code 3 because unresolved is non-empty (this is the tool's design, not a crash).
- This shows the RPX parses and its code can be partitioned. It does **not** show the code recompiles or runs.
- Upstream's "windowed port" path is a Cemu-derived host (an emulator). That path is **not** a native port and is not used here.
- Not yet attempted: upstream's runtime/recompiler (`nwiiu-recompile`). It needs shaderc via pkg-config, and its `-Werror` flags are GCC/Clang-only, so MSVC may fail. A shaderc install was started (see below).

### Disk space (resolved)
The drive was full (0.8 GB free) and vcpkg's shaderc build failed with `No space left on device`. At the user's request I deleted 18 installer files from Downloads (5.3 GB) plus my own regenerable build leftovers (vcpkg buildtrees/packages, the extracted `.wua`). Free space afterwards: ~14 GB. shaderc, OpenSSL and zlib are now installed under the `x64-windows-release` overlay triplet (`toolscpkg-triplets`).

## 5c. Milestone 2: upstream recompiler + runtime built under MSVC and run on this RPX

All of `third_party
WiiURecomp` (analyzer, runtime, recompiler, tests) builds under MSVC with no compile errors (`toolsuild-nwiiurecomp.bat`). Tests: **33/36 pass**. The 3 failures are environmental, not logic: `cafe_filesystem_test` (needs symlink privilege), `recompile_cli_test` (shells out through a path with spaces), `native_test` (git `autocrlf` gives the fixture CRLF; with an LF copy it **passes**, exit 0, verified).

Recompiling `RedCarpet.rpx` initially stopped on unsupported instructions. Local changes (kept as `tools\patches\combined-local-changes.patch`, GPLv3 upstream, not yet offered upstream):
1. `fdivs` was missing from the generator's support gate even though the emitter and interpreter implement it: 1,308 rejected blocks fell to 26 (1,282 were `fdivs`).
2. Added `ps_mr`, `ps_div`, `eqv`, `subfme`, `addme`, `lfdu` (semantics, interpreter, generator). **Not unit-tested**; they follow the sibling instructions' patterns and have only been exercised by compiling. Treat as unverified until tested against known results.
3. Directory rename retry (Windows denied renaming the output dir, probably a scanner holding file handles).

Result of `nwiiu-recompile --config configs\sm3dw-eu-rev1.toml` (14 s): **exit 0; 401,351 blocks, 1,833,762 instructions (all), 3,136 C++ shards, ~570 MB** in `out
ecomp\sm3dw` (generated, not committed anywhere). Three sample shards (0000, 1500, 3000) compiled with MSVC /O2 (~4 s each, warnings only). **The full set has NOT been compiled or linked**, so nothing native has been run yet. The 959 unresolved jump tables from the analyzer are not reflected as failures here; whether they matter at runtime is unknown.

Interpreter bring-up (`nwiiu-run`, upstream's headless interpreter with HLE; used only as a validation tool):
- The runtime hardcodes Wind Waker HD's memory map (MEM2 heap at `0x10520000`), which collides with this game's `.bss` (ends `0x10E3A4A0`). I made the base overridable (`NWIIU_MEM2_HEAP_BASE`) and chose `0x10E40000` for SM3DW (`toolsuild-sm3dw.bat`). **That value is my approximation, not verified Cafe behaviour.**
- With that, the game's own code runs: **~3.55 M instructions** to the first unimplemented import (`coreinit:MCP_Open`), then **~5.12 M** after scaffolding stubs for `MCP_Open`/`MCP_Close` (`tools\hle_iter.py`).
- Next wall: `nn_save:SAVEGetSharedDataTitlePath` for title `0005001B-10056000`, the console's shared system fonts. These are not on the game disc. With my "not found" stub the game dereferences a null object (fault at PC `0x02508020`, read of `0x8C`). The runtime has a `--shared-font <ttf>` option, so a font from a Wii U console may be needed. **I do not have one and did not fabricate one.**
- All stubs in the clone are labelled `SCAFFOLDING`; they are guesses to find the next failure, not implementations.

Realistic reading: the pipeline translates the code and the game starts executing, but this is a very early point. Every remaining Cafe OS API the game touches (hundreds across coreinit, gx2, snd, vpad, nn_save, proc_ui…) must be implemented for real, and GX2 rendering, audio and input are not done at all in a way that targets Windows (upstream's windowed path is Cemu-based, which we are not using).

## 5d. Milestone 3: content mounted, Yaz0 hook, native build started (2026-10-26)

**Correction to 5c.** The "shared system fonts" wall was misdiagnosed twice. (1) The strings are `FFLResMiddleLG.dat`/`FFLResHighLG.dat`: the console's Mii face-library resources, not fonts. (2) More importantly, the failure only occurred because the runner derives the content root from the RPX location (`<title>/code/x.rpx` -> `<title>/content`); my RPX copy sat in `work/rpx/`, so **no content was mounted**. Running `work/title/0000000000000000_v0/code/RedCarpet.rpx` (full extraction, 1.61 GiB, via `tools\zar.py extract`) mounts `/vol/content`, and the game then opens `ResourceSystem.szs` and `EffectData.szs` successfully (FS trace result=0) with no FFL open. The `title_root` key in `configs\sm3dw-eu-rev1.toml` is ignored by `nwiiu-run`. Whether the Mii files are needed later is unknown.

- **Yaz0 hook** (profile `[hle_hooks]`: `"026BBC20" = "Yaz0Decode"`). The game's decompressor at `0x026BBC20` was identified from the `Yaz0` magic check and read in disassembly (`tools\disasm.py`, needs `pip install capstone`). It matches upstream's hook contract (r3=dst, r4=stream, size at +4, payload at +0x10, returns size; same overrun-exit behaviour; `dcbz` only touches memory about to be overwritten). **Not yet verified by output comparison**, and the speed-up is untimed.
- **Interpreter speed:** measured ~130,000 guest instr/s (6 M instr = 46 s, 10 M = 76 s; 20 M and 40 M did not finish in 120 s). A full boot needs billions, so the interpreter cannot get to the title screen. This is why the native build matters.
- **Diagnostic hooks** `ReturnZero`/`ReturnOne` added to the local runtime. Hooking `0x0261F624` (assumed FFL init) never fired, i.e. the game does not reach the Mii path through the static call graph. Removed from the profile.
- **Native build:** `nwiiu-recompile` regenerated `out
ecomp\sm3dw` (3,136 shards, hook table included). SDL3 3.4.18 installed via vcpkg. `toolsuild-sm3dw-native.bat` builds `sm3dw-native` (~3,175 steps, ~30 steps/min on 14 cores). Generated `main.cpp` uses upstream's header-only SDL3 renderer (`wwhd_renderer.h`, written for Wind Waker HD, window title hard-coded to it); its suitability for this game is unknown.
- Status at time of writing: compile in progress, **no errors so far**, not linked, not run.

**Estimated progress to a testable build:** roughly 10% (judgement, not measurement). Biggest unknowns: Cafe OS HLE breadth and the GX2/Latte graphics path.

### HLE gap analysis (name match only; a handler may still be partial)
The game imports **563 distinct functions** (the "entries" counts printed earlier by `rpxinfo.py` were not function counts). The runtime registers a handler by name for about **241**; about **322 have none**. Per library (imported / has-handler): coreinit 143/99, gx2 134/80, snd_core 67/29, nn_olv 41/8, nsysnet 25/0, padscore 18/6, snd_user 17/0, nlibcurl 17/0, nn_save 14/8, vpad 6/2, proc_ui 8/3, zlib125 6/0, sysapp 3/0, camera 1/0, mic 9/0. Full missing list: `out\hle-gap.txt` (regenerate with the script in this section's commit history / re-derive from the analyzer manifest). Online/Miiverse/network/camera/mic libraries can likely be stubbed as "unavailable"; gameplay-critical gaps are coreinit, gx2, snd_core/snd_user, vpad/padscore, proc_ui, nn_save, zlib.

## 5e. Milestone 4: native executable links, runs, and its main loop ticks (2026-10-26)

- **Native build:** `toolsuild-sm3dw-native.bat` compiled all 3,175 steps (3,136 recompiled shards + runtime) with **zero errors** and linked `build\sm3dw-native\sm3dw-native.exe` (159 MB). Incremental rebuild + 60 s run is ~90 s: `tools
ebuild-run.sh [max-instr]`.
- **Speed:** ~4-10 M guest instr/s native vs ~0.13 M/s in the interpreter (30x+). (An earlier "stall" was a misjudgement: a 1.345 B budget needs >200 s at this rate.)
- **Progress:** the game runs >1.6 billion guest instructions, opens 84 files, creates/resumes 14 threads, loads the **EuEn** locale, builds ~6,400 shader display lists, and its **main loop runs: 971 frames** in a 1.45 B-instruction run (971 each of `GX2SwapScanBuffers`, `GX2WaitForVsync`, `VPADRead`, `ProcUIProcessMessages`; ~1,900 scan-buffer copies = TV + GamePad). 134,558 `GX2DrawIndexedEx` calls (probably shader warm-up). Time is dominated by guest code; OS calls total ~25 s of 336 s (`GX2DirectCallDisplayList` 14.7 s, `GX2CopyColorBufferToScanBuffer` 6.2 s).
- **Root causes fixed on the way:** (1) no content mounted when the RPX is not under `<title>/code/` (see 5d); (2) `MCP_Open` failing made the game pick the **JpJa** locale and then dereference null message data. Now `MCP_Open` returns a handle and `MCP_GetSysProdSettings` reports Europe (struct layout unverified). (3) `OSJoinThread` + join wake-up implemented; (4) GX2 linear/thick tile modes allowed in size computation; (5) `GX2GetDisplayListWriteStatus`, ProcUI/VPAD/WPAD/zlib/`OSTicksToCalendarTime` handlers added (all unverified except by running).
- **Scaffolding in the local runtime (not implementations):** env-gated `NWIIU_OFFLINE_STUBS=1` makes unimplemented imports of online/peripheral libs (nn_olv, nn_boss, nn_fp, nn_ac, nn_act, nn_ndm, nn_acp, nlibcurl, nsysnet, camera, mic) return -1 and logs them; unimplemented `snd_core`/`snd_user`/`sysapp` calls and **all unimplemented `GX2Set*` calls are silent no-ops that return 0** (so render state is NOT applied, audio is not produced). `UCReadSysConfig` unknown keys return zeros (logged). Debug aids: `NWIIU_IMPORT_STATS=1` (counts + wall time per import), `NWIIU_FAULT_DUMP=1` (registers + stack walk), `NWIIU_FS_TRACE=1`, livelock detector in the scheduler.
- **Window:** upstream's `--window` path uses a Vulkan SDL GPU renderer written for Wind Waker HD. It failed until SDL3 was rebuilt with the `vulkan` feature (`vcpkg install "sdl3[vulkan]" --recurse`); I also let SDL choose the 2D renderer backend, disabled GPU debug mode, and fixed the window title. It now opens a window titled "Super Mario 3D World (native port, work in progress)". **What it displays is unknown**: my window-only capture (`tools\window-shot.ps1`, PrintWindow) is black, which may just mean PrintWindow cannot read Vulkan swapchains. Needs a human look.
- **Not done:** real GX2 state/shader translation for this game, audio, input mapping (VPAD/KPAD return no devices), saves, resolution/aspect/fullscreen options, frame pacing, Mii files (`FFLRes*.dat` are console system files the game tries to open; it continued after the failed open).

**Estimated progress to a testable build: ~20-25%** (judgement).

## 5f. Milestone 5: first real game image on screen (2026-10-26)

- The user's windowed run showed a black window. Cause: the upstream renderer **exits with `unsupported sampled GX2 texture format 8`** (it only knows the formats Wind Waker HD uses). Format 8 is `UNORM_R5_G6_B5`. I added a CPU decoder for RGB565, plus 5551/4444 (`0x0A`/`0x0B`; format ids and alpha-bit order recalled from GX2 docs, unverified) in `wwhd_renderer.h` (`decode_packed16`).
- With that, `NWIIU_FRAME_DUMP=outrames NWIIU_FRAME_DUMP_INTERVAL=60` (an existing renderer option) dumps the presented TV image as BMP; `toolsmp2png.ps1` converts it. **Frames 180 and 240 show the game's real "how to hold the Wii U GamePad / Wii Remote + Nunchuk" illustration**, 1280x720, drawn by `sm3dw-native.exe` (swap 60 and earlier were black). Saved examples: `out\shotsrame_180.png`, `frame_240.png`.
- The picture was identical at frames 180 and 240, with ~62 draws/frame still being issued (draw_count 3,676 at swap 120, 7,396 at 180, 11,116 at 240). Whether that is shader warm-up behind a static screen, or the game waiting for input, is not determined.
- **Speed:** with the window and CPU texture decoding, ~0.5 swaps/s (180 swaps took ~8 min) versus the 60 fps target. Playable speed needs a real renderer; the upstream one is an SDL 2D renderer with CPU decoding (plus an SDL GPU path for shaders).
- Keyboard is wired by the upstream renderer to fixed VPAD buttons: arrows = D-pad, Enter/Space = A (bit 15), P = bit 3, Esc = bit 14. This is not the configurable input system required; it is a stand-in.
- Launcher: `run-sm3dw.bat` (window; log in `work
un-window.log`).

**Estimated progress to a testable build: ~25-30%** (judgement).

## 5g. Load-time work and the "stuck on the controller screen" investigation (2026-10-26)

Observed by the user in a real windowed run: game boot screen, then the Wii U GamePad / Wii Remote + Nunchuk illustration, then no further progress.

**Speed-ups (measured):**
- Guest code: a 1.3 B-instruction headless run went **227 s -> 71 s (3.2x)**. Cause: the standalone build never used upstream's flat-memory fast path, so every guest load/store did a bounds check plus an `unordered_map` page lookup, and every 16/32/64-bit store also called `std::getenv` (slow on Windows). Fix (`GuestMemory`, tools\patchespply_0003_fastmem.py): a 1M-entry direct page table + per-page permission bits in front of the unchanged slow path (faults behave as before), and the two trace `getenv`s cached. Runtime tests still pass (same 3 environmental failures). Requires recompiling all generated shards (the header is inlined).
- Renderer: `translate_shader()` re-ran the Latte->GLSL translation and two shaderc compiles on **every draw call** and then discarded the result (pipelines were already cached by address). Added a content-hash translation cache that also remembers failures (tools\patchespply_0004_translation_cache.py). Windowed throughput went from ~0.55 swaps/s to ~1.5 swaps/s (swaps 30->60 took 5 s instead of 46 s). Time to the controller screen is now roughly 3 minutes instead of 8+; the renderer (SDL 2D + CPU texture decode + a GPU->CPU readback per draw) is still far from 60 fps.
- Profile of loading (`NWIIU_PC_SAMPLE=1`, `tools\profile_report.py`): ~82% of guest instructions during loading are in a **streaming Yaz0 decoder** (`0x026BBF1C`, plus helpers `0x026BB59C`, `0x026BBE28`). It is a resumable state machine (state struct: dst, remaining, final-flag, mask, code byte, state 0/1/2, copy distance, header bytes left), not the one-shot decoder that was already hooked. A native hook would cut loading further but must match its exact semantics (including `dcbz` zeroing); not done.

**Why it is stuck (findings):**
- Not a crash or deadlock: the main thread is running its frame loop, 16 of 19 threads are idle on message queues (normal), 3 have exited; PC sampling in the stuck state shows ordinary per-frame game code spread over many functions.
- Frames are byte-identical from swap 150 to swap 2,720 (~45 game-seconds), so waiting longer does not help. `draw_count` grows by a constant ~62 draws/frame.
- Per frame the game calls `VPADRead` once, `KPADReadEx`/`WPADProbe` 4x (one per Wii Remote channel; WPADProbe reports "no controller") and `VPADGetTPCalibratedPoint` 3x. Scripted A taps (`NWIIU_AUTO_A=all`, ~420 swaps) did not change the screen.
- The screen shows only the illustration, no text. Either the text layer is not rendering (likely: many `GX2Set*` calls are no-ops and the renderer only knows a few formats) or the screen is waiting for input we do not deliver correctly. Undetermined.
- Hypotheses to test next: (1) the screen needs input the stand-in mapping does not give (e.g. GamePad touch, or a button other than A/Plus); (2) the "Press A"-style prompt is invisible because text rendering fails, and the game needs a real *trigger* edge through a path we mis-model; (3) an unimplemented system service the game waits on (online/account/save), currently stubbed as "offline".

**New debug aids:** `SDL_VIDEODRIVER=offscreen` (no window on screen; works with `--window`), `NWIIU_GPU_SKIP_TO_SWAP=N` (skip GPU draws before swap N, ~20x faster fast-forward), `NWIIU_THREAD_DUMP=1`, `NWIIU_PC_SAMPLE_AFTER=N`, `NWIIU_AUTO_A=all`, frame timestamps in `FRAME t=...ms`.

## 5h. Milestone 6: text renders, the controller guide is left behind, game reaches the title demo (2026-10-26)

**What the stuck screen was.** `WindowControllerGuide` (layout `LayoutData/WindowControllerGuide.szs`, English text "You can play this game using the following controllers: Wii U GamePad / Wii Remote / Wii U Pro Controller / Wii Remote + Nunchuk ... Classic Controller Pro"). It is a loading-time guide, not an input prompt: scripted and manual A presses reached the game (`NWIIU_INPUT_TRACE=1` shows `VPAD-HOLD 0x8000` alternating) and changed nothing. Three independent bugs kept the game on it:
1. **Text did not draw.** The Latte->GLSL translator only knew Wind Waker HD's ALU subset. The text vertex shaders start with ALU opcode `0x16` (`MOVA_FLOOR`), which loads the GPU address register; the translator had no `AR` or relative addressing. Added `MOVA` (0x15), `MOVA_FLOOR` (0x16), `MOVA_INT` (0x18), relative GPR/constant sources and destinations via `AR.x..w` (`tools\patchespply_0005_latte_address_register.py`; LOOP index mode and relative kcache access still throw). A fourth shader used vertex format 26 = `FMT_8_8_8_8`; added as UBYTE4_NORM/BYTE4_NORM (`apply_0006_vertex_8888.py`; scaled/int variants rejected). Result: the guide now renders with correct text (decorative window border is visibly scrambled: texture tiling/UVs wrong). Opcode numbers and bit positions are from memory of the R6xx/R7xx ISA and verified only by the shaders now translating and the text appearing.
2. **OS alarms never fired.** `OSSetPeriodicAlarm` only stored the callback; nothing ever invoked it. Added `CafeCoreinit::service_alarms()` (called once per scheduler iteration), plus `OSSetAlarm`, `OSCancelAlarm`, `OSGetAlarmUserData` (`apply_0007_alarms.py`).
3. **Game time ran ~20x too fast** once alarms fired: the clock advanced 1 tick per guest instruction, but the console retires ~20 instructions per 62.156 MHz tick. A watchdog-style timer then made the game's main thread exit early. New `NWIIU_INSTR_PER_TICK` (default 1 = old behaviour); **`run-sm3dw.bat` and all SM3DW runs now use 20**.

**Other fixes made while following the game forward** (all in the local clone, in `tools\patches\combined-local-changes.patch`):
- `SAVEGetStatOtherApplication` / `SAVEOpenFileOtherApplication` answer `FS_STATUS_NOT_FOUND` (-6): no other application's save data exists.
- GX2: non-command helpers (`GX2Init*`, `Calc*`, `Get*`, `Is*`, `Temp*`) are no longer recorded and deferred inside display lists (they read stale stack memory on replay); `GX2CopySurface` accepts more uncompressed element sizes; `GX2ClearColor` no longer faults on non-RGBA8 targets (guest-memory write skipped; the renderer clears its own target); unimplemented `GX2Set*`, `GX2Save*`, `GX2Load*` are logged no-ops.
- Load speed (see 5g): 3.2x on guest code, ~3x on the window. Translation cache in the renderer.

**Where it stands now.** In a fast run (GPU draws skipped, `SDL_VIDEODRIVER=offscreen NWIIU_GPU_SKIP_TO_SWAP=...`) the game executes ~3.26 B guest instructions and opens **653 files** (previously stuck at 84), including `SystemData/TitleDemoData.szs` and `ObjectData/CourseSelectTexture.szs`, i.e. it starts loading the title demo. Then the **main thread returns normally (exit value 0)** and all workers wait forever (scheduler "deadlock" is only the aftermath). Cause not yet determined. Candidates: a deliberate quit path (a failed check, an error dialog), or corrupted state: one worker thread was created with entry `0x31203d20` (ASCII "1 = "). `NWIIU_EXIT_TRACE=1` prints the last PCs of every exiting thread; the main thread's final PCs are in `0x02230c24` (function epilogue) -> `0x02371dbc` -> `0x02386fdc`. Not yet analysed.
- In a windowed run the user will see the controller guide with text for a while, then the program ends (check `work
un-window.log`).
- `COLORBUFFER-UNSUPPORTED` earlier turned out to be a symptom of the display-list deferral bug, not a real unsupported format.

**New debug aids:** `NWIIU_EXIT_TRACE`, `NWIIU_RENDER_FAIL_TRACE` (logs shaders that fail translation), `NWIIU_INPUT_TRACE`, `NWIIU_INSTR_PER_TICK`, `tools\szs.py` (Yaz0 + SARC reader: `python -I tools\szs.py list <file.szs>`), `tools\disasm.py` (needs `pip install capstone`).

**Estimated progress to a testable build: ~35%** (judgement). The game now boots through its loading screens and starts its title sequence; what is missing is why the main loop ends, then real rendering of 3D scenes (GX2 state is mostly stubbed), audio, input mapping, saves, and speed.

## 6. Reproduce what exists

Requires Python 3.14+ (uses `compression.zstd`) and 7-Zip. Originals in Downloads are untouched.

```
# extract the WUA from the 7z (done once)
"C:\Program Files\7-Zip\7z.exe" x "<Downloads>\Super Mario 3D World (Europe) (En,Fr,De,Es,It,Nl,Pt,Ru) (Rev 1).7z" -owork\extracted-wua

python -I tools\zar.py list work\extracted-wua\*.wua > work\wua-listing.txt
python -I tools\zar.py cat  work\extracted-wua\*.wua 0000000000000000_v0/code/RedCarpet.rpx work\rpx\RedCarpet.rpx
python -I tools\rpxinfo.py work\rpx\RedCarpet.rpx --dump-dir work\rpx\sections

# third-party analyzer (needs git, VS 2026 C++ workload, vcpkg openssl+zlib)
git clone --depth 1 https://github.com/BlackLineInteractive/nWiiURecomp third_party\nWiiURecomp
git clone --depth 1 https://github.com/microsoft/vcpkg third_party\vcpkg && third_party\vcpkg\bootstrap-vcpkg.bat -disableMetrics
third_party\vcpkg\vcpkg install openssl:x64-windows zlib:x64-windows
tools\build-analyzer.bat
build\analyzer\analyzer\nwiiu-analyze.exe --any-title work\rpx\RedCarpet.rpx out\sm3dw-eu-rev1-manifest.json
```

Layout: `tools/` scripts I wrote · `work/` generated/extracted data (safe to delete and regenerate) · originals only in Downloads.

## 7. Known issues
- `zar.py list` shows a few duplicate `code/`/`meta/` entries with different sizes (e.g. `app.xml` 642 and 580 bytes). The cause is unexamined; it may be a bug in my tree walk. RPX extraction by path worked and parsed as a valid RPX.
- `work/` holds ~1.5 GB (the extracted `.wua`) plus the RPX and section dumps.

## 8. Next concrete steps
1. Decide how to get system shared data: ask the user whether they have the console's shared fonts (`CafeStd.ttf` etc.) dumped from their own Wii U; otherwise find what the game does without them.
2. Continue the HLE loop with real (not stub) behaviour where the game consumes the result: `tools\hle_iter.py <lib> <Name> <r3>` shows the next stop each time. Write unit tests for each new API.
3. Unit-test the six added instructions against known PowerPC results.
4. Compile all 3,136 shards in the background and link `sm3dw-native` (check disk: expect several GB of objects).
5. Own the platform layer: replace upstream's Cemu-based window path with an SDL3 window + D3D12/Vulkan GX2 backend, input and audio (not started).

## 5i. Milestone 7 — past the controller guide, title screen draws (partial)
Observed (offscreen run, frame dumps in `out/frames13`, PNG in `out/shots/f13_*.png`):
- Correction: the earlier "main thread exits normally at ~3.26 B instructions" was a misreading. Short runs were killed by my own `timeout`; the game keeps rendering frames (~7 fps in this unoptimised build).
- The controller guide is a timed screen. After it the game shows a title/logo layout ("© 2013 Nintendo" text visible); half of the image is black with scrambled strips (texture format / tiling gaps, not diagnosed).
- Fixed: FLOAT RG16 texture format (GX2 0x810) added to the CPU decoder (`decode_rg16_float`, approximation: clamped to 0..1, HDR lost). Previously this ended the run with `INPUT ERROR: unsupported sampled GX2 texture format 2064`.
- Still: scheduler reports `deadlock` at 3,262,620,565 instructions. Thread-dump analysis in progress.
- Audio: correction to earlier note — the upstream runtime already mixes AX voices and plays them via SDL. User hears a faint, buggy, high-pitched "Super Mario 3D World" voice clip. Audio is paced per swapped frame (1/60 s of samples per swap), so at ~7 fps it stutters. Cause of the pitch not verified.
- Diagnostics added (local): `NWIIU_EXIT_TRACE` now prints thread name + last imports; `NWIIU_FS_TRACE` logs ErrEula export names/calls and the ProcUI caller; `FSGetVolumeState` returns READY whenever FS is initialised.

## 5j. Milestone 8 — speed work and the "game ends at frame ~488" investigation
Measured (offscreen windowed run, `NWIIU_PERF=1`, 30-frame groups): ~3.0 s wall per 30 frames (~10 fps). Renderer ~1.3 s of that
(62 draws/frame; draw replay ~0.8-1.0 s, scan-buffer copy ~0.25-0.4 s); the rest is guest CPU. Not representative of a real GPU: the
offscreen driver may rasterise in software.
- Profile after 2 B instructions: 72% of guest instructions were in 0x026BBF1C, the **streaming Yaz0 decoder** (state-struct based,
  resumable) plus its header helper 0x026BBE28. Added native hook `Yaz0DecodeStream` (native_hooks.cpp), registered in the profile
  (`configs/sm3dw-eu-rev1.toml` and generated `out/recomp/sm3dw/main.cpp`). It is a transliteration of the guest code; `dcbz`
  cache-line zeroing is not performed and the guest's degenerate "copy length 0" case is skipped. Evidence it is functionally
  equivalent: the game opens the same 653 files, renders the same 488 frames and reaches the same end state with 2.13 B instead of
  3.29 B guest instructions. No byte-for-byte comparison against the guest decoder was done.
- GPU draws are now batched into one open SDL GPU command buffer (flushed before any upload/download/clear/swap): draw time
  ~1035 -> ~835 ms per 30 frames; total frame time unchanged within noise.
- **The game's main thread returns normally after ~488 frames** (always the same count, with or without input). All `OSExitThread`
  calls come from the thread-return trampoline, i.e. entry functions returning, not from an error path. Findings so far:
  every FS open succeeds (653), `GameData.bin` in save slot 1 is "not found" (normal first run), no OSFatal/OSPanic import is
  called, nn_erreula is never asked to show an error, `FSGetVolumeState` reports READY, `IsNetworkAccount` now reports false
  (tried; no change). The last calls before the return are the frame-end sequence ProcUIProcessMessages -> GX2GPUTimeToCPUTime x6,
  then float frame-time arithmetic. Root cause **not found**.
- New diagnostics (local): NWIIU_PERF (renderer time split), NWIIU_EXIT_TRACE (thread name, stack walk, ring of the last 4000
  filtered imports tagged per thread, OSExitThread caller), NWIIU_FS_TRACE (ErrEula export names/calls with LR, ProcUI caller,
  FSGetVolumeState caller, SAVEOpenFile results).
- Audio: the runtime mixes AX voices itself and plays them through SDL; it is paced per swapped frame, so at ~10 fps the music
  stutters. Not a mixer bug as far as checked; pitch not verified.

## 5k. Milestone 9 — the "game ends after ~488 frames" bug is fixed
Root cause: my callback mechanism (AX frame callbacks, OS alarms) hijacks a ready guest thread and runs the callback on that
thread's stack directly below r1. Interrupted guest code can still read just-released frame slots below r1, so a callback arriving
at the wrong moment corrupted them; the thread later returned into the thread-return trampoline (OSExitThread with garbage r3) and
the main thread "exited" while deep in its infinite main loop (0x023747DC `loop { update }`).
Fix (machine.cpp `begin_callback`): start the callback 0x400 bytes below the interrupted r1 when the thread's recorded stack has
>0x1800 bytes of room. A 0x1000 shift crashed early (small-stack threads overran: "invalid message queue"), so it is conditional.
Result (offscreen, windowed renderer, no input): 6.0 B instructions, 1450 frames, no deadlock/exit (was: 488 frames, exit at ~2.1 B).
Not a real fix of the design: callbacks should run on their own stacks/threads; this margin is a mitigation, not verified in general.
Related experiments: no AX callbacks => game runs but waits forever (needs them); no alarms+no AX callbacks => idles.

## 5l. Milestone 10 — title menu reached; hand-over state (2026-10-28)
Observed (offscreen, windowed renderer, A held, `out/shots/f17_900.png`): controller guide -> title ("Super Mario 3D World" logo, Start,
(c) 2013 Nintendo; logo drawn in a corner on a white box) -> "Select a controller and character" menu (Mario, Join slots, header
text; several panels white where textures are missing) -> gray screen from ~frame 1100 to 1500 (3D/stage content not drawn). No
crash, no exit, no deadlock up to 1500 frames. Speed ~10 fps in the headless run.
Added since 5k: `IMIsAPDEnabledBySysSettings`/`IMIsAPDEnabled`/`IMEnableAPD`/`IMDisableAPD` (report disabled), `OSWaitEventWithTimeout`
(deadline kept per thread; woken by signal or by timeout; re-executed on wake), shader translator ALU ops DOT4_IEEE (0x51, treated
as DOT4), SETE/SETGE/SETNE_DX10 (0x0C/0x0E/0x0F), SIN/COS (0x6E/0x6F, argument scaled by 2*pi: unverified), TRUNC, CEIL, LOG_IEEE,
RECIPSQRT_CLAMPED/FF. Still failing in the last trace: CUBE (0x52) and possibly more (re-run with NWIIU_RENDER_FAIL_TRACE=1).
The last build (with TRUNC/CEIL/LOG) was only smoke-tested (400 M instructions), not re-run to the gray-screen frames.
Files for the laptop: `CLAUDE.md`, `TRANSFER.md`, `run-sm3dw-wine.sh` (Wine launcher, untested).
Estimate toward a beta-testable build: ~45%. Remaining big items: 3D rendering correctness (shader gaps, textures/tiling, blending
and state setters that are still silent no-ops), performance (60 fps needs far more than today's ~10), real input mapping and
options (remapping, dead zones, resolution/fullscreen), audio pacing, save verification, Linux/Wine validation.
