"""Adds ps_mr, ps_div, eqv, subfme, addme, lfdu to the local nWiiURecomp clone
(generator gate+emitter, interpreter gate+executor, semantics). Each edit asserts its
anchor text occurs exactly once. Run: python -I apply_0002.py <path-to-nWiiURecomp>"""
import sys, pathlib

root = pathlib.Path(sys.argv[1])
def edit(rel, old, new):
    p = root / rel
    s = p.read_text(encoding="utf-8")
    assert s.count(old) == 1, f"{rel}: anchor count {s.count(old)} for {old[:60]!r}"
    p.write_text(s.replace(old, new), encoding="utf-8")

G = "nWiiURecomp/src/native_generator.cpp"
E = "nWiiURuntime/src/executor.cpp"
H = "nWiiURuntime/include/runtime/ppc_semantics.h"
I = "nWiiURuntime/include/runtime/ppc_semantics_inl.h"

# ---- semantics header
edit(H, "void ps_neg(CPUContext& cpu, uint32_t frt, uint32_t frb);\n",
 "void ps_neg(CPUContext& cpu, uint32_t frt, uint32_t frb);\n"
 "void ps_mr(CPUContext& cpu, uint32_t frt, uint32_t frb);\n"
 "void ps_div(CPUContext& cpu, uint32_t frt, uint32_t fra, uint32_t frb);\n")
edit(H, "void andc(CPUContext& cpu, uint32_t ra, uint32_t rs, uint32_t rb, bool rc);\n",
 "void andc(CPUContext& cpu, uint32_t ra, uint32_t rs, uint32_t rb, bool rc);\n"
 "void eqv(CPUContext& cpu, uint32_t ra, uint32_t rs, uint32_t rb, bool rc);\n"
 "void subfme(CPUContext& cpu, uint32_t rt, uint32_t ra, bool oe, bool rc);\n"
 "void addme(CPUContext& cpu, uint32_t rt, uint32_t ra, bool oe, bool rc);\n")
edit(H, "void lfsu(CPUContext& cpu, GuestMemory& memory, uint32_t frt, uint32_t ra,",
 "void lfdu(CPUContext& cpu, GuestMemory& memory, uint32_t frt, uint32_t ra,\n"
 "          int32_t displacement);\n"
 "void lfsu(CPUContext& cpu, GuestMemory& memory, uint32_t frt, uint32_t ra,")

# ---- semantics implementation
edit(I, "inline void nor_(CPUContext& cpu,",
 "inline void eqv(CPUContext& cpu, uint32_t ra, uint32_t rs, uint32_t rb, bool rc) {\n"
 "    cpu.gpr[ra] = ~(cpu.gpr[rs] ^ cpu.gpr[rb]);\n"
 "    if (rc) {\n"
 "        set_integer_cr(cpu, 0, cpu.gpr[ra]);\n"
 "    }\n"
 "    cpu.pc += 4;\n"
 "}\n\n"
 "inline void nor_(CPUContext& cpu,")
edit(I, "inline void subfze(CPUContext& cpu,",
 "// subfme: rt = ~ra + CA - 1\n"
 "inline void subfme(CPUContext& cpu, uint32_t rt, uint32_t ra, bool oe, bool rc) {\n"
 "    const uint32_t a = cpu.gpr[ra];\n"
 "    const uint32_t carry_in = (cpu.xer & kXerCa) != 0;\n"
 "    const uint64_t result = static_cast<uint64_t>(~a) + carry_in + 0xFFFFFFFFULL;\n"
 "    cpu.gpr[rt] = static_cast<uint32_t>(result);\n"
 "    set_ca(cpu, (result >> 32) != 0);\n"
 "    if (oe) {\n"
 "        const int64_t s = static_cast<int64_t>(static_cast<int32_t>(~a)) +\n"
 "                          static_cast<int64_t>(carry_in) - 1;\n"
 "        set_ov(cpu, s != static_cast<int32_t>(s));\n"
 "    }\n"
 "    if (rc) {\n"
 "        set_integer_cr(cpu, 0, cpu.gpr[rt]);\n"
 "    }\n"
 "    cpu.pc += 4;\n"
 "}\n"
 "inline void subfze(CPUContext& cpu,")
