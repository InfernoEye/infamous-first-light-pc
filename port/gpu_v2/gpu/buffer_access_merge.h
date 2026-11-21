// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <algorithm>
#include <cstddef>

namespace iss::buffer_access {

// Merge pending read accesses into the same sorted union as the original
// LazyReadList::Merge. A single interval is already sorted: insert it directly
// into IntervalList (whose Add coalesces overlaps/touching ranges) rather than
// copying every existing interval and sorting the whole set.
//
// For two or more pending intervals the historical algorithm is unchanged:
// append the sorted list, sort by start, coalesce overlaps/touching intervals,
// and repopulate the list. No access/barrier range is discarded.
template <typename IntervalListT, typename PendingT>
void MergePendingReadRanges(IntervalListT& merged, PendingT& pending) {
    if (pending.empty()) {
        return;
    }
    if (pending.size() == 1) {
        merged.Add(pending.front());
        pending.clear();
        return;
    }

    pending.insert(pending.end(), merged.begin(), merged.end());
    using Range = typename PendingT::value_type;
    std::ranges::sort(pending, {}, &Range::start);
    merged.Clear();
    Range current = pending.front();
    for (std::size_t i = 1; i < pending.size(); ++i) {
        const auto& next = pending[i];
        if (next.start <= current.end) {
            current.end = std::max(current.end, next.end);
        } else {
            merged.Add(current);
            current = next;
        }
    }
    merged.Add(current);
    pending.clear();
}

} // namespace iss::buffer_access
