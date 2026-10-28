"""Adds address-register (AR) support to the Latte->GLSL translator:
 - MOVA (0x15), MOVA_FLOOR (0x16), MOVA_INT (0x18) write AR.<dst channel>
 - relative addressing on ALU sources (GPR and constant file) and on the destination GPR,
   indexed by AR.x/y/z/w per the instruction's INDEX_MODE (0..3). LOOP index mode (4) and
   relative access to the cached-constant banks (kcache) are NOT supported and throw.
Semantics recalled from the R6xx/R7xx ISA docs (opcode numbers 0x15/0x16/0x18 and bit positions:
SRC0_REL w0[9], SRC1_REL w0[22], SRC2_REL w1[9], INDEX_MODE w0[26:28], DST_REL w1[28]).
They are NOT verified against hardware; the only evidence is that the failing text shaders'
first ALU opcode decodes to 0x16.
Run: python -I apply_0005_latte_address_register.py <path-to-latte_shader.cpp>"""
import sys, pathlib

p = pathlib.Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:70])
    s = s.replace(old, new)

# 1) source_count: MOVA family takes one source (like MOV)
rep("""    case 0x19: return 1;
    case 0x50: return 2;""", """    case 0x19:
    case 0x15:
    case 0x16:
    case 0x18: return 1;
    case 0x50: return 2;""")

# 2) source(): relative addressing
rep("""    std::string value;
    if (selector < 128) {
        value = "R[" + std::to_string(selector) + "]." + kChannel[channel];
    } else if (selector < 192) {""", """    // LOCAL: relative addressing through the address register AR.
    bool relative = false;
    if (index == 0) {
        relative = ((instruction.w0 >> 9) & 1u) != 0;
    } else if (index == 1) {
        relative = ((instruction.w0 >> 22) & 1u) != 0;
    } else {
        relative = ((instruction.w1 >> 9) & 1u) != 0;
    }
    std::string rel_suffix;
    if (relative) {
        const uint32_t mode = (instruction.w0 >> 26) & 7u;
        if (mode > 3) {
            throw std::runtime_error("unsupported Latte LOOP index mode");
        }
        rel_suffix = std::string{" + AR."} + kChannel[mode];
    }
    std::string value;
    if (selector < 128) {
        value = "R[" + std::to_string(selector) + rel_suffix + "]." + kChannel[channel];
    } else if (selector < 192) {
        if (relative) {
            throw std::runtime_error("unsupported Latte relative kcache access");
        }""")
rep("""        value = "c[" + std::to_string(selector - 256) + "]." +
                kChannel[channel];""", """        value = "c[" + std::to_string(selector - 256) + rel_suffix + "]." +
                kChannel[channel];""")

# 3) MOVA family in the ALU op2 switch (before the KILLE_INT case)
rep("""                case 0x46:
                    if (std::string_view(stage_) != "pixel") {""", """                case 0x15:
                case 0x16:
                case 0x18: {
                    // LOCAL: write the address register. 0x15 MOVA rounds to nearest, 0x16
                    // MOVA_FLOOR floors, 0x18 MOVA_INT takes the integer bit pattern.
                    const uint32_t ar_channel = (instruction.w1 >> 29) & 3u;
                    std::string index_expr =
                        opcode == 0x16 ? "int(floor(" + first + "))"
                        : opcode == 0x15 ? "int(roundEven(" + first + "))"
                                         : "floatBitsToInt(" + first + ")";
                    output << "  AR." << kChannel[ar_channel] << " = clamp(" << index_expr
                           << ", -256, 255);\\n";
                    continue;
                }
                case 0x46:
                    if (std::string_view(stage_) != "pixel") {""")

# 4) destination relative addressing
rep("""            if (encoding != 0 || ((instruction.w1 >> 4) & 1u) != 0) {
                writes << "  R[" << ((instruction.w1 >> 21) & 0x7Fu) << "]."
                       << kChannel[channel] << " = alu" << group_id << "_" << i
                       << ";\\n";
            }""", """            if (encoding != 0 || ((instruction.w1 >> 4) & 1u) != 0) {
                std::string destination = std::to_string((instruction.w1 >> 21) & 0x7Fu);
                if (((instruction.w1 >> 28) & 1u) != 0) {  // LOCAL: DST_REL
                    const uint32_t mode = (instruction.w0 >> 26) & 7u;
                    if (mode > 3) {
                        throw std::runtime_error("unsupported Latte LOOP index mode");
                    }
                    destination += std::string{" + AR."} + kChannel[mode];
                }
                writes << "  R[" << destination << "]." << kChannel[channel]
                       << " = alu" << group_id << "_" << i << ";\\n";
            }""")

# 5) declare AR in both shader prologs
rep("vec4 R[128]; vec4 PV=vec4(0.0); float PS=0.0;", "vec4 R[128]; vec4 PV=vec4(0.0); float PS=0.0; ivec4 AR=ivec4(0);", count=2)

p.write_text(s, encoding="utf-8")
print("address register support added")
