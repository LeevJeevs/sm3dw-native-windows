"""Aggregate NWIIU_PC_SAMPLE output by guest function. Usage: python -I profile_report.py <stderr-log> [topN]"""
import json, bisect, sys, collections
m = json.load(open("out/sm3dw-eu-rev1-manifest.json"))
fs = sorted(m["functions"], key=lambda f: int(f["start"], 16))
st = [int(f["start"], 16) for f in fs]
w = collections.Counter(); tot = 0
for l in open(sys.argv[1], errors="ignore"):
    if l.startswith("PC-SAMPLE"):
        _, n, pc = l.split(); n = int(n); pc = int(pc, 16); tot += n
        if 0x02000000 <= pc < 0x10000000:
            i = bisect.bisect_right(st, pc) - 1; w[st[i]] += n
        else:
            w[pc] += n
print("sampled instructions:", tot)
for a, n in w.most_common(int(sys.argv[2]) if len(sys.argv) > 2 else 25):
    f = fs[bisect.bisect_right(st, a) - 1]
    size = (int(f["end"], 16) - int(f["start"], 16)) // 4 if int(f["start"], 16) == a else 0
    print(f"{100*n/tot:5.1f}%  {a:08x}  ({size} instr)  callers={f['callers'][:2] if int(f['start'],16)==a else ''}")
