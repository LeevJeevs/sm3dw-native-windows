"""Bring-up helper: add a scaffolding stub (returns r3=<value>) for a coreinit/other import in the local
nWiiURecomp clone, rebuild the SM3DW variant, rerun nwiiu-run, print the next stop.
Usage: python -I hle_iter.py <lib> <Name> <r3-value> [max-instr]"""
import subprocess, sys, pathlib, re
root = pathlib.Path(__file__).resolve().parent.parent
lib, name, val = sys.argv[1], sys.argv[2], sys.argv[3]
maxi = sys.argv[4] if len(sys.argv) > 4 else "200000000"
p = root / "third_party/nWiiURecomp/nWiiURuntime/src/cafe_coreinit.cpp"
s = p.read_text(encoding="utf-8")
marker = '    runtime.register_handler(\n        "coreinit", "OSGetSystemInfo",'
assert s.count(marker) == 1
stub = (f'    // SCAFFOLDING (local, SM3DW bring-up): {lib}:{name} -> r3={val}\n'
        f'    runtime.register_handler(\n        "{lib}", "{name}",\n'
        f'        [](CPUContext& cpu, GuestMemory&) {{\n'
        f'            cpu.gpr[3] = {val};\n            return HleAction::return_to_lr;\n        }});\n')
p.write_text(s.replace(marker, stub + marker), encoding="utf-8")
r = subprocess.run(["cmd", "/c", str(root / "tools/build-sm3dw.bat")], capture_output=True, text=True)
(root / "work/build-sm3dw.log").write_text(r.stdout + r.stderr)
if r.returncode:
    print("BUILD FAILED"); print("\n".join(l for l in (r.stdout + r.stderr).splitlines() if "error" in l)[:1500]); sys.exit(1)
out = subprocess.run([str(root / "build/nwiiurecomp-sm3dw/nWiiURecomp/nwiiu-run.exe"), str(root / "work/rpx/RedCarpet.rpx"),
                      "--config", str(root / "configs/sm3dw-eu-rev1.toml"), "--max-instructions", maxi,
                      "--save-root", str(root / "out/save")], capture_output=True, text=True)
for l in (out.stdout + out.stderr).splitlines():
    if re.match(r"(STOP|PC:|Instructions|Import|Arguments|INPUT|ERROR|FAULT|Fault)", l) or "fault" in l.lower():
        print(l[:220])
