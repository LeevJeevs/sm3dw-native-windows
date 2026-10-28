"""Makes OS alarms actually fire. Previously OSSetPeriodicAlarm only stored the callback and schedule.
 - CafeCoreinit::service_alarms(): queues the guest callback (r3 = alarm) for every armed alarm whose
   next-fire time has passed; periodic alarms advance past 'now' (no catch-up flood), one-shots disarm.
 - adds OSSetAlarm (relative time), OSCancelAlarm, OSGetAlarmUserData
 - Machine::run calls service_alarms() once per scheduler iteration.
OSAlarmCallback is void(OSAlarm*, OSContext*); r4 (context) is not provided.
Run: python -I apply_0007_alarms.py <nWiiURuntime dir>"""
import sys, pathlib

root = pathlib.Path(sys.argv[1])

def patch(rel, edits):
    p = root / rel
    s = p.read_text(encoding="utf-8")
    for old, new in edits:
        assert s.count(old) == 1, (rel, s.count(old), old[:70])
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")

# ---------------- header
patch("include/runtime/cafe_coreinit.h", [
    ("    uint64_t ticks() const { return ticks_; }",
     "    uint64_t ticks() const { return ticks_; }\n"
     "    // LOCAL: fires due OS alarms (queues their guest callbacks). Called by Machine::run.\n"
     "    void service_alarms();"),
    ("    uint64_t ticks_{};",
     "    uint64_t ticks_{};\n    std::vector<uint32_t> armed_alarms_;"),
])

# ---------------- implementation
p = root / "src/cafe_coreinit.cpp"
s = p.read_text(encoding="utf-8")

old = """            abi::write_u32(memory_, alarm, abi::kAlarmStateOffset, 1, cpu.pc);
            abi::write_u32(memory_, alarm, abi::kAlarmContextOffset, 0,
                           cpu.pc);
            cpu.gpr[3] = 1;
            return HleAction::return_to_lr;
        });"""
assert s.count(old) == 1
new = """            abi::write_u32(memory_, alarm, abi::kAlarmStateOffset, 1, cpu.pc);
            abi::write_u32(memory_, alarm, abi::kAlarmContextOffset, 0,
                           cpu.pc);
            if (std::find(armed_alarms_.begin(), armed_alarms_.end(), alarm) ==
                armed_alarms_.end()) {
                armed_alarms_.push_back(alarm);
            }
            cpu.gpr[3] = 1;
            return HleAction::return_to_lr;
        });
    // LOCAL: OSSetAlarm(OSAlarm*, OSTime relativeTime (r4:r5), callback (r6)) -> BOOL.
    runtime.register_handler(
        "coreinit", "OSSetAlarm",
        [this](CPUContext& cpu, GuestMemory&) {
            const uint32_t alarm = cpu.gpr[3];
            validate_range(alarm, abi::kOsAlarmSize, cpu.pc, MemoryAccess::read);
            validate_range(alarm, abi::kOsAlarmSize, cpu.pc, MemoryAccess::write);
            if (abi::read_u32(memory_, alarm, abi::kAlarmTagOffset, cpu.pc) !=
                abi::kOsAlarmTag) {
                fault("invalid alarm", alarm, abi::kOsAlarmSize, cpu.pc,
                      MemoryAccess::read);
            }
            const uint64_t delay =
                static_cast<uint64_t>(cpu.gpr[4]) << 32 | cpu.gpr[5];
            const uint64_t now =
                machine_ == nullptr ? ticks_ : machine_->current_time_ticks();
            abi::write_u32(memory_, alarm, abi::kAlarmCallbackOffset, cpu.gpr[6], cpu.pc);
            abi::write_u64(memory_, alarm, abi::kAlarmNextFireOffset, now + delay, cpu.pc);
            abi::write_u64(memory_, alarm, abi::kAlarmPeriodOffset, 0, cpu.pc);
            abi::write_u32(memory_, alarm, abi::kAlarmStateOffset, 1, cpu.pc);
            if (std::find(armed_alarms_.begin(), armed_alarms_.end(), alarm) ==
                armed_alarms_.end()) {
                armed_alarms_.push_back(alarm);
            }
            cpu.gpr[3] = 1;
            return HleAction::return_to_lr;
        });
    // LOCAL: OSCancelAlarm(OSAlarm*) disarms; OSGetAlarmUserData(OSAlarm*) returns the stored value.
    runtime.register_handler(
        "coreinit", "OSCancelAlarm",
        [this](CPUContext& cpu, GuestMemory&) {
            const uint32_t alarm = cpu.gpr[3];
            validate_range(alarm, abi::kOsAlarmSize, cpu.pc, MemoryAccess::write);
            abi::write_u32(memory_, alarm, abi::kAlarmStateOffset, 0, cpu.pc);
            armed_alarms_.erase(
                std::remove(armed_alarms_.begin(), armed_alarms_.end(), alarm),
                armed_alarms_.end());
            return HleAction::return_to_lr;
        });
    runtime.register_handler(
        "coreinit", "OSGetAlarmUserData",
        [this](CPUContext& cpu, GuestMemory&) {
            const uint32_t alarm = cpu.gpr[3];
            validate_range(alarm, abi::kOsAlarmSize, cpu.pc, MemoryAccess::read);
            cpu.gpr[3] = abi::read_u32(memory_, alarm, abi::kAlarmUserDataOffset, cpu.pc);
            return HleAction::return_to_lr;
        });"""
s = s.replace(old, new)

# service_alarms definition: put before wait_event
old = "HleAction CafeCoreinit::wait_event(CPUContext& cpu) {"
assert s.count(old) == 1
s = s.replace(old, """void CafeCoreinit::service_alarms() {
    if (machine_ == nullptr || armed_alarms_.empty()) {
        return;
    }
    const uint64_t now = machine_->current_time_ticks();
    for (size_t index = 0; index < armed_alarms_.size();) {
        const uint32_t alarm = armed_alarms_[index];
        if (abi::read_u32(memory_, alarm, abi::kAlarmTagOffset, 0) != abi::kOsAlarmTag ||
            abi::read_u32(memory_, alarm, abi::kAlarmStateOffset, 0) != 1) {
            armed_alarms_.erase(armed_alarms_.begin() + static_cast<std::ptrdiff_t>(index));
            continue;
        }
        uint64_t next = abi::read_u64(memory_, alarm, abi::kAlarmNextFireOffset, 0);
        if (now >= next) {
            const uint32_t callback = abi::read_u32(memory_, alarm, abi::kAlarmCallbackOffset, 0);
            const uint64_t period = abi::read_u64(memory_, alarm, abi::kAlarmPeriodOffset, 0);
            machine_->queue_callback(callback, alarm, true);
            if (period != 0) {
                next += period * (1 + (now - next) / period);
                abi::write_u64(memory_, alarm, abi::kAlarmNextFireOffset, next, 0);
            } else {
                abi::write_u32(memory_, alarm, abi::kAlarmStateOffset, 0, 0);
                armed_alarms_.erase(armed_alarms_.begin() + static_cast<std::ptrdiff_t>(index));
                continue;
            }
        }
        ++index;
    }
}

""" + old)
if "#include <algorithm>" not in s:
    s = s.replace("#include", "#include <algorithm>\n#include", 1)
p.write_text(s, encoding="utf-8")

# ---------------- machine.cpp: call it each scheduler iteration
patch("src/machine.cpp", [
    ("        wake_elapsed_sleepers();\n        current_ = select_ready();",
     "        wake_elapsed_sleepers();\n        coreinit_.service_alarms();  // LOCAL: fire due OS alarms\n        current_ = select_ready();"),
])
print("alarms patched")
