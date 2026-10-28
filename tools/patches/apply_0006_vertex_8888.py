"""Adds Latte vertex data format 26 (FMT_8_8_8_8, one 32-bit word per vertex) for NORM numeric format.
 - latte_shader.cpp components(): 26 -> 4 (GLSL vec4)
 - wwhd_renderer.h gpu_vertex_format(): takes the whole input; 26 -> UBYTE4_NORM / BYTE4_NORM, 1 word.
SCALED/INT numeric formats are rejected (not guessed). Run: python -I apply_0006_vertex_8888.py <nWiiURuntime dir>"""
import sys, pathlib

root = pathlib.Path(sys.argv[1])

p = root / "src/latte_shader.cpp"
s = p.read_text(encoding="utf-8")
old = """    case 34:
    case 35: return 4;
    default:
        throw std::runtime_error("unsupported Latte vertex format " +"""
assert s.count(old) == 1
s = s.replace(old, """    case 34:
    case 35:
    case 26: return 4;  // LOCAL: 26 = FMT_8_8_8_8
    default:
        throw std::runtime_error("unsupported Latte vertex format " +""")
p.write_text(s, encoding="utf-8")

p = root / "include/runtime/wwhd_renderer.h"
s = p.read_text(encoding="utf-8")
i = s.index("gpu_vertex_format(uint32_t format) {")
# the declaration line begins with the return type on the previous line(s); patch the signature only
s = s.replace("gpu_vertex_format(uint32_t format) {", "gpu_vertex_format(const LatteVertexInput& input) {\n        const uint32_t format = input.data_format;", 1)
old = """        case 34:
        case 35: return {SDL_GPU_VERTEXELEMENTFORMAT_FLOAT4, 4};
        default:"""
assert s.count(old) == 1
s = s.replace(old, """        case 34:
        case 35: return {SDL_GPU_VERTEXELEMENTFORMAT_FLOAT4, 4};
        case 26:  // LOCAL: FMT_8_8_8_8 is one 32-bit word per vertex; normalized only.
            if (input.num_format != 0) {
                throw std::runtime_error("unsupported GPU 8_8_8_8 numeric format " +
                                         std::to_string(input.num_format));
            }
            return {input.is_signed ? SDL_GPU_VERTEXELEMENTFORMAT_BYTE4_NORM
                                    : SDL_GPU_VERTEXELEMENTFORMAT_UBYTE4_NORM,
                    1};
        default:""")
old = "gpu_vertex_format(input.data_format);"
assert s.count(old) == 1
s = s.replace(old, "gpu_vertex_format(input);")
p.write_text(s, encoding="utf-8")
print("vertex format 26 added")
