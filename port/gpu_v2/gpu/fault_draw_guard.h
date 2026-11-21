// SPDX-License-Identifier: GPL-2.0-or-later
// An opt-in diagnostic isolation predicate for the repeated First Light RADV hang.
// The blackbox marker is before the draw, so a match is NOT evidence that this
// shader is conclusively at fault. Do not enable the bypass during normal play.
#pragma once
#include <cstdint>

namespace iss::fault_draw_guard {
inline constexpr std::uint64_t VertexShader = 0x04e70448ull;
inline constexpr std::uint64_t FragmentShader = 0x258acc2bull;
inline constexpr std::uint32_t IndexCount = 3789;

constexpr bool Matches(bool indexed, std::uint32_t indices,
                       std::uint64_t vs, std::uint64_t ps) noexcept {
    return indexed && indices == IndexCount && vs == VertexShader && ps == FragmentShader;
}
} // namespace iss::fault_draw_guard
