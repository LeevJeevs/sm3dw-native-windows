"""Adds a direct page table fast path to GuestMemory and caches two getenv() lookups.
Run: python -I apply_0003_fastmem.py <path-to-nWiiURuntime>. Each edit asserts its anchor occurs once."""
import sys, pathlib

root = pathlib.Path(sys.argv[1])

# ---------------- memory.cpp
p = root / "src/memory.cpp"
s = p.read_text(encoding="utf-8")
n1 = s.count('std::getenv("NWIIU_POOL_TRACE") != nullptr')
n2 = s.count('std::getenv("NWIIU_MATRIX_TRACE") != nullptr')
s = s.replace('std::getenv("NWIIU_POOL_TRACE") != nullptr', "pool_trace_enabled()")
s = s.replace('std::getenv("NWIIU_MATRIX_TRACE") != nullptr', "matrix_trace_enabled()")
a = "bool overlaps_matrix_trace(uint32_t address, uint64_t size) {"
assert s.count(a) == 1
s = s.replace(a, """// LOCAL: getenv is slow on Windows and these used to run on every guest store.
bool pool_trace_enabled() {
    static const bool enabled = std::getenv("NWIIU_POOL_TRACE") != nullptr;
    return enabled;
}
bool matrix_trace_enabled() {
    static const bool enabled = std::getenv("NWIIU_MATRIX_TRACE") != nullptr;
    return enabled;
}
""" + a)
a = """    auto [found, inserted] = pages_.try_emplace(address >> 12);
    if (inserted) {
        found->second.fill(0);
    }
    return found->second.data() + (address & (kPageSize - 1));"""
assert s.count(a) == 1
s = s.replace(a, """    auto [found, inserted] = pages_.try_emplace(address >> 12);
    if (inserted) {
        found->second.fill(0);
    }
    table_[address >> 12] = found->second.data();  // LOCAL: direct page table (see memory.h)
    return found->second.data() + (address & (kPageSize - 1));""")
a = "    mappings_.insert(next, Mapping{address, size, permissions});"
assert s.count(a) == 1
s = s.replace(a, a + """
    // LOCAL: pages fully inside this mapping get fast-path permission bits (1=read, 2=write).
    // Partially covered edge pages keep 0 and so keep taking the exact slow path.
    {
        const uint64_t first = (static_cast<uint64_t>(address) + kPageSize - 1) / kPageSize;
        const uint64_t last = end / kPageSize;  // exclusive
        const uint8_t bits = static_cast<uint8_t>((permissions.readable ? 1u : 0u) |
                                                  (permissions.writable ? 2u : 0u));
        for (uint64_t pg = first; pg < last; ++pg) {
            perm_[static_cast<size_t>(pg)] = bits;
        }
    }""")
p.write_text(s, encoding="utf-8")
print("getenv sites replaced:", n1, n2)

# ---------------- memory.h
p = root / "include/runtime/memory.h"
s = p.read_text(encoding="utf-8")

def rep(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)

rep("""    uint8_t read8(uint32_t address, uint32_t pc) const {
        if (flat_base_ != nullptr)
            return flat_base_[address];
        return read8_slow(address, pc);
    }""", """    uint8_t read8(uint32_t address, uint32_t pc) const {
        if (flat_base_ != nullptr)
            return flat_base_[address];
        const uint32_t pg = address >> 12;
        if ((perm_[pg] & 1u) != 0) {
            if (const uint8_t* p = table_[pg]) return p[address & 0xFFFu];
        }
        return read8_slow(address, pc);
    }""")
rep("""            return NWII_BSWAP16(raw);
        }
        return read16_slow(address, pc);""", """            return NWII_BSWAP16(raw);
        }
        const uint32_t pg = address >> 12, off = address & 0xFFFu;
        if (off <= 0xFFEu && (perm_[pg] & 1u) != 0) {
            if (const uint8_t* p = table_[pg]) {
                uint16_t raw;
                std::memcpy(&raw, p + off, sizeof raw);
                return NWII_BSWAP16(raw);
            }
        }
        return read16_slow(address, pc);""")
rep("""            return NWII_BSWAP32(raw);
        }
        return read32_slow(address, pc);""", """            return NWII_BSWAP32(raw);
        }
        const uint32_t pg = address >> 12, off = address & 0xFFFu;
        if (off <= 0xFFCu && (perm_[pg] & 1u) != 0) {
            if (const uint8_t* p = table_[pg]) {
                uint32_t raw;
                std::memcpy(&raw, p + off, sizeof raw);
                return NWII_BSWAP32(raw);
            }
        }
        return read32_slow(address, pc);""")