edit(I, "inline void addze(CPUContext& cpu,",
 "// addme: rt = ra + CA - 1\n"
 "inline void addme(CPUContext& cpu, uint32_t rt, uint32_t ra, bool oe, bool rc) {\n"
 "    const uint32_t a = cpu.gpr[ra];\n"
 "    const uint32_t carry_in = (cpu.xer & kXerCa) != 0;\n"
 "    const uint64_t result = static_cast<uint64_t>(a) + carry_in + 0xFFFFFFFFULL;\n"
 "    cpu.gpr[rt] = static_cast<uint32_t>(result);\n"
 "    set_ca(cpu, (result >> 32) != 0);\n"
 "    if (oe) {\n"
 "        const int64_t s = static_cast<int64_t>(static_cast<int32_t>(a)) +\n"
 "                          static_cast<int64_t>(carry_in) - 1;\n"
 "        set_ov(cpu, s != static_cast<int32_t>(s));\n"
 "    }\n"
 "    if (rc) {\n"
 "        set_integer_cr(cpu, 0, cpu.gpr[rt]);\n"
 "    }\n"
 "    cpu.pc += 4;\n"
 "}\n"
 "inline void addze(CPUContext& cpu,")
edit(I, "inline void lfd(CPUContext& cpu, GuestMemory& memory, uint32_t frt, uint32_t ra,",
 "inline void lfdu(CPUContext& cpu, GuestMemory& memory, uint32_t frt, uint32_t ra,\n"
 "           int32_t displacement) {\n"
 "    require_update_form(cpu, frt, ra, false);\n"
 "    const uint32_t address = cpu.gpr[ra] + static_cast<uint32_t>(displacement);\n"
 "    cpu.fpr[frt][0] = memory.read64(address, cpu.pc);\n"
 "    cpu.gpr[ra] = address;\n"
 "    cpu.pc += 4;\n"
 "}\n\n"
 "inline void lfd(CPUContext& cpu, GuestMemory& memory, uint32_t frt, uint32_t ra,")
edit(I, "inline void ps_neg(CPUContext& cpu, uint32_t frt, uint32_t frb) {",
 "inline void ps_mr(CPUContext& cpu, uint32_t frt, uint32_t frb) {\n"
 "    const uint64_t lane0 = cpu.fpr[frb][0];\n"
 "    const uint64_t lane1 = cpu.fpr[frb][1];\n"
 "    cpu.fpr[frt][0] = lane0;\n"
 "    cpu.fpr[frt][1] = lane1;\n"
 "    cpu.pc += 4;\n"
 "}\n\n"
 "inline void ps_div(CPUContext& cpu, uint32_t frt, uint32_t fra, uint32_t frb) {\n"
 "    const float lane0 =\n"
 "        static_cast<float>(std::bit_cast<double>(cpu.fpr[fra][0])) /\n"
 "        static_cast<float>(std::bit_cast<double>(cpu.fpr[frb][0]));\n"
 "    const float lane1 =\n"
 "        static_cast<float>(std::bit_cast<double>(cpu.fpr[fra][1])) /\n"
 "        static_cast<float>(std::bit_cast<double>(cpu.fpr[frb][1]));\n"
 "    cpu.fpr[frt][0] = std::bit_cast<uint64_t>(static_cast<double>(lane0));\n"
 "    cpu.fpr[frt][1] = std::bit_cast<uint64_t>(static_cast<double>(lane1));\n"
 "    cpu.pc += 4;\n"
 "}\n\n"
 "inline void ps_neg(CPUContext& cpu, uint32_t frt, uint32_t frb) {")

