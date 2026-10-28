"""Disassemble guest PPC code from the dumped .text section. Usage: python -I disasm.py <start-hex> <end-hex>
Annotates bl targets that are import stubs when known (uses work/rpx/sections)."""
import sys, glob
from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN
text = open(glob.glob("work/rpx/sections/02*")[0], "rb").read()
base = 0x02000020
a, b = int(sys.argv[1], 16), int(sys.argv[2], 16)
md = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
for i in md.disasm(text[a - base:b - base], a):
    print(f"{i.address:08X}: {text[i.address-base:i.address-base+4].hex()}  {i.mnemonic:<8}{i.op_str}")
