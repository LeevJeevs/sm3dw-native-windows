"""Caches Latte->SPIR-V translations in WwhdRenderer by content hash (and caches failures).
Run: python -I apply_0004_translation_cache.py <path-to-wwhd_renderer.h>"""
import sys, pathlib

p = pathlib.Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

old = """        const auto fs = bytes(state.fetch_shader_address, 0x08, 0x0C);
        return translate_latte({vs_regs, vs, ps_regs, ps, fs});
    }"""
new = """        const auto fs = bytes(state.fetch_shader_address, 0x08, 0x0C);
        // LOCAL: translate_latte runs a GLSL generator plus two shaderc compiles, and this used to
        // run on every draw call. Cache by a content hash (addresses can be reused for different
        // shaders), and remember failures so they are not retried per draw.
        uint64_t key = 1469598103934665603ull;  // FNV-1a
        const auto mix = [&key](const uint8_t* data, size_t size) {
            for (size_t i = 0; i < size; ++i) {
                key = (key ^ data[i]) * 1099511628211ull;
            }
            key = (key ^ 0xFFu) * 1099511628211ull;  // separator between inputs
        };
        mix(reinterpret_cast<const uint8_t*>(vs_regs.data()), vs_regs.size() * 4);
        mix(reinterpret_cast<const uint8_t*>(ps_regs.data()), ps_regs.size() * 4);
        mix(vs.data(), vs.size());
        mix(ps.data(), ps.size());
        mix(fs.data(), fs.size());
        if (const auto found = translation_cache_.find(key);
            found != translation_cache_.end()) {
            if (!found->second.has_value()) {
                throw std::runtime_error("cached Latte translation failure");
            }
            return *found->second;
        }
        try {
            auto result = translate_latte({vs_regs, vs, ps_regs, ps, fs});
            translation_cache_.emplace(key, result);
            return result;
        } catch (const std::exception&) {
            translation_cache_.emplace(key, std::nullopt);
            throw;
        }
    }"""
assert s.count(old) == 1
s = s.replace(old, new)

old = "    LatteTranslation translate_shader(const Gx2State& state) {"
assert s.count(old) == 1
s = s.replace(old, "    std::map<uint64_t, std::optional<LatteTranslation>> translation_cache_;\n\n" + old)

for inc in ("#include <optional>\n", "#include <map>\n"):
    if inc not in s:
        s = s.replace("#include <memory>\n", "#include <memory>\n" + inc, 1)
p.write_text(s, encoding="utf-8")
print("translation cache added")