# ---- generator gate
edit(G, "        if ((instruction.xo5() == 20 || instruction.xo5() == 21) &&\n            instruction.frc() == 0) {\n            return;\n        }\n        if (xo == 26 && instruction.ra() == 0) {",
 "        if ((instruction.xo5() == 18 || instruction.xo5() == 20 ||\n             instruction.xo5() == 21) &&\n            instruction.frc() == 0) {\n            return;\n        }\n        if (xo == 72 && instruction.ra() == 0) {\n            return;\n        }\n        if (xo == 26 && instruction.ra() == 0) {")
edit(G, "        case 316:\n        case 444:\n        case 459:",
 "        case 316:\n        case 284:\n        case 444:\n        case 459:")
edit(G, "        case 200:\n        case 712:\n        case 202:\n        case 714:\n            if (instruction.rb() == 0) {",
 "        case 200:\n        case 712:\n        case 202:\n        case 714:\n        case 232:\n        case 744:\n        case 234:\n        case 746:\n            if (instruction.rb() == 0) {")
edit(G, "    case 49:\n        if (instruction.ra() != 0) {\n            return;\n        }\n        throw std::invalid_argument(\"reserved update load form\");",
 "    case 49:\n    case 51:\n        if (instruction.ra() != 0) {\n            return;\n        }\n        throw std::invalid_argument(\"reserved update load form\");")
# ---- generator emitter
edit(G, "        } else if (xo == 40) {\n            output << \"    nwii::runtime::ppc::ps_neg(cpu, \"",
 "        } else if (xo == 72) {\n            output << \"    nwii::runtime::ppc::ps_mr(cpu, \"\n                   << instruction.rt() << \", \" << instruction.rb() << \");\\n\";\n        } else if (xo == 40) {\n            output << \"    nwii::runtime::ppc::ps_neg(cpu, \"")
edit(G, "        } else if (instruction.xo5() == 20 ||\n                   instruction.xo5() == 21) {\n            output << \"    nwii::runtime::ppc::\"\n                   << (instruction.xo5() == 20 ? \"ps_sub\" : \"ps_add\")",
 "        } else if (instruction.xo5() == 18 ||\n                   instruction.xo5() == 20 ||\n                   instruction.xo5() == 21) {\n            output << \"    nwii::runtime::ppc::\"\n                   << (instruction.xo5() == 18   ? \"ps_div\"\n                       : instruction.xo5() == 20 ? \"ps_sub\"\n                                                : \"ps_add\")")
edit(G, "        case 202:\n        case 714:\n            output << \"    nwii::runtime::ppc::addze(cpu, \"",
 "        case 232:\n        case 744:\n            output << \"    nwii::runtime::ppc::subfme(cpu, \"\n                   << instruction.rt() << \", \" << instruction.ra() << \", \"\n                   << boolean(xo == 744) << \", \"\n                   << boolean(instruction.rc()) << \");\\n\";\n            return;\n        case 234:\n        case 746:\n            output << \"    nwii::runtime::ppc::addme(cpu, \"\n                   << instruction.rt() << \", \" << instruction.ra() << \", \"\n                   << boolean(xo == 746) << \", \"\n                   << boolean(instruction.rc()) << \");\\n\";\n            return;\n        case 202:\n        case 714:\n            output << \"    nwii::runtime::ppc::addze(cpu, \"")
edit(G, "        case 316:\n        case 28:\n        case 60:\n        case 412:",
 "        case 316:\n        case 284:\n        case 28:\n        case 60:\n        case 412:")
edit(G, "                               : xo == 316 ? \"xor_\"\n",
 "                               : xo == 316 ? \"xor_\"\n                               : xo == 284 ? \"eqv\"\n")
