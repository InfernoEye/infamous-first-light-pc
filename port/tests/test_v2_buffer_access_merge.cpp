// SPDX-License-Identifier: GPL-2.0-or-later
// Standalone command: c++ -std=c++20 -O2 -Wall -Wextra -Werror -Iport/gpu_v2/gpu port/tests/test_v2_buffer_access_merge.cpp -o /tmp/first-light-buffer-ranges-test && /tmp/first-light-buffer-ranges-test
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <random>
#include <vector>

#include "buffer_access_merge.h"

namespace {
struct Range {
    std::uint64_t start{}, end{};
    friend bool operator==(const Range&, const Range&) = default;
};
struct SimpleIntervalList {
    std::vector<Range> items;
    auto begin() const { return items.begin(); }
    auto end() const { return items.end(); }
    void Clear() { items.clear(); }
    void Add(Range range) {
        if (range.start >= range.end) return;
        items.push_back(range);
        std::ranges::sort(items, {}, &Range::start);
        std::vector<Range> compact;
        for (const auto& r : items) {
            if (!compact.empty() && r.start <= compact.back().end) {
                compact.back().end = std::max(compact.back().end, r.end);
            } else {
                compact.push_back(r);
            }
        }
        items.swap(compact);
    }
    bool Overlaps(std::uint64_t start, std::uint64_t end) const {
        if (start >= end) return false;
        for (const auto& r : items) {
            if (r.start < end && start < r.end) return true;
        }
        return false;
    }
};

// Former v2 LazyReadList::Merge, preserved as a reference.
void OldMerge(SimpleIntervalList& merged, std::vector<Range>& pending) {
    if (pending.empty()) return;
    pending.insert(pending.end(), merged.begin(), merged.end());
    std::ranges::sort(pending, {}, &Range::start);
    merged.Clear();
    Range current = pending.front();
    for (std::size_t i = 1; i < pending.size(); ++i) {
        const auto& next = pending[i];
        if (next.start <= current.end) current.end = std::max(current.end, next.end);
        else { merged.Add(current); current = next; }
    }
    merged.Add(current);
    pending.clear();
}

void AssertSame(SimpleIntervalList& old_list, SimpleIntervalList& new_list,
                std::vector<Range>& old_pending, std::vector<Range>& new_pending) {
    OldMerge(old_list, old_pending);
    iss::buffer_access::MergePendingReadRanges(new_list, new_pending);
    assert(old_pending.empty() && new_pending.empty());
    assert(old_list.items == new_list.items);
}
}

int main() {
    SimpleIntervalList old_list, new_list;
    std::vector<Range> old_pending, new_pending;

    // A single pending range intersects, extends, adjoins or misses old ranges.
    for (const Range range : std::vector<Range>{{5, 10}, {20, 30}, {10, 20}, {40, 45},
                                                {12, 14}, {0, 2}, {80, 90}, {3, 82}}) {
        old_pending.push_back(range);
        new_pending.push_back(range);
        AssertSame(old_list, new_list, old_pending, new_pending);
    }
    // Equal and empty ranges are filtered at the Add call site in the renderer.
    assert(!old_list.Overlaps(30, 30));
    assert(old_list.Overlaps(5, 6));

    // Mixed additions and queries with 130,000 seeded operations.
    std::mt19937_64 rng{0xB00F50A7ULL};
    for (std::size_t n = 0; n < 130000; ++n) {
        const auto start = rng() % 16384;
        const auto end = start + 1 + rng() % 1024;
        if (n % 3 == 0 || n % 7 == 0) {
            // Original Overlaps calls Merge unconditionally; optimized calls
            // only when pending is nonempty.
            OldMerge(old_list, old_pending);
            if (!new_pending.empty()) {
                iss::buffer_access::MergePendingReadRanges(new_list, new_pending);
            }
            assert(old_list.Overlaps(start, end) == new_list.Overlaps(start, end));
            assert(old_list.items == new_list.items);
        } else {
            const Range added{start, end};
            old_pending.push_back(added);
            new_pending.push_back(added);
        }
    }
    AssertSame(old_list, new_list, old_pending, new_pending);

    // Larger pending batches, including unsorted ranges and touching edges.
    for (unsigned trial = 0; trial < 1000; ++trial) {
        old_list.Clear();
        new_list.Clear();
        const unsigned n = 2 + rng() % 64;
        for (unsigned i = 0; i < n; ++i) {
            const auto start = rng() % 50000;
            Range r{start, start + 1 + rng() % 1000};
            old_pending.push_back(r);
            new_pending.push_back(r);
        }
        AssertSame(old_list, new_list, old_pending, new_pending);
    }
}
