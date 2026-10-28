"""Minimal read-only ZArchive (.wua/.zar) reader. Format per Exzap/ZArchive
(include/zarchive/zarchivecommon.h, src/zarchivereader.cpp). Big-endian, zstd 64KiB blocks.

Usage: python -I zar.py list  <archive> [prefix]
       python -I zar.py cat   <archive> <path> <out-file>
       python -I zar.py extract <archive> <path-prefix> <out-dir>
Requires Python 3.14+ (compression.zstd).
"""
import struct, sys, os
from compression import zstd

BLOCK = 65536
PER_REC = 16


class ZAR:
    def __init__(self, path):
        self.f = open(path, "rb")
        self.f.seek(0, 2)
        size = self.f.tell()
        self.f.seek(size - 144)
        ft = self.f.read(144)
        secs = struct.unpack(">12Q", ft[:96])
        self.total, self.version, self.magic = struct.unpack(">QII", ft[128:144])
        if self.magic != 0x169F52D6 or self.version != 0x61BF3A01 or self.total != size:
            raise ValueError("not a ZArchive v1")
        (self.cd_off, self.cd_size, ro, rs, no, ns, to, ts, _, _, _, _) = secs
        self.f.seek(ro)
        self.recs = []
        raw = self.f.read(rs)
        for i in range(0, len(raw), 40):
            base, *sz = struct.unpack(">Q16H", raw[i:i + 40])
            self.recs.append((base, sz))
        self.f.seek(no)
        self.names = self.f.read(ns)
        self.f.seek(to)
        traw = self.f.read(ts)
        self.tree = [struct.unpack(">4I", traw[i:i + 16]) for i in range(0, len(traw), 16)]
        self._cache = {}

    def name(self, off):
        n = self.names[off]
        if n & 0x80:
            n = (n & 0x7F) | (self.names[off + 1] << 7)
            off += 2
        else:
            n &= 0x7F
            off += 1
        return self.names[off:off + n].decode("cp1252")

    def block(self, idx):
        if idx in self._cache:
            return self._cache[idx]
        base, sz = self.recs[idx // PER_REC]
        sub = idx % PER_REC
        off = base + sum(s + 1 for s in sz[:sub])
        csize = sz[sub] + 1
        self.f.seek(self.cd_off + off)
        data = self.f.read(csize)
        out = data if csize == BLOCK else zstd.decompress(data)
        if len(self._cache) > 64:
            self._cache.clear()
        self._cache[idx] = out
        return out

    def entry(self, i):
        flags, a, b, c = self.tree[i]
        is_file = bool(flags & 0x80000000)
        name = self.name(flags & 0x7FFFFFFF) if i else ""
        if is_file:
            off = a | ((c & 0xFFFF) << 32)
            size = b | ((c & 0xFFFF0000) << 16)
            return name, True, off, size
        return name, False, a, b  # start index, count

    def walk(self, i=0, prefix=""):
        name, is_file, a, b = self.entry(i)
        path = f"{prefix}/{name}" if name else prefix
        if is_file:
            yield path.lstrip("/"), a, b
        else:
            for j in range(a, a + b):
                yield from self.walk(j, path)

    def read(self, off, size):
        out = bytearray()
        while size > 0:
            bi, bo = divmod(off, BLOCK)
            chunk = self.block(bi)[bo:bo + size]
            out += chunk
            off += len(chunk)
            size -= len(chunk)
        return bytes(out)


if __name__ == "__main__":
    cmd, arc = sys.argv[1], sys.argv[2]
    z = ZAR(arc)
    if cmd == "list":
        pre = sys.argv[3] if len(sys.argv) > 3 else ""
        for p, off, size in z.walk():
            if p.startswith(pre):
                print(f"{size:>12}  {p}")
    elif cmd == "cat":
        want = sys.argv[3].lower()
        for p, off, size in z.walk():
            if p.lower() == want:
                open(sys.argv[4], "wb").write(z.read(off, size))
                print("wrote", sys.argv[4], size)
                break
        else:
            sys.exit("not found")
    elif cmd == "extract":
        pre, outd = sys.argv[3].lower(), sys.argv[4]
        for p, off, size in z.walk():
            if p.lower().startswith(pre):
                dst = os.path.join(outd, *p.split("/"))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, "wb") as o:
                    left, cur = size, off
                    while left > 0:
                        n = min(left, 1 << 22)
                        o.write(z.read(cur, n)); cur += n; left -= n
                print("wrote", dst, size)