edit(G, "    case 48:\n    case 49:\n    case 50:\n    case 52:\n    case 53:\n    case 54:\n    case 55: {\n        const char* name = opcode == 48   ? \"lfs\"\n                           : opcode == 49 ? \"lfsu\"\n                           : opcode == 50 ? \"lfd\"",
 "    case 48:\n    case 49:\n    case 50:\n    case 51:\n    case 52:\n    case 53:\n    case 54:\n    case 55: {\n        const char* name = opcode == 48   ? \"lfs\"\n                           : opcode == 49 ? \"lfsu\"\n                           : opcode == 50 ? \"lfd\"\n                           : opcode == 51 ? \"lfdu\"")

# ---- interpreter gate + executor
edit(E, "        case 20: // ps_sub\n        case 21: // ps_add\n            if (instruction.frc() != 0) {",
 "        case 18: // ps_div\n        case 20: // ps_sub\n        case 21: // ps_add\n            if (instruction.frc() != 0) {")
edit(E, "            } else if (xo == 40) { // ps_neg\n                if (instruction.ra() != 0) {",
 "            } else if (xo == 40 || xo == 72) { // ps_neg, ps_mr\n                if (instruction.ra() != 0) {")
edit(E, "    case 49:\n    case 50:\n    case 52:\n    case 53:\n    case 54:\n    case 55:\n        break;",
 "    case 49:\n    case 50:\n    case 51:\n    case 52:\n    case 53:\n    case 54:\n    case 55:\n        break;")
edit(E, "        case 200:\n        case 712:\n        case 202:\n        case 714:\n        case 235:",
 "        case 200:\n        case 712:\n        case 202:\n        case 714:\n        case 232:\n        case 744:\n        case 234:\n        case 746:\n        case 284:\n        case 235:")
edit(E, "        case 60:\n            ppc::andc(cpu, instruction.ra(), instruction.rs(),\n                      instruction.rb(), instruction.rc());\n            return;",
 "        case 60:\n            ppc::andc(cpu, instruction.ra(), instruction.rs(),\n                      instruction.rb(), instruction.rc());\n            return;\n        case 284:\n            ppc::eqv(cpu, instruction.ra(), instruction.rs(),\n                     instruction.rb(), instruction.rc());\n            return;\n        case 232:\n        case 744:\n            ppc::subfme(cpu, instruction.rt(), instruction.ra(), xo == 744,\n                        instruction.rc());\n            return;\n        case 234:\n        case 746:\n            ppc::addme(cpu, instruction.rt(), instruction.ra(), xo == 746,\n                       instruction.rc());\n            return;")
edit(E, "    case 50:\n        ppc::lfd(cpu, image_.memory, instruction.rt(), instruction.ra(),\n                 instruction.simm());\n        return;",
 "    case 50:\n        ppc::lfd(cpu, image_.memory, instruction.rt(), instruction.ra(),\n                 instruction.simm());\n        return;\n    case 51:\n        ppc::lfdu(cpu, image_.memory, instruction.rt(), instruction.ra(),\n                  instruction.simm());\n        return;")
print("all anchors applied")

# ---- interpreter execute path for case 4
edit(E, "        } else if (xo == 40) {\n            ppc::ps_neg(cpu, instruction.rt(), instruction.rb());",
 "        } else if (xo == 72) {\n            ppc::ps_mr(cpu, instruction.rt(), instruction.rb());\n        } else if (xo == 40) {\n            ppc::ps_neg(cpu, instruction.rt(), instruction.rb());")
edit(E, "        } else if (instruction.xo5() == 25) {\n            ppc::ps_mul(cpu, instruction.rt(), instruction.ra(),\n                        instruction.frc());",
 "        } else if (instruction.xo5() == 18) {\n            ppc::ps_div(cpu, instruction.rt(), instruction.ra(),\n                        instruction.rb());\n        } else if (instruction.xo5() == 25) {\n            ppc::ps_mul(cpu, instruction.rt(), instruction.ra(),\n                        instruction.frc());")
print("execute path applied")
