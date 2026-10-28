# CLAUDE.md — private native port of Super Mario 3D World (Wii U, EU rev1)

Read `PROGRESS.md` first: it is the honest, dated log of what works, what is guessed and what is open. Do not call anything
"playable" or "done" unless the behaviour was actually observed and recorded there.

## What this project is
A private, local-only static recompilation of the user's own game copy (`RedCarpet.rpx`, title 0005000010145D00, SHA-1
09e104248e04bfcc7fa99fdb60456a680e5b1f5a) into a native Windows executable, using a locally modified clone of
nWiiURecomp (`third_party/nWiiURecomp`, GPLv3 upstream). Not an emulator, not a streaming layer, not a remake.
Never distribute game data, the extracted files, or built binaries that embed them.

## Rules from the user (standing)
- Do not open unrelated personal files. Game files were found in Downloads; leave everything else alone.
- Preserve original files. Generated/extracted data goes in clearly named dirs (`work/`, `out/`, `build/`).
- Ask before deleting or overwriting anything that already exists (own scratch/test outputs excepted).
- Test each milestone, record real results, label scaffolding and approximations, cite sources for research.
- Keep working through long test runs: poll inside the turn (bounded wait loops), do not end a turn just because a run is
  pending. The user is annoyed when asked to prompt "continue".
- Give an honest % when asked how far along the project is.

## Layout
- `PROGRESS.md` — running log (sections 5a–5k+), known issues, next steps.
- `configs/sm3dw-eu-rev1.toml` — recompiler profile (`[hle_hooks]` = native replacements of guest functions).
- `out/recomp/sm3dw/` — generated C++ shards (~570 MB). `main.cpp` there holds the runtime `profile_hooks()` table
  (keep it in sync with the TOML).
- `third_party/nWiiURecomp/` — modified recompiler + runtime. All local changes: `tools/patches/combined-local-changes.patch`
  (regenerate with `git diff` inside the clone) plus the numbered `apply_*.py` scripts.
- `build/` — CMake/Ninja trees (`sm3dw-native` is the game exe). `tools/*.bat` wrap the VS 2026 + vcpkg environment.
- `work/title/0000000000000000_v0/` — extracted game (code/content/meta). `work/rpx/sections/` — dumped RPX sections
  (`tools/disasm.py` reads `02.text.bin`). `out/frames*`, `out/shots/` — captured frames.
- `tools/` — `zar.py` (ZArchive), `rpxinfo.py`, `szs.py`, `disasm.py`, `profile_report.py`, `bmp2png.ps1`, build scripts.

## Build and run
- Incremental rebuild: `cmd //c tools\build-sm3dw-native.bat` (the exe must not be running: Windows locks it).
- User launcher: `run-sm3dw.bat`. Test run pattern (headless, silent):
  `SDL_VIDEODRIVER=offscreen SDL_AUDIODRIVER=dummy NWIIU_INSTR_PER_TICK=20 NWIIU_OFFLINE_STUBS=1 build/sm3dw-native/sm3dw-native.exe work/title/0000000000000000_v0/code/RedCarpet.rpx --window --max-instructions N --save-root out/saveX`
  Add `NWIIU_AUTO_A=all` to hold A, `NWIIU_FRAME_DUMP=<dir> NWIIU_FRAME_DUMP_INTERVAL=100` to capture frames
  (`tools/bmp2png.ps1` converts). Use a throwaway `--save-root` for experiments.
- Speed today: ~10 fps in the headless run, ~10 M guest instr/s. 1000 frames take ~15 minutes.
- Diagnostics (all local env vars): NWIIU_PERF, NWIIU_IMPORT_STATS, NWIIU_EXIT_TRACE(+_ALL), NWIIU_FS_TRACE,
  NWIIU_FAULT_DUMP, NWIIU_THREAD_DUMP, NWIIU_PC_SAMPLE(+_AFTER) with `tools/profile_report.py`, NWIIU_RENDER_FAIL_TRACE
  (shader translation failures), NWIIU_CALLBACK_TRACE, NWIIU_NO_AUDIO_CB, NWIIU_NO_ALARMS.

## Hard-won facts
- `NWIIU_INSTR_PER_TICK=20` is required: without it timers fire ~20x too early and the game quits at boot.
- The game's main loop is infinite (`0x023747DC`); it never legitimately returns. If the main thread "exits", look at the
  callback mechanism (`Machine::begin_callback`): callbacks hijack a ready thread and run on its stack. The fix in place
  starts them 0x400 below r1 (only when the stack has room); a proper design would give callbacks their own stack/thread.
- STOP lines to expect when iterating: `missing_hle` (add the import in `cafe_*.cpp`), `guest_fault`, `deadlock`.
  Duplicate `register_handler` for the same module/symbol aborts at start-up — grep before adding.
- Streaming Yaz0 decoder (0x026BBF1C) is a native hook; it was 72% of guest CPU.
- Shader translator (`latte_shader.cpp`) gaps appear as `LATTE-TRANSLATE-FAIL ... unsupported Latte ... raw=w0:w1`;
  ALU opcode = `(w1 >> 7) & 0x7FF` when `(w1 >> 15) & 7 == 0`. Known still missing: CUBE (0x52). SIN/COS scaling is a guess.
- Python heredocs inside bash turn `\n` in C++ string literals into real newlines; use the Edit tool or write patch files.
- Do not open game windows on the user's screen or play audio from test runs: use offscreen + dummy audio.

## Current status (2026-10-28, estimate ~45% to a beta-testable build)
Boots, shows controller guide, title screen and the "Select a controller and character" menu; no crash/exit; ~10 fps;
3D scenes render gray (shader translation gaps); input is a keyboard stand-in (Enter/Space=A, arrows, P=Plus, Esc=B);
audio plays but stutters; no resolution/fullscreen/remapping options; 60 fps and correct game speed are not achieved.