rep("""            return NWII_BSWAP64(raw);
        }
        return read64_slow(address, pc);""", """            return NWII_BSWAP64(raw);
        }
        const uint32_t pg = address >> 12, off = address & 0xFFFu;
        if (off <= 0xFF8u && (perm_[pg] & 1u) != 0) {
            if (const uint8_t* p = table_[pg]) {
                uint64_t raw;
                std::memcpy(&raw, p + off, sizeof raw);
                return NWII_BSWAP64(raw);
            }
        }
        return read64_slow(address, pc);""")
rep("""            mutable_flat()[address] = value;
            return;
        }
        write8_slow(address, value, pc);""", """            mutable_flat()[address] = value;
            return;
        }
        const uint32_t pg = address >> 12;
        if ((perm_[pg] & 2u) != 0) {
            if (uint8_t* p = table_[pg]) {
                p[address & 0xFFFu] = value;
                return;
            }
        }
        write8_slow(address, value, pc);""")
rep("""            std::memcpy(mutable_flat() + address, &raw, sizeof raw);
            return;
        }
        write16_slow(address, value, pc);""", """            std::memcpy(mutable_flat() + address, &raw, sizeof raw);
            return;
        }
        const uint32_t pg = address >> 12, off = address & 0xFFFu;
        if (off <= 0xFFEu && (perm_[pg] & 2u) != 0) {
            if (uint8_t* p = table_[pg]) {
                const uint16_t raw = NWII_BSWAP16(value);
                std::memcpy(p + off, &raw, sizeof raw);
                return;
            }
        }
        write16_slow(address, value, pc);""")
rep("""            std::memcpy(mutable_flat() + address, &raw, sizeof raw);
            return;
        }
        write32_slow(address, value, pc);""", """            std::memcpy(mutable_flat() + address, &raw, sizeof raw);
            return;
        }
        const uint32_t pg = address >> 12, off = address & 0xFFFu;
        if (off <= 0xFFCu && (perm_[pg] & 2u) != 0) {
            if (uint8_t* p = table_[pg]) {
                const uint32_t raw = NWII_BSWAP32(value);
                std::memcpy(p + off, &raw, sizeof raw);
                return;
            }
        }
        write32_slow(address, value, pc);""")
rep("""            std::memcpy(mutable_flat() + address, &raw, sizeof raw);
            return;
        }
        write64_slow(address, value, pc);""", """            std::memcpy(mutable_flat() + address, &raw, sizeof raw);
            return;
        }
        const uint32_t pg = address >> 12, off = address & 0xFFFu;
        if (off <= 0xFF8u && (perm_[pg] & 2u) != 0) {
            if (uint8_t* p = table_[pg]) {
                const uint64_t raw = NWII_BSWAP64(value);
                std::memcpy(p + off, &raw, sizeof raw);
                return;
            }
        }
        write64_slow(address, value, pc);""")
rep("""    GuestMemory() = default;
    explicit GuestMemory(GuestMemoryCallbacks callbacks);""", """    GuestMemory() = default;
    explicit GuestMemory(GuestMemoryCallbacks callbacks);
    // LOCAL: table_ holds pointers into pages_, so a copy would alias the source's pages.
    GuestMemory(const GuestMemory&) = delete;
    GuestMemory& operator=(const GuestMemory&) = delete;
    GuestMemory(GuestMemory&&) = default;
    GuestMemory& operator=(GuestMemory&&) = default;""")
rep("""    std::unordered_map<uint32_t, Page> pages_;
};""", """    std::unordered_map<uint32_t, Page> pages_;
    // LOCAL fast path: per 4 KiB page, permission bits (1=read, 2=write) for pages fully inside a
    // mapping, and a pointer to its resident backing page (nullptr until first touched). Anything
    // else falls through to the exact *_slow path, so fault behaviour is unchanged.
    std::vector<uint8_t> perm_ = std::vector<uint8_t>(size_t{1} << 20, 0);
    std::vector<uint8_t*> table_ = std::vector<uint8_t*>(size_t{1} << 20, nullptr);
};""")
p.write_text(s, encoding="utf-8")
print("memory.h patched")
