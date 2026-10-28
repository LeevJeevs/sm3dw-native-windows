"""Inspect a Wii U RPX/RPL (ELF32 big-endian, PPC EABI, zlib-compressed sections).
Usage: python -I rpxinfo.py <file.rpx> [--dump-dir DIR]
Writes decompressed sections to DIR if given. Layout facts (SHF_RPL_ZLIB=0x08000000,
SHT_RPL_EXPORTS/IMPORTS/CRCS/FILEINFO = 0x80000001..4) follow public Cemu/decaf-emu docs;
verified here only by the output printed below."""
import struct, sys, zlib, os

def main(path, dump=None):
    d = open(path, "rb").read()
    assert d[:4] == b"\x7fELF" and d[4] == 1 and d[5] == 2, "not ELF32 BE"
    (etype, mach, ver, entry, phoff, shoff, flags, ehsize, phentsize, phnum,
     shentsize, shnum, shstrndx) = struct.unpack(">HHIIIIIHHHHHH", d[16:52])
    print(f"e_type=0x{etype:x} machine={mach} entry=0x{entry:08x} sections={shnum} osabi={d[7]:#x}")
    secs = []
    for i in range(shnum):
        o = shoff + i * shentsize
        name, typ, fl, addr, off, size, link, info, align, entsize = struct.unpack(">10I", d[o:o + 40])
        secs.append(dict(i=i, name=name, type=typ, flags=fl, addr=addr, off=off, size=size, link=link, info=info))
    def sdata(s):
        if s["type"] == 8:  # NOBITS
            return b""
        raw = d[s["off"]:s["off"] + s["size"]]
        if s["flags"] & 0x08000000:
            rawsize = struct.unpack(">I", raw[:4])[0]
            out = zlib.decompress(raw[4:])
            assert len(out) == rawsize
            return out
        return raw
    strs = sdata(secs[shstrndx])
    def nm(s):
        e = strs.index(b"\0", s["name"]); return strs[s["name"]:e].decode()
    tot_code = 0
    for s in secs:
        s["data"] = sdata(s)
        print(f'{s["i"]:3} {nm(s):<16} type=0x{s["type"]:08x} flags=0x{s["flags"]:08x} addr=0x{s["addr"]:08x} size={len(s["data"]):>9}')
        if dump and s["data"]:
            os.makedirs(dump, exist_ok=True)
            open(os.path.join(dump, f'{s["i"]:02d}{nm(s).replace("/", "_")}.bin'), "wb").write(s["data"])
    # imports: each section 0x80000002 starts with count, signature, then name
    for s in secs:
        if s["type"] == 0x80000002:
            dd = s["data"]
            count = struct.unpack(">I", dd[:4])[0]
            lib = dd[8:].split(b"\0")[0].decode()
            print(f"IMPORT lib {nm(s)} entries={count}")
    for s in secs:
        if s["type"] in (0x80000001,):
            cnt = struct.unpack(">I", s["data"][:4])[0]
            print("EXPORTS section", nm(s), "count", cnt)
    has_symtab = any(s["type"] == 2 for s in secs)
    print("has .symtab:", has_symtab)
    for s in secs:
        if s["type"] == 0x80000004:
            print("FILEINFO bytes:", len(s["data"]), s["data"][:0x60].hex())

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--dump-dir" else None)
