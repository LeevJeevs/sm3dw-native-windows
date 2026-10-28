"""Minimal Yaz0 + SARC reader. Usage: python -I szs.py list <file.szs> | cat <file.szs> <inner-name> <out>"""
import struct, sys
def yaz0(d):
    assert d[:4] == b"Yaz0"
    size = struct.unpack(">I", d[4:8])[0]; out = bytearray(); i = 16
    while len(out) < size:
        code = d[i]; i += 1
        for b in range(8):
            if len(out) >= size: break
            if code & (0x80 >> b): out.append(d[i]); i += 1
            else:
                b1, b2 = d[i], d[i+1]; i += 2
                dist = ((b1 & 15) << 8 | b2) + 1; n = b1 >> 4
                if n == 0: n = d[i] + 18; i += 1
                else: n += 2
                for _ in range(n): out.append(out[-dist])
    return bytes(out)
def sarc(d):
    assert d[:4] == b"SARC"; bom = d[6:8]; e = ">" if bom == b"\xfe\xff" else "<"
    hdr, = struct.unpack(e+"H", d[4:6]); data_off, = struct.unpack(e+"I", d[0xC:0x10])
    assert d[hdr:hdr+4] == b"SFAT"; cnt, = struct.unpack(e+"H", d[hdr+6:hdr+8])
    sfat = hdr + 12; sfnt = sfat + cnt*16 + 8; names = sfnt
    files = {}
    for k in range(cnt):
        nh, nattr, s, en = struct.unpack(e+"IIII", d[sfat+k*16:sfat+k*16+16])
        no = (nattr & 0xFFFFFF) * 4
        nm = d[names+no:d.index(b"\0", names+no)].decode("utf-8", "replace") if nattr >> 24 else "%08x" % nh
        files[nm] = d[data_off+s:data_off+en]
    return files
if __name__ == "__main__":
    raw = open(sys.argv[2], "rb").read(); d = yaz0(raw) if raw[:4] == b"Yaz0" else raw
    f = sarc(d)
    if sys.argv[1] == "list":
        for n, b in f.items(): print(len(b), n)
    else:
        open(sys.argv[4], "wb").write(f[sys.argv[3]]); print("wrote", sys.argv[4])
