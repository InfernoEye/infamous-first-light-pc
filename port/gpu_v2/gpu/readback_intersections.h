// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <algorithm>
#include <cstdint>

namespace iss::readback {

// Dirty-page intervals from MemoryTracker::ForEachDownloadRange are ascending and
// non-overlapping (RegionManager walks page words in address order). The old
// FinishReadback loop visited every dirty interval for *each* GPU copy, even
// when most intervals were outside that copy.
//
// Visit exactly the same intersections, in the same order, but start at the
// first interval whose end is greater than the copy's start. No readback range,
// downloaded byte, host write, completion order, or GPU synchronization changes.
template <typename Ranges, typename Visit>
void ForEachCopyIntersection(const Ranges& dirty_pages, std::uint64_t copy_start,
                             std::uint64_t copy_end, Visit&& visit) {
    if (copy_start >= copy_end) {
        return;
    }
    const auto first = std::lower_bound(
        dirty_pages.begin(), dirty_pages.end(), copy_start,
        [](const auto& page, std::uint64_t address) { return page.second <= address; });
    for (auto it = first; it != dirty_pages.end() && it->first < copy_end; ++it) {
        const auto start = std::max(copy_start, it->first);
        const auto end = std::min(copy_end, it->second);
        if (start < end) {
            visit(start, end);
        }
    }
}

} // namespace iss::readback
